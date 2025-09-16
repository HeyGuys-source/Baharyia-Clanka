"""
Echo Cog
Administrator-only cog for making the bot send custom messages with advanced formatting options.
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import logging

logger = logging.getLogger(__name__)

class EchoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def create_embed(self, title, description, color=0x3498db, footer=None):
        """Create a styled embed"""
        embed = discord.Embed(title=title, description=description, color=color)
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text="Echo System", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed
    
    @app_commands.command(name="echo", description="Make the bot say something (Administrator only)")
    @app_commands.describe(
        message="The message content to send",
        format_type="Format type: 'plain' for normal text or 'embed' for rich embed",
        reply_to_id="Message ID to reply to (optional)",
        channel="Channel to send message to (optional)"
    )
    async def echo(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        format_type: str = "plain",
        reply_to_id: str = None,
        channel: discord.TextChannel = None
    ):
        # Check if user is administrator
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Access Denied", "This command is restricted to administrators only.", 0xff0000),
                ephemeral=True
            )
        
        # Set target channel
        target_channel = channel or interaction.channel
        
        try:
            # Handle reply functionality
            reference = None
            if reply_to_id:
                try:
                    reply_message = await target_channel.fetch_message(int(reply_to_id))
                    reference = reply_message
                except (discord.NotFound, ValueError):
                    return await interaction.response.send_message(
                        embed=self.create_embed("❌ Error", "Could not find message with that ID to reply to.", 0xff0000),
                        ephemeral=True
                    )
            
            # Send message based on format type
            if format_type.lower() == "embed":
                # Parse JSON-like content for advanced embed formatting
                try:
                    if message.startswith('{') and message.endswith('}'):
                        embed_data = json.loads(message)
                        embed = discord.Embed()
                        
                        if 'title' in embed_data:
                            embed.title = embed_data['title']
                        if 'description' in embed_data:
                            embed.description = embed_data['description']
                        if 'color' in embed_data:
                            embed.color = int(embed_data['color'], 16) if isinstance(embed_data['color'], str) else embed_data['color']
                        if 'thumbnail' in embed_data:
                            embed.set_thumbnail(url=embed_data['thumbnail'])
                        if 'image' in embed_data:
                            embed.set_image(url=embed_data['image'])
                        if 'footer' in embed_data:
                            embed.set_footer(text=embed_data['footer'])
                        if 'author' in embed_data:
                            embed.set_author(name=embed_data['author'])
                        if 'fields' in embed_data:
                            for field in embed_data['fields']:
                                embed.add_field(
                                    name=field.get('name', 'Field'),
                                    value=field.get('value', 'Value'),
                                    inline=field.get('inline', False)
                                )
                        
                        sent_message = await target_channel.send(embed=embed, reference=reference)
                    else:
                        # Simple embed with just the message as description
                        embed = discord.Embed(description=message, color=0x3498db)
                        sent_message = await target_channel.send(embed=embed, reference=reference)
                
                except json.JSONDecodeError:
                    # If JSON parsing fails, create simple embed
                    embed = discord.Embed(description=message, color=0x3498db)
                    sent_message = await target_channel.send(embed=embed, reference=reference)
                
            else:
                # Plain text message
                sent_message = await target_channel.send(message, reference=reference)
            
            # Confirmation message
            confirmation_embed = self.create_embed(
                "✅ Message Sent Successfully",
                f"**Channel:** {target_channel.mention}\n"
                f"**Format:** {format_type.title()}\n"
                f"**Reply To:** {'Yes (ID: ' + reply_to_id + ')' if reply_to_id else 'No'}\n"
                f"**Message ID:** {sent_message.id}",
                0x2ecc71
            )
            
            await interaction.response.send_message(embed=confirmation_embed, ephemeral=True)
            
            # Log the action
            try:
                if self.bot.db_pool:
                    async with self.bot.db_pool.acquire() as conn:
                        result = await conn.fetchrow(
                            "SELECT log_channel_id FROM guild_settings WHERE guild_id = $1",
                            interaction.guild.id
                        )
                        
                    if result and result['log_channel_id']:
                        log_channel = interaction.guild.get_channel(result['log_channel_id'])
                        if log_channel and log_channel != target_channel:
                            log_embed = self.create_embed(
                                "📢 Echo Command Used",
                                f"**Administrator:** {interaction.user.mention}\n"
                                f"**Channel:** {target_channel.mention}\n"
                                f"**Format:** {format_type.title()}\n"
                                f"**Reply:** {'Yes' if reply_to_id else 'No'}\n"
                                f"**Message Preview:** {message[:100]}{'...' if len(message) > 100 else ''}",
                                0x9b59b6
                            )
                            await log_channel.send(embed=log_embed)
            except Exception as e:
                logger.error(f"Failed to log echo action: {e}")
                
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Error", "I don't have permission to send messages in that channel.", 0xff0000),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to send message: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="echo_help", description="Get help for using the echo command")
    async def echo_help(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Access Denied", "This command is restricted to administrators only.", 0xff0000),
                ephemeral=True
            )
        
        help_embed = discord.Embed(
            title="📢 Echo Command Help",
            color=0x3498db
        )
        
        help_embed.add_field(
            name="Basic Usage",
            value="Use `/echo` to make the bot send a message in any channel.",
            inline=False
        )
        
        help_embed.add_field(
            name="Parameters",
            value="""
            **message** - The content to send (required)
            **format_type** - 'plain' for text or 'embed' for rich formatting
            **reply_to_id** - Message ID to reply to (optional)
            **channel** - Target channel (defaults to current channel)
            """,
            inline=False
        )
        
        help_embed.add_field(
            name="Plain Text Example",
            value="`/echo message:Hello everyone! format_type:plain`",
            inline=False
        )
        
        help_embed.add_field(
            name="Simple Embed Example",
            value="`/echo message:Welcome to our server! format_type:embed`",
            inline=False
        )
        
        help_embed.add_field(
            name="Advanced Embed Example",
            value="""```json
{
  "title": "Server Rules",
  "description": "Please follow these rules",
  "color": "0x3498db",
  "fields": [
    {
      "name": "Rule 1",
      "value": "Be respectful",
      "inline": true
    },
    {
      "name": "Rule 2", 
      "value": "No spam",
      "inline": true
    }
  ],
  "footer": "Thank you for reading"
}```""",
            inline=False
        )
        
        help_embed.add_field(
            name="Reply Example",
            value="`/echo message:Thanks for that! reply_to_id:1234567890`\n*Right-click a message and copy ID to get the message ID*",
            inline=False
        )
        
        help_embed.set_footer(text="Echo System - Administrator Only")
        
        await interaction.response.send_message(embed=help_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EchoCog(bot))