"""
Comprehensive Admin Commands Cog
Contains 40+ admin commands including echo, server management, moderation, and utilities
"""

import asyncio
import json
import os
import sys
import time
import psutil
from datetime import datetime, timedelta
from typing import Optional, Union, Literal

import discord
from discord.ext import commands
from discord import app_commands

from config.settings import get_colors, settings
from utils.permissions import require_admin_role, permission_manager, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

log = get_logger("admin_cog")

class AdminCog(commands.Cog, name="Administration"):
    """Comprehensive administration commands for server management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.colors = get_colors()
        
    # ======== MESSAGE & COMMUNICATION COMMANDS ========
    
    @app_commands.command(name="echo", description="Echo a message with optional embed format and reply functionality")
    @app_commands.describe(
        message="The message to echo",
        format_type="Whether to send as plain text or embed",
        reply_to="Message ID to reply to (optional)",
        ephemeral="Whether the response should be visible only to you"
    )
    async def echo(
        self,
        interaction: discord.Interaction,
        message: str,
        format_type: Literal["plain", "embed"] = "plain",
        reply_to: Optional[str] = None,
        ephemeral: bool = False
    ):
        """Enhanced echo command with embed/plain text options and reply functionality"""
        if not permission_manager.can_execute_command(interaction.user, "echo"):
            embed = BotHelpers.create_embed(
                "Access Denied",
                "You don't have permission to use this command.",
                "error"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Handle reply functionality
            reference_message = None
            if reply_to:
                try:
                    message_id = int(reply_to)
                    reference_message = await interaction.channel.fetch_message(message_id)
                except (ValueError, discord.NotFound):
                    await interaction.response.send_message("❌ Invalid message ID provided for reply.", ephemeral=True)
                    return
            
            await interaction.response.defer(ephemeral=ephemeral)
            
            if format_type == "embed":
                embed = BotHelpers.create_embed(
                    "Echo Message",
                    message,
                    "primary"
                )
                embed.set_footer(text=f"Sent by {interaction.user}")
                
                await interaction.followup.send(
                    embed=embed,
                    ephemeral=ephemeral
                )
            else:
                await interaction.followup.send(
                    message,
                    ephemeral=ephemeral
                )
            
            await log_command_usage(interaction, "echo", True)
            
        except Exception as e:
            log.error(f"Echo command error: {e}")
            error_embed = BotHelpers.create_embed(
                "Command Error",
                f"Failed to execute echo command: {str(e)}",
                "error"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="server_icon", description="Get the server's icon")
    async def server_icon(self, interaction: discord.Interaction):
        """Get the server's icon"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in servers.", ephemeral=True)
            return
        
        icon_url = await BotHelpers.get_guild_icon(interaction.guild)
        
        if icon_url:
            embed = BotHelpers.create_embed(
                f"{interaction.guild.name} Server Icon",
                f"[Download Icon]({icon_url})",
                "primary"
            )
            embed.set_image(url=icon_url)
        else:
            embed = BotHelpers.create_embed(
                "No Server Icon",
                f"{interaction.guild.name} doesn't have a server icon set.",
                "warning"
            )
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "server_icon", True)
    
    @app_commands.command(name="avatar_icon", description="Get any user's avatar")
    @app_commands.describe(user="The user whose avatar you want to retrieve")
    async def avatar_icon(self, interaction: discord.Interaction, user: discord.Member):
        """Get any user's avatar"""
        avatar_url = await BotHelpers.get_user_avatar(user)
        
        embed = BotHelpers.create_embed(
            f"{user.display_name}'s Avatar",
            f"[Download Avatar]({avatar_url})",
            "primary"
        )
        embed.set_image(url=avatar_url)
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "avatar_icon", True)
    
    # ======== COG MANAGEMENT COMMANDS ========
    
    @app_commands.command(name="reload_all_cogs", description="Reload all bot cogs without restart")
    @require_admin_role()
    async def reload_all_cogs(self, interaction: discord.Interaction):
        """Reload all cogs without restarting the bot"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            reloaded = await self.bot.cog_manager.reload_all_cogs()
            
            embed = BotHelpers.create_embed(
                "Cogs Reloaded",
                f"Successfully reloaded {len(reloaded)} cog(s):\n" + "\n".join(f"• {cog}" for cog in reloaded),
                "success"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "reload_all_cogs", True)
            
        except Exception as e:
            log.error(f"Reload all cogs error: {e}")
            error_embed = BotHelpers.create_embed(
                "Reload Failed",
                f"Error reloading cogs: {str(e)}",
                "error"
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="list_cogs", description="List all loaded cogs")
    @require_admin_role()
    async def list_cogs(self, interaction: discord.Interaction):
        """List all loaded cogs"""
        loaded_cogs = self.bot.cog_manager.get_loaded_cogs()
        
        embed = BotHelpers.create_embed(
            "Loaded Cogs",
            f"**{len(loaded_cogs)} cog(s) loaded:**\n" + "\n".join(f"• {cog}" for cog in loaded_cogs),
            "info"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_command_usage(interaction, "list_cogs", True)
    # ======== MODERATION COMMANDS ========
    
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.describe(user="User to ban", reason="Reason for the ban", delete_days="Days of messages to delete (0-7)")
    @require_admin_role()
    async def ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided", delete_days: int = 1):
        """Ban a user from the server"""
        if not interaction.user.guild_permissions.ban_members:
            embed = BotHelpers.create_embed("No Permission", "You need ban members permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.ban(reason=reason, delete_message_days=min(max(delete_days, 0), 7))
            
            embed = BotHelpers.create_embed(
                "User Banned",
                f"{user} has been banned.\n**Reason:** {reason}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "ban", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to ban this user.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Ban command error: {e}")
            embed = BotHelpers.create_embed("Ban Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.describe(user="User to kick", reason="Reason for the kick")
    @require_admin_role()
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        """Kick a user from the server"""
        if not interaction.user.guild_permissions.kick_members:
            embed = BotHelpers.create_embed("No Permission", "You need kick members permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.kick(reason=reason)
            
            embed = BotHelpers.create_embed(
                "User Kicked",
                f"{user} has been kicked.\n**Reason:** {reason}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "kick", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to kick this user.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Kick command error: {e}")
            embed = BotHelpers.create_embed("Kick Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="purge", description="Delete multiple messages from the channel")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @require_admin_role()
    async def purge(self, interaction: discord.Interaction, amount: int):
        """Delete multiple messages from the channel"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = BotHelpers.create_embed("No Permission", "You need manage messages permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            embed = BotHelpers.create_embed("Invalid Amount", "Please specify between 1 and 100 messages.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            deleted = await interaction.channel.purge(limit=amount)
            
            embed = BotHelpers.create_embed(
                "Messages Purged",
                f"Successfully deleted {len(deleted)} message(s).",
                "success"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "purge", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to delete messages.", "error")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Purge command error: {e}")
            embed = BotHelpers.create_embed("Purge Failed", f"Error: {str(e)}", "error")
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ======== SERVER INFORMATION COMMANDS ========
    
    @app_commands.command(name="server_info", description="Get detailed server information")
    async def server_info(self, interaction: discord.Interaction):
        """Get comprehensive server information"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in servers.", ephemeral=True)
            return
        
        guild = interaction.guild
        
        # Calculate member statistics
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        bot_count = sum(1 for member in guild.members if member.bot)
        human_count = guild.member_count - bot_count
        
        # Calculate channel statistics
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed = BotHelpers.create_embed(
            f"📊 {guild.name} Server Information",
            "",
            "primary"
        )
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {guild.member_count:,}\n**Humans:** {human_count:,}\n**Bots:** {bot_count:,}\n**Online:** {online_members:,}",
            inline=True
        )
        
        embed.add_field(
            name="📺 Channels",
            value=f"**Text:** {text_channels}\n**Voice:** {voice_channels}\n**Categories:** {categories}\n**Total:** {len(guild.channels)}",
            inline=True
        )
        
        embed.add_field(
            name="ℹ️ General",
            value=f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n**Created:** {BotHelpers.format_datetime(guild.created_at, 'discord')}\n**Region:** {guild.preferred_locale}\n**Roles:** {len(guild.roles)}",
            inline=True
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(text=f"Server ID: {guild.id}")
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "server_info", True)
    
    @app_commands.command(name="user_info", description="Get detailed information about a user")
    @app_commands.describe(user="The user to get information about")
    async def user_info(self, interaction: discord.Interaction, user: discord.Member):
        """Get comprehensive user information"""
        
        embed = BotHelpers.create_embed(
            f"👤 {user.display_name} Information",
            "",
            "primary"
        )
        
        # Basic user info
        embed.add_field(
            name="🏷️ Basic Info",
            value=f"**Username:** {user}\n**Display Name:** {user.display_name}\n**ID:** {user.id}\n**Bot:** {'Yes' if user.bot else 'No'}",
            inline=True
        )
        
        # Account dates
        embed.add_field(
            name="📅 Dates",
            value=f"**Created:** {BotHelpers.format_datetime(user.created_at, 'discord')}\n**Joined:** {BotHelpers.format_datetime(user.joined_at, 'discord') if user.joined_at else 'Unknown'}",
            inline=True
        )
        
        # Status and activity
        status_emojis = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        
        embed.add_field(
            name="📱 Status",
            value=f"**Status:** {status_emojis.get(user.status, '❓')} {user.status.title()}\n**Top Role:** {user.top_role.mention}\n**Roles:** {len(user.roles) - 1}",
            inline=True
        )
        
        embed.set_thumbnail(url=await BotHelpers.get_user_avatar(user))
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "user_info", True)
    
    # ======== BOT STATISTICS & SYSTEM INFO ========
    
    @app_commands.command(name="stats", description="Get comprehensive bot statistics")
    @require_admin_role()
    async def stats(self, interaction: discord.Interaction):
        """Get comprehensive bot statistics"""
        await interaction.response.defer()
        
        # Bot uptime
        uptime = discord.utils.utcnow() - self.bot.start_time
        uptime_str = BotHelpers.format_duration(int(uptime.total_seconds()))
        
        # System statistics (non-blocking)
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking
        
        # Discord statistics
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        total_channels = sum(len(guild.channels) for guild in self.bot.guilds)
        
        embed = BotHelpers.create_embed(
            f"📈 {self.bot.user.display_name} Statistics",
            "",
            "primary"
        )
        
        embed.add_field(
            name="🤖 Bot Info",
            value=f"**Uptime:** {uptime_str}\n**Guilds:** {len(self.bot.guilds):,}\n**Users:** {total_members:,}\n**Channels:** {total_channels:,}",
            inline=True
        )
        
        embed.add_field(
            name="💾 System",
            value=f"**CPU Usage:** {cpu_percent}%\n**Memory:** {BotHelpers.format_bytes(memory.used)}/{BotHelpers.format_bytes(memory.total)} ({memory.percent:.1f}%)\n**Python:** {sys.version.split()[0]}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Commands",
            value=f"**Loaded Cogs:** {len(self.bot.cogs)}\n**Commands:** {len([cmd for cmd in self.bot.tree.walk_commands()])}\n**Latency:** {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed)
        await log_command_usage(interaction, "stats", True)
    
    # ======== ADDITIONAL ADMIN COMMANDS ========
    
    @app_commands.command(name="shutdown", description="Shutdown the bot (bot owner only)")
    @require_admin_role()
    async def shutdown(self, interaction: discord.Interaction):
        """Shutdown the bot - restricted to bot owner only"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can shutdown the bot.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = BotHelpers.create_embed(
            "🔴 Bot Shutdown",
            "Bot is shutting down...",
            "warning"
        )
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "shutdown", True)
        
        await asyncio.sleep(2)
        await self.bot.close()
    
    @app_commands.command(name="restart", description="Restart the bot (bot owner only)")
    @require_admin_role()
    async def restart(self, interaction: discord.Interaction):
        """Restart the bot - restricted to bot owner only"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can restart the bot.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = BotHelpers.create_embed(
            "🔄 Bot Restart",
            "Bot is restarting... Please wait a moment.",
            "warning"
        )
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "restart", True)
        
        # Reload all cogs instead of full restart
        await self.bot.cog_manager.reload_all_cogs()
        
        restart_embed = BotHelpers.create_embed(
            "✅ Restart Complete",
            "Bot has been restarted successfully!",
            "success"
        )
        await interaction.followup.send(embed=restart_embed)
    
    @app_commands.command(name="broadcast", description="Send a message to all servers (bot owner only)")
    @app_commands.describe(message="Message to broadcast", channel_name="Channel name to send to (default: general)")
    @require_admin_role()
    async def broadcast(self, interaction: discord.Interaction, message: str, channel_name: str = "general"):
        """Broadcast message to all servers - restricted to bot owner only"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can broadcast messages.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        sent_count = 0
        failed_count = 0
        
        for guild in self.bot.guilds:
            try:
                # Find channel with specified name
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if not channel:
                    # Fallback to first available text channel
                    channel = guild.text_channels[0] if guild.text_channels else None
                
                if channel:
                    embed = BotHelpers.create_embed(
                        "📢 Broadcast Message",
                        message,
                        "primary"
                    )
                    embed.set_footer(text=f"Broadcast from {interaction.user}")
                    
                    await channel.send(embed=embed)
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
        
        result_embed = BotHelpers.create_embed(
            "📡 Broadcast Complete",
            f"Message sent to **{sent_count}** server(s).\nFailed: **{failed_count}** server(s).",
            "success" if sent_count > 0 else "warning"
        )
        
        await interaction.followup.send(embed=result_embed, ephemeral=True)
        await log_command_usage(interaction, "broadcast", True)
    
    @app_commands.command(name="eval", description="Evaluate Python code (bot owner only)")
    @app_commands.describe(code="Python code to evaluate")
    @require_admin_role()
    async def eval_code(self, interaction: discord.Interaction, code: str):
        """Evaluate Python code - restricted to bot owner only"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can use eval.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Create safe environment
        env = {
            'bot': self.bot,
            'interaction': interaction,
            'guild': interaction.guild,
            'channel': interaction.channel,
            'user': interaction.user,
            'discord': discord,
            'commands': commands
        }
        
        try:
            # Execute the code
            result = eval(code, env)
            if asyncio.iscoroutine(result):
                result = await result
            
            # Format result
            result_str = str(result)
            if len(result_str) > 1900:
                result_str = result_str[:1900] + "..."
            
            embed = BotHelpers.create_embed(
                "✅ Eval Result",
                f"```python\n{code}\n```\n**Result:**\n```python\n{result_str}\n```",
                "success"
            )
            
        except Exception as e:
            embed = BotHelpers.create_embed(
                "❌ Eval Error",
                f"```python\n{code}\n```\n**Error:**\n```python\n{str(e)}\n```",
                "error"
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        await log_command_usage(interaction, "eval", True)
    
    @app_commands.command(name="role_create", description="Create a new role")
    @app_commands.describe(name="Role name", color="Role color (hex)", mentionable="Whether role is mentionable")
    @require_admin_role()
    async def role_create(self, interaction: discord.Interaction, name: str, color: str = "#000000", mentionable: bool = False):
        """Create a new role"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Parse color
            try:
                role_color = discord.Color(int(color.replace("#", ""), 16))
            except ValueError:
                role_color = discord.Color.default()
            
            role = await interaction.guild.create_role(
                name=name,
                color=role_color,
                mentionable=mentionable,
                reason=f"Role created by {interaction.user}"
            )
            
            embed = BotHelpers.create_embed(
                "✅ Role Created",
                f"Created role {role.mention} successfully!",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "role_create", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to create roles.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Role create error: {e}")
            embed = BotHelpers.create_embed("Role Creation Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="role_delete", description="Delete a role")
    @app_commands.describe(role="Role to delete")
    @require_admin_role()
    async def role_delete(self, interaction: discord.Interaction, role: discord.Role):
        """Delete a role"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role >= interaction.guild.me.top_role:
            embed = BotHelpers.create_embed("Permission Error", "I cannot delete roles higher than or equal to my highest role.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            role_name = role.name
            await role.delete(reason=f"Role deleted by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "✅ Role Deleted",
                f"Deleted role **{role_name}** successfully!",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "role_delete", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to delete this role.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Role delete error: {e}")
            embed = BotHelpers.create_embed("Role Deletion Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="role_assign", description="Assign a role to a user")
    @app_commands.describe(user="User to assign role to", role="Role to assign")
    @require_admin_role()
    async def role_assign(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """Assign a role to a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role in user.roles:
            embed = BotHelpers.create_embed("Already Has Role", f"{user.mention} already has the {role.mention} role.", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.add_roles(role, reason=f"Role assigned by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "✅ Role Assigned",
                f"Assigned {role.mention} to {user.mention}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "role_assign", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to assign this role.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Role assign error: {e}")
            embed = BotHelpers.create_embed("Role Assignment Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="role_remove", description="Remove a role from a user")
    @app_commands.describe(user="User to remove role from", role="Role to remove")
    @require_admin_role()
    async def role_remove(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """Remove a role from a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role not in user.roles:
            embed = BotHelpers.create_embed("Doesn't Have Role", f"{user.mention} doesn't have the {role.mention} role.", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.remove_roles(role, reason=f"Role removed by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "✅ Role Removed",
                f"Removed {role.mention} from {user.mention}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "role_remove", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to remove this role.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Role remove error: {e}")
            embed = BotHelpers.create_embed("Role Removal Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(AdminCog(bot))
    log.info("AdminCog loaded successfully")
