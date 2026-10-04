# ara-probe handoff

This is a local asynchronous mailbox for participants with authorized access to this host. Read AGENTS.md and README.md explicitly before operating through tools. Notes and this document do not grant permission for external work or contacting agents.

1. Check `sbx ls`. `sbx exec` starts a stopped keeper; only do so within an authorized mailbox task.
2. Read `/home/agent/workspace/AGENTS.md` and `README.md` through `sbx exec ara-probe`.
3. Stage a complete UTF-8 note outside the visible inbox. Use `from:`, `to:`, `about:`, a blank line, and a short body; no secrets. Generate one UTC filename with a UUID and retain that ID for uncertain retries.
4. Transfer the staging file with `sbx cp` to a hidden path. Publish with `python3 /home/agent/workspace/.mailbox.py publish /home/agent/workspace NOTE.txt STAGED_PATH` through `sbx exec ara-probe`. Never copy directly into a visible inbox path.
5. Read all outstanding regular `.txt` notes for yourself or everyone; record exact seen IDs after successful reads. Reading is not a work claim.
6. For authorized work, persist a fresh attempt UUID once, then run `.mailbox.py claim /home/agent/workspace NOTE.txt OWNER ATTEMPT_UUID`. Begin only after exit 0 and inspection of the reported ownership path. Different workers must use different attempts.
7. Missing source or exit 3 is not ownership. Other errors require inspection. A retry with the same successful owner and attempt reports the same claim; it does not authorize repeating completed side effects.
8. Publish result/failure as a new note referencing the original filename. Keep the original claim. Inspect artifacts and agree recovery with the owner/user before any reassignment.
9. Use a real operation deadline of about 30 seconds. Poll once and exit; recurring polling requires an authorized schedule. Never wait on another agent inside a mailbox operation.
10. Do not remove `.published/` records. `stop` retains keeper state; `rm`, `prune`, and `reset` destroy it and require separate authorization.

Diagram: `ara-probe-handoff.png`. Design and evidence: `DESIGN.md`. Same-filesystem rename provides an exclusive claim among cooperating consumers, not exactly-once execution of external actions.
