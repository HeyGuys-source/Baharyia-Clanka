"""
Helper utilities for Discord Bot
Common functions used across different cogs and commands
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import discord
from discord.ext import commands
from PIL import Image
import io

from config.settings import get_colors, settings
from utils.logging_setup import get_logger

log = get_logger("helpers")

class BotHelpers:
    """Collection of helpful utility functions"""
    
    @staticmethod
    def get_embed_color(embed_type: str = "primary") -> int:
        """Get embed color based on type"""
        colors = get_colors()
        color_map = {
            "primary": colors["primary"],
            "secondary": colors["secondary"],
            "error": colors["error"],
            "warning": colors["warning"],
            "success": colors["success"],
            "info": colors["info"]
        }
        color_hex = color_map.get(embed_type, colors["primary"])
        return int(color_hex.replace("#", ""), 16)
    
    @staticmethod
    def create_embed(title: str, description: str, embed_type: str = "primary", 
                    fields: Optional[List[Dict[str, Any]]] = None,
                    thumbnail: Optional[str] = None,
                    image: Optional[str] = None,
                    footer: Optional[str] = None) -> discord.Embed:
        """Create a standardized embed with bot colors"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=BotHelpers.get_embed_color(embed_type),
            timestamp=datetime.utcnow()
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", "Field"),
                    value=field.get("value", "No value"),
                    inline=field.get("inline", False)
                )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
        
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text="Advanced Discord Bot • Made with ❤️")
        
        return embed
    
    @staticmethod
    async def safe_send(destination, content: str = None, **kwargs) -> Optional[discord.Message]:
        """Safely send message with error handling"""
        try:
            if content and len(content) > 2000:
                # Split long messages
                chunks = [content[i:i+2000] for i in range(0, len(content), 2000)]
                messages = []
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        msg = await destination.send(chunk, **kwargs)
                        messages.append(msg)
                    else:
                        msg = await destination.send(chunk)
                        messages.append(msg)
                return messages[0]  # Return first message
            else:
                return await destination.send(content, **kwargs)
        except discord.HTTPException as e:
            log.error(f"Failed to send message: {e}")
            return None
        except Exception as e:
            log.error(f"Unexpected error sending message: {e}")
            return None
    
    @staticmethod
    async def get_user_avatar(user: Union[discord.User, discord.Member], size: int = 1024) -> str:
        """Get user avatar URL with fallback to default"""
        if user.avatar:
            return user.avatar.with_size(size).url
        else:
            return user.default_avatar.url
    
    @staticmethod
    async def get_guild_icon(guild: discord.Guild, size: int = 1024) -> Optional[str]:
        """Get guild icon URL"""
        if guild.icon:
            return guild.icon.with_size(size).url
        return None
    
    @staticmethod
    def format_datetime(dt: datetime, format_type: str = "full") -> str:
        """Format datetime in various styles"""
        formats = {
            "full": "%Y-%m-%d %H:%M:%S UTC",
            "short": "%m/%d/%Y %H:%M",
            "date": "%Y-%m-%d",
            "time": "%H:%M:%S",
            "discord": f"<t:{int(dt.timestamp())}:F>",  # Discord timestamp
            "relative": f"<t:{int(dt.timestamp())}:R>"   # Discord relative time
        }
        return dt.strftime(formats.get(format_type, formats["full"]))
    
    @staticmethod
    def format_bytes(bytes_value: int) -> str:
        """Format bytes into human readable format"""
        float_value = float(bytes_value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if float_value < 1024.0:
                return f"{float_value:.1f} {unit}"
            float_value /= 1024.0
        return f"{float_value:.1f} PB"
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format seconds into human readable duration"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds}s"
        elif seconds < 86400:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours}h {remaining_minutes}m"
        else:
            days = seconds // 86400
            remaining_hours = (seconds % 86400) // 3600
            return f"{days}d {remaining_hours}h"
    
    @staticmethod
    async def download_image(url: str, max_size: int = 10 * 1024 * 1024) -> Optional[bytes]:
        """Download image from URL with size limit"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return None
                    
                    content_length = response.headers.get('content-length')
                    if content_length and int(content_length) > max_size:
                        log.warning(f"Image too large: {content_length} bytes")
                        return None
                    
                    data = await response.read()
                    if len(data) > max_size:
                        log.warning(f"Downloaded image too large: {len(data)} bytes")
                        return None
                    
                    return data
        except Exception as e:
            log.error(f"Failed to download image: {e}")
            return None
    
    @staticmethod
    def is_image_url(url: str) -> bool:
        """Check if URL points to an image"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
        return any(url.lower().endswith(ext) for ext in image_extensions)
    
    @staticmethod
    async def create_progress_bar(current: int, total: int, length: int = 20) -> str:
        """Create a text progress bar"""
        if total == 0:
            return "█" * length
        
        filled = int(length * current / total)
        bar = "█" * filled + "░" * (length - filled)
        percentage = round(100 * current / total, 1)
        return f"{bar} {percentage}%"
    
    @staticmethod
    def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks of specified size"""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    
    @staticmethod
    def save_json(data: Dict[str, Any], filepath: Union[str, Path]) -> bool:
        """Save data to JSON file safely"""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            log.error(f"Failed to save JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def load_json(filepath: Union[str, Path], default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load data from JSON file safely"""
        try:
            if not Path(filepath).exists():
                return default if default is not None else {}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load JSON from {filepath}: {e}")
            return default if default is not None else {}
    
    @staticmethod
    async def wait_for_confirmation(interaction: discord.Interaction, 
                                  timeout: int = 30,
                                  confirm_text: str = "✅ Confirm",
                                  cancel_text: str = "❌ Cancel") -> bool:
        """Wait for user confirmation with buttons"""
        view = ConfirmationView(timeout=timeout, confirm_text=confirm_text, cancel_text=cancel_text)
        
        embed = BotHelpers.create_embed(
            "Confirmation Required",
            "Please confirm this action.",
            "warning"
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await view.wait()
        
        return getattr(view, 'confirmed', False)

class ConfirmationView(discord.ui.View):
    """Confirmation view with confirm/cancel buttons"""
    
    def __init__(self, timeout: int = 30, confirm_text: str = "✅ Confirm", cancel_text: str = "❌ Cancel"):
        super().__init__(timeout=timeout)
        self.confirmed = False
        
        # Add buttons
        self.add_item(ConfirmButton(label=confirm_text, confirmed=True))
        self.add_item(ConfirmButton(label=cancel_text, confirmed=False))

class ConfirmButton(discord.ui.Button):
    """Confirmation button"""
    
    def __init__(self, label: str, confirmed: bool):
        style = discord.ButtonStyle.green if confirmed else discord.ButtonStyle.red
        super().__init__(label=label, style=style)
        self.confirmed = confirmed
    
    async def callback(self, interaction: discord.Interaction):
        if self.view:
            self.view.confirmed = self.confirmed
            self.view.stop()
        
        embed = BotHelpers.create_embed(
            "Confirmed" if self.confirmed else "Cancelled",
            "Action has been " + ("confirmed" if self.confirmed else "cancelled"),
            "success" if self.confirmed else "error"
        )
        
        await interaction.response.edit_message(embed=embed, view=None)