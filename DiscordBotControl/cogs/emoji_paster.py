"""
Discord Bot Cog: Emoji Paster
Clone emojis from other servers using slash commands.

To import in bot.py, add this line:
await bot.load_extension('emoji_paster')
"""

import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
import logging

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

class EmojiPaster(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    def extract_emoji_info(self, emoji_string):
        """Extract emoji ID and name from Discord emoji format"""
        # Pattern for custom emojis: <:name:id> or <a:name:id>
        pattern = r'<(a?):([^:]+):(\d+)>'
        match = re.match(pattern, emoji_string)
        
        if match:
            animated = bool(match.group(1))
            name = match.group(2)
            emoji_id = int(match.group(3))
            return {
                'animated': animated,
                'name': name,
                'id': emoji_id,
                'url': f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if animated else 'png'}"
            }
        return None
    
    async def download_emoji(self, url):
        """Download emoji image data"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Failed to download emoji: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"Error downloading emoji: {e}")
            raise
    
    @app_commands.command(name="emoji.paster", description="Clone an emoji from another server")
    @app_commands.describe(
        emoji="The emoji to clone (e.g., <:name:123456789>)",
        new_name="Optional new name for the emoji (defaults to original name)"
    )
    async def emoji_paster(self, interaction: discord.Interaction, emoji: str, new_name: str = None):
        """Clone an emoji from another server"""
        await interaction.response.defer()
        
        try:
            # Check permissions
            if not interaction.user.guild_permissions.manage_emojis:
                await interaction.followup.send("❌ You need 'Manage Emojis' permission to use this command.", ephemeral=True)
                return
            
            # Extract emoji information
            emoji_info = self.extract_emoji_info(emoji)
            if not emoji_info:
                await interaction.followup.send("❌ Invalid emoji format. Please use a custom Discord emoji (e.g., <:name:123456789>)", ephemeral=True)
                return
            
            # Use new name if provided, otherwise use original
            final_name = new_name if new_name else emoji_info['name']
            
            # Validate emoji name
            if not re.match(r'^[a-zA-Z0-9_]{2,32}$', final_name):
                await interaction.followup.send("❌ Emoji name must be 2-32 characters long and contain only letters, numbers, and underscores.", ephemeral=True)
                return
            
            # Check if emoji already exists
            existing_emoji = discord.utils.get(interaction.guild.emojis, name=final_name)
            if existing_emoji:
                await interaction.followup.send(f"❌ An emoji with the name '{final_name}' already exists in this server.", ephemeral=True)
                return
            
            # Check emoji limits
            emoji_limit = interaction.guild.emoji_limit
            current_emoji_count = len([e for e in interaction.guild.emojis if e.animated == emoji_info['animated']])
            
            if current_emoji_count >= emoji_limit:
                emoji_type = "animated" if emoji_info['animated'] else "static"
                await interaction.followup.send(f"❌ Server has reached the {emoji_type} emoji limit ({emoji_limit}).", ephemeral=True)
                return
            
            # Download emoji
            try:
                emoji_data = await self.download_emoji(emoji_info['url'])
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to download emoji: {str(e)}", ephemeral=True)
                return
            
            # Create emoji in server
            try:
                new_emoji = await interaction.guild.create_custom_emoji(
                    name=final_name,
                    image=emoji_data,
                    reason=f"Emoji cloned by {interaction.user} ({interaction.user.id})"
                )
                
                # Success message
                embed = discord.Embed(
                    title="✅ Emoji Successfully Cloned!",
                    color=discord.Color.green(),
                    description=f"Emoji `{emoji_info['name']}` has been added as {new_emoji}"
                )
                embed.add_field(name="Original", value=emoji_info['name'], inline=True)
                embed.add_field(name="New Name", value=final_name, inline=True)
                embed.add_field(name="Type", value="Animated" if emoji_info['animated'] else "Static", inline=True)
                embed.set_thumbnail(url=emoji_info['url'])
                embed.set_footer(text=f"Cloned by {interaction.user}", icon_url=interaction.user.display_avatar.url)
                
                await interaction.followup.send(embed=embed)
                
                # Log the action
                self.logger.info(f"Emoji '{final_name}' cloned by {interaction.user} in {interaction.guild}")
                
            except discord.HTTPException as e:
                if e.status == 400:
                    await interaction.followup.send("❌ Invalid emoji file. The emoji might be corrupted or too large.", ephemeral=True)
                elif e.status == 403:
                    await interaction.followup.send("❌ Bot doesn't have permission to manage emojis in this server.", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Failed to create emoji: {str(e)}", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Unexpected error in emoji_paster: {e}")
            await interaction.followup.send("❌ An unexpected error occurred. Please try again.", ephemeral=True)
    
    @app_commands.command(name="emoji.info", description="Get information about an emoji")
    @app_commands.describe(emoji="The emoji to get information about")
    async def emoji_info(self, interaction: discord.Interaction, emoji: str):
        """Get information about an emoji"""
        emoji_info = self.extract_emoji_info(emoji)
        if not emoji_info:
            await interaction.response.send_message("❌ Invalid emoji format.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Emoji Information",
            color=discord.Color.blue()
        )
        embed.add_field(name="Name", value=emoji_info['name'], inline=True)
        embed.add_field(name="ID", value=emoji_info['id'], inline=True)
        embed.add_field(name="Type", value="Animated" if emoji_info['animated'] else "Static", inline=True)
        embed.add_field(name="URL", value=f"[Direct Link]({emoji_info['url']})", inline=False)
        embed.set_thumbnail(url=emoji_info['url'])
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiPaster(bot))
