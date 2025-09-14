"""
Extended Moderation Commands Cog
Additional moderation tools for server management
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

log = get_logger("moderation_cog")

class ModerationCog(commands.Cog, name="Moderation"):
    """Extended moderation commands for server management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.muted_roles = {}  # Guild ID -> Role mapping
        
    @app_commands.command(name="mute", description="Mute a user by removing their ability to send messages")
    @app_commands.describe(user="User to mute", duration="Duration in minutes (optional)", reason="Reason for the mute")
    @require_admin_role()
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: Optional[int] = None, reason: str = "No reason provided"):
        """Mute a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Get or create muted role
            muted_role = await self._get_muted_role(interaction.guild)
            
            await user.add_roles(muted_role, reason=reason)
            
            duration_text = f" for {duration} minutes" if duration else ""
            embed = BotHelpers.create_embed(
                "User Muted",
                f"{user.mention} has been muted{duration_text}.\n**Reason:** {reason}",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            
            # Auto-unmute after duration
            if duration:
                await asyncio.sleep(duration * 60)
                if muted_role in user.roles:
                    await user.remove_roles(muted_role, reason="Mute duration expired")
            
            await log_command_usage(interaction, "mute", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to manage roles.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Mute command error: {e}")
            embed = BotHelpers.create_embed("Mute Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unmute", description="Unmute a previously muted user")
    @app_commands.describe(user="User to unmute")
    @require_admin_role()
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        """Unmute a user"""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.manage_roles:
            embed = BotHelpers.create_embed("No Permission", "You need manage roles permission.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            muted_role = await self._get_muted_role(interaction.guild)
            
            if muted_role not in user.roles:
                embed = BotHelpers.create_embed("Not Muted", f"{user.mention} is not currently muted.", "warning")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            await user.remove_roles(muted_role, reason="Unmuted by admin")
            
            embed = BotHelpers.create_embed(
                "User Unmuted",
                f"{user.mention} has been unmuted.",
                "success"
            )
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "unmute", True)
            
        except discord.Forbidden:
            embed = BotHelpers.create_embed("Permission Error", "I don't have permission to manage roles.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Unmute command error: {e}")
            embed = BotHelpers.create_embed("Unmute Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="warn", description="Issue a warning to a user")
    @app_commands.describe(user="User to warn", reason="Reason for the warning")
    @require_admin_role()
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
        """Issue a warning to a user"""
        embed = BotHelpers.create_embed(
            "⚠️ Warning Issued",
            f"{user.mention} has been warned.\n**Reason:** {reason}\n**Moderator:** {interaction.user.mention}",
            "warning"
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Try to DM the user
        try:
            dm_embed = BotHelpers.create_embed(
                f"Warning from {interaction.guild.name}",
                f"You have been warned by {interaction.user.mention}.\n**Reason:** {reason}",
                "warning"
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # User has DMs disabled
        
        await log_command_usage(interaction, "warn", True)
    
    async def _get_muted_role(self, guild: discord.Guild) -> discord.Role:
        """Get or create the muted role for a guild"""
        if guild.id in self.muted_roles:
            return self.muted_roles[guild.id]
        
        # Look for existing muted role
        for role in guild.roles:
            if role.name.lower() in ["muted", "timeout"]:
                self.muted_roles[guild.id] = role
                return role
        
        # Create new muted role
        muted_role = await guild.create_role(
            name="Muted",
            permissions=discord.Permissions.none(),
            reason="Auto-created muted role"
        )
        
        # Set permissions for all channels
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        
        self.muted_roles[guild.id] = muted_role
        return muted_role

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(ModerationCog(bot))
    log.info("ModerationCog loaded successfully")