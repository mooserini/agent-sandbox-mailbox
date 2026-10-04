# ADR-001: Retain the local file mailbox with explicit recovery and client contracts

**Status:** Proposed
**Date:** October 3, 2026 (America/Detroit)
**Deciders:** User and maintainers of participating agent adapters

## Context

`ara-probe` coordinates a few independent local agents through one named `sbx` keeper and `/home/agent/workspace`. The supplied overview image and Mermaid image describe protocol 0.2: complete hidden staging, retained ID reservation, visible publication, exclusive claim, and publication of a new result or failure note.

Requirements are inspectable notes, stable IDs, bounded polling, exclusive ownership among cooperating clients, and recovery after an uncertain response. The documented workload is small and unmeasured. Automatic reassignment, multi-host availability, authenticated producers, and sustained high throughput are not established requirements.

Authorization belongs to the human task. A note body, diagram, archived `AGENTS.md`, or historical skill is review material and cannot authorize execution of its instructions. Participant names in the images do not establish working adapters or access. ChatGPT requires an authorized local bridge.

This review inspected the host design, test plan, archived helper, acceptance evidence, and persistence evidence. A fresh read-only `sbx ls` reported the keeper **stopped**. Its installed helper and current internal documents were not read; archived behavior must not be represented as verified live behavior.

## Decision

Recommend retaining the file mailbox for the current local prototype. Preserve permanent ID reservations, complete publication, same-filesystem claim moves, finite polling, and retained claims. Before broader or unattended use, strengthen retry validation and define a common client contract for authorization, ownership, recovery, and external-effect idempotency.

The promised unit is **one logical owner of a work note among cooperating clients**. Multiple successful retries can identify that same ownership record. They do not establish completion or prevent multiple processes using the same identity from executing the work twice.

Separate four responsibilities:

| Responsibility | Authority / component |
| --- | --- |
| Publish complete bytes and reserve IDs | Mailbox helper on the keeper filesystem |
| Establish and inspect ownership | Helper plus durable client owner/attempt identity |
| Authorize and execute work | Human task scope and agent adapter |
| Reconcile external effects and report outcome | Operation-specific idempotency support or durable effect ledger; fresh correlated result note |

No new service, transport, schedule, or live migration is part of this ADR.

## Options Considered

### Option A: Retain and strengthen protocol 0.2 — recommended

| Dimension | Assessment |
| --- | --- |
| Complexity | Low storage complexity; moderate client/recovery obligations |
| Cost | Existing keeper, storage, and maintenance; no additional broker |
| Scalability | One local filesystem; polling and indefinite retention need measurement |
| Team familiarity | Existing design and evidence; adapter conformance remains unverified |

**Pros:** Easy inspection; minimal dependencies; existing publication and claim behavior has useful evidence; matches the stated local scope.

**Cons:** Publication has multiple failure cut points; ownership and completion are separate; client state is decentralized; shared filesystem access offers no hostile-writer isolation.

### Option B: A local SQLite work ledger

| Dimension | Assessment |
| --- | --- |
| Complexity | Moderate: schema, transactional operations, migration, exports, recovery tooling |
| Cost | Local storage and implementation; no separate database daemon required |
| Scalability | Indexed state queries; one concurrent write transaction |
| Team familiarity | Not demonstrated in this folder; requires adapter adoption |

