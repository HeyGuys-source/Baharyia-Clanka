import discord
from discord.ext import commands


class YTReactionCog(commands.Cog):
    """A cog that automatically adds YT emoji reactions to every message in a specific channel."""
    
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1421567126149271662
        self.yt_emoji = "<:YT:1421567032419287091>"
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Automatically add YT emoji reaction to every message in the target channel."""
        try:
            # Skip if message is from a bot to avoid potential loops
            if message.author.bot:
                return
            
            # Check if message is in the target channel
            if message.channel.id != self.target_channel_id:
                return
            
            # Add YT emoji reaction
            await message.add_reaction(self.yt_emoji)
            
        except discord.errors.Forbidden:
            print(f"Missing permissions to add YT reaction in channel {message.channel.id}")
        except discord.errors.HTTPException as e:
            print(f"HTTP error adding YT reaction: {e}")
        except Exception as e:
            print(f"Unexpected error in YT reaction cog: {e}")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(YTReactionCog(bot))