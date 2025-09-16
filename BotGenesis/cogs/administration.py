"""
Administration Cog
Contains 10 administrator commands for advanced server management.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
import json
import logging
import io
import zipfile

logger = logging.getLogger(__name__)

class AdministrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def create_embed(self, title, description, color=0x3498db, footer=None):
        """Create a styled embed"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.timestamp = datetime.utcnow()
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text="Advanced Administration Bot", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed
    
    async def log_action(self, guild, action, moderator, target, reason=None):
        """Log administration actions to the log channel"""
        try:
            if not self.bot.db_pool:
                return
                
            async with self.bot.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT log_channel_id FROM guild_settings WHERE guild_id = $1",
                    guild.id
                )
                
            if result and result['log_channel_id']:
                channel = guild.get_channel(result['log_channel_id'])
                if channel:
                    embed = self.create_embed(
                        f"⚙️ {action}",
                        f"**Target:** {target}\n**Administrator:** {moderator}\n**Details:** {reason or 'No details provided'}",
                        color=0x9b59b6
                    )
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    @app_commands.command(name="backup_server", description="Create a backup of server settings")
    @app_commands.describe(include_messages="Include recent messages in backup")
    async def backup_server(self, interaction: discord.Interaction, include_messages: bool = False):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need administrator permission.", 0xff0000),
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        try:
            guild = interaction.guild
            backup_data = {
                'guild_info': {
                    'name': guild.name,
                    'description': guild.description,
                    'icon_url': str(guild.icon.url) if guild.icon else None,
                    'banner_url': str(guild.banner.url) if guild.banner else None,
                    'verification_level': str(guild.verification_level),
                    'explicit_content_filter': str(guild.explicit_content_filter),
                    'default_notifications': str(guild.default_notifications),
                    'created_at': guild.created_at.isoformat()
                },
                'channels': [],
                'roles': [],
                'categories': [],
                'emojis': []
            }
            
            # Backup channels
            for channel in guild.channels:
                if isinstance(channel, discord.CategoryChannel):
                    backup_data['categories'].append({
                        'name': channel.name,
                        'position': channel.position,
                        'overwrites': {str(target.id): {perm: value for perm, value in overwrite._values.items()} 
                                      for target, overwrite in channel.overwrites.items()}
                    })
                elif isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                    channel_data = {
                        'name': channel.name,
                        'type': str(channel.type),
                        'position': channel.position,
                        'category': channel.category.name if channel.category else None,
                        'topic': getattr(channel, 'topic', None),
                        'slowmode_delay': getattr(channel, 'slowmode_delay', 0),
                        'nsfw': getattr(channel, 'nsfw', False),
                        'overwrites': {str(target.id): {perm: value for perm, value in overwrite._values.items()} 
                                      for target, overwrite in channel.overwrites.items()}
                    }
                    
                    if include_messages and isinstance(channel, discord.TextChannel):
                        messages = []
                        async for message in channel.history(limit=100):
                            messages.append({
                                'author': str(message.author),
                                'content': message.content,
                                'timestamp': message.created_at.isoformat(),
                                'attachments': [att.url for att in message.attachments]
                            })
                        channel_data['recent_messages'] = messages
                    
                    backup_data['channels'].append(channel_data)
            
            # Backup roles
            for role in guild.roles:
                if role != guild.default_role:
                    backup_data['roles'].append({
                        'name': role.name,
                        'color': role.color.value,
                        'hoist': role.hoist,
                        'mentionable': role.mentionable,
                        'position': role.position,
                        'permissions': role.permissions.value
                    })
            
            # Backup emojis
            for emoji in guild.emojis:
                backup_data['emojis'].append({
                    'name': emoji.name,
                    'url': str(emoji.url),
                    'animated': emoji.animated
                })
            
            # Create backup file
            backup_json = json.dumps(backup_data, indent=2)
            backup_file = discord.File(
                io.StringIO(backup_json), 
                filename=f"{guild.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            embed = self.create_embed(
                "💾 Server Backup Created",
                f"**Server:** {guild.name}\n**Channels:** {len(backup_data['channels'])}\n**Roles:** {len(backup_data['roles'])}\n**Categories:** {len(backup_data['categories'])}\n**Emojis:** {len(backup_data['emojis'])}\n**Messages Included:** {include_messages}",
                0x2ecc71
            )
            
            await interaction.followup.send(embed=embed, file=backup_file)
            await self.log_action(guild, "Server Backup Created", interaction.user, f"Full server backup with {len(backup_data['channels'])} channels")
            
        except Exception as e:
            await interaction.followup.send(
                embed=self.create_embed("❌ Error", f"Failed to create backup: {str(e)}", 0xff0000)
            )
    
    @app_commands.command(name="config_bot", description="Configure bot settings for this server")
    @app_commands.describe(log_channel="Channel for logging bot actions", auto_mod="Enable automatic moderation")
    async def config_bot(self, interaction: discord.Interaction, log_channel: discord.TextChannel = None, auto_mod: bool = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need administrator permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            if not self.bot.db_pool:
                return await interaction.response.send_message(
                    embed=self.create_embed("❌ Error", "Database not available", 0xff0000),
                    ephemeral=True
                )
            
            async with self.bot.db_pool.acquire() as conn:
                # Check if settings exist
                existing = await conn.fetchrow(
                    "SELECT * FROM guild_settings WHERE guild_id = $1",
                    interaction.guild.id
                )
                
                if existing:
                    # Update existing settings
                    updates = []
                    params = [interaction.guild.id]
                    param_count = 2
                    
                    if log_channel:
                        updates.append(f"log_channel_id = ${param_count}")
                        params.append(log_channel.id)
                        param_count += 1
                    
                    if auto_mod is not None:
                        updates.append(f"auto_mod = ${param_count}")
                        params.append(auto_mod)
                        param_count += 1
                    
                    if updates:
                        query = f"UPDATE guild_settings SET {', '.join(updates)} WHERE guild_id = $1"
                        await conn.execute(query, *params)
                else:
                    # Create new settings
                    await conn.execute(
                        "INSERT INTO guild_settings (guild_id, log_channel_id, auto_mod) VALUES ($1, $2, $3)",
                        interaction.guild.id, log_channel.id if log_channel else None, auto_mod or False
                    )
            
            embed = self.create_embed(
                "⚙️ Bot Configuration Updated",
                f"**Log Channel:** {log_channel.mention if log_channel else 'Not set'}\n**Auto Moderation:** {'Enabled' if auto_mod else 'Disabled' if auto_mod is not None else 'Not changed'}",
                0x3498db
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Bot Configuration Updated", interaction.user, "Settings modified")
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to update configuration: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="setup_permissions", description="Setup role permissions for bot commands")
    @app_commands.describe(moderator_role="Role for moderator commands", admin_role="Role for admin commands")
    async def setup_permissions(self, interaction: discord.Interaction, moderator_role: discord.Role = None, admin_role: discord.Role = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need administrator permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            settings = {}
            if moderator_role:
                settings['moderator_role_id'] = moderator_role.id
            if admin_role:
                settings['admin_role_id'] = admin_role.id
            
            if self.bot.db_pool and settings:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO guild_settings (guild_id, settings) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET settings = guild_settings.settings || $2",
                        interaction.guild.id, json.dumps(settings)
                    )
            
            embed = self.create_embed(
                "🔐 Permissions Setup",
                f"**Moderator Role:** {moderator_role.mention if moderator_role else 'Not set'}\n**Admin Role:** {admin_role.mention if admin_role else 'Not set'}",
                0x9b59b6
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Permissions Setup", interaction.user, "Role permissions configured")
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to setup permissions: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="create_channel", description="Create a new channel")
    @app_commands.describe(name="Channel name", channel_type="Type of channel", category="Category to place channel in")
    async def create_channel(self, interaction: discord.Interaction, name: str, channel_type: str = "text", category: discord.CategoryChannel = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage channels permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            if channel_type.lower() == "voice":
                channel = await interaction.guild.create_voice_channel(name, category=category)
            else:
                channel = await interaction.guild.create_text_channel(name, category=category)
            
            embed = self.create_embed(
                "📝 Channel Created",
                f"**Channel:** {channel.mention}\n**Type:** {channel.type}\n**Category:** {category.name if category else 'None'}",
                0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Channel Created", interaction.user, f"{channel.mention} ({channel.type})")
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to create channel: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="delete_channel", description="Delete a channel")
    @app_commands.describe(channel="Channel to delete", reason="Reason for deletion")
    async def delete_channel(self, interaction: discord.Interaction, channel: discord.abc.GuildChannel, reason: str = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage channels permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            channel_name = channel.name
            await channel.delete(reason=reason)
            
            embed = self.create_embed(
                "🗑️ Channel Deleted",
                f"**Channel:** #{channel_name}\n**Reason:** {reason or 'No reason provided'}",
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Channel Deleted", interaction.user, f"#{channel_name}", reason)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to delete channel: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="create_role", description="Create a new role")
    @app_commands.describe(name="Role name", color="Role color (hex)", hoist="Display separately", mentionable="Allow mentioning")
    async def create_role(self, interaction: discord.Interaction, name: str, color: str = None, hoist: bool = False, mentionable: bool = False):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage roles permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            role_color = discord.Color.default()
            if color:
                try:
                    role_color = discord.Color(int(color.replace('#', ''), 16))
                except:
                    pass
            
            role = await interaction.guild.create_role(
                name=name,
                color=role_color,
                hoist=hoist,
                mentionable=mentionable
            )
            
            embed = self.create_embed(
                "🎭 Role Created",
                f"**Role:** {role.mention}\n**Color:** {str(role.color)}\n**Hoist:** {hoist}\n**Mentionable:** {mentionable}",
                0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Role Created", interaction.user, role.mention)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to create role: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="delete_role", description="Delete a role")
    @app_commands.describe(role="Role to delete", reason="Reason for deletion")
    async def delete_role(self, interaction: discord.Interaction, role: discord.Role, reason: str = None):
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage roles permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            role_name = role.name
            await role.delete(reason=reason)
            
            embed = self.create_embed(
                "🗑️ Role Deleted",
                f"**Role:** {role_name}\n**Reason:** {reason or 'No reason provided'}",
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Role Deleted", interaction.user, role_name, reason)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to delete role: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="manage_emoji", description="Add or remove custom emojis")
    @app_commands.describe(action="Add or remove emoji", name="Emoji name", image="Image URL for adding emoji")
    async def manage_emoji(self, interaction: discord.Interaction, action: str, name: str, image: str = None):
        if not interaction.user.guild_permissions.manage_emojis:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage emojis permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            if action.lower() == "add":
                if not image:
                    return await interaction.response.send_message(
                        embed=self.create_embed("❌ Error", "Image URL required for adding emoji", 0xff0000),
                        ephemeral=True
                    )
                
                async with self.bot.session.get(image) as resp:
                    if resp.status == 200:
                        emoji_data = await resp.read()
                        emoji = await interaction.guild.create_custom_emoji(name=name, image=emoji_data)
                        
                        embed = self.create_embed(
                            "😀 Emoji Added",
                            f"**Emoji:** {emoji}\n**Name:** {name}",
                            0x2ecc71
                        )
                    else:
                        raise Exception("Failed to fetch image")
            
            elif action.lower() == "remove":
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                if emoji:
                    await emoji.delete()
                    embed = self.create_embed(
                        "🗑️ Emoji Removed",
                        f"**Name:** {name}",
                        0xe74c3c
                    )
                else:
                    raise Exception("Emoji not found")
            
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, f"Emoji {action.title()}ed", interaction.user, name)
            
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to {action} emoji: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="audit_logs", description="View recent audit log entries")
    @app_commands.describe(limit="Number of entries to show (1-25)", action="Filter by action type")
    async def audit_logs(self, interaction: discord.Interaction, limit: int = 10, action: str = None):
        if not interaction.user.guild_permissions.view_audit_log:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need view audit log permission.", 0xff0000),
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        try:
            limit = max(1, min(25, limit))
            audit_entries = []
            
            async for entry in interaction.guild.audit_logs(limit=limit):
                if action and action.lower() not in str(entry.action).lower():
                    continue
                    
                audit_entries.append(f"**{entry.action}** by {entry.user.mention}\n"
                                   f"Target: {entry.target}\n"
                                   f"Time: {entry.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                   f"Reason: {entry.reason or 'None'}\n")
            
            if not audit_entries:
                embed = self.create_embed("📋 Audit Logs", "No matching audit log entries found.", 0x3498db)
            else:
                description = "\n".join(audit_entries[:10])  # Limit to prevent embed size issues
                embed = self.create_embed("📋 Audit Logs", description, 0x3498db)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                embed=self.create_embed("❌ Error", f"Failed to fetch audit logs: {str(e)}", 0xff0000)
            )
    
    @app_commands.command(name="mass_action", description="Perform mass actions on members")
    @app_commands.describe(action="Action to perform", role="Target role for action", reason="Reason for action")
    async def mass_action(self, interaction: discord.Interaction, action: str, role: discord.Role, reason: str = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need administrator permission.", 0xff0000),
                ephemeral=True
            )
        
        await interaction.response.defer()
        
        try:
            members = role.members
            if not members:
                return await interaction.followup.send(
                    embed=self.create_embed("❌ Error", "No members found with that role.", 0xff0000)
                )
            
            success_count = 0
            failed_count = 0
            
            if action.lower() == "kick":
                for member in members:
                    try:
                        await member.kick(reason=reason)
                        success_count += 1
                    except:
                        failed_count += 1
            
            elif action.lower() == "ban":
                for member in members:
                    try:
                        await member.ban(reason=reason)
                        success_count += 1
                    except:
                        failed_count += 1
            
            elif action.lower() == "remove_role":
                for member in members:
                    try:
                        await member.remove_roles(role, reason=reason)
                        success_count += 1
                    except:
                        failed_count += 1
            
            embed = self.create_embed(
                f"⚡ Mass {action.title()} Complete",
                f"**Target Role:** {role.mention}\n**Successful:** {success_count}\n**Failed:** {failed_count}\n**Reason:** {reason or 'No reason provided'}",
                0x9b59b6
            )
            await interaction.followup.send(embed=embed)
            await self.log_action(interaction.guild, f"Mass {action.title()}", interaction.user, f"{role.mention} ({success_count} members)", reason)
            
        except Exception as e:
            await interaction.followup.send(
                embed=self.create_embed("❌ Error", f"Failed to perform mass action: {str(e)}", 0xff0000)
            )

async def setup(bot):
    await bot.add_cog(AdministrationCog(bot))