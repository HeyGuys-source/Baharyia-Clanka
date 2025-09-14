"""
System Administration Commands Cog
System-level commands for bot management and monitoring
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional, List

import discord
from discord.ext import commands
from discord import app_commands

from config.settings import settings
from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

log = get_logger("system_admin_cog")

class SystemAdminCog(commands.Cog, name="System Administration"):
    """System administration and monitoring commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="load_cog", description="Load a specific cog")
    @app_commands.describe(cog="Cog name to load (e.g., cogs.admin)")
    @require_admin_role()
    async def load_cog(self, interaction: discord.Interaction, cog: str):
        """Load a specific cog"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can load cogs.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await self.bot.load_extension(cog)
            
            embed = BotHelpers.create_embed(
                "✅ Cog Loaded",
                f"Successfully loaded cog: **{cog}**",
                "success"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "load_cog", True)
            
        except commands.ExtensionAlreadyLoaded:
            embed = BotHelpers.create_embed("Already Loaded", f"Cog **{cog}** is already loaded.", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            embed = BotHelpers.create_embed("Not Found", f"Cog **{cog}** was not found.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Load cog error: {e}")
            embed = BotHelpers.create_embed("Load Failed", f"Error loading cog: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unload_cog", description="Unload a specific cog")
    @app_commands.describe(cog="Cog name to unload")
    @require_admin_role()
    async def unload_cog(self, interaction: discord.Interaction, cog: str):
        """Unload a specific cog"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can unload cogs.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await self.bot.unload_extension(cog)
            
            embed = BotHelpers.create_embed(
                "✅ Cog Unloaded",
                f"Successfully unloaded cog: **{cog}**",
                "success"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "unload_cog", True)
            
        except commands.ExtensionNotLoaded:
            embed = BotHelpers.create_embed("Not Loaded", f"Cog **{cog}** is not currently loaded.", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Unload cog error: {e}")
            embed = BotHelpers.create_embed("Unload Failed", f"Error unloading cog: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reload_cog", description="Reload a specific cog")
    @app_commands.describe(cog="Cog name to reload")
    @require_admin_role()
    async def reload_cog(self, interaction: discord.Interaction, cog: str):
        """Reload a specific cog"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can reload cogs.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await self.bot.reload_extension(cog)
            
            embed = BotHelpers.create_embed(
                "🔄 Cog Reloaded",
                f"Successfully reloaded cog: **{cog}**",
                "success"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "reload_cog", True)
            
        except commands.ExtensionNotLoaded:
            embed = BotHelpers.create_embed("Not Loaded", f"Cog **{cog}** is not currently loaded.", "warning")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Reload cog error: {e}")
            embed = BotHelpers.create_embed("Reload Failed", f"Error reloading cog: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="sync_commands", description="Sync slash commands")
    @require_admin_role()
    async def sync_commands(self, interaction: discord.Interaction):
        """Sync slash commands"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can sync commands.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            synced = await self.bot.tree.sync()
            
            embed = BotHelpers.create_embed(
                "✅ Commands Synced",
                f"Successfully synced {len(synced)} command(s)",
                "success"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "sync_commands", True)
            
        except Exception as e:
            log.error(f"Sync commands error: {e}")
            embed = BotHelpers.create_embed("Sync Failed", f"Error syncing commands: {str(e)}", "error")
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="command_stats", description="Show command usage statistics")
    @require_admin_role()
    async def command_stats(self, interaction: discord.Interaction):
        """Show command usage statistics"""
        
        # Get all commands
        all_commands = list(self.bot.tree.walk_commands())
        
        embed = BotHelpers.create_embed(
            "📊 Command Statistics",
            f"Total registered commands: **{len(all_commands)}**",
            "primary"
        )
        
        # Group commands by cog
        commands_by_cog = {}
        for command in all_commands:
            cog_name = "Unknown"
            if hasattr(command, 'extras') and command.extras.get('cog'):
                cog_name = command.extras['cog']
            elif hasattr(command, 'cog') and command.cog:
                cog_name = command.cog.qualified_name
            
            if cog_name not in commands_by_cog:
                commands_by_cog[cog_name] = []
            commands_by_cog[cog_name].append(command.name)
        
        # Add fields for each cog
        for cog_name, command_names in commands_by_cog.items():
            embed.add_field(
                name=f"{cog_name} ({len(command_names)})",
                value=", ".join(f"`{name}`" for name in command_names[:10]) + 
                      (f"\n+ {len(command_names) - 10} more..." if len(command_names) > 10 else ""),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_command_usage(interaction, "command_stats", True)
    
    @app_commands.command(name="guild_list", description="List all guilds the bot is in")
    @require_admin_role()
    async def guild_list(self, interaction: discord.Interaction):
        """List all guilds the bot is in"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can view guild list.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        guilds = self.bot.guilds
        total_members = sum(guild.member_count for guild in guilds)
        
        embed = BotHelpers.create_embed(
            "🏰 Bot Guilds",
            f"Connected to **{len(guilds)}** guild(s) with **{total_members:,}** total members",
            "primary"
        )
        
        # Show top guilds by member count
        sorted_guilds = sorted(guilds, key=lambda g: g.member_count, reverse=True)[:10]
        
        guild_list = []
        for guild in sorted_guilds:
            guild_list.append(f"**{guild.name}** - {guild.member_count:,} members")
        
        if guild_list:
            embed.add_field(
                name="Top Guilds",
                value="\n".join(guild_list),
                inline=False
            )
        
        if len(guilds) > 10:
            embed.add_field(
                name="Additional",
                value=f"... and {len(guilds) - 10} more guilds",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_command_usage(interaction, "guild_list", True)
    
    @app_commands.command(name="leave_guild", description="Make the bot leave a guild")
    @app_commands.describe(guild_id="Guild ID to leave")
    @require_admin_role()
    async def leave_guild(self, interaction: discord.Interaction, guild_id: str):
        """Make the bot leave a guild"""
        # Restrict to bot owner only
        app_info = await self.bot.application_info()
        if interaction.user.id != app_info.owner.id:
            embed = BotHelpers.create_embed("No Permission", "Only the bot owner can make the bot leave guilds.", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                embed = BotHelpers.create_embed("Guild Not Found", "Could not find a guild with that ID.", "error")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            guild_name = guild.name
            await guild.leave()
            
            embed = BotHelpers.create_embed(
                "✅ Left Guild",
                f"Successfully left guild: **{guild_name}**",
                "success"
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await log_command_usage(interaction, "leave_guild", True)
            
        except (ValueError, discord.HTTPException) as e:
            embed = BotHelpers.create_embed("Leave Failed", f"Error leaving guild: {str(e)}", "error")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="botinfo", description="Show comprehensive bot information")
    async def botinfo(self, interaction: discord.Interaction):
        """Show comprehensive bot information"""
        
        embed = BotHelpers.create_embed(
            f"🤖 {self.bot.user.display_name} Information",
            "Advanced Discord Bot with comprehensive admin features",
            "primary"
        )
        
        # Basic info
        embed.add_field(
            name="📋 Basic Info",
            value=f"**Name:** {self.bot.user}\n**ID:** {self.bot.user.id}\n**Created:** {BotHelpers.format_datetime(self.bot.user.created_at, 'discord')}",
            inline=True
        )
        
        # Statistics
        embed.add_field(
            name="📊 Statistics",
            value=f"**Guilds:** {len(self.bot.guilds):,}\n**Users:** {sum(g.member_count for g in self.bot.guilds):,}\n**Commands:** {len([cmd for cmd in self.bot.tree.walk_commands()])}",
            inline=True
        )
        
        # System info
        embed.add_field(
            name="⚙️ System",
            value=f"**Python:** {sys.version.split()[0]}\n**discord.py:** {discord.__version__}\n**Latency:** {round(self.bot.latency * 1000)}ms",
            inline=True
        )
        
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "botinfo", True)

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(SystemAdminCog(bot))
    log.info("SystemAdminCog loaded successfully")