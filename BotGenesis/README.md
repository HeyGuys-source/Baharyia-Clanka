# Advanced Discord Moderation Bot

A comprehensive Discord bot with 30+ commands for server moderation and administration, featuring a specialized echo system and 24/7 uptime monitoring.

## 🚀 Features

### 🔨 Moderation Commands (20)
- **Member Management**: kick, ban, unban, mute, unmute, timeout
- **Message Management**: purge, slowmode, lock/unlock channels
- **User Tracking**: warn, warnings history, user information
- **Server Utilities**: nickname changes, invite management, verification

### ⚙️ Administration Commands (10)
- **Server Management**: backup/restore, channel/role creation/deletion
- **Bot Configuration**: permissions setup, logging configuration
- **Advanced Tools**: emoji management, audit logs, mass actions
- **Monitoring**: webhook management, database management

### 📢 Echo System (Administrator Only)
- **Flexible Messaging**: Plain text or rich embed formats
- **Advanced Features**: Reply to specific messages, cross-channel sending
- **Rich Formatting**: JSON-based embed creation with fields, colors, images
- **Administrative Control**: Restricted to administrators only

### 🛠️ Technical Features
- **Database Integration**: PostgreSQL for persistent data storage
- **24/7 Uptime**: Built-in keepalive web server
- **Comprehensive Logging**: Action logging and audit trails
- **Error Handling**: Robust error management and user feedback
- **Modular Design**: Organized cog system for maintainability

## 📦 Installation

### Prerequisites
- Python 3.11+
- Discord Developer Application & Bot Token
- PostgreSQL Database (optional - uses built-in database if available)

### Quick Setup

1. **Clone/Download the Project**
   ```bash
   git clone <your-repository-url>
   cd discord-bot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discord bot token
   ```

4. **Run the Bot**
   ```bash
   python main.py
   ```

### Discord Bot Setup

1. **Create Discord Application**
   - Go to https://discord.com/developers/applications
   - Click "New Application" and name it
   - Go to "Bot" section and create a bot
   - Copy the bot token

2. **Bot Permissions**
   Add these permissions in the OAuth2 → URL Generator:
   - View Channels
   - Send Messages
   - Manage Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Kick Members
   - Ban Members
   - Manage Roles
   - Manage Channels
   - Manage Nicknames
   - Moderate Members

3. **Invite Bot to Server**
   - Use the generated OAuth2 URL
   - Select your server and authorize

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token_here

# Optional Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_NAME=discord_bot

# Optional Settings
LOG_LEVEL=INFO
```

### Bot Commands Setup

1. **Initial Configuration**
   ```
   /config_bot log_channel:#mod-logs auto_mod:true
   ```

2. **Permission Setup**
   ```
   /setup_permissions moderator_role:@Moderator admin_role:@Admin
   ```

## 📖 Command Reference

### Moderation Commands

| Command | Description | Permission Required |
|---------|-------------|-------------------|
| `/kick` | Kick a member | Kick Members |
| `/ban` | Ban a member | Ban Members |
| `/unban` | Unban a user | Ban Members |
| `/mute` | Timeout a member | Moderate Members |
| `/unmute` | Remove timeout | Moderate Members |
| `/warn` | Warn a member | Moderate Members |
| `/purge` | Delete multiple messages | Manage Messages |
| `/slowmode` | Set channel slowmode | Manage Channels |
| `/lock` | Lock a channel | Manage Channels |
| `/unlock` | Unlock a channel | Manage Channels |
| `/nickname` | Change member nickname | Manage Nicknames |
| `/userinfo` | Get user information | None |
| `/warnings` | View user warnings | Moderate Members |
| `/invites` | Manage server invites | Manage Server |

### Administration Commands

| Command | Description | Permission Required |
|---------|-------------|-------------------|
| `/backup_server` | Create server backup | Administrator |
| `/config_bot` | Configure bot settings | Administrator |
| `/setup_permissions` | Setup role permissions | Administrator |
| `/create_channel` | Create new channel | Manage Channels |
| `/delete_channel` | Delete channel | Manage Channels |
| `/create_role` | Create new role | Manage Roles |
| `/delete_role` | Delete role | Manage Roles |
| `/manage_emoji` | Add/remove emojis | Manage Emojis |
| `/audit_logs` | View audit logs | View Audit Log |
| `/mass_action` | Perform mass actions | Administrator |

### Echo System Commands

| Command | Description | Permission Required |
|---------|-------------|-------------------|
| `/echo` | Send custom message | Administrator |
| `/echo_help` | Echo command help | Administrator |

#### Echo Usage Examples

**Basic Text Message:**
```
/echo message:"Hello everyone!" format_type:plain
```

**Simple Embed:**
```
/echo message:"Welcome to our server!" format_type:embed
```

**Advanced Embed with JSON:**
```json
{
  "title": "Server Rules",
  "description": "Please follow these important rules",
  "color": "0x3498db",
  "fields": [
    {
      "name": "Rule 1",
      "value": "Be respectful to all members",
      "inline": true
    },
    {
      "name": "Rule 2", 
      "value": "No spam or excessive caps",
      "inline": true
    }
  ],
  "footer": "Thank you for reading!"
}
```

**Reply to Message:**
```
/echo message:"Thanks for that suggestion!" reply_to_id:1234567890
```

### Utility Commands

| Command | Description |
|---------|-------------|
| `/serverinfo` | Get server information |
| `/botinfo` | Get bot information |
| `/help` | Show command help |

## 🔄 24/7 Uptime

The bot includes a built-in web server for uptime monitoring:

- **Web Interface**: Accessible at `http://localhost:5000`
- **Health Endpoints**: `/health`, `/status`, `/ping`
- **Monitoring Ready**: Compatible with UptimeRobot, StatusCake, etc.

## 📊 Database Features

- **Warning System**: Persistent warning storage and tracking
- **Guild Settings**: Server-specific bot configuration
- **Audit Trail**: Comprehensive action logging
- **Data Persistence**: Automatic table creation and management

## 🚦 Troubleshooting

### Common Issues

1. **Bot Not Responding**
   - Check if bot token is correct
   - Verify bot has proper permissions
   - Check bot is online in Discord

2. **Database Errors**
   - Ensure PostgreSQL is running
   - Check database credentials
   - Verify database exists

3. **Permission Errors**
   - Check bot role hierarchy
   - Verify required permissions
   - Ensure bot role is above target roles

### Log Files

- **Bot Logs**: `logs/bot.log`
- **Error Tracking**: Built-in error handling with detailed logging
- **Debug Mode**: Set `LOG_LEVEL=DEBUG` in .env

## 📝 Development

### Project Structure

```
discord-bot/
├── main.py              # Bot entry point
├── keepalive.py         # Uptime web server
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
├── README.md           # This file
├── cogs/               # Command modules
│   ├── moderation.py   # Moderation commands
│   ├── administration.py # Admin commands
│   ├── echo.py         # Echo system
│   └── utility.py      # Utility commands
├── logs/               # Log files
└── data/               # Data storage
```

### Adding Custom Commands

1. Create new command in appropriate cog file
2. Follow existing patterns for error handling
3. Add database integration if needed
4. Update help documentation

### Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with proper documentation
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is provided as-is for educational and personal use.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review Discord.py documentation
3. Check bot permissions and setup
4. Review log files for errors

---

**Made with ❤️ for Discord Server Management**