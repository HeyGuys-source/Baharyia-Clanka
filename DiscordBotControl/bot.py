"""
Advanced Discord Bot with Modular Cog System
Supports dynamic loading, comprehensive admin commands, and advanced error handling
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Optional, List

import discord
from discord.ext import commands
from discord import app_commands

import keepalive
import port3001
import automod_call
# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import get_bot_token, get_colors, get_server_config, settings
from utils.logging_setup import setup_logging, setup_discord_logging, get_logger, log
from utils.permissions import permission_manager
from utils.helpers import BotHelpers

# Initialize logging
log = setup_logging()

class AdvancedBot(commands.Bot):
    """Advanced Discord Bot with comprehensive features"""
    
    def __init__(self):
        # Get configuration
        self.colors = get_colors()
        self.server_config = get_server_config()
        
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guild_messages = True
        intents.guilds = True
        intents.members = True
        intents.reactions = True
        
        # Initialize bot with slash commands only
        super().__init__(
            command_prefix=settings.get("bot.prefix", "!"),  # For hybrid commands
            intents=intents,
            help_command=None,  # Disable default help command
            case_insensitive=True,
            activity=self._get_activity(),
            status=self._get_status()
        )
        
        # Bot statistics and state
        self.start_time = None
        self.cog_load_errors = []
        self.command_stats = {}
        
        # Initialize web server port
        self.port = int(os.environ.get("PORT", self.server_config.get("port", 3001)))
        
        log.info("AdvancedBot initialized with comprehensive features")
    
    def _get_activity(self) -> Optional[discord.Activity]:
        """Get bot activity from configuration"""
        activity_config = settings.get("bot.activity", {})
        activity_type = activity_config.get("type", "streaming")
        activity_name = activity_config.get("name", "Magster's kidnapping tape")
        
        type_mapping = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming
        }
        
        return discord.Activity(
            type=type_mapping.get(activity_type, discord.ActivityType.playing),
            name=activity_name
        )
    
    def _get_status(self) -> discord.Status:
        """Get bot status from configuration"""
        status_str = settings.get("bot.status", "online")
        status_mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }
        return status_mapping.get(status_str, discord.Status.online)
    
    async def setup_hook(self):
        """Setup hook called when bot is starting"""
        self.start_time = discord.utils.utcnow()
        
        log.info("Setting up bot...")
        
        # Setup Discord logging if channel ID is provided
        log_channel_id = settings.get("logging.log_channel_id")
        if log_channel_id:
            try:
                setup_discord_logging(self, int(log_channel_id))
                log.info(f"Discord logging enabled for channel {log_channel_id}")
            except (ValueError, TypeError):
                log.warning("Invalid log channel ID in configuration")
        
        # Load all cogs
        await self._load_all_cogs()
        
        # Sync commands globally (for production, consider guild-specific sync)
        try:
            log.info("Syncing application commands...")
            synced = await self.tree.sync()
            log.success(f"Synced {len(synced)} command(s)")
        except Exception as e:
            log.error(f"Failed to sync commands: {e}")
        
        log.success("Bot setup completed successfully!")
    
    async def _load_all_cogs(self):
        """Load all configured cogs"""
        autoload_cogs = settings.get("cogs.autoload", [
            "cogs.automod_call",
            "cogs.automod",
            "cogs.echo",
            "cogs.emojo_paster",
            "cogs.keepalive",
            "cogs.lockdown",
            "cogs.port3001",
            "cogs.trigger_system",
            "cogs.vclockdown",
            "cogs.welcome_goodbye"
        ])
        
        log.info(f"Loading {len(autoload_cogs)} cogs...")
        
        for cog_name in autoload_cogs:
            try:
                await self.load_extension(cog_name)
                log.success(f"Loaded cog: {cog_name}")
            except Exception as e:
                error_msg = f"Failed to load cog {cog_name}: {str(e)}"
                log.error(error_msg)
                self.cog_load_errors.append(error_msg)
        
        if self.cog_load_errors:
            log.warning(f"{len(self.cog_load_errors)} cog(s) failed to load")
        else:
            log.success("All cogs loaded successfully!")
    
    try: 
        await self.tree.clear_commands()  # clears old leftover commands
        await self.tree.sync()            # syncs only currently loaded commands
        log.success("Command tree cleared and synced!")
    except Exception as e:
        log.error(f"Failed to clear/sync command tree: {e}")
        
    async def on_ready(self):
        """Called when bot is ready"""
        log.success(f"Bot is ready!")
        log.info(f"Logged in as: {self.user} (ID: {self.user.id})")
        log.info(f"Connected to {len(self.guilds)} guild(s)")
        log.info(f"Serving {sum(guild.member_count for guild in self.guilds)} users")
        
        # Log any cog loading errors
        if self.cog_load_errors:
            log.warning("Cog loading errors:")
            for error in self.cog_load_errors:
                log.warning(f"  - {error}")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Called when bot joins a new guild"""
        log.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        log.info(f"Guild has {guild.member_count} members")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when bot leaves a guild"""
        log.info(f"Left guild: {guild.name} (ID: {guild.id})")
    
    async def on_application_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Global error handler for application commands"""
        log.error(f"Application command error in {interaction.command}: {error}")
        
        # Create error embed
        embed = discord.Embed(
            title="❌ Command Error",
            color=int(self.colors["error"].replace("#", ""), 16),
            timestamp=discord.utils.utcnow()
        )
        
        if isinstance(error, app_commands.CommandOnCooldown):
            embed.description = f"Command is on cooldown. Try again in {error.retry_after:.1f} seconds."
        elif isinstance(error, app_commands.MissingPermissions):
            embed.description = f"You're missing required permissions: {', '.join(error.missing_permissions)}"
        elif isinstance(error, app_commands.BotMissingPermissions):
            embed.description = f"I'm missing required permissions: {', '.join(error.missing_permissions)}"
        elif isinstance(error, app_commands.CommandNotFound):
            embed.description = "Command not found."
        else:
            embed.description = "An unexpected error occurred while processing your command."
            embed.add_field(
                name="Error Details",
                value=f"```{str(error)[:1000]}```",
                inline=False
            )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            log.error(f"Failed to send error message: {e}")
    
    async def on_error(self, event: str, *args, **kwargs):
        """Global error handler"""
        log.error(f"Error in event {event}:")
        log.error(traceback.format_exc())
    
    async def close(self):
        """Clean shutdown"""
        log.info("Shutting down bot...")
        await super().close()
        log.info("Bot shut down complete")

