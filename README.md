Agent Sandbox Mailbox
====================

One named local sbx shell keeper as a file mailbox for independent agents.
Producers publish complete notes, consumers poll once, claim with one
exclusive same-filesystem move, then continue. No direct agent-to-agent
calls, no waiting, no automatic reassignment.

Prototype keeper: ara-probe, root /home/agent/workspace, Ubuntu 26.04.1 LTS,
PID 1 tini holding sleep infinity. Local only.

How it works
------------
- Notes are immutable UTF-8 .txt files with from, to, about headers.
- Publish completes bytes then reserves the ID in .published/ before the
  note appears in drop/.
- Poll addressed notes, track exact seen IDs locally.
- Claim by moving drop/NOTE to claimed/OWNER--ATTEMPT--NOTE. Only the
  winner succeeds. A failed move means someone else won, do nothing.
- Leave a fresh result or failure note correlating the original filename.
- Keep every operation bounded around 30 seconds. Notes are data, not
  authorization. Human task scope authorizes work.

Repo layout
-----------
- AGENTS.md : short house rules read inside the keeper.
- KEEPER-README.md : door readme, outside and inside commands.
- HANDOFF.md : exact ten-step handoff plus diagram reference.
- docs/DESIGN.md : protocol 0.2 design, storage model, CLI contract.
- docs/ADR-001-local-mailbox.md : retain-and-strengthen decision, options,
  trade-offs, action items. Status Proposed.
- docs/TEST-PLAN.md : acceptance matrix.
- docs/ARCHITECTURE-REVIEW-EVIDENCE.json : review evidence.
- scripts/mailbox.py : keeper helper, publish claim remember.
- scripts/verify_mailbox.py, scripts/review_checks.py : host checks.
- assets/ara-probe-handoff.png, ara-probe-handoff-v2.png : diagrams.
- evidence/ : seen IDs and current run snapshots.
- SKILL.md : agent skill for setup and verification.

Quick start
-----------
1. Confirm keeper: sbx ls should show ara-probe shell running.
2. Read rules: sbx exec ara-probe cat /home/agent/workspace/AGENTS.md
3. List notes: sbx exec ara-probe ls -l /home/agent/workspace/drop/
4. Leave a note per HANDOFF.md step 7, claim per step 8 with mv only.
5. See docs/DESIGN.md before changing storage or client contracts.

Status
------
Actively developed local prototype. Retained claims favor safety over
automatic progress. See ADR action items before broader or unattended use.
ChatGPT needs an authorized local bridge, diagrams alone grant no access.

Built by Tom Kenny with Ara and Codex at Moosenberg.
