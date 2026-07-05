# Nexus Telegram — Token Rotation Required

**Generated**: 2026-07-05
**Status**: ROTATION_REQUIRED

## What Happened

During Telegram setup, the bot token was exposed in environment exports and test commands. The current token must be revoked and replaced.

## Exposed Token

- Token preview: 893561...hXjw
- Bot: NexusHermes27bot (ID: 8935612290)
- Private chat resolved: 1288928049 (Ray Davis @rayscentro)

## Rotation Steps

### Step 1: Revoke Exposed Token

1. Open BotFather in Telegram: @BotFather
2. Send `/mybots`
3. Select `NexusHermes27bot`
4. Send `/revoke`
5. Confirm revocation

### Step 2: Generate Fresh Token

1. In BotFather, send `/token`
2. Select `NexusHermes27bot`
3. Copy the new token

### Step 3: Set New Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="NEW_TOKEN_HERE"
export TELEGRAM_ADMIN_CHAT_ID="1288928049"
export TELEGRAM_ALLOWED_CHAT_IDS="1288928049"
export TELEGRAM_MODE="TELEGRAM_OPERATOR"
```

### Step 4: Verify New Token

```bash
curl -sS "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

Expected: `{"ok":true, ...}`

### Step 5: Verify Bridge

```bash
python3 scripts/telegram/nexus_telegram_bridge.py --dry-run
```

### Step 6: Verify Once

```bash
python3 scripts/telegram/nexus_telegram_bridge.py --once
```

### Step 7: Verify Active Runner

```bash
python3 scripts/operations/nexus_active_operator_runner.py --once
```

### Step 8: Confirm Receipt

Check that a Telegram message arrives at Ray's private chat.

## Persisting Environment Variables

### Option A: Shell Profile (Simple)

Add to `~/.zshrc` or `~/.bashrc`:

```bash
export TELEGRAM_BOT_TOKEN="NEW_TOKEN_HERE"
export TELEGRAM_ADMIN_CHAT_ID="1288928049"
export TELEGRAM_ALLOWED_CHAT_IDS="1288928049"
export TELEGRAM_MODE="TELEGRAM_OPERATOR"
```

Then: `source ~/.zshrc`

### Option B: Launchctl plist (macOS)

Create `~/Library/LaunchAgents/com.nexus.telegram.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nexus.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>bash</string>
        <string>-c</string>
        <string>export TELEGRAM_BOT_TOKEN="NEW_TOKEN_HERE"; export TELEGRAM_ADMIN_CHAT_ID="1288928049"; export TELEGRAM_ALLOWED_CHAT_IDS="1288928049"; export TELEGRAM_MODE="TELEGRAM_OPERATOR"; cd ~/nexus-os-v2; python3 scripts/telegram/nexus_telegram_bridge.py --once</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
```

### Option C: Server/Oracle VM

Set env vars in the VM's startup script or systemd service file.

### Option D: Netlify

Netlify env does not run Python bridge continuously. Use Netlify only for static frontend. Telegram bridge must run on a machine with Python.

## Post-Rotation Checklist

- [ ] Old token revoked in BotFather
- [ ] New token generated
- [ ] New token exported in shell
- [ ] curl getMe returns ok=true
- [ ] Bridge --dry-run works
- [ ] Bridge --once works
- [ ] Active runner --once works
- [ ] Telegram message arrives at Ray's chat
- [ ] Old token no longer works (verify with curl)
