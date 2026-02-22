# Discord Bot Setup Guide

## Bot Token Configuration

**IMPORTANT:** The Discord bot token must be set as an environment variable. Never commit tokens to the repository.

### Setting the Token

Obtain your bot token from the [Discord Developer Portal](https://discord.com/developers/applications) → Your App → Bot → Reset Token / Copy.

**Windows PowerShell:**
```powershell
# Set for current session (replace YOUR_TOKEN with your actual token)
$env:DISCORD_BOT_TOKEN = "YOUR_TOKEN"

# Set permanently (User-level)
[System.Environment]::SetEnvironmentVariable("DISCORD_BOT_TOKEN", "YOUR_TOKEN", "User")
```

**Windows Command Prompt:**
```cmd
setx DISCORD_BOT_TOKEN "YOUR_TOKEN"
```

**Linux/Mac:**
```bash
export DISCORD_BOT_TOKEN="YOUR_TOKEN"

# Add to ~/.bashrc or ~/.zshrc for persistence
echo 'export DISCORD_BOT_TOKEN="YOUR_TOKEN"' >> ~/.bashrc
```

**Security:** Never paste your token into documentation, scripts, or any file that may be committed to version control.

### Verify Token is Set

**Windows PowerShell:**
```powershell
echo $env:DISCORD_BOT_TOKEN
```

**Windows Command Prompt:**
```cmd
echo %DISCORD_BOT_TOKEN%
```

**Linux/Mac:**
```bash
echo $DISCORD_BOT_TOKEN
```

## Channel Configuration

Current configuration in `runtime/discord_config.json`:

- **Station Health Channel:** `1465903939659632807`
- **Authorized User ID:** `315642751419023371` (for DM processing)

### Supported Message Types

1. **Channel Messages:** Messages in the Station Health channel (`1465903939659632807`) are processed automatically
2. **Direct Messages (DMs):** DMs from the authorized user (`315642751419023371`) are processed automatically
   - DMs from other users are ignored
   - The bot will respond with confirmation when messages are processed

### Adding More Channels

To add more channels to the allowlist, edit `runtime/discord_config.json`:

```json
{
  "channel_allowlist": [
    "1465903939659632807",
    "new_channel_id_here"
  ]
}
```

## Running the Discord Intake

### Test Mode (Create Test Envelope)

```bash
python -m calyx.cbo.discord_intake --test-envelope --repo-root .
```

### Start Bot (Requires discord.py)

First, install discord.py:
```bash
pip install discord.py
```

Then start the bot (stays online until Ctrl+C):
```bash
python -m calyx.cbo.discord_intake --run --repo-root .
```

### Startup Script (Single Instance, No Manual Steps)

Ensures only one discord_intake runs. Kills existing instances before starting.

```powershell
.\scripts\start_station_calyx.ps1 -StartDiscord
```

With CBO API:
```powershell
.\scripts\start_station_calyx.ps1 -StartDiscord -StartApi
```

Requires `DISCORD_BOT_TOKEN` in environment. See Token section above.

Or use the Python API:
```python
from calyx.cbo.discord_intake import DiscordIntake

intake = DiscordIntake("runtime/discord_config.json", ".")
await intake.start_bot()
```

## Security Notes

1. **Never commit the bot token** to the repository
2. **Never log the token** in production code
3. **Use environment variables** for token storage
4. **Rotate tokens** if accidentally exposed
5. **Use least privilege** - only grant necessary bot permissions

## Bot Permissions Required

The bot needs the following permissions:
- Read Messages
- Send Messages
- Read Message History
- View Channels

## Troubleshooting

### Token Not Found Error

If you see: `ValueError: Discord bot token not found in env var: DISCORD_BOT_TOKEN`

1. Verify the environment variable is set: `echo $DISCORD_BOT_TOKEN` (or equivalent for your OS)
2. Restart your terminal/IDE after setting the variable
3. Ensure you're using the correct environment variable name

### Channel Not in Allowlist

If messages aren't being processed:
1. Check `runtime/discord_config.json` - ensure channel ID is in `channel_allowlist`
2. Verify `intake_enabled` is `true`
3. Check bot has access to the channel

### Import Error (discord.py not installed)

```bash
pip install discord.py
```

## OpenClaw Integration (Full Assistant)

For OpenClaw-level capabilities (multi-channel, voice, skills, tools), see **docs/OPENCLAW_CALYX_INTEGRATION.md**.

Quick start:
```powershell
.\scripts\setup_openclaw_calyx.ps1
.\scripts\start_station_calyx.ps1 -UseOpenClaw
```

Requires Node ≥22. Stops discord_intake (one Discord bot only).

---

## Next Steps

1. Set the `DISCORD_BOT_TOKEN` environment variable
2. Verify token is accessible
3. Test with `--test-envelope` flag
4. Start the bot to begin processing messages
5. Monitor `telemetry/outbox/intents/` for created envelopes
6. Check `runtime/receipts/discord_intake__*.jsonl` for intake receipts
