"""
Discord Bot Cog: Voice Channel Lockdown
Lock down voice channels with duration and exemption options.

To import in bot.py, add this line:
await bot.load_extension('vclockdown')
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import os
import logging

class VCLockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.vc_lockdown_file = "vc_lockdown_data.json"
        self.active_vc_lockdowns = self.load_vc_lockdowns()
        
        # Start background task to monitor VC lockdown durations
        self.bot.loop.create_task(self.vc_lockdown_monitor())
    
    def load_vc_lockdowns(self):
        """Load active VC lockdowns from file"""
        try:
            if os.path.exists(self.vc_lockdown_file):
                with open(self.vc_lockdown_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading VC lockdowns: {e}")
            return {}
    
    def save_vc_lockdowns(self):
        """Save active VC lockdowns to file"""
        try:
            with open(self.vc_lockdown_file, 'w') as f:
                json.dump(self.active_vc_lockdowns, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving VC lockdowns: {e}")
    
    async def vc_lockdown_monitor(self):
        """Monitor VC lockdowns and auto-unlock when duration expires"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                current_time = datetime.now()
                expired_lockdowns = []
                
                for channel_id, lockdown_data in self.active_vc_lockdowns.items():
                    if lockdown_data.get('end_time'):
                        end_time = datetime.fromisoformat(lockdown_data['end_time'])
                        if current_time >= end_time:
                            expired_lockdowns.append(channel_id)
                
                # Auto-unlock expired VC lockdowns
                for channel_id in expired_lockdowns:
                    await self.unlock_vc_channel(int(channel_id), auto=True)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in VC lockdown monitor: {e}")
                await asyncio.sleep(60)
    
    async def lock_vc_channel(self, channel, duration_minutes=None, exempted_users=None, exempted_roles=None, moderator=None):
        """Lock a voice channel with optional exemptions"""
        try:
            # Store original permissions
            original_perms = {}
            for role in channel.guild.default_role, *channel.guild.roles:
                perms = channel.overwrites_for(role)
                original_perms[str(role.id)] = {
                    'connect': perms.connect,
                    'speak': perms.speak
                }
            
            # Set @everyone to not connect or speak
            await channel.set_permissions(channel.guild.default_role, connect=False, speak=False)
            
            # Disconnect all current users except exempted ones
            exempted_user_ids = [u.id for u in exempted_users] if exempted_users else []
            exempted_role_ids = [r.id for r in exempted_roles] if exempted_roles else []
            
            for member in channel.members:
                # Check if user is exempted
                user_exempted = member.id in exempted_user_ids
                role_exempted = any(role.id in exempted_role_ids for role in member.roles)
                
                if not user_exempted and not role_exempted:
                    try:
                        await member.move_to(None)  # Disconnect user
                    except:
                        pass  # User might have disconnected already
            
            # Set exempted users permissions
            if exempted_users:
                for user in exempted_users:
                    await channel.set_permissions(user, connect=True, speak=True)
            
            # Set exempted roles permissions
            if exempted_roles:
                for role in exempted_roles:
                    await channel.set_permissions(role, connect=True, speak=True)
            
            # Calculate end time if duration specified
            end_time = None
            if duration_minutes:
                end_time = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
            
            # Store lockdown data
            self.active_vc_lockdowns[str(channel.id)] = {
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
            
            self.save_vc_lockdowns()
            return True
            
        except Exception as e:
            self.logger.error(f"Error locking VC channel {channel.id}: {e}")
            return False
    
    async def unlock_vc_channel(self, channel_id, auto=False):
        """Unlock a voice channel and restore original permissions"""
        try:
            if str(channel_id) not in self.active_vc_lockdowns:
                return False, "Voice channel is not locked"
            
            lockdown_data = self.active_vc_lockdowns[str(channel_id)]
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                # Channel not found, remove from lockdowns
                del self.active_vc_lockdowns[str(channel_id)]
                self.save_vc_lockdowns()
                return False, "Voice channel not found"
            
            # Restore original permissions
            await channel.set_permissions(channel.guild.default_role, connect=None, speak=None)
            
            # Clear exempted user/role permissions
            for user_id in lockdown_data.get('exempted_users', []):
                user = channel.guild.get_member(user_id)
                if user:
                    await channel.set_permissions(user, connect=None, speak=None)
            
            for role_id in lockdown_data.get('exempted_roles', []):
                role = channel.guild.get_role(role_id)
                if role:
                    await channel.set_permissions(role, connect=None, speak=None)
            
            # Remove from active lockdowns
            del self.active_vc_lockdowns[str(channel_id)]
            self.save_vc_lockdowns()
            
            # Send unlock notification to a text channel (find general or first available)
            text_channel = None
            for ch in channel.guild.text_channels:
                if ch.name in ['general', 'announcements', 'bot-commands']:
                    text_channel = ch
                    break
            if not text_channel:
                text_channel = channel.guild.text_channels[0] if channel.guild.text_channels else None
            
            if text_channel and auto:
                embed = discord.Embed(
                    title="🔓 Voice Channel Auto-Unlocked",
                    description=f"**{channel.name}** has been automatically unlocked after the lockdown duration expired.",
                    color=discord.Color.green()
                )
                try:
                    await text_channel.send(embed=embed)
                except:
                    pass  # Channel might not have permissions
            
            return True, "Voice channel unlocked successfully"
            
        except Exception as e:
            self.logger.error(f"Error unlocking VC channel {channel_id}: {e}")
            return False, f"Error unlocking voice channel: {str(e)}"
    
    @app_commands.command(name="vclockdown", description="Lock down a voice channel")
    @app_commands.describe(
        channel="Voice channel to lock down",
        duration="Duration in minutes (leave empty for manual unlock)",
        exempted_users="Up to 10 users who can still use VC (separate with spaces)",
        exempted_roles="Up to 10 roles that can still use VC (separate with spaces)"
    )
    async def vclockdown(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel,
        duration: int = None,
        exempted_users: str = None,
        exempted_roles: str = None
    ):
        """Lock down a voice channel"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Check if VC is already locked
            if str(channel.id) in self.active_vc_lockdowns:
                await interaction.followup.send(f"❌ **{channel.name}** is already locked down.", ephemeral=True)
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
            
            # Lock the voice channel
            success = await self.lock_vc_channel(
                channel,
                duration,
                exempted_user_list,
                exempted_role_list,
                interaction.user
            )
            
            if success:
                # Create lockdown embed
                embed = discord.Embed(
                    title="🔒 Voice Channel Locked Down",
                    description=f"**{channel.name}** has been locked down.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                
                if duration:
                    embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
                    end_time = datetime.now() + timedelta(minutes=duration)
                    embed.add_field(name="Ends At", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
                else:
                    embed.add_field(name="Duration", value="Manual unlock required", inline=True)
                
                # Show current members that were disconnected
                disconnected_count = len([m for m in channel.members if m.id not in [u.id for u in exempted_user_list]])
                if disconnected_count > 0:
                    embed.add_field(name="Users Disconnected", value=str(disconnected_count), inline=True)
                
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
                
                embed.set_footer(text=f"Use /vcunlock to manually unlock • ID: {channel.id}")
                
                await interaction.followup.send(embed=embed)
                
                self.logger.info(f"VC {channel.name} locked by {interaction.user} in {interaction.guild.name}")
                
            else:
                await interaction.followup.send("❌ Failed to lock the voice channel.", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Error in vclockdown command: {e}")
            await interaction.followup.send("❌ An error occurred while locking the voice channel.", ephemeral=True)
    
    @app_commands.command(name="vcunlock", description="Unlock a locked voice channel")
    @app_commands.describe(channel="Voice channel to unlock")
    async def vcunlock(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        """Unlock a locked voice channel"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            success, message = await self.unlock_vc_channel(channel.id)
            
            if success:
                embed = discord.Embed(
                    title="🔓 Voice Channel Unlocked",
                    description=f"**{channel.name}** has been unlocked.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Unlocked by", value=interaction.user.mention)
                
                await interaction.followup.send(embed=embed)
                
                self.logger.info(f"VC {channel.name} unlocked by {interaction.user} in {interaction.guild.name}")
                
            else:
                await interaction.followup.send(f"❌ {message}", ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"Error in vcunlock command: {e}")
            await interaction.followup.send("❌ An error occurred while unlocking the voice channel.", ephemeral=True)
    
    @app_commands.command(name="vclockdown.status", description="Check voice channel lockdown status")
    async def vclockdown_status(self, interaction: discord.Interaction):
        """Check VC lockdown status"""
        
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ You need 'Manage Channels' permission to use this command.", ephemeral=True)
            return
        
        guild_vc_lockdowns = {k: v for k, v in self.active_vc_lockdowns.items() if v['guild_id'] == interaction.guild.id}
        
        if not guild_vc_lockdowns:
            await interaction.response.send_message("✅ No voice channels are currently locked down in this server.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Active Voice Channel Lockdowns",
            color=discord.Color.orange()
        )
        
        for channel_id, data in guild_vc_lockdowns.items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                value = f"**Locked by:** <@{data['locked_by']}>\n"
                value += f"**Started:** <t:{int(datetime.fromisoformat(data['locked_at']).timestamp())}:R>\n"
                
                if data.get('end_time'):
                    end_timestamp = int(datetime.fromisoformat(data['end_time']).timestamp())
                    value += f"**Ends:** <t:{end_timestamp}:R>"
                else:
                    value += f"**Duration:** Manual unlock required"
                
                embed.add_field(name=f"🔊 {channel.name}", value=value, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(VCLockdown(bot))