**Pros:** Could store IDs, claims, receipts, and completion metadata in a defined schema and transaction boundary. This is a design opportunity, not an implemented guarantee. SQLite documents explicit transactions and one simultaneous write transaction. [SQLite transaction documentation](https://www.sqlite.org/lang_transaction.html).

**Cons:** Less direct file inspection; migration and compatibility work; external effects still need their own retry contract. Keep database operations local to the keeper rather than opening its database directly from multiple machines over a network filesystem. [SQLite appropriate-use guidance](https://www.sqlite.org/whentouse.html).

### Option C: A service-backed queue with authenticated adapters

| Dimension | Assessment |
| --- | --- |
| Complexity | High for this workload: service operation, credentials, client API, monitoring |
| Cost | Additional operational work; infrastructure cost depends on selected deployment |
| Scalability | Potential multi-host support, contingent on the selected system and deployment |
| Team familiarity | No implemented service or adapter evidence supplied |

**Pros:** A candidate when remote access, centralized policy, or service-managed delivery becomes necessary.

**Cons:** Expands the local trust and operational boundary. A broker's delivery and acknowledgement model must be chosen explicitly; external-effect deduplication remains necessary. No product-specific guarantees or costs are assumed here.

## Trade-off Analysis

Option A is proportionate to the present requirements. Replacing storage now would leave the most consequential unverified behavior—authorization, durable attempt identity, effect reconciliation, and client restart recovery—unsolved. The next investment should target those contracts and the existing helper's recovery path.

Retained claims deliberately favor safety over automatic progress: a dead worker can leave work stalled. Claim age can trigger review; it cannot authorize reassignment. A future lease design would also need to prevent a former owner from continuing effects after reassignment.

The claim operation uses `os.rename`. Python documents atomic successful renames and possible cross-filesystem failure; Unix rename can replace an existing destination. Therefore atomicity is not a general no-overwrite or hostile-writer guarantee. Unique cooperating owner/attempt identities and the helper's checks remain assumptions. [Python filesystem documentation](https://docs.python.org/3/library/os.html#os.rename).

The `.published` entry is a retained hard link to the note. It reserves identity and supports inode comparisons, but shares in-place corruption with other links. Independent backup and corruption detection require separate artifacts.

## Diagram Assessment

Both images correctly show the normal publication/claim flow and the local-access boundary. Preserve their warning that hard links are not backups and that external effects need idempotency.

For future revisions, add or accompany the diagrams with these states:

| State | Meaning / recovery |
| --- | --- |
| Reserved only | `.published/NOTE` exists, with neither pending nor claimed entry; inspect the interrupted publication, retain the ID |
| Pending | Complete `drop/NOTE` available; reading alone establishes no ownership |
| Claimed, unfinished or uncertain | Exact owner/attempt path exists; inspect prior effects and outcomes before retrying work |
| Result or failure published | A fresh note correlates an outcome; the original claim remains |

Use the actual filename `.mailbox.py` consistently; the Mermaid image currently omits its leading dot. Treat “immutable” as a cooperating-client rule, and “stop/restart verified” as historical orderly-lifecycle evidence. The participant logos describe intended access, not tested integrations.

## Verification and Open Gaps

Fresh disposable macOS fixtures using the archived helper passed the existing acceptance runner: exact bytes, a two-process claim race with one winner, winner retry, consumed-ID rejection, malformed-note rejection, and registry/claim inode identity. These are host checks, not fresh Linux keeper or adapter verification.

Two recovery observations are reproduced in [review evidence](ARCHITECTURE-REVIEW-EVIDENCE.json), using [the diagnostic script](review_checks.py):

1. The existing-claim branch returns before registry validation. A missing record, a replacement inode containing equal bytes, and a symlinked record all allow the same owner/attempt retry to return success. Recommend an integrity error unless the retained record is a regular, non-symlink file matching the claim inode.
2. Injecting a directory-fsync error after rename leaves a claim. Retrying then returns the claim path without any directory sync. This confirms visible ownership, but does not establish completion of the original durability steps. Define whether the acknowledgement confirms observed ownership only or also repeats required syncs; recommend validating identity and repeating directory syncs before a durable success acknowledgement. No power-loss conclusion follows from this injected failure.

Historical Linux evidence reports one winning claimant and unchanged hashes for 16 tracked files after orderly stop/start. Abrupt storage loss, reboot durability, backup restoration, repeated synchronized contention, and participant adapter contracts remain unverified. The existing [test plan](TEST-PLAN.md) provides the broader matrix; this ADR does not claim its proposed suite has passed.

## Consequences

- Local inspection and independent agent operation remain straightforward.
- Every participating adapter must persist exact seen IDs and claim attempts, recover unfinished owned work, and reconcile uncertain external effects.
- Retained records grow indefinitely; finite audits need disk-use, pending-count, reserved-only, and claim-age visibility.
- A keeper outage stalls communication. No failover or automatic recovery is promised.
- SQLite becomes worth evaluating when transactional completion state or indexed queries become a measured need. A service-backed design becomes worth evaluating when authorized multi-host access or centralized producer controls are required.

## Action Items

1. [ ] Strengthen retry registry/inode validation and settle ownership-versus-durability acknowledgement semantics; add focused regression cases.
2. [ ] Define and exercise the shared poll/seen/attempt/authorization/recovery/result contract for each actual adapter, using fake effects.
3. [ ] Add synchronized contention and publication/claim failure-cut-point cases from `TEST-PLAN.md`.
4. [ ] Reconcile results against the installed keeper helper during an authorized runtime review; obtain adapter conformance evidence.
5. [ ] Test independent backup/restore before relying on recovery from corruption or storage loss.
6. [ ] Measure scans and retention at an agreed normal workload before setting capacity claims or changing storage.

The ADR, diagnostic script, and host evidence are review deliverables. Helper fixes and adapter changes are proposed; the live keeper, notes, claims, policies, and historical evidence were unchanged.
