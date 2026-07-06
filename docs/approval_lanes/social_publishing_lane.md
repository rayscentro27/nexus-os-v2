# Social Publishing Lane

**Status**: SOCIAL_PUBLISHING_APPROVAL_GATED_READY

## Workflow

1. Create content (Nexus creates approval packet)
2. Ray Review (via Telegram /review)
3. Approve (via Telegram /approve SOCIAL-XXX)
4. Publish to approved account
5. Write receipt
6. Log performance

## Supported Platforms

- Facebook (supported)
- Instagram (supported)
- TikTok (pending)
- YouTube (pending)
- X/Twitter (pending)
- LinkedIn (pending)

## Commands

```bash
# Create content
python3 scripts/approval_lanes/nexus_social_publishing_lane.py create <platform> <type> <caption> [media_path]

# Approve and publish
python3 scripts/approval_lanes/nexus_social_publishing_lane.py approve <item_id>

# Request revision
python3 scripts/approval_lanes/nexus_social_publishing_lane.py revise <item_id> <feedback>

# Check status
python3 scripts/approval_lanes/nexus_social_publishing_lane.py status <item_id>
```

## Revision Memory

Supports: not creative enough, needs animation, needs avatar, stronger hook, better CTA, QR/link placement, compliance rewrite
