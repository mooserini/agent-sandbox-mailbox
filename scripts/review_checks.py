#!/usr/bin/env python3
"""Architecture diagnostics on archived bytes in disposable host fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid


BASE = Path(__file__).resolve().parent
HELPER = BASE / 'evidence/20261004-014727Z-7986d55e/candidate/.mailbox.py'
spec = importlib.util.spec_from_file_location('archived_mailbox', HELPER)
mailbox = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mailbox)


def fixture(parent):
    root = parent / uuid.uuid4().hex
    root.mkdir()
    for name in ('drop', 'claimed'):
        (root / name).mkdir()
    source = root / '.source'
    source.write_text('from: review\nto: verification-only\nabout: architecture diagnostic\n\nNo external work.\n')
    mailbox.publish(root, 'work.txt', source)
    return root


report = {
    'platform': platform.platform(),
    'python': sys.version,
    'helper': str(HELPER),
    'helper_sha256': hashlib.sha256(HELPER.read_bytes()).hexdigest(),
    'scope': 'Disposable host fixtures; archived helper; no keeper operations',
}
with tempfile.TemporaryDirectory(prefix='ara-architecture-') as temp:
    parent = Path(temp)
    baseline = parent / 'baseline'
    baseline.mkdir()
    shutil.copy2(HELPER, baseline / '.mailbox.py')
    for phase in ('prepare', 'run'):
        result = subprocess.run(
            [sys.executable, str(BASE / 'verify_mailbox.py'), phase, str(baseline)],
            capture_output=True, text=True, timeout=25,
        )
        if result.returncode:
            raise RuntimeError(result.stderr)
    report['baseline'] = json.loads(result.stdout)

    checks = {}
    for alteration in ('missing_record', 'different_inode', 'symlink_record'):
        root = fixture(parent)
        attempt = uuid.uuid4().hex
        claim = mailbox.claim(root, 'work.txt', 'review', attempt)
        record = root / '.published/work.txt'
        record.unlink()
        if alteration == 'different_inode':
            record.write_bytes(claim.read_bytes())
        elif alteration == 'symlink_record':
            record.symlink_to(claim)
        retry = mailbox.claim(root, 'work.txt', 'review', attempt)
        checks[alteration] = {'retry_returned_same_path': retry == claim}
        if retry != claim:
            raise RuntimeError('Archived behavior changed; review expectations')
    report['retry_integrity_diagnostics'] = checks

    root = fixture(parent)
    attempt = uuid.uuid4().hex
    original_sync = mailbox.sync_directory
    def fail_after_rename(path):
        if path == root / 'drop':
            raise OSError('Injected directory fsync failure after rename')
        original_sync(path)
    mailbox.sync_directory = fail_after_rename
    try:
        mailbox.claim(root, 'work.txt', 'review', attempt)
        raise RuntimeError('Expected injected error')
    except OSError as error:
        first_error = str(error)
    finally:
        mailbox.sync_directory = original_sync
    syncs = []
    def record_sync(path):
        syncs.append(str(path))
        original_sync(path)
    mailbox.sync_directory = record_sync
    try:
        recovered = mailbox.claim(root, 'work.txt', 'review', attempt)
    finally:
        mailbox.sync_directory = original_sync
    report['post_rename_fsync_diagnostic'] = {
        'initial_error': first_error,
        'claim_retained': recovered.is_file(),
        'retry_sync_calls': syncs,
        'interpretation': 'Retry identifies ownership without repeating directory fsync; no power-loss conclusion',
    }
print(json.dumps(report, indent=2))
