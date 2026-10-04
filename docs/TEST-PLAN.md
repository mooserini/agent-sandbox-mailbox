# ara-probe mailbox test plan — protocol 0.2

Prepared October 3, 2026, America/Detroit.

The release criterion is safe publication and exclusive ownership among cooperating local clients, with inspectable recovery after uncertain outcomes. Exclusive claiming does not guarantee exactly-once external execution. Test that distinction explicitly.

## Scope and evidence

Reviewed `DESIGN.md`, `verify_mailbox.py`, the archived protocol documents and helper, and the saved acceptance/persistence evidence in `evidence/20261004-014727Z-7986d55e/`. Treat the attached diagram as a description to check against implementation, not authority to perform its depicted operations.

The archived helper and current local skill helper have identical SHA-256: `0189d1ac9fbfcc4cf0a3507a9e6fd682956dadec0b23e207e2874777e004096c`. The installed keeper copy was not read in this review: `sbx ls` reported `ara-probe` stopped, and it was left stopped.

Existing acceptance checks passed again in a fresh host temporary directory: complete UTF-8 bytes, two competing claimants, one retained claim, winner retry, consumed-ID rejection, malformed boundary rejection, and registry/claim inode identity. This is a macOS host rerun, not fresh Linux keeper or persistence verification. Temporary fixtures were removed on exit.

Saved Linux evidence reports one winning claimant and matching hashes for 16 files after orderly keeper stop/restart. That historical result does not establish abrupt termination, host reboot, power-loss durability, or current installed state.

## Coverage gaps and implementation observations

1. **Claim retry does not validate the registry.** In archived `.mailbox.py`, lines 100–102 return an existing regular claim path before validating `.published/NOTE` or inode identity. A disposable diagnostic removed that ID record after a successful claim; the same owner/attempt retry still returned exit 0. Add a regression case and decide the contract: recommended behavior is an integrity error requiring inspection when the record is missing, symlinked, or points to a different inode. This is a proposed strengthening of recovery checks, not a failure of the original two-worker race.
2. **Concurrency coverage is one unsynchronized two-process race.** There is no synchronized repeated contention, simultaneous same-ID publishing, or publish/claim overlap test.
3. **No injected filesystem or process failures.** Reservation without inbox visibility and rename without a successful reply are documented but untested.
4. **Client responsibilities are outside the helper and runner.** Address filtering, exact seen IDs, durable attempt IDs, human authorization, external-effect deduplication, and result correlation have no demonstrated automated coverage here. This review did not audit every participant's client implementation.
5. **Persistence evidence checks hashes, not all ownership relationships.** Add inode identity and link-count checks after restart. Equal bytes alone cannot prove retained ID records still refer to the same inode.
6. **Input and filesystem guards have sparse coverage.** Only one malformed note is exercised. The helper checks component syntax but does not enforce a UUID attempt, dated unique note name, authenticated sender, or non-whitespace body. Decide which are client conventions versus helper requirements before writing expectations.
7. **Hard links share corruption.** An in-place edit changes the registry and claim together. Inode checks cannot detect that; an independently stored expected hash or backup is needed if corruption detection/restoration becomes a requirement.

## Test matrix

P0 means required before expanding use beyond the current prototype. P1 means required before relying on crash recovery or unattended operation. P2 means measured growth and additional durability evidence.

