"""
Advanced Permissions System for Discord Bot
Handles role-based and permission-based access control
"""

from typing import List, Dict, Any, Optional, Union
import discord
from discord.ext import commands
from functools import wraps

from config.settings import get_admin_roles, settings
from utils.logging_setup import get_logger

log = get_logger("permissions")

class PermissionError(commands.CommandError):
    """Custom exception for permission-related errors"""
    pass

class PermissionManager:
    """Advanced permission management system"""
    
    def __init__(self):
        self.admin_roles = get_admin_roles()
        self.required_permissions = settings.get("permissions.required_permissions", {})
    
    def has_admin_role(self, member: discord.Member) -> bool:
        """Check if member has any admin role"""
        if not member or not hasattr(member, 'roles'):
            return False
            
        member_roles = [role.name for role in member.roles]
        return any(role in self.admin_roles for role in member_roles)
    
    def has_permission(self, member: discord.Member, permission: str) -> bool:
        """Check if member has specific permission"""
        if not member or not hasattr(member, 'guild_permissions'):
            return False
            
        # Administrator always has all permissions
        if member.guild_permissions.administrator:
            return True
            
        # Check if they have the specific permission
        return getattr(member.guild_permissions, permission, False)
    
    def has_required_permission(self, member: discord.Member, command_name: str) -> bool:
        """Check if member has required permission for command"""
        if not member:
            return False
            
        # Check if command has specific permission requirement
        required_perm = self.required_permissions.get(command_name)
        if required_perm:
            return self.has_permission(member, required_perm)
        
        # Default to admin role check
        return self.has_admin_role(member)
    
    def can_execute_command(self, member: discord.Member, command_name: str) -> bool:
        """Comprehensive check if member can execute command"""
        if not member:
            return False
            
        # Bot owner always has access
        if member.id == member.guild.owner_id:
            return True
            
        # Administrator always has access
        if member.guild_permissions.administrator:
            return True
            
        # Check admin roles
        if self.has_admin_role(member):
            return True
            
        # Check specific permissions
        return self.has_required_permission(member, command_name)

# Global permission manager instance
permission_manager = PermissionManager()

def require_permissions(*permissions: str):
    """Decorator to require specific Discord permissions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not interaction.user:
                embed = create_error_embed("Error", "Cannot verify user.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Cast to Member to access guild_permissions
            if not isinstance(interaction.user, discord.Member):
                embed = create_error_embed("Error", "This command can only be used in servers.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            missing_perms = []
            for perm in permissions:
                if not getattr(interaction.user.guild_permissions, perm, False):
                    missing_perms.append(perm.replace('_', ' ').title())
            
            if missing_perms and not interaction.user.guild_permissions.administrator:
                embed = create_error_embed(
                    "Insufficient Permissions",
                    f"You need the following permissions: {', '.join(missing_perms)}"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def require_admin_role():
    """Decorator to require admin role"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not interaction.user:
                embed = create_error_embed("Error", "Cannot verify user.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Cast to Member if needed
            member = interaction.user if isinstance(interaction.user, discord.Member) else None
            if not member or not permission_manager.can_execute_command(member, func.__name__):
                embed = create_error_embed(
                    "Access Denied",
                    f"You need one of these roles: {', '.join(permission_manager.admin_roles)}"
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create standardized error embed"""
    from config.settings import get_colors
    colors = get_colors()
    
    embed = discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=int(colors["error"].replace("#", ""), 16)
    )
    return embed

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create standardized success embed"""
    from config.settings import get_colors
    colors = get_colors()
    
    embed = discord.Embed(
        title=f"✅ {title}",
        description=description,
        color=int(colors["success"].replace("#", ""), 16)
    )
    return embed

def create_warning_embed(title: str, description: str) -> discord.Embed:
    """Create standardized warning embed"""
    from config.settings import get_colors
    colors = get_colors()
    
    embed = discord.Embed(
        title=f"⚠️ {title}",
        description=description,
        color=int(colors["warning"].replace("#", ""), 16)
    )
    return embed

def create_info_embed(title: str, description: str) -> discord.Embed:
    """Create standardized info embed"""
    from config.settings import get_colors
    colors = get_colors()
    
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=description,
        color=int(colors["info"].replace("#", ""), 16)
    )
    return embed

async def log_command_usage(interaction: discord.Interaction, command_name: str, success: bool = True):
    """Log command usage for monitoring and statistics"""
    user_info = f"{interaction.user} ({interaction.user.id})" if interaction.user else "Unknown"
    guild_info = f"{interaction.guild} ({interaction.guild.id})" if interaction.guild else "DM"
    
    status = "SUCCESS" if success else "FAILED"
    log.info(f"Command {command_name} executed by {user_info} in {guild_info} - {status}")
    
    # Add to statistics if enabled
    if settings.get("commands.enable_stats", True):
        # This would integrate with a database to store command statistics
        # For now, just log it
        pass