#!/usr/bin/env python3
"""Acceptance checks on an isolated keeper directory, with no external work."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid


root = Path(sys.argv[2])
helper = root / '.mailbox.py'


def call(*args):
    result = subprocess.run([sys.executable, str(helper), *map(str, args)],
                            capture_output=True, text=True, timeout=5)
    return {'code': result.returncode, 'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip()}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sys.argv[1] == 'prepare':
    for name in ('drop', 'claimed'):
        (root / name).mkdir()
    prefix = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%SZ')
    note = prefix + '-codex-verification-' + uuid.uuid4().hex + '.txt'
    pending = prefix + '-codex-persistence-' + uuid.uuid4().hex + '.txt'
    source = root / '.fixture.txt'
    source.write_text('from: codex\nto: verification-only\nabout: disposable acceptance test\n\n'
                      'No external work is requested. UTF-8: café.\n')
    for filename in (note, pending):
        result = call('publish', root, filename, source)
        assert result['code'] == 0, result
    fixture = {'note': note, 'pending': pending, 'sha256': digest(source),
               'attempts': [uuid.uuid4().hex, uuid.uuid4().hex]}
    (root / 'fixture.json').write_text(json.dumps(fixture, indent=2) + '\n')
    print(json.dumps({'phase': 'prepare', **fixture}, indent=2))
elif sys.argv[1] == 'run':
    fixture = json.loads((root / 'fixture.json').read_text())
    note = fixture['note']
    assert digest(root / 'drop' / note) == fixture['sha256']
    assert digest(root / 'drop' / fixture['pending']) == fixture['sha256']
    assert not list((root / 'drop').glob('.posting-*'))
    processes = []
    for owner, attempt in zip(('verify-a', 'verify-b'), fixture['attempts']):
        args = [sys.executable, str(helper), 'claim', str(root), note, owner, attempt]
        processes.append(subprocess.Popen(args, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, text=True))
    race = []
    for process in processes:
        try:
            out, err = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise
        race.append({'code': process.returncode, 'stdout': out.strip(), 'stderr': err.strip()})
    assert sorted(r['code'] for r in race) == [0, 3], race
    winner = next(i for i, r in enumerate(race) if r['code'] == 0)
    owner = ('verify-a', 'verify-b')[winner]
    claim_path = Path(race[winner]['stdout'])
    assert digest(claim_path) == fixture['sha256']
    assert not (root / 'drop' / note).exists()
    assert len(list((root / 'claimed').iterdir())) == 1
    retry = call('claim', root, note, owner, fixture['attempts'][winner])
    assert retry['code'] == 0 and retry['stdout'] == str(claim_path), retry
    duplicate = call('publish', root, note, root / '.fixture.txt')
    assert duplicate['code'] == 1 and not (root / 'drop' / note).exists(), duplicate
    assert (root / '.published' / note).samefile(claim_path)
    malformed = root / '.malformed.txt'
    malformed.write_text('from: codex\nto: verification-only\nabout: malformed\nNO BLANK LINE\nbody\n')
    invalid = call('publish', root, 'invalid-' + uuid.uuid4().hex + '.txt', malformed)
    assert invalid['code'] == 1, invalid
    report = {'separate_shell_readback': True, 'race': race, 'winner_retry': retry,
              'consumed_id_republication': duplicate, 'malformed_note': invalid,
              'pending_note': fixture['pending'], 'work_note': note,
              'claim': str(claim_path), 'sha256': fixture['sha256'],
              'device_ids': [(root / name).stat().st_dev for name in ('drop', 'claimed', '.published')]}
    (root / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
else:
    raise SystemExit('Use prepare or run')