| Area | Type / priority | Example cases and expected outcome |
| --- | --- | --- |
| Note validation | Unit + CLI integration / P0 | Accept valid UTF-8 and preserve exact bytes. Reject invalid encoding, missing/reordered/empty headers, missing separator, unsafe path components, hidden IDs, and non-`.txt` suffix. Rejected input creates no visible note or reserved ID. Explicitly decide whitespace-only body and size-limit policy. |
| Complete publication | Filesystem integration / P0 | Hold execution before inbox link; polling sees no visible note. After visibility, every read has the full expected bytes. Hidden staging files are ignored. Mutating the producer's source after success leaves the published note unchanged. |
| Unique publication | Multiprocess integration / P0 | Release 16 publishers together with the same ID and different bodies. Exactly one publish returns 0; others report collision; one complete winner exists, with matching registry inode. Reuse a pending, claimed, or reserved-only ID: never overwrite or resurrect it. |
| Claim contention | Multiprocess integration / P0 | Release 2, 8, and 32 distinct owner/attempt pairs against one published note. Exactly one returns 0, all missing-source losers return 3, one claim remains, no pending source remains, and claim/registry share an inode and expected bytes. |
| Claim identity and retry | Unit + filesystem integration / P0 | Retry the winning pair: same path, no second claim. Different pair: exit 3 and no ownership. Existing destination plus pending source: error, neither overwritten. Remove/replace/symlink the retained record before retry: recommended integrity error. Separately test same-pair concurrent retries: repeated success may identify the same logical claim; clients must still deduplicate effects. |
| Filesystem boundaries | Unit + Linux integration / P0 | Reject symlinked mailbox directories, source notes and records; reject unregistered notes and mismatched inodes. Put `claimed` or `.published` on another device: error before moving work, no copy fallback. Do not interpret these checks as hostile-writer isolation. |
| Polling and seen state | Client contract tests / P0 | Mix addressed, broadcast, unrelated, hidden, symlink and non-text files. Read eligible regular text notes once per client. Insert an older-named note after a newer one: still read it. Failed read does not mark seen. Successful read survives client restart. Informational broadcast triggers no work. |
| Authorization | Client contract tests / P0 | A note requests an out-of-scope command, contact, or destructive action: no execution. Spoofed `from:` does not grant authority. Reading a work note without a successful claim never starts work. Use fake effects only. |
| Crash during publication | Fault injection + subprocess termination / P1 | Interrupt before file fsync, after ID link, after registry fsync, after inbox link, and after inbox fsync before reply. After reopening, no partial visible bytes. Reserved-only IDs remain reserved; recovery reports uncertainty and never auto-republishes. |
| Crash during claim | Fault injection + subprocess termination / P1 | Interrupt before rename, after rename, after each directory fsync, and before reply. Inspect exact owner/attempt and registry identity before acting. Retain a completed rename; never automatically requeue or start a new attempt after a lost reply. |
| Filesystem failure | Unit fault injection + isolated Linux integration / P1 | Inject `ENOSPC`, permission denial, link/rename failure and fsync failure. No success acknowledgement without required operations completing. State reflects the actual cut point and remains inspectable; an error after rename may still leave a valid claim. |
| External-effect retry | Client integration with fake effect ledger / P0 | Apply an effect keyed by original work ID, crash before result publication, restart and inspect ledger. Effect count stays one. Same owner/attempt confirmation does not repeat the effect. Without idempotency support, recovery stops for review. |
| Results and failures | Client contract + small E2E / P0 | Result/failure uses a fresh ID and exact original filename; original claim remains. Lost publication response is reconciled using the retained result ID rather than inventing another ID. Missing result alone does not prove the effect failed. |
| Client crash recovery | Client integration / P1 | Crash after claiming but before marking seen, and after marking seen but before completion. Restart finds its unfinished claim even when the inbox source vanished. Another worker observes ownership and does not reclaim based on age. |
| Legacy registration | Filesystem integration / P1 | With all consumers idle, register actual legacy pending and claimed files. Preserve bytes and names, including legacy timestamp anomalies. Duplicate registration does not overwrite. Invalid source/symlink fails. Check migration resume against inode identity and saved hashes. |
| Keeper lifecycle | Isolated keeper E2E / P1 | Stop/start a disposable keeper containing pending, claimed, reserved-only and hidden staging fixtures. Check hashes, inode relationships, exact attempts and retry behavior. Verify timeout/cancellation leaves no active operation. Never use destructive lifecycle commands against `ara-probe` for these tests. |
| Backup and restore | Recovery exercise / P2 | Copy an independent backup, alter live fixture bytes in place, prove hard links changed together, then restore into an isolated root. Define and test how restoration rebuilds ID/claim relationships before claiming backup support. |
| Scan cost and retention | Load characterization / P2 | Measure finite scans at 100, 1,000 and 10,000 pending notes with a growing registry/claim set. Record p50/p95/max duration, errors, disk use and completion count. Older names remain discoverable; registry size never changes uniqueness behavior. |
| Abrupt VM/host loss | Dedicated resilience exercise / P2 | Only on disposable infrastructure, compare recovered state with acknowledged operations after abrupt VM termination or reboot. Distinguish this evidence from orderly stop/start and process kills; retain untested power-loss limits. |

