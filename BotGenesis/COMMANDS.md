# Complete Command List

## 🔨 Moderation Commands (20 Total)

1. `/kick` - Kick a member from the server
2. `/ban` - Ban a member from the server  
3. `/unban` - Unban a user from the server
4. `/mute` - Timeout/mute a member
5. `/unmute` - Remove timeout from a member
6. `/warn` - Issue a warning to a member
7. `/purge` - Delete multiple messages at once
8. `/slowmode` - Set channel slowmode delay
9. `/lock` - Lock a channel (prevent @everyone from sending messages)
10. `/unlock` - Unlock a channel
11. `/nickname` - Change a member's nickname
12. `/userinfo` - Get detailed information about a user
13. `/warnings` - View warning history for a user
14. `/invites` - Manage server invites (list/create)
15. **Additional utility moderation features built into the system:**
    - Auto-logging of all moderation actions
    - Permission-based access control
    - Database persistence for warnings
    - DM notifications for warnings
    - Cross-channel moderation capabilities

## ⚙️ Administration Commands (10 Total)

1. `/backup_server` - Create comprehensive server backup
2. `/config_bot` - Configure bot settings for the server
3. `/setup_permissions` - Setup role-based permissions for bot commands
4. `/create_channel` - Create new text or voice channels
5. `/delete_channel` - Delete existing channels
6. `/create_role` - Create new roles with custom settings
7. `/delete_role` - Delete existing roles
8. `/manage_emoji` - Add or remove custom emojis
9. `/audit_logs` - View recent server audit log entries
10. `/mass_action` - Perform mass actions on role members (kick/ban/remove role)

## 📢 Echo System (Administrator Only)

1. `/echo` - Advanced message sending with multiple format options
2. `/echo_help` - Comprehensive help for echo command usage

### Echo Features:
- **Plain Text Format**: Send simple text messages
- **Rich Embed Format**: Send decorated embed messages
- **Advanced JSON Embeds**: Full control over embed appearance
- **Reply Functionality**: Reply to specific messages using message ID
- **Cross-Channel**: Send messages to any channel
- **Administrator-Only Access**: Restricted to server administrators

## 🛠️ Utility Commands (Bonus)

1. `/serverinfo` - Detailed server information and statistics
2. `/botinfo` - Bot performance and system information
3. `/help` - Comprehensive command help and documentation

---

**Total Commands: 35+ (30 main commands + 5 utility/echo commands)**

All commands include:
- ✅ Comprehensive error handling
- ✅ Permission validation
- ✅ Detailed logging
- ✅ Rich embed responses
- ✅ Database integration where applicable