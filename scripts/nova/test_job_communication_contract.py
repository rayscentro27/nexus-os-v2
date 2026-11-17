from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs/architecture/NOVA_JOB_COMMUNICATION_CONTRACT.md"
text = DOC.read_text()
required = [
    "RECEIVED", "SUBMITTED", "QUEUED", "PLANNING", "APPROVAL_REQUIRED",
    "APPROVED", "REJECTED", "RUNNING", "COMPLETED", "BLOCKED", "FAILED",
    "human-readable subject", "Internal job IDs are secondary", "Format each update as", "<Subject> — <STATE>",
    "accepted count", "no job was created", "Approve", "Reject",
    "Request Changes", "primary intent", "completion-event/notification",
]
missing = [item for item in required if item.casefold() not in text.casefold()]
if missing:
    raise SystemExit("MISSING=" + ",".join(missing))
print("NOVA_JOB_COMMUNICATION_CONTRACT=PASS")
print("REQUIRED_CONCEPTS=" + str(len(required)))