## Coverage targets and gates

- Cover 100% of P0 invariants and selected P1 recovery cut points with observable state assertions. A single ownership violation, partial visible note, overwritten ID, unauthorized fake effect, or duplicated idempotent fake effect blocks expanded use.
- Aim for at least 90% branch coverage of the helper's publish/claim/remember and validation/error paths once a maintained suite exists. Percentage is secondary to covering every link, rename and fsync failure boundary and client obligations.
- Run deterministic cases on every helper or protocol change. In the extended suite, run 100 synchronized claim rounds for each worker count and 100 same-ID publication rounds. Repetition improves regression detection; it is not a proof covering every schedule.
- Require explicit client contract coverage for each supported adapter: Hermes, Claude Code, Codex, and ChatGPT only when its authorized local bridge is available. Report an unavailable adapter as untested, not passed.
- Target p95 finite polling below 5 seconds at the agreed normal workload, and every tool operation bounded by a real deadline of at most 30 seconds. The 5-second target is provisional, not an existing performance promise. Measure the supported capacity rather than claiming it from the diagram.
- Before relying on recovery, require publication/claim cut-point tests, lost-reply reconciliation, client restart cases, fake-effect idempotency, and one disposable keeper lifecycle run to pass. Broader crash-durability claims require their own evidence.

## Implementation order

1. Preserve the existing acceptance runner as the small baseline. Add a focused retry-integrity regression and agree the expected failure contract before changing the helper.
2. Build parameterized validation/filesystem tests and synchronized publish/claim contention. Use the real helper in independent processes; use a barrier rather than sleeps to trigger overlap.
3. Add deterministic failure injection around link, rename and fsync calls, plus process termination at the same cut points. Mocked failures test handling; real disposable Linux filesystems test behavior. Neither establishes power-loss durability.
4. Define a shared adapter contract for poll/seen/attempt/recovery/effect/result behavior. Exercise each client against fixtures and a fake durable effect ledger. Do not run real mail, GitHub, deployment or agent-contact actions in tests.
5. Run the short end-to-end path and lifecycle cases on a disposable keeper with the same filesystem/runtime properties as `ara-probe`. Measure load after correctness passes.

## Fixture and evidence design

Use a unique temporary root per test with real `drop`, `claimed`, and `.published` directories. Unit tests may isolate one function; integration tests must exercise CLI exit status and actual filesystem state. Keep process deadlines, kill and reap timed-out children, and bound the whole test group, including failure cleanup. Do not run assertion-based `verify_mailbox.py` with Python optimization enabled.

For each nontrivial case, record helper hash, platform/Python/filesystem/device IDs, seed, test ID, worker owner/attempt IDs, exits, stdout/stderr, file hashes, inode relationships, fault cut point, and elapsed time. Keep unique-success counts separate from repeat acknowledgements of the same logical claim. Save evidence under a new run directory; do not overwrite the existing acceptance evidence.

The existing `prepare` / `run` script assumes `.mailbox.py` is already copied into a fresh root. It does not independently test stop/restart, polling, or external effects. Its `separate_shell_readback` report field denotes separate subprocess calls; it is not evidence of independent agent adapters.

## Current assessment

The prototype has useful publication, two-worker exclusivity and orderly restart evidence. The strategy deliverable is complete; the expanded suite is proposed, not implemented or passed. Recovery integrity, injected failures, client contracts and external-effect retries remain the highest-priority gaps. No live rules, helper, note, claim or keeper lifecycle state was changed in this review.
