"""
Discord Bot Cog: Welcome & Goodbye System
Decorative welcome and goodbye messages with channel configuration.

To import in bot.py, add this line:
await bot.load_extension('welcome_goodbye')
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

class WelcomeGoodbye(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.config_file = "welcome_config.json"
        self.config = self.load_config()
    
    def load_config(self):
        """Load welcome/goodbye configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading welcome config: {e}")
            return {}
    
    def save_config(self):
        """Save welcome/goodbye configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving welcome config: {e}")
    
    def get_guild_config(self, guild_id):
        """Get configuration for a specific guild"""
        return self.config.get(str(guild_id), {
            'welcome_channel': None,
            'goodbye_channel': None,
            'welcome_enabled': True,
            'goodbye_enabled': True,
            'custom_welcome_message': None,
            'custom_goodbye_message': None
        })
    
    def set_guild_config(self, guild_id, config):
        """Set configuration for a specific guild"""
        self.config[str(guild_id)] = config
        self.save_config()
    
    def create_welcome_embed(self, member):
        """Create decorative welcome embed"""
        guild = member.guild
        guild_config = self.get_guild_config(guild.id)
        
        # Custom message or default
        if guild_config.get('custom_welcome_message'):
            message = guild_config['custom_welcome_message'].format(
                user=member.mention,
                server=guild.name,
                user_name=member.display_name,
                member_count=guild.member_count
            )
        else:
            message = f"Welcome to **{guild.name}**, {member.mention}! 🎉\n\nWe're excited to have you here! You're our **{guild.member_count}** member."
        
        embed = discord.Embed(
            title="👋 Welcome!",
            description=message,
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        # Set user avatar as thumbnail
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Set server icon and banner if available
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.add_field(
            name="📅 Account Created",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="🆔 User ID",
            value=f"`{member.id}`",
            inline=True
        )
        
        embed.add_field(
            name="👥 Member Count",
            value=f"**{guild.member_count}** members",
            inline=True
        )
        
        embed.set_footer(
            text=f"Welcome to {guild.name}!",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        return embed
    
    def create_goodbye_embed(self, member):
        """Create decorative goodbye embed"""
        guild = member.guild
        guild_config = self.get_guild_config(guild.id)
        
        # Custom message or default
        if guild_config.get('custom_goodbye_message'):
            message = guild_config['custom_goodbye_message'].format(
                user=member.mention,
                server=guild.name,
                user_name=member.display_name,
                member_count=guild.member_count
            )
        else:
            message = f"Farewell {member.mention}, I will see you next time!! 👋\n\nWe'll miss you in **{guild.name}**."
        
        embed = discord.Embed(
            title="👋 Goodbye!",
            description=message,
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        # Set user avatar as thumbnail
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Set server icon
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        
        embed.add_field(
            name="⏰ Joined",
            value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown",
            inline=True
        )
        
        embed.add_field(
            name="👥 Members Left",
            value=f"**{guild.member_count}** members",
            inline=True
        )
        
        # Calculate time in server
        if member.joined_at:
            time_in_server = datetime.utcnow() - member.joined_at
            days = time_in_server.days
            embed.add_field(
                name="📊 Time in Server",
                value=f"{days} days",
                inline=True
            )
        
        embed.set_footer(
            text=f"Goodbye from {guild.name}",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        return embed
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        try:
            guild_config = self.get_guild_config(member.guild.id)
            
            if not guild_config.get('welcome_enabled', True):
                return
            
            welcome_channel_id = guild_config.get('welcome_channel')
            if not welcome_channel_id:
                return
            
            welcome_channel = self.bot.get_channel(welcome_channel_id)
            if not welcome_channel:
                return
            
            embed = self.create_welcome_embed(member)
            await welcome_channel.send(embed=embed)
            
            self.logger.info(f"Welcome message sent for {member} in {member.guild.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending welcome message: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        try:
            guild_config = self.get_guild_config(member.guild.id)
            
            if not guild_config.get('goodbye_enabled', True):
                return
            
            goodbye_channel_id = guild_config.get('goodbye_channel')
            if not goodbye_channel_id:
                return
            
            goodbye_channel = self.bot.get_channel(goodbye_channel_id)
            if not goodbye_channel:
                return
            
            embed = self.create_goodbye_embed(member)
            await goodbye_channel.send(embed=embed)
            
            self.logger.info(f"Goodbye message sent for {member} in {member.guild.name}")
            
        except Exception as e:
            self.logger.error(f"Error sending goodbye message: {e}")
    
    @app_commands.command(name="welcome_chan", description="Set the welcome channel")
    @app_commands.describe(channel="Channel for welcome messages")
    async def welcome_chan(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set welcome channel"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        guild_config['welcome_channel'] = channel.id
        self.set_guild_config(interaction.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"Welcome messages will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="goodbye_chan", description="Set the goodbye channel")
    @app_commands.describe(channel="Channel for goodbye messages")
    async def goodbye_chan(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set goodbye channel"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        guild_config['goodbye_channel'] = channel.id
        self.set_guild_config(interaction.guild.id, guild_config)
        
        embed = discord.Embed(
            title="✅ Goodbye Channel Set",
            description=f"Goodbye messages will now be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="welcome.toggle", description="Toggle welcome messages on/off")
    async def welcome_toggle(self, interaction: discord.Interaction):
        """Toggle welcome messages"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        guild_config['welcome_enabled'] = not guild_config.get('welcome_enabled', True)
        self.set_guild_config(interaction.guild.id, guild_config)
        
        status = "enabled" if guild_config['welcome_enabled'] else "disabled"
        emoji = "✅" if guild_config['welcome_enabled'] else "❌"
        
        embed = discord.Embed(
            title=f"{emoji} Welcome Messages {status.title()}",
            description=f"Welcome messages are now **{status}**",
            color=discord.Color.green() if guild_config['welcome_enabled'] else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="goodbye.toggle", description="Toggle goodbye messages on/off")
    async def goodbye_toggle(self, interaction: discord.Interaction):
        """Toggle goodbye messages"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        guild_config['goodbye_enabled'] = not guild_config.get('goodbye_enabled', True)
        self.set_guild_config(interaction.guild.id, guild_config)
        
        status = "enabled" if guild_config['goodbye_enabled'] else "disabled"
        emoji = "✅" if guild_config['goodbye_enabled'] else "❌"
        
        embed = discord.Embed(
            title=f"{emoji} Goodbye Messages {status.title()}",
            description=f"Goodbye messages are now **{status}**",
            color=discord.Color.green() if guild_config['goodbye_enabled'] else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="welcome.preview", description="Preview the welcome message")
    async def welcome_preview(self, interaction: discord.Interaction):
        """Preview welcome message"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        embed = self.create_welcome_embed(interaction.user)
        embed.title = "👋 Welcome Preview"
        embed.set_footer(text="This is a preview of the welcome message")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="goodbye.preview", description="Preview the goodbye message")
    async def goodbye_preview(self, interaction: discord.Interaction):
        """Preview goodbye message"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        embed = self.create_goodbye_embed(interaction.user)
        embed.title = "👋 Goodbye Preview"
        embed.set_footer(text="This is a preview of the goodbye message")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="welcome.status", description="Check welcome/goodbye configuration")
    async def welcome_status(self, interaction: discord.Interaction):
        """Check configuration status"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="📋 Welcome/Goodbye Configuration",
            color=discord.Color.blue()
        )
        
        # Welcome settings
        welcome_channel = self.bot.get_channel(guild_config.get('welcome_channel')) if guild_config.get('welcome_channel') else None
        welcome_status = "✅ Enabled" if guild_config.get('welcome_enabled', True) else "❌ Disabled"
        welcome_channel_text = welcome_channel.mention if welcome_channel else "❌ Not set"
        
        embed.add_field(
            name="👋 Welcome Messages",
            value=f"**Status:** {welcome_status}\n**Channel:** {welcome_channel_text}",
            inline=False
        )
        
        # Goodbye settings
        goodbye_channel = self.bot.get_channel(guild_config.get('goodbye_channel')) if guild_config.get('goodbye_channel') else None
        goodbye_status = "✅ Enabled" if guild_config.get('goodbye_enabled', True) else "❌ Disabled"
        goodbye_channel_text = goodbye_channel.mention if goodbye_channel else "❌ Not set"
        
        embed.add_field(
            name="👋 Goodbye Messages",
            value=f"**Status:** {goodbye_status}\n**Channel:** {goodbye_channel_text}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(WelcomeGoodbye(bot))
