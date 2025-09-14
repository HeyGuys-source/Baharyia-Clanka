"""
Utility Commands Cog
General utility commands for server management and information
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, List

import discord
from discord.ext import commands
from discord import app_commands

from config.settings import settings
from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

log = get_logger("utility_cog")

class UtilityCog(commands.Cog, name="Utility"):
    """General utility commands and server management tools"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(name="ping", description="Check bot latency and response time")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency"""
        latency = round(self.bot.latency * 1000)
        
        embed = BotHelpers.create_embed(
            "🏓 Pong!",
            f"Bot latency: **{latency}ms**",
            "success"
        )
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "ping", True)
    
    @app_commands.command(name="invite_link", description="Get the bot's invite link")
    async def invite_link(self, interaction: discord.Interaction):
        """Generate bot invite link"""
        permissions = discord.Permissions(
            ban_members=True,
            kick_members=True,
            manage_messages=True,
            manage_roles=True,
            manage_channels=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            add_reactions=True,
            use_slash_commands=True
        )
        
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=("bot", "applications.commands")
        )
        
        embed = BotHelpers.create_embed(
            "🔗 Bot Invite Link",
            f"[Click here to invite me to your server!]({invite_url})",
            "primary"
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await log_command_usage(interaction, "invite_link", True)
    
    @app_commands.command(name="command_list", description="List all available commands")
    async def command_list(self, interaction: discord.Interaction):
        """List all available slash commands"""
        commands_by_cog = {}
        
        for command in self.bot.tree.walk_commands():
            cog_name = getattr(command, 'extras', {}).get('cog', 'No Category')
            if hasattr(command, 'parent') and command.parent:
                continue  # Skip subcommands for now
                
            if cog_name not in commands_by_cog:
                commands_by_cog[cog_name] = []
            commands_by_cog[cog_name].append(command)
        
        embed = BotHelpers.create_embed(
            "📋 Available Commands",
            f"Total: {len([cmd for cmd in self.bot.tree.walk_commands()])} commands",
            "primary"
        )
        
        for cog_name, commands in commands_by_cog.items():
            command_list = [f"• `/{cmd.name}` - {cmd.description[:50]}{'...' if len(cmd.description) > 50 else ''}" for cmd in commands[:5]]
            if len(commands) > 5:
                command_list.append(f"• ... and {len(commands) - 5} more")
            
            embed.add_field(
                name=f"{cog_name} ({len(commands)})",
                value="\n".join(command_list) or "No commands",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "command_list", True)
    
    @app_commands.command(name="embed_creator", description="Create a custom embed message")
    @app_commands.describe(
        title="Embed title",
        description="Embed description", 
        color="Embed color (hex code or primary/secondary/success/error/warning/info)",
        thumbnail="Thumbnail URL (optional)",
        image="Image URL (optional)"
    )
    @require_admin_role()
    async def embed_creator(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        color: str = "primary",
        thumbnail: Optional[str] = None,
        image: Optional[str] = None
    ):
        """Create a custom embed"""
        try:
            # Parse color
            embed_color = color
            if color.startswith("#"):
                try:
                    embed_color = int(color.replace("#", ""), 16)
                except ValueError:
                    embed_color = "primary"
            
            embed = BotHelpers.create_embed(title, description, embed_color)
            
            if thumbnail and BotHelpers.is_image_url(thumbnail):
                embed.set_thumbnail(url=thumbnail)
            
            if image and BotHelpers.is_image_url(image):
                embed.set_image(url=image)
            
            await interaction.response.send_message(embed=embed)
            await log_command_usage(interaction, "embed_creator", True)
            
        except Exception as e:
            log.error(f"Embed creator error: {e}")
            error_embed = BotHelpers.create_embed("Embed Creation Failed", f"Error: {str(e)}", "error")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="role_info", description="Get information about a role")
    @app_commands.describe(role="The role to get information about")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        """Get detailed role information"""
        
        embed = BotHelpers.create_embed(
            f"🎭 {role.name} Role Information",
            "",
            "primary"
        )
        
        embed.add_field(
            name="📋 Basic Info",
            value=f"**Name:** {role.name}\n**ID:** {role.id}\n**Color:** {role.color}\n**Position:** {role.position}",
            inline=True
        )
        
        embed.add_field(
            name="👥 Members",
            value=f"**Count:** {len(role.members)}\n**Mentionable:** {'Yes' if role.mentionable else 'No'}\n**Hoisted:** {'Yes' if role.hoist else 'No'}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Created",
            value=BotHelpers.format_datetime(role.created_at, "discord"),
            inline=True
        )
        
        # Show key permissions
        key_perms = []
        if role.permissions.administrator:
            key_perms.append("Administrator")
        if role.permissions.manage_guild:
            key_perms.append("Manage Server")
        if role.permissions.manage_roles:
            key_perms.append("Manage Roles")
        if role.permissions.manage_channels:
            key_perms.append("Manage Channels")
        if role.permissions.ban_members:
            key_perms.append("Ban Members")
        if role.permissions.kick_members:
            key_perms.append("Kick Members")
        
        if key_perms:
            embed.add_field(
                name="🔑 Key Permissions",
                value="\n".join(f"• {perm}" for perm in key_perms[:10]),
                inline=False
            )
        
        if role.color != discord.Color.default():
            embed.color = role.color
        
        await interaction.response.send_message(embed=embed)
        await log_command_usage(interaction, "role_info", True)

async def setup(bot: commands.Bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(UtilityCog(bot))
    log.info("UtilityCog loaded successfully")