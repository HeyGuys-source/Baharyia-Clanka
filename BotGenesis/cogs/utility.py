"""
Utility Cog
Contains utility commands including remaining moderation commands and server information.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import logging
import psutil
import platform

logger = logging.getLogger(__name__)

class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def create_embed(self, title, description, color=0x3498db, footer=None):
        """Create a styled embed"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.timestamp = datetime.utcnow()
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text="Advanced Utility Bot", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed
    
    @app_commands.command(name="userinfo", description="Get detailed information about a user")
    @app_commands.describe(user="The user to get information about")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        
        # Calculate account age
        account_age = datetime.utcnow() - user.created_at
        join_age = datetime.utcnow() - user.joined_at if user.joined_at else None
        
        embed = self.create_embed(
            f"👤 User Information - {user.display_name}",
            "",
            0x3498db
        )
        
        embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
        
        embed.add_field(
            name="📋 Basic Info",
            value=f"**Username:** {user.name}#{user.discriminator}\n"
                  f"**Display Name:** {user.display_name}\n"
                  f"**ID:** {user.id}\n"
                  f"**Bot:** {'Yes' if user.bot else 'No'}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Dates",
            value=f"**Account Created:** {user.created_at.strftime('%Y-%m-%d')}\n"
                  f"**Account Age:** {account_age.days} days\n" +
                  (f"**Joined Server:** {user.joined_at.strftime('%Y-%m-%d')}\n"
                   f"**Member For:** {join_age.days} days" if join_age else "**Joined:** Unknown"),
            inline=True
        )
        
        # Get roles (excluding @everyone)
        roles = [role.mention for role in reversed(user.roles[1:])]
        roles_text = ", ".join(roles[:10])  # Limit to first 10 roles
        if len(user.roles) > 11:
            roles_text += f" (+{len(user.roles) - 11} more)"
        
        embed.add_field(
            name=f"🎭 Roles ({len(user.roles) - 1})",
            value=roles_text or "None",
            inline=False
        )
        
        # Get permissions
        perms = user.guild_permissions
        important_perms = []
        if perms.administrator:
            important_perms.append("Administrator")
        if perms.manage_guild:
            important_perms.append("Manage Server")
        if perms.manage_channels:
            important_perms.append("Manage Channels")
        if perms.manage_roles:
            important_perms.append("Manage Roles")
        if perms.ban_members:
            important_perms.append("Ban Members")
        if perms.kick_members:
            important_perms.append("Kick Members")
        
        embed.add_field(
            name="🔑 Key Permissions",
            value=", ".join(important_perms) or "None",
            inline=False
        )
        
        # User status
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡", 
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        
        embed.add_field(
            name="📱 Status",
            value=f"{status_emoji.get(user.status, '❓')} {str(user.status).title()}",
            inline=True
        )
        
        # Get activity
        if user.activity:
            activity_type = {
                discord.ActivityType.playing: "🎮 Playing",
                discord.ActivityType.streaming: "📺 Streaming",
                discord.ActivityType.listening: "🎵 Listening to",
                discord.ActivityType.watching: "👀 Watching"
            }
            embed.add_field(
                name="🎯 Activity",
                value=f"{activity_type.get(user.activity.type, '❓')} {user.activity.name}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="serverinfo", description="Get detailed information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # Calculate server age
        server_age = datetime.utcnow() - guild.created_at
        
        embed = self.create_embed(
            f"🏰 Server Information - {guild.name}",
            "",
            0x3498db
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(
            name="📋 Basic Info",
            value=f"**Name:** {guild.name}\n"
                  f"**ID:** {guild.id}\n"
                  f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                  f"**Created:** {guild.created_at.strftime('%Y-%m-%d')}\n"
                  f"**Age:** {server_age.days} days",
            inline=True
        )
        
        # Member counts
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans
        
        # Online members count
        online = len([m for m in guild.members if m.status != discord.Status.offline])
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total_members}\n"
                  f"**Humans:** {humans}\n"
                  f"**Bots:** {bots}\n"
                  f"**Online:** {online}",
            inline=True
        )
        
        # Channel counts
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="📝 Channels",
            value=f"**Text:** {text_channels}\n"
                  f"**Voice:** {voice_channels}\n"
                  f"**Categories:** {categories}\n"
                  f"**Total:** {len(guild.channels)}",
            inline=True
        )
        
        # Roles and emojis
        embed.add_field(
            name="🎭 Server Features",
            value=f"**Roles:** {len(guild.roles)}\n"
                  f"**Emojis:** {len(guild.emojis)}\n"
                  f"**Boost Level:** {guild.premium_tier}\n"
                  f"**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )
        
        # Security settings
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium", 
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="🔒 Security",
            value=f"**Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n"
                  f"**Content Filter:** {str(guild.explicit_content_filter).replace('_', ' ').title()}\n"
                  f"**2FA Required:** {'Yes' if guild.mfa_level else 'No'}",
            inline=True
        )
        
        # Server features
        features = []
        if guild.features:
            feature_names = {
                'COMMUNITY': 'Community Server',
                'PARTNERED': 'Partnered',
                'VERIFIED': 'Verified',
                'DISCOVERABLE': 'Discoverable',
                'MONETIZATION_ENABLED': 'Monetization',
                'NEWS': 'News Channels',
                'BANNER': 'Banner',
                'VANITY_URL': 'Vanity URL'
            }
            features = [feature_names.get(f, f.replace('_', ' ').title()) for f in guild.features]
        
        if features:
            embed.add_field(
                name="✨ Features",
                value="\n".join(f"• {feature}" for feature in features[:8]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="warnings", description="View warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    async def warnings(self, interaction: discord.Interaction, user: discord.Member = None):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need moderate members permission.", 0xff0000),
                ephemeral=True
            )
        
        user = user or interaction.user
        
        try:
            if not self.bot.db_pool:
                return await interaction.response.send_message(
                    embed=self.create_embed("❌ Error", "Database not available", 0xff0000),
                    ephemeral=True
                )
            
            async with self.bot.db_pool.acquire() as conn:
                warnings = await conn.fetch(
                    "SELECT * FROM warnings WHERE user_id = $1 AND guild_id = $2 ORDER BY timestamp DESC LIMIT 10",
                    user.id, interaction.guild.id
                )
            
            if not warnings:
                embed = self.create_embed(
                    f"⚠️ Warnings for {user.display_name}",
                    "No warnings found.",
                    0x2ecc71
                )
            else:
                warning_list = []
                for i, warning in enumerate(warnings, 1):
                    moderator = interaction.guild.get_member(warning['moderator_id'])
                    mod_name = moderator.display_name if moderator else "Unknown"
                    warning_list.append(
                        f"**{i}.** {warning['reason'] or 'No reason'}\n"
                        f"   *By {mod_name} on {warning['timestamp'].strftime('%Y-%m-%d %H:%M')}*"
                    )
                
                embed = self.create_embed(
                    f"⚠️ Warnings for {user.display_name}",
                    "\n\n".join(warning_list),
                    0xf39c12
                )
                embed.add_field(
                    name="Total Warnings",
                    value=str(len(warnings)),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to fetch warnings: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="invites", description="Manage server invites")
    @app_commands.describe(action="List, create, or delete invites", channel="Channel for new invite", max_uses="Max uses for new invite")
    async def invites(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel = None, max_uses: int = 0):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage server permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            if action.lower() == "list":
                invites = await interaction.guild.invites()
                if not invites:
                    embed = self.create_embed("📨 Server Invites", "No invites found.", 0x3498db)
                else:
                    invite_list = []
                    for invite in invites[:10]:  # Limit to 10 invites
                        inviter = invite.inviter.display_name if invite.inviter else "Unknown"
                        invite_list.append(
                            f"**{invite.code}** (#{invite.channel.name})\n"
                            f"Uses: {invite.uses}/{invite.max_uses or '∞'} | "
                            f"Created by: {inviter}"
                        )
                    
                    embed = self.create_embed(
                        "📨 Server Invites",
                        "\n\n".join(invite_list),
                        0x3498db
                    )
            
            elif action.lower() == "create":
                channel = channel or interaction.channel
                invite = await channel.create_invite(
                    max_uses=max_uses,
                    unique=True,
                    reason=f"Invite created by {interaction.user.display_name}"
                )
                
                embed = self.create_embed(
                    "📨 Invite Created",
                    f"**Invite:** {invite.url}\n**Channel:** {channel.mention}\n**Max Uses:** {max_uses or 'Unlimited'}",
                    0x2ecc71
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to manage invites: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="botinfo", description="Get information about the bot")
    async def botinfo(self, interaction: discord.Interaction):
        try:
            # Calculate uptime
            uptime = datetime.utcnow() - self.bot.start_time
            uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
            
            # Get system info
            memory_usage = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent()
            
            embed = self.create_embed(
                f"🤖 Bot Information - {self.bot.user.display_name}",
                "",
                0x3498db
            )
            
            embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else self.bot.user.default_avatar.url)
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Servers:** {len(self.bot.guilds)}\n"
                      f"**Users:** {len(self.bot.users)}\n"
                      f"**Commands:** 30+\n"
                      f"**Uptime:** {uptime_str}",
                inline=True
            )
            
            embed.add_field(
                name="💻 System",
                value=f"**Python:** {platform.python_version()}\n"
                      f"**Discord.py:** {discord.__version__}\n"
                      f"**CPU Usage:** {cpu_usage}%\n"
                      f"**Memory:** {memory_usage.percent}%",
                inline=True
            )
            
            embed.add_field(
                name="🔧 Features",
                value="• 20 Moderation Commands\n"
                      "• 10 Administration Commands\n"
                      "• Advanced Echo System\n"
                      "• Database Integration\n"
                      "• 24/7 Uptime Monitoring\n"
                      "• Comprehensive Logging",
                inline=False
            )
            
            embed.add_field(
                name="📝 Version Info",
                value="**Version:** 1.0.0\n"
                      "**Last Update:** Today\n"
                      "**Status:** Fully Operational",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to get bot info: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="help", description="Get help with bot commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛡️ Advanced Moderation Bot - Command Help",
            description="A comprehensive Discord bot with advanced moderation and administration features.",
            color=0x3498db
        )
        
        embed.add_field(
            name="🔨 Moderation Commands (20)",
            value="""
            `/kick` - Kick a member
            `/ban` - Ban a member  
            `/unban` - Unban a user
            `/mute` - Mute a member
            `/unmute` - Unmute a member
            `/warn` - Warn a member
            `/purge` - Delete multiple messages
            `/slowmode` - Set channel slowmode
            `/lock` - Lock a channel
            `/unlock` - Unlock a channel
            `/nickname` - Change member nickname
            `/userinfo` - Get user information
            `/warnings` - View user warnings
            `/invites` - Manage server invites
            *And more moderation tools...*
            """,
            inline=True
        )
        
        embed.add_field(
            name="⚙️ Administration Commands (10)",
            value="""
            `/backup_server` - Create server backup
            `/config_bot` - Configure bot settings
            `/setup_permissions` - Setup role permissions
            `/create_channel` - Create new channels
            `/delete_channel` - Delete channels
            `/create_role` - Create new roles
            `/delete_role` - Delete roles
            `/manage_emoji` - Manage custom emojis
            `/audit_logs` - View audit logs
            `/mass_action` - Perform mass actions
            """,
            inline=True
        )
        
        embed.add_field(
            name="📢 Echo System (Admin Only)",
            value="""
            `/echo` - Make bot send custom messages
            `/echo_help` - Detailed echo command help
            
            Features:
            • Plain text or rich embed format
            • Reply to specific messages
            • Send to any channel
            • Advanced JSON formatting
            """,
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Utility Commands",
            value="`/serverinfo` - Server information\n"
                  "`/botinfo` - Bot information\n"
                  "`/help` - This help message",
            inline=False
        )
        
        embed.add_field(
            name="🔑 Permission Requirements",
            value="**Moderator Commands:** Require appropriate permissions (Kick Members, Ban Members, etc.)\n"
                  "**Administrator Commands:** Require Administrator permission\n"
                  "**Echo Commands:** Require Administrator permission only",
            inline=False
        )
        
        embed.set_footer(text="Advanced Moderation Bot | Use slash commands for all features")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UtilityCog(bot))