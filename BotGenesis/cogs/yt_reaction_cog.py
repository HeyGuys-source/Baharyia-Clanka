import discord
from discord.ext import commands


class YTReactionCog(commands.Cog):
    """A cog that automatically adds YT emoji reactions to every message in a specific channel."""
    
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1421567126149271662
        self.yt_emoji_id = 1421567032419287091
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Automatically add YT emoji reaction to every message in the target channel."""
        try:
            # Debug logging - check your onrender.com logs for these
            print(f"Message received - Channel ID: {message.channel.id}, Author: {message.author}, Bot: {message.author.bot}")
            
            # Skip if message is from a bot to avoid potential loops
            if message.author.bot:
                return
            
            # Check if message is in the target channel or thread
            is_target_channel = message.channel.id == self.target_channel_id
            is_target_thread = (hasattr(message.channel, 'parent_id') and 
                              message.channel.parent_id == self.target_channel_id)
            
            if not (is_target_channel or is_target_thread):
                return
            
            print(f"Target channel matched! Attempting to add YT reaction...")
            
            # Try to get the emoji from the guild first (more reliable)
            yt_emoji = discord.utils.get(message.guild.emojis, id=self.yt_emoji_id)
            
            if yt_emoji:
                print(f"Found YT emoji in guild: {yt_emoji}")
                await message.add_reaction(yt_emoji)
            else:
                # Fallback to string format
                print(f"YT emoji not found in guild, trying string format...")
                await message.add_reaction(f"<:YT:{self.yt_emoji_id}>")
            
            print("YT reaction added successfully!")
            
        except discord.errors.Forbidden as e:
            print(f"PERMISSION ERROR: Missing permissions to add YT reaction in channel {message.channel.id}: {e}")
        except discord.errors.HTTPException as e:
            print(f"HTTP ERROR adding YT reaction: {e}")
        except Exception as e:
            print(f"UNEXPECTED ERROR in YT reaction cog: {e}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(YTReactionCog(bot))
