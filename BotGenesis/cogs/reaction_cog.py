import discord
from discord.ext import commands
import json
import os
import asyncio


class ReactionCog(commands.Cog):
    """A cog that automatically adds reactions to messages and manages star reactions based on votes."""
    
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from config.json or create default if it doesn't exist."""
        default_config = {
            "target_channels": [
                1421550570342191184,
                1421549026741981194, 
                1421550094653853707,
                1421550270680272937
            ],
            "emojis": {
                "thumbs_up": "<:thumbsUp:1421558929778802780>",
                "thumbs_down": "<:thumbsDown:1421558877790408713>",
                "star": "<:star:1421559626188456017>"
            },
            "star_threshold": 5
        }
        
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                return default_config
        else:
            # Create config file with defaults
            with open("config.json", "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config
    
    def save_config(self):
        """Save current configuration to config.json."""
        try:
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Automatically add thumbs up and thumbs down reactions to messages in target channels."""
        try:
            # Skip if message is from a bot
            if message.author.bot:
                return
            
            # Check if message is in one of the target channels
            if message.channel.id not in self.config["target_channels"]:
                return
            
            # Add thumbs up and thumbs down reactions
            await message.add_reaction(self.config["emojis"]["thumbs_up"])
            await message.add_reaction(self.config["emojis"]["thumbs_down"])
            
        except discord.errors.Forbidden:
            print(f"Missing permissions to add reactions in channel {message.channel.id}")
        except discord.errors.HTTPException as e:
            print(f"HTTP error adding initial reactions: {e}")
        except Exception as e:
            print(f"Unexpected error in on_message: {e}")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Monitor reactions and add star when thumbs up threshold is reached."""
        try:
            # Skip if reaction is from a bot
            if user.bot:
                return
            
            # Check if reaction is in one of the target channels
            if reaction.message.channel.id not in self.config["target_channels"]:
                return
            
            # Check if the reaction is a thumbs up
            thumbs_up_emoji = self.config["emojis"]["thumbs_up"]
            star_emoji = self.config["emojis"]["star"]
            
            # Handle custom emoji format
            if str(reaction.emoji) == thumbs_up_emoji:
                # Count only non-bot users for the threshold
                user_count = 0
                async for reaction_user in reaction.users():
                    if not reaction_user.bot:
                        user_count += 1
                
                # Check if thumbs up count has reached the threshold
                if user_count >= self.config["star_threshold"]:
                    # Check if star reaction is already present
                    has_star = False
                    for existing_reaction in reaction.message.reactions:
                        if str(existing_reaction.emoji) == star_emoji:
                            has_star = True
                            break
                    
                    # Add star reaction if not already present
                    if not has_star:
                        await reaction.message.add_reaction(star_emoji)
                        
        except discord.errors.Forbidden:
            print(f"Missing permissions to add star reaction in channel {reaction.message.channel.id}")
        except discord.errors.HTTPException as e:
            print(f"HTTP error adding star reaction: {e}")
        except Exception as e:
            print(f"Unexpected error in on_reaction_add: {e}")
    
    @commands.command(name="set_threshold")
    @commands.has_permissions(administrator=True)
    async def set_threshold(self, ctx, threshold: int):
        """Set the star reaction threshold (admin only)."""
        if threshold < 1:
            await ctx.send("Threshold must be at least 1.")
            return
        
        self.config["star_threshold"] = threshold
        self.save_config()
        await ctx.send(f"Star reaction threshold set to {threshold}.")
    
    @commands.command(name="show_config")
    @commands.has_permissions(administrator=True)
    async def show_config(self, ctx):
        """Show current configuration (admin only)."""
        embed = discord.Embed(title="Reaction Cog Configuration", color=0x00ff00)
        embed.add_field(name="Star Threshold", value=self.config["star_threshold"], inline=False)
        embed.add_field(name="Target Channels", value="\n".join([f"<#{channel_id}>" for channel_id in self.config["target_channels"]]), inline=False)
        embed.add_field(name="Emojis", value=f"👍: {self.config['emojis']['thumbs_up']}\n👎: {self.config['emojis']['thumbs_down']}\n⭐: {self.config['emojis']['star']}", inline=False)
        await ctx.send(embed=embed)
    
    @commands.command(name="reload_config")
    @commands.has_permissions(administrator=True)
    async def reload_config(self, ctx):
        """Reload configuration from file (admin only)."""
        self.config = self.load_config()
        await ctx.send("Configuration reloaded successfully.")


async def setup(bot):
    """Setup function for loading the cog."""
    await bot.add_cog(ReactionCog(bot))