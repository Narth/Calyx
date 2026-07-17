### Discord Bot Configuration

- **Bot Token**: `YOUR_DISCORD_BOT_TOKEN` (store securely, never share)
- **Command Prefix**: `!` (customizable)
- **Intents**:
  - `GUILD_MESSAGES`
  - `DIRECT_MESSAGES`
  - `MESSAGE_CONTENT` (for command parsing)
- **Log File**: `C:\Calyx_Terminal\logs\discord-bot.log`
- **Status Message**: "AI Workstation - Ready to assist!"

## Message Routing

```javascript
// Basic message handler for Discord bot
const handleDiscordMessage = async (message) => {
  // Log all messages to telemetry
  await write({
    file_path: 'C:\Calyx_Terminal\logs\discord-bot.log',
    content: `\n[Discord] ${message.author.username}: ${message.content}\n`
  });

  // Route messages to main session for processing
  await sessions_send({
    sessionKey: 'main',
    message: `Discord message from ${message.author.username}: ${message.content}`
  });
};

// Register message handler with Discord API
message.on('message', handleDiscordMessage);
```
