"""
Extended Admin Commands Cog
Additional specialized admin commands to reach 40+ total commands
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Literal
from urllib.parse import urlparse

import discord
from discord.ext import commands
from discord import app_commands

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

log = get_logger("advanced_admin_cog")

class AdvancedAdminCog(commands.Cog, name="Advanced Admin"):
    """Extended administration commands for advanced server management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    # ======== CHANNEL MANAGEMENT COMMANDS ========
    
    @app_commands.command(name="channel_create", description="Create a new text or voice channel")
    @app_commands.describe(
        name="Channel name",
        channel_type="Type of channel to create",
        category="Category to place channel in (optional)"
    )
    @require_admin_role()
    async def channel_create(
        self,
        interaction: discord.Interaction,
        name: str,
        channel_type: Literal["text", "voice"] = "text",
        category: Optional[discord.CategoryChannel] = None
    ):
        """Create a new channel"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_channels:
            embed = BotHelpers.create_embed("No Permission", "You need manage channels permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            if channel_type == "text":
                channel = await interaction.guild.create_text_channel(
                    name=name,
                    category=category,
                    reason=f"Channel created by {interaction.user}"
                )
            else:
                channel = await interaction.guild.create_voice_channel(
                    name=name,
                    category=category,
                    reason=f"Channel created by {interaction.user}"
                )
            
            embed = BotHelpers.create_embed(
                "✅ Channel Created",
                f"Created {channel_type} channel {channel.mention}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "channel_create", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to create channels.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Channel create error: {e}")
            embed = BotHelpers.create_embed("Channel Creation Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="channel_delete", description="Delete a channel")
    @app_commands.describe(channel="Channel to delete")
    @require_admin_role()
    async def channel_delete(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Delete a channel"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_channels:
            embed = BotHelpers.create_embed("No Permission", "You need manage channels permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            channel_name = channel.name
            await channel.delete(reason=f"Channel deleted by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "✅ Channel Deleted",
                f"Deleted channel **#{channel_name}**",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "channel_delete", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to delete this channel.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Channel delete error: {e}")
            embed = BotHelpers.create_embed("Channel Deletion Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="slowmode", description="Set slowmode for a channel")
    @app_commands.describe(channel="Channel to modify", seconds="Slowmode delay in seconds (0-21600)")
    @require_admin_role()
    async def slowmode(self, interaction: discord.Interaction, channel: discord.TextChannel, seconds: int):
        """Set slowmode for a channel"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_channels:
            embed = BotHelpers.create_embed("No Permission", "You need manage channels permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if seconds < 0 or seconds > 21600:
            embed = BotHelpers.create_embed("Invalid Duration", "Slowmode must be between 0 and 21600 seconds (6 hours).", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await channel.edit(slowmode_delay=seconds, reason=f"Slowmode set by {interaction.user}")
            
            if seconds == 0:
                embed = BotHelpers.create_embed(
                    "✅ Slowmode Disabled",
                    f"Disabled slowmode for {channel.mention}",
                    "success"
                )
            else:
                embed = BotHelpers.create_embed(
                    "✅ Slowmode Set",
                    f"Set slowmode to {seconds} seconds for {channel.mention}",
                    "success"
                )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "slowmode", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to edit this channel.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Slowmode error: {e}")
            embed = BotHelpers.create_embed("Slowmode Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ======== MESSAGE MANAGEMENT COMMANDS ========
    
    @app_commands.command(name="pin", description="Pin a message")
    @app_commands.describe(message_id="ID of the message to pin")
    @require_admin_role()
    async def pin(self, interaction: discord.Interaction, message_id: str):
        """Pin a message"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
            embed = BotHelpers.create_embed("No Permission", "You need manage messages permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            await message.pin(reason=f"Pinned by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "📌 Message Pinned",
                f"Pinned [message]({message.jump_url}) successfully",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "pin", True)
            
        except (ValueError, discord.NotFound):
            embed = BotHelpers.create_embed("Message Not Found", "Could not find the specified message.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to pin messages.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Pin error: {e}")
            embed = BotHelpers.create_embed("Pin Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unpin", description="Unpin a message")
    @app_commands.describe(message_id="ID of the message to unpin")
    @require_admin_role()
    async def unpin(self, interaction: discord.Interaction, message_id: str):
        """Unpin a message"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_messages:
            embed = BotHelpers.create_embed("No Permission", "You need manage messages permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            await message.unpin(reason=f"Unpinned by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "📌 Message Unpinned",
                f"Unpinned [message]({message.jump_url}) successfully",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "unpin", True)
            
        except (ValueError, discord.NotFound):
            embed = BotHelpers.create_embed("Message Not Found", "Could not find the specified message.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to unpin messages.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Unpin error: {e}")
            embed = BotHelpers.create_embed("Unpin Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="say", description="Make the bot say something in a specific channel")
    @app_commands.describe(channel="Channel to send message to", message="Message to send")
    @require_admin_role()
    async def say(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        """Make the bot say something"""
        try:
            await channel.send(message)
            
            embed = BotHelpers.create_embed(
                "✅ Message Sent",
                f"Sent message to {channel.mention}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "say", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to send messages in that channel.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Say error: {e}")
            embed = BotHelpers.create_embed("Send Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ======== TEMPORARY MODERATION COMMANDS ========
    
    @app_commands.command(name="temp_ban", description="Temporarily ban a user")
    @app_commands.describe(user="User to ban", duration="Duration in hours", reason="Reason for the ban")
    @require_admin_role()
    async def temp_ban(self, interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = "No reason provided"):
        """Temporarily ban a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.ban_members:
            embed = BotHelpers.create_embed("No Permission", "You need ban members permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.ban(reason=f"Temporary ban: {reason}")
            
            embed = BotHelpers.create_embed(
                "⏰ User Temporarily Banned",
                f"{user} has been temporarily banned for {duration} hours.\n**Reason:** {reason}",
                "warning"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "temp_ban", True)
            
            # Schedule unban
            await asyncio.sleep(duration * 3600)  # Convert hours to seconds
            try:
                await interaction.guild.unban(user, reason="Temporary ban expired")
            except discord.NotFound:
                pass  # User was already unbanned
                
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to ban this user.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Temp ban error: {e}")
            embed = BotHelpers.create_embed("Temp Ban Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user_id="User ID to unban")
    @require_admin_role()
    async def unban(self, interaction: discord.Interaction, user_id: str):
        """Unban a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.ban_members:
            embed = BotHelpers.create_embed("No Permission", "You need ban members permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user}")
            
            embed = BotHelpers.create_embed(
                "✅ User Unbanned",
                f"{user} has been unbanned",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "unban", True)
            
        except (ValueError, discord.NotFound):
            embed = BotHelpers.create_embed("User Not Found", "Could not find the specified user or they are not banned.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to unban users.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Unban error: {e}")
            embed = BotHelpers.create_embed("Unban Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # ======== SERVER CONFIGURATION COMMANDS ========
    
    @app_commands.command(name="nickname", description="Change a user's nickname")
    @app_commands.describe(user="User to change nickname", nickname="New nickname (leave empty to remove)")
    @require_admin_role()
    async def nickname(self, interaction: discord.Interaction, user: discord.Member, nickname: Optional[str] = None):
        """Change a user's nickname"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_nicknames:
            embed = BotHelpers.create_embed("No Permission", "You need manage nicknames permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            old_nick = user.display_name
            await user.edit(nick=nickname, reason=f"Nickname changed by {interaction.user}")
            
            if nickname:
                embed = BotHelpers.create_embed(
                    "✅ Nickname Changed",
                    f"Changed {user.mention}'s nickname from **{old_nick}** to **{nickname}**",
                    "success"
                )
            else:
                embed = BotHelpers.create_embed(
                    "✅ Nickname Removed",
                    f"Removed {user.mention}'s nickname (was **{old_nick}**)",
                    "success"
                )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "nickname", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to change this user's nickname.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Nickname error: {e}")
            embed = BotHelpers.create_embed("Nickname Change Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(AdvancedAdminCog(bot))
    log.info("AdvancedAdminCog loaded successfully")