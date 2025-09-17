"""
Forum Reactions Cog
Automatically adds upvote and downvote reactions to forum posts in specified channels.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging

logger = logging.getLogger(__name__)

class ForumReactionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Configuration - Forum channel and emojis
        self.FORUM_CHANNEL_ID = 1415412373363101726
        self.UPVOTE_EMOJI = "<:upvote:1417669128927444992>"
        self.DOWNVOTE_EMOJI = "<:downvote:1417669176645914624>"
        
    def create_embed(self, title, description, color=0x3498db):
        """Create a styled embed"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="Forum Reactions System")
        return embed
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        """Listen for new forum threads and add reactions"""
        try:
            # Check if this is a forum thread in our target channel
            if (hasattr(thread, 'parent') and 
                thread.parent and 
                thread.parent.id == self.FORUM_CHANNEL_ID and
                isinstance(thread.parent, discord.ForumChannel)):
                
                logger.info(f"New forum thread detected: {thread.name} in {thread.parent.name}")
                
                # Get the initial message (forum post)
                try:
                    # Wait a moment for the message to be fully created
                    await asyncio.sleep(1)
                    
                    # Get the starter message of the forum thread
                    starter_message = None
                    async for message in thread.history(limit=1, oldest_first=True):
                        starter_message = message
                        break
                    
                    if starter_message:
                        # Add upvote reaction
                        try:
                            await starter_message.add_reaction(self.UPVOTE_EMOJI)
                            logger.info(f"Added upvote reaction to forum post: {thread.name}")
                        except Exception as e:
                            logger.error(f"Failed to add upvote reaction: {e}")
                        
                        # Add downvote reaction
                        try:
                            await starter_message.add_reaction(self.DOWNVOTE_EMOJI)
                            logger.info(f"Added downvote reaction to forum post: {thread.name}")
                        except Exception as e:
                            logger.error(f"Failed to add downvote reaction: {e}")
                    else:
                        logger.warning(f"Could not find starter message for forum thread: {thread.name}")
                        
                except Exception as e:
                    logger.error(f"Error processing forum thread {thread.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in on_thread_create listener: {e}")
    
    @app_commands.command(name="forum_reactions_info", description="Get information about the forum reactions system")
    async def forum_reactions_info(self, interaction: discord.Interaction):
        """Display information about the forum reactions system"""
        
        # Get forum channel info
        forum_channel = self.bot.get_channel(self.FORUM_CHANNEL_ID)
        channel_info = f"<#{self.FORUM_CHANNEL_ID}>" if forum_channel else f"Channel ID: {self.FORUM_CHANNEL_ID} (Not found)"
        
        embed = self.create_embed(
            "🗳️ Forum Reactions System",
            f"Automatically adds voting reactions to new forum posts",
            0x3498db
        )
        
        embed.add_field(
            name="📍 Target Forum Channel",
            value=channel_info,
            inline=False
        )
        
        embed.add_field(
            name="⬆️ Upvote Emoji",
            value=self.UPVOTE_EMOJI,
            inline=True
        )
        
        embed.add_field(
            name="⬇️ Downvote Emoji", 
            value=self.DOWNVOTE_EMOJI,
            inline=True
        )
        
        embed.add_field(
            name="🔧 How it Works",
            value="• Listens for new forum threads\n• Automatically adds both reactions\n• Works only in the specified forum channel\n• Reactions are added to the initial forum post",
            inline=False
        )
        
        embed.add_field(
            name="📊 Status",
            value="✅ Active and monitoring" if forum_channel else "❌ Forum channel not accessible",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="toggle_forum_reactions", description="Enable/disable forum reactions (Administrator only)")
    @app_commands.describe(enabled="Enable or disable the forum reactions system")
    async def toggle_forum_reactions(self, interaction: discord.Interaction, enabled: bool):
        """Toggle the forum reactions system on/off"""
        
        # Check if user has administrator permissions
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Error", "This command can only be used in a server.", 0xff0000),
                ephemeral=True
            )
        
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need administrator permission to toggle this feature.", 0xff0000),
                ephemeral=True
            )
        
        # Store the setting in database if available
        try:
            if self.bot.db_pool and interaction.guild:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO guild_settings (guild_id, settings) 
                           VALUES ($1, $2) 
                           ON CONFLICT (guild_id) 
                           DO UPDATE SET settings = guild_settings.settings || $2""",
                        interaction.guild.id, 
                        '{"forum_reactions_enabled": ' + str(enabled).lower() + '}'
                    )
        except Exception as e:
            logger.error(f"Failed to save forum reactions setting: {e}")
        
        status = "enabled" if enabled else "disabled"
        color = 0x2ecc71 if enabled else 0xe74c3c
        
        embed = self.create_embed(
            f"🗳️ Forum Reactions {status.title()}",
            f"Forum reactions system has been **{status}** for this server.",
            color
        )
        
        await interaction.response.send_message(embed=embed)
        guild_name = interaction.guild.name if interaction.guild else "Unknown Guild"
        user_name = interaction.user.display_name if hasattr(interaction.user, 'display_name') else str(interaction.user)
        logger.info(f"Forum reactions {status} by {user_name} in {guild_name}")
    
    async def is_enabled(self, guild_id):
        """Check if forum reactions are enabled for a guild"""
        try:
            if self.bot.db_pool:
                async with self.bot.db_pool.acquire() as conn:
                    result = await conn.fetchrow(
                        "SELECT settings FROM guild_settings WHERE guild_id = $1",
                        guild_id
                    )
                    if result and result['settings']:
                        settings = result['settings']
                        return settings.get('forum_reactions_enabled', True)  # Default to enabled
            return True  # Default to enabled if no database
        except Exception as e:
            logger.error(f"Error checking forum reactions status: {e}")
            return True  # Default to enabled on error

async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(ForumReactionsCog(bot))
    logger.info("Forum Reactions cog loaded successfully")