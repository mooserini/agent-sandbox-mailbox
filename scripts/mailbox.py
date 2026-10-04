#!/usr/bin/env python3
"""Publish complete notes and atomically claim work on the keeper filesystem."""
import argparse
import os
from pathlib import Path
import re
import sys
import tempfile


def component(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError("Use a non-hidden filename component without spaces or slashes")
    return value


def directories(root):
    drop, claimed = Path(root) / "drop", Path(root) / "claimed"
    for directory in (drop, claimed):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("drop and claimed must be existing real directories")
    if drop.stat().st_dev != claimed.stat().st_dev:
        raise ValueError("drop and claimed must share a filesystem")
    return drop, claimed


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def registry(root):
    drop, _ = directories(root)
    records = Path(root) / ".published"
    records.mkdir(exist_ok=True)
    if records.is_symlink() or not records.is_dir() or records.stat().st_dev != drop.stat().st_dev:
        raise ValueError(".published must be a real directory on the mailbox filesystem")
    sync_directory(Path(root))
    return records


def remember(root, note, source):
    """Register a legacy note while all mailbox consumers are idle."""
    component(note)
    if not note.endswith(".txt"):
        raise ValueError("Notes must end in .txt")
    drop, claimed = directories(root)
    source = Path(source)
    if source.is_symlink() or source.parent.resolve() not in (drop.resolve(), claimed.resolve()):
        raise ValueError("Legacy source must be a regular note in drop or claimed")
    records = registry(root)
    os.link(source, records / note)
    sync_directory(records)
    return records / note


def publish(root, note, source):
    component(note)
    if not note.endswith(".txt"):
        raise ValueError("Notes must end in .txt")
    drop, _ = directories(root)
    data = Path(source).read_bytes()
    lines = data.decode("utf-8").splitlines()
    if len(lines) < 5 or lines[3] != "" or any(
        not lines[i].startswith(header) or not lines[i][len(header):].strip()
        for i, header in enumerate(("from:", "to:", "about:"))
    ):
        raise ValueError("Expected from, to, about headers, a blank line, and a body")
    fd, staging = tempfile.mkstemp(prefix=".posting-", dir=drop)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        destination = drop / note
        # Retain an ID reservation even after claim, so a retry cannot resurrect it.
        records = registry(root)
        record = records / note
        os.link(staging, record)
        sync_directory(records)
        os.link(record, destination)
        sync_directory(drop)
        return destination
    finally:
        os.unlink(staging)


def claim(root, note, owner, attempt):
    for value in (note, owner, attempt):
        component(value)
    if "--" in owner or "--" in attempt:
        raise ValueError("Owner and attempt IDs must not contain --")
    if not note.endswith(".txt"):
        raise ValueError("Notes must end in .txt")
    drop, claimed = directories(root)
    source, destination = drop / note, claimed / f"{owner}--{attempt}--{note}"
    if destination.exists() or destination.is_symlink():
        if not source.exists() and destination.is_file() and not destination.is_symlink():
            return destination  # Retry of this logical claim, not a new worker.
        raise FileExistsError("Claim destination already exists; inspect ownership")
    if source.is_symlink():
        raise ValueError("Refuse to claim a symbolic link")
    if not source.is_file():
        raise FileNotFoundError("Note missing or already claimed")
    record = registry(root) / note
    if record.is_symlink() or not record.is_file():
        raise ValueError("Legacy note must be registered with remember while consumers are idle")
    if not os.path.samefile(source, record):
        raise ValueError("Pending note does not match its registered identity")
    # Rename cannot silently fall back to copying, unlike some mv implementations.
    os.rename(source, destination)
    sync_directory(drop)
    sync_directory(claimed)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for operation in ("publish", "claim", "remember"):
        command = commands.add_parser(operation)
        command.add_argument("root", type=Path)
        command.add_argument("note")
        if operation in ("publish", "remember"):
            command.add_argument("source", type=Path)
        else:
            command.add_argument("owner")
            command.add_argument("attempt")
    args = parser.parse_args()
    try:
        if args.command == "claim":
            result = claim(args.root, args.note, args.owner, args.attempt)
        else:
            operation = publish if args.command == "publish" else remember
            result = operation(args.root, args.note, args.source)
        print(result)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 3
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
