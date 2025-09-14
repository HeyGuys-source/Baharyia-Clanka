"""
Advanced Logging System for Discord Bot
Supports colored console output, file logging, and Discord channel logging
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from colorama import init, Fore, Back, Style
import discord
from discord.ext import commands

from config.settings import get_logging_config, get_colors

# Initialize colorama for Windows compatibility
init(autoreset=True)

class ColoredFormatter:
    """Custom formatter for colored console output"""
    
    def __init__(self):
        self.colors = get_colors()
        self.level_colors = {
            "TRACE": Fore.MAGENTA,
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "SUCCESS": Fore.GREEN + Style.BRIGHT,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Back.WHITE + Style.BRIGHT
        }
    
    def format(self, record):
        """Format log record with colors"""
        level_color = self.level_colors.get(record["level"].name, "")
        
        # Create colored format string
        format_string = (
            f"{Fore.BLUE}{{time:HH:mm:ss}}{Style.RESET_ALL} | "
            f"{level_color}{{level: <8}}{Style.RESET_ALL} | "
            f"{Fore.MAGENTA}{{name}}{Style.RESET_ALL}:"
            f"{Fore.CYAN}{{function}}{Style.RESET_ALL}:"
            f"{Fore.YELLOW}{{line}}{Style.RESET_ALL} | "
            f"{{message}}"
        )
        
        return format_string

class DiscordLogHandler:
    """Custom log handler for sending logs to Discord channel"""
    
    def __init__(self, bot: Optional[commands.Bot] = None):
        self.bot = bot
        self.log_channel_id = None
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
    def set_bot(self, bot: commands.Bot):
        """Set the bot instance"""
        self.bot = bot
        
    def set_log_channel(self, channel_id: int):
        """Set the log channel ID"""
        self.log_channel_id = channel_id
        
    async def send_log(self, level: str, message: str, **kwargs):
        """Send log message to Discord channel"""
        if not self.bot or not self.log_channel_id:
            return
            
        try:
            channel = self.bot.get_channel(self.log_channel_id)
            if not channel or not hasattr(channel, 'send'):
                return
                
            colors = get_colors()
            color_map = {
                "INFO": int(colors["info"].replace("#", ""), 16),
                "WARNING": int(colors["warning"].replace("#", ""), 16),
                "ERROR": int(colors["error"].replace("#", ""), 16),
                "CRITICAL": int(colors["error"].replace("#", ""), 16),
                "SUCCESS": int(colors["success"].replace("#", ""), 16),
            }
            
            embed = discord.Embed(
                title=f"{level} Log",
                description=f"```{message[:1900]}```",
                color=color_map.get(level, int(colors["primary"].replace("#", ""), 16)),
                timestamp=kwargs.get("timestamp", discord.utils.utcnow())
            )
            
            if len(message) > 1900:
                embed.add_field(name="Truncated", value="Message was truncated due to length", inline=False)
            
            await channel.send(embed=embed)
            
        except Exception as e:
            # Avoid infinite recursion by not logging this error
            print(f"Failed to send log to Discord: {e}")

# Global Discord log handler instance
discord_log_handler = DiscordLogHandler()

def setup_logging():
    """Setup advanced logging system"""
    config = get_logging_config()
    
    # Get logger instance and remove default handler
    from loguru import logger
    logger.remove()
    
    # Setup file logging if enabled
    if config.get("file_logging", {}).get("enabled", True):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Main log file with rotation
        from loguru import logger
        logger.add(
            "logs/bot.log",
            rotation=config.get("file_logging", {}).get("max_size", "10 MB"),
            retention=config.get("file_logging", {}).get("backup_count", 5),
            level=config.get("level", "INFO"),
            format=config.get("file_logging", {}).get("format", 
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"),
            backtrace=True,
            diagnose=True
        )
        
        # Error log file
        from loguru import logger
        logger.add(
            "logs/errors.log",
            rotation="1 week",
            retention="1 month",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
            backtrace=True,
            diagnose=True
        )
    
    # Setup colored console logging
    from loguru import logger
    formatter = ColoredFormatter()
    logger.add(
        sys.stdout,
        level=config.get("level", "INFO"),
        format=formatter.format,
        backtrace=True,
        diagnose=True
    )
    
    # Custom filter for sensitive information
    def filter_sensitive(record):
        """Filter out sensitive information from logs"""
        message = str(record["message"]).lower()
        sensitive_words = ["token", "password", "secret", "key", "auth"]
        
        for word in sensitive_words:
            if word in message:
                record["message"] = record["message"].replace(word, "[REDACTED]")
        
        return record
    
    from loguru import logger as bound_logger
    bound_logger = logger.bind(filter=filter_sensitive)
    
    return logger

def get_logger(name: str = "discord_bot"):
    """Get a logger instance with the specified name"""
    return logger.bind(name=name)

async def log_to_discord(level: str, message: str, **kwargs):
    """Convenience function to log to Discord channel"""
    await discord_log_handler.send_log(level, message, **kwargs)

def setup_discord_logging(bot: commands.Bot, log_channel_id: Optional[int] = None):
    """Setup Discord channel logging"""
    discord_log_handler.set_bot(bot)
    
    if log_channel_id:
        discord_log_handler.set_log_channel(log_channel_id)
    
    # Add Discord handler to loguru
    async def discord_sink(message):
        """Custom sink for Discord logging"""
        record = message.record
        await discord_log_handler.send_log(
            record["level"].name,
            record["message"],
            timestamp=record["time"]
        )
    
    if log_channel_id:
        logger.add(discord_sink, level="WARNING", serialize=False)

# Initialize logging on import
log = setup_logging()