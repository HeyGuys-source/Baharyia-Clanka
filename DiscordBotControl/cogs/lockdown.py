"""
Discord Bot Cog: Channel Lockdown
Lock down text channels with duration and exemption options.

To import in bot.py, add this line:
await bot.load_extension('lockdown')
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import os
import logging

class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.lockdown_file = "lockdown_data.json"
        self.active_lockdowns = self.load_lockdowns()
        
        # Start background task to monitor lockdown durations
        self.bot.loop.create_task(self.lockdown_monitor())
    
    def load_lockdowns(self):
        """Load active lockdowns from file"""
        try:
            if os.path.exists(self.lockdown_file):
                with open(self.lockdown_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading lockdowns: {e}")
            return {}
    
    def save_lockdowns(self):
        """Save active lockdowns to file"""
        try:
            with open(self.lockdown_file, 'w') as f:
                json.dump(self.active_lockdowns, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving lockdowns: {e}")
    
    async def lockdown_monitor(self):
        """Monitor lockdowns and auto-unlock when duration expires"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = datetime.now()
                expired_lockdowns = []
                
                for channel_id, lockdown_data in self.active_lockdowns.items():
                    if lockdown_data.get('end_time'):
                        end_time = datetime.fromisoformat(lockdown_data['end_time'])
                        if current_time >= end_time:
                            expired_lockdowns.append(channel_id)
                
                # Auto-unlock expired lockdowns
                for channel_id in expired_lockdowns:
                    await self.unlock_channel(int(channel_id), auto=True)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in lockdown monitor: {e}")
                await asyncio.sleep(60)
    
    async def lock_channel(self, channel, duration_minutes=None, exempted_users=None, exempted_roles=None, moderator=None):
        """Lock a channel with optional exemptions"""
        try:
            # Store original permissions
            original_perms = {}
            for role in channel.guild.default_role, *channel.guild.roles:
                if role != channel.guild.default_role or channel.permissions_for(role).send_messages:
                    original_perms[str(role.id)] = channel.overwrites_for(role).send_messages
            
            # Set @everyone to not send messages
            await channel.set_permissions(channel.guild.default_role, send_messages=False)
            
            # Set exempted users permissions
            if exempted_users:
                for user in exempted_users:
                    await channel.set_permissions(user, send_messages=True)
            
            # Set exempted roles permissions
            if exempted_roles:
                for role in exempted_roles:
                    await channel.set_permissions(role, send_messages=True)
            
            # Calculate end time if duration specified
            end_time = None
            if duration_minutes:
                end_time = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
            
            # Store lockdown data
            self.active_lockdowns[str(channel.id)] = {
                'guild_id': channel.guild.id,
                'channel_name': channel.name,
                'locked_by': moderator.id if moderator else None,
                'locked_at': datetime.now().isoformat(),
                'end_time': end_time,
                'duration_minutes': duration_minutes,
                'original_permissions': original_perms,
                'exempted_users': [u.id for u in exempted_users] if exempted_users else [],
                'exempted_roles': [r.id for r in exempted_roles] if exempted_roles else []
            }
            
            self.save_lockdowns()
            return True
            
        except Exception as e:
            self.logger.error(f"Error locking channel {channel.id}: {e}")
            return False
    
    async def unlock_channel(self, channel_id, auto=False):
        """Unlock a channel and restore original permissions"""
        try:
            if str(channel_id) not in self.active_lockdowns:
                return False, "Channel is not locked"
            
            lockdown_data = self.active_lockdowns[str(channel_id)]
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                # Channel not found, remove from lockdowns
                del self.active_lockdowns[str(channel_id)]
                self.save_lockdowns()
                return False, "Channel not found"
            
            # Restore original permissions
            await channel.set_permissions(channel.guild.default_role, send_messages=None)
            
            # Clear exempted user/role permissions
            for user_id in lockdown_data.get('exempted_users', []):
                user = channel.guild.get_member(user_id)
                if user:
                    await channel.set_permissions(user, send_messages=None)
            
            for role_id in lockdown_data.get('exempted_roles', []):
                role = channel.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, send_messages=None)
            
            # Remove from active lockdowns
            del self.active_lockdowns[str(channel_id)]
            self.save_lockdowns()
            
            # Send unlock notification
            if auto:
                embed = discord.Embed(
                    title="🔓 Channel Auto-Unlocked",
                    description=f"#{channel.name} has been automatically unlocked after the lockdown duration expired.",
                    color=discord.Color.green()
                )
                await channel.send(embed=embed)
            
            return True, "Channel unlocked successfully"
            
        except Exception as e:
            self.logger.error(f"Error unlocking channel {channel_id}: {e}")
            return False, f"Error unlocking channel: {str(e)}"
    
    @app_commands.command(name="lockdown", description="Lock down a text channel")
    @app_commands.describe(
        channel="Channel to lock down (defaults to current channel)",
        duration="Duration in minutes (leave empty for manual unlock)",
        exempted_users="Up to 10 users who can still speak (separate with spaces)",
        exempted_roles="Up to 10 roles that can still speak (separate with spaces)"
    )
    async def lockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel = None,
        duration: int = None,
        exempted_users: str = None,
        exempted_roles: str = None
    ):
        """Lock down a text channel"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Use current channel if none specified
            target_channel = channel or interaction.channel
            
            # Check if channel is already locked
            if str(target_channel.id) in self.active_lockdowns:
                await interaction.followup.send(f"❌ {target_channel.mention} is already locked down.", ephemeral=True)
                return
            
            # Parse exempted users (limit to 10)
            exempted_user_list = []
            if exempted_users:
                user_mentions = exempted_users.split()[:10]  # Limit to 10
                for mention in user_mentions:
                    # Remove < @ ! > characters and get user ID
                    user_id = ''.join(filter(str.isdigit, mention))
                    if user_id:
                        user = interaction.guild.get_member(int(user_id))
                        if user:
                            exempted_user_list.append(user)
            
            # Parse exempted roles (limit to 10)
            exempted_role_list = []
            if exempted_roles:
                role_mentions = exempted_roles.split()[:10]  # Limit to 10
                for mention in role_mentions:
                    # Remove < @ & > characters and get role ID
                    role_id = ''.join(filter(str.isdigit, mention))
                    if role_id:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            exempted_role_list.append(role)
            
            # Lock the channel
            success = await self.lock_channel(
                target_channel,
                duration,
                exempted_user_list,
                exempted_role_list,
                interaction.user
            )
            
            if success:
                # Create lockdown embed
                embed = discord.Embed(
                    title="🔒 Channel Locked Down",
                    description=f"{target_channel.mention} has been locked down.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                
                if duration:
                    embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
                    end_time = datetime.now() + timedelta(minutes=duration)
                    embed.add_field(name="Ends At", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
                else:
                    embed.add_field(name="Duration", value="Manual unlock required", inline=True)
                
                if exempted_user_list:
                    users_text = ", ".join([u.mention for u in exempted_user_list[:5]])
                    if len(exempted_user_list) > 5:
                        users_text += f" and {len(exempted_user_list) - 5} more"
                    embed.add_field(name="Exempted Users", value=users_text, inline=False)
                
                if exempted_role_list:
                    roles_text = ", ".join([r.mention for r in exempted_role_list[:5]])
                    if len(exempted_role_list) > 5:
                        roles_text += f" and {len(exempted_role_list) - 5} more"
                    embed.add_field(name="Exempted Roles", value=roles_text, inline=False)
                
                embed.set_footer(text=f"Use /unlock to manually unlock • ID: {target_channel.id}")
                
                await interaction.followup.send(embed=embed)
                
                # Send notification in the locked channel
                notification_embed = discord.Embed(
                    title="🔒 This channel has been locked",
                    description="Only exempted users and roles can send messages.",
                    color=discord.Color.red()
                )
                await target_channel.send(embed=notification_embed)
                
                self.logger.info(f"Channel {target_channel.name} locked by {interaction.user} in {interaction.guild.name}")
                
            else:
                await interaction.followup.send("❌ Failed to lock the channel.", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Error in lockdown command: {e}")
            await interaction.followup.send("❌ An error occurred while locking the channel.", ephemeral=True)
    
    @app_commands.command(name="unlock", description="Unlock a locked text channel")
    @app_commands.describe(channel="Channel to unlock (defaults to current channel)")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Unlock a locked text channel"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            target_channel = channel or interaction.channel
            
            success, message = await self.unlock_channel(target_channel.id)
            
            if success:
                embed = discord.Embed(
                    title="🔓 Channel Unlocked",
                    description=f"{target_channel.mention} has been unlocked.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Unlocked by", value=interaction.user.mention)
                
                await interaction.followup.send(embed=embed)
                
                # Send notification in the unlocked channel
                notification_embed = discord.Embed(
                    title="🔓 This channel has been unlocked",
                    description="Everyone can now send messages again.",
                    color=discord.Color.green()
                )
                await target_channel.send(embed=notification_embed)
                
                self.logger.info(f"Channel {target_channel.name} unlocked by {interaction.user} in {interaction.guild.name}")
                
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Error in unlock command: {e}")
            await interaction.followup.send("❌ An error occurred while unlocking the channel.", ephemeral=True)
    
    @app_commands.command(name="lockdown.status", description="Check lockdown status of channels")
    async def lockdown_status(self, interaction: discord.Interaction):
        """Check lockdown status"""
        
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        guild_lockdowns = {k: v for k, v in self.active_lockdowns.items() if v['guild_id'] == interaction.guild.id}
        
        if not guild_lockdowns:
            await interaction.response.send_message("✅ No channels are currently locked down in this server.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Active Lockdowns",
            color=discord.Color.orange()
        )
        
        for channel_id, data in guild_lockdowns.items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                value = f"**Locked by:** <@{data['locked_by']}>\n"
                value += f"**Started:** <t:{int(datetime.fromisoformat(data['locked_at']).timestamp())}:R>\n"
                
                if data.get('end_time'):
                    end_timestamp = int(datetime.fromisoformat(data['end_time']).timestamp())
                    value += f"**Ends:** <t:{end_timestamp}:R>"
                else:
                    value += f"**Duration:** Manual unlock required"
                
                embed.add_field(name=f"#{channel.name}", value=value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Lockdown(bot))