"""
Discord Bot Cog: Echo Command
Bot sends messages with embed options and reply functionality (Admin only).

To import in bot.py, add this line:
await bot.load_extension('echo')
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

class Echo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    @app_commands.command(name="echo", description="Make the bot say something (Admin only)")
    @app_commands.describe(
        message="The message you want the bot to say",
        format_type="Choose between plain text or embed format",
        reply_to="Optional: Message ID to reply to"
    )
    @app_commands.choices(format_type=[
        app_commands.Choice(name="Plain Text", value="plain"),
        app_commands.Choice(name="Embed", value="embed")
    ])
    async def echo(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        format_type: app_commands.Choice[str] = None,
        reply_to: str = None
    ):
        """Echo command - Bot says what you want (Admin only)"""
        
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        # Acknowledge the command without showing who used it
        await interaction.response.send_message("✅ Message sent!", ephemeral=True)
        
        try:
            # Get the format type (default to plain if not specified)
            chosen_format = format_type.value if format_type else "plain"
            
            # Handle reply functionality
            reference_message = None
            if reply_to:
                try:
                    # Try to fetch the message to reply to
                    message_id = int(reply_to)
                    reference_message = await interaction.channel.fetch_message(message_id)
                except (ValueError, discord.NotFound):
                    await interaction.edit_original_response(content="❌ Invalid message ID or message not found.")
                    return
                except discord.Forbidden:
                    await interaction.edit_original_response(content="❌ Don't have permission to access that message.")
                    return
            
            # Send the message based on format type
            if chosen_format == "embed":
                embed = discord.Embed(
                    description=message,
                    color=discord.Color.blurple()
                )
                embed.set_footer(text=f"Echo • {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
                
                if reference_message:
                    await reference_message.reply(embed=embed)
                else:
                    await interaction.channel.send(embed=embed)
            else:
                # Plain text format
                if reference_message:
                    await reference_message.reply(message)
                else:
                    await interaction.channel.send(message)
            
            # Log the echo command usage
            self.logger.info(f"Echo command used by {interaction.user} in {interaction.guild.name}#{interaction.channel.name}")
            
        except discord.HTTPException as e:
            await interaction.edit_original_response(content=f"❌ Failed to send message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error in echo command: {e}")
            await interaction.edit_original_response(content="❌ An unexpected error occurred.")
    
    @app_commands.command(name="echo.embed", description="Send a custom embed message (Admin only)")
    @app_commands.describe(
        title="Embed title",
        description="Embed description/content",
        color="Embed color (hex code, e.g., #ff0000)",
        footer="Optional footer text",
        thumbnail="Optional thumbnail URL",
        image="Optional image URL",
        reply_to="Optional: Message ID to reply to"
    )
    async def echo_embed(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        color: str = None,
        footer: str = None,
        thumbnail: str = None,
        image: str = None,
        reply_to: str = None
    ):
        """Advanced embed echo command"""
        
        # Check administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("✅ Embed sent!", ephemeral=True)
        
        try:
            # Create embed
            embed = discord.Embed(title=title, description=description)
            
            # Set color
            if color:
                try:
                    # Remove # if present and convert to int
                    color_hex = color.lstrip('#')
                    embed.color = discord.Color(int(color_hex, 16))
                except ValueError:
                    embed.color = discord.Color.blurple()
            else:
                embed.color = discord.Color.blurple()
            
            # Set footer
            if footer:
                embed.set_footer(text=footer, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            # Set thumbnail
            if thumbnail:
                try:
                    embed.set_thumbnail(url=thumbnail)
                except:
                    pass  # Invalid URL, skip thumbnail
            
            # Set image
            if image:
                try:
                    embed.set_image(url=image)
                except:
                    pass  # Invalid URL, skip image
            
            # Handle reply
            reference_message = None
            if reply_to:
                try:
                    message_id = int(reply_to)
                    reference_message = await interaction.channel.fetch_message(message_id)
                except:
                    pass  # Invalid message ID, send normally
            
            # Send embed
            if reference_message:
                await reference_message.reply(embed=embed)
            else:
                await interaction.channel.send(embed=embed)
            
            self.logger.info(f"Echo embed used by {interaction.user} in {interaction.guild.name}#{interaction.channel.name}")
            
        except Exception as e:
            self.logger.error(f"Error in echo embed: {e}")
            await interaction.edit_original_response(content="❌ Failed to send embed.")

async def setup(bot):
    await bot.add_cog(Echo(bot))
