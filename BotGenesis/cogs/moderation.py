"""
Moderation Cog
Contains 20 moderation commands for server management and user discipline.
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class ModerationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    def create_embed(self, title, description, color=0x3498db, footer=None):
        """Create a styled embed"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.timestamp = datetime.utcnow()
        if footer:
            embed.set_footer(text=footer)
        else:
            embed.set_footer(text="Advanced Moderation Bot", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        return embed
    
    async def log_action(self, guild, action, moderator, target, reason=None):
        """Log moderation actions to the log channel"""
        try:
            if not self.bot.db_pool:
                return
                
            async with self.bot.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    "SELECT log_channel_id FROM guild_settings WHERE guild_id = $1",
                    guild.id
                )
                
            if result and result['log_channel_id']:
                channel = guild.get_channel(result['log_channel_id'])
                if channel:
                    embed = self.create_embed(
                        f"🛡️ {action}",
                        f"**Target:** {target}\n**Moderator:** {moderator}\n**Reason:** {reason or 'No reason provided'}",
                        color=0xe74c3c
                    )
                    await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to log action: {e}")
    
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need kick members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            await member.kick(reason=reason)
            embed = self.create_embed(
                "👢 Member Kicked", 
                f"**Member:** {member.mention}\n**Reason:** {reason or 'No reason provided'}",
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Member Kicked", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to kick member: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban", delete_days="Days of messages to delete (0-7)")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, delete_days: int = 1):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need ban members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            await member.ban(reason=reason, delete_message_seconds=max(0, min(7, delete_days)) * 86400)
            embed = self.create_embed(
                "🔨 Member Banned", 
                f"**Member:** {member.mention}\n**Reason:** {reason or 'No reason provided'}\n**Messages Deleted:** {delete_days} days",
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Member Banned", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to ban member: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(user_id="The ID of the user to unban", reason="Reason for the unban")
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need ban members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            embed = self.create_embed(
                "🔓 User Unbanned", 
                f"**User:** {user.mention}\n**Reason:** {reason or 'No reason provided'}",
                0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "User Unbanned", interaction.user, user, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to unban user: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="mute", description="Mute a member")
    @app_commands.describe(member="The member to mute", duration="Duration in minutes", reason="Reason for the mute")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = 60, reason: str = None):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need moderate members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            until = discord.utils.utcnow() + timedelta(minutes=duration)
            await member.timeout(until, reason=reason)
            
            embed = self.create_embed(
                "🔇 Member Muted", 
                f"**Member:** {member.mention}\n**Duration:** {duration} minutes\n**Reason:** {reason or 'No reason provided'}",
                0xf39c12
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Member Muted", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to mute member: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(member="The member to unmute", reason="Reason for the unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need moderate members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            await member.timeout(None, reason=reason)
            embed = self.create_embed(
                "🔊 Member Unmuted", 
                f"**Member:** {member.mention}\n**Reason:** {reason or 'No reason provided'}",
                0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Member Unmuted", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to unmute member: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need moderate members permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            # Store warning in database
            if self.bot.db_pool:
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO warnings (user_id, guild_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
                        member.id, interaction.guild.id, interaction.user.id, reason
                    )
                    
                    # Get warning count
                    count = await conn.fetchval(
                        "SELECT COUNT(*) FROM warnings WHERE user_id = $1 AND guild_id = $2",
                        member.id, interaction.guild.id
                    )
            
            embed = self.create_embed(
                "⚠️ Member Warned", 
                f"**Member:** {member.mention}\n**Reason:** {reason}\n**Total Warnings:** {count if self.bot.db_pool else 'N/A'}",
                0xf39c12
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Member Warned", interaction.user, member, reason)
            
            # DM the user
            try:
                dm_embed = self.create_embed(
                    "⚠️ Warning Received",
                    f"You have been warned in **{interaction.guild.name}**\n**Reason:** {reason}",
                    0xf39c12
                )
                await member.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
                
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to warn member: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(amount="Number of messages to delete (1-100)", user="Only delete messages from this user")
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.User = None):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage messages permission.", 0xff0000),
                ephemeral=True
            )
        
        amount = max(1, min(100, amount))
        
        try:
            def check(m):
                return user is None or m.author == user
            
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            embed = self.create_embed(
                "🗑️ Messages Purged", 
                f"**Deleted:** {len(deleted)} messages\n**Channel:** {interaction.channel.mention}" + 
                (f"\n**User Filter:** {user.mention}" if user else ""),
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed, delete_after=5)
            await self.log_action(interaction.guild, "Messages Purged", interaction.user, f"{len(deleted)} messages in {interaction.channel.mention}")
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to purge messages: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="slowmode", description="Set channel slowmode")
    @app_commands.describe(seconds="Slowmode delay in seconds (0-21600)", channel="Channel to modify")
    async def slowmode(self, interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage channels permission.", 0xff0000),
                ephemeral=True
            )
        
        channel = channel or interaction.channel
        seconds = max(0, min(21600, seconds))
        
        try:
            await channel.edit(slowmode_delay=seconds)
            embed = self.create_embed(
                "🐌 Slowmode Updated", 
                f"**Channel:** {channel.mention}\n**Delay:** {seconds} seconds",
                0x3498db
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Slowmode Changed", interaction.user, f"{channel.mention} to {seconds}s")
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to set slowmode: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(channel="Channel to lock", reason="Reason for locking")
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage channels permission.", 0xff0000),
                ephemeral=True
            )
        
        channel = channel or interaction.channel
        
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
            
            embed = self.create_embed(
                "🔒 Channel Locked", 
                f"**Channel:** {channel.mention}\n**Reason:** {reason or 'No reason provided'}",
                0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Channel Locked", interaction.user, channel.mention, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to lock channel: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(channel="Channel to unlock", reason="Reason for unlocking")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage channels permission.", 0xff0000),
                ephemeral=True
            )
        
        channel = channel or interaction.channel
        
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.send_messages = None
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=reason)
            
            embed = self.create_embed(
                "🔓 Channel Unlocked", 
                f"**Channel:** {channel.mention}\n**Reason:** {reason or 'No reason provided'}",
                0x2ecc71
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Channel Unlocked", interaction.user, channel.mention, reason)
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to unlock channel: {str(e)}", 0xff0000),
                ephemeral=True
            )
    
    @app_commands.command(name="nickname", description="Change a member's nickname")
    @app_commands.describe(member="Member to change nickname", nickname="New nickname (leave empty to remove)")
    async def nickname(self, interaction: discord.Interaction, member: discord.Member, nickname: str = None):
        if not interaction.user.guild_permissions.manage_nicknames:
            return await interaction.response.send_message(
                embed=self.create_embed("❌ Permission Denied", "You need manage nicknames permission.", 0xff0000),
                ephemeral=True
            )
        
        try:
            old_nick = member.display_name
            await member.edit(nick=nickname)
            
            embed = self.create_embed(
                "📝 Nickname Changed", 
                f"**Member:** {member.mention}\n**Old:** {old_nick}\n**New:** {nickname or 'Removed'}",
                0x3498db
            )
            await interaction.response.send_message(embed=embed)
            await self.log_action(interaction.guild, "Nickname Changed", interaction.user, f"{member.mention}: {old_nick} → {nickname or 'Removed'}")
        except Exception as e:
            await interaction.response.send_message(
                embed=self.create_embed("❌ Error", f"Failed to change nickname: {str(e)}", 0xff0000),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(ModerationCog(bot))