class CogManager:
    """Advanced cog management system"""
    
    def __init__(self, bot: AdvancedBot):
        self.bot = bot
        self.log = get_logger("CogManager")
    
    async def load_cog(self, cog_name: str) -> bool:
        """Load a single cog"""
        try:
            await self.bot.load_extension(cog_name)
            self.log.success(f"Loaded cog: {cog_name}")
            return True
        except Exception as e:
            self.log.error(f"Failed to load cog {cog_name}: {e}")
            return False
    
    async def unload_cog(self, cog_name: str) -> bool:
        """Unload a single cog"""
        try:
            await self.bot.unload_extension(cog_name)
            self.log.success(f"Unloaded cog: {cog_name}")
            return True
        except Exception as e:
            self.log.error(f"Failed to unload cog {cog_name}: {e}")
            return False
    
    async def reload_cog(self, cog_name: str) -> bool:
        """Reload a single cog"""
        try:
            await self.bot.reload_extension(cog_name)
            self.log.success(f"Reloaded cog: {cog_name}")
            return True
        except Exception as e:
            self.log.error(f"Failed to reload cog {cog_name}: {e}")
            return False
    
    async def reload_all_cogs(self) -> List[str]:
        """Reload all loaded cogs"""
        reloaded = []
        failed = []
        
        for cog_name in list(self.bot.extensions.keys()):
            if await self.reload_cog(cog_name):
                reloaded.append(cog_name)
            else:
                failed.append(cog_name)
        
        self.log.info(f"Reloaded {len(reloaded)} cog(s), {len(failed)} failed")
        return reloaded
    
    def get_loaded_cogs(self) -> List[str]:
        """Get list of loaded cogs"""
        return list(self.bot.extensions.keys())

async def main():
    """Main function to run the bot"""
    try:
        # Create bot instance
        bot = AdvancedBot()
        
        # Create cog manager
        bot.cog_manager = CogManager(bot)
        
        # Get bot token from environment/config
        try:
            token = get_bot_token()
            if not token:
                log.error("Bot token is not configured. Please set BOT_TOKEN environment variable.")
                return
        except Exception as e:
            log.error(f"Failed to get bot token: {e}")
            return
        
        # Run the bot
        log.info("Starting bot...")
        await bot.start(token)
        
    except discord.LoginFailure:
        log.error("Invalid bot token provided")
    except discord.PrivilegedIntentsRequired:
        log.error("Bot requires privileged intents. Please enable them in Discord Developer Portal.")
    except Exception as e:
        log.error(f"Fatal error: {e}")
        log.error(traceback.format_exc())
    finally:
        log.info("Bot session ended")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot stopped by user")
    except Exception as e:
        log.error(f"Unhandled exception: {e}")
        sys.exit(1)
