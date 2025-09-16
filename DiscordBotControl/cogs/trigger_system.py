"""
Discord Bot Cog: Custom Trigger System
Create custom message triggers with automated responses.

To import in bot.py, add this line:
await bot.load_extension('trigger_system')
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re
import logging
from typing import Dict, List

from utils.permissions import require_admin_role, log_command_usage
from utils.helpers import BotHelpers
from utils.logging_setup import get_logger

class TriggerSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.triggers_file = "triggers.json"
        self.triggers = self.load_triggers()
    
    def load_triggers(self):
        """Load triggers from file"""
        try:
            if os.path.exists(self.triggers_file):
                with open(self.triggers_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading triggers: {e}")
            return {}
    
    def save_triggers(self):
        """Save triggers to file"""
        try:
            with open(self.triggers_file, 'w', encoding='utf-8') as f:
                json.dump(self.triggers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving triggers: {e}")
    
    def get_guild_triggers(self, guild_id: int) -> Dict:
        """Get triggers for a specific guild"""
        return self.triggers.get(str(guild_id), {})
    
    def add_trigger(self, guild_id: int, trigger_message: str, response_message: str, created_by: int) -> bool:
        """Add a new trigger"""
        try:
            guild_str = str(guild_id)
            if guild_str not in self.triggers:
                self.triggers[guild_str] = {}
            
            # Use lowercase trigger for case-insensitive matching
            trigger_key = trigger_message.lower()
            
            self.triggers[guild_str][trigger_key] = {
                'original_trigger': trigger_message,
                'response': response_message,
                'created_by': created_by,
                'created_at': discord.utils.utcnow().isoformat(),
                'uses': 0
            }
            
            self.save_triggers()
            return True
        except Exception as e:
            self.logger.error(f"Error adding trigger: {e}")
            return False
    
    def remove_trigger(self, guild_id: int, trigger_message: str) -> bool:
        """Remove a trigger"""
        try:
            guild_str = str(guild_id)
            trigger_key = trigger_message.lower()
            
            if guild_str in self.triggers and trigger_key in self.triggers[guild_str]:
                del self.triggers[guild_str][trigger_key]
                self.save_triggers()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing trigger: {e}")
            return False
    
    def find_trigger_response(self, guild_id: int, message_content: str) -> str:
        """Find matching trigger and return response"""
        try:
            guild_triggers = self.get_guild_triggers(guild_id)
            message_lower = message_content.lower().strip()
            
            # Check for exact match first
            if message_lower in guild_triggers:
                trigger_data = guild_triggers[message_lower]
                trigger_data['uses'] = trigger_data.get('uses', 0) + 1
                self.save_triggers()
                return trigger_data['response']
            
            # Check for partial matches (if trigger is contained in message)
            for trigger_key, trigger_data in guild_triggers.items():
                if trigger_key in message_lower:
                    trigger_data['uses'] = trigger_data.get('uses', 0) + 1
                    self.save_triggers()
                    return trigger_data['response']
            
            return None
        except Exception as e:
            self.logger.error(f"Error finding trigger: {e}")
            return None
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that match triggers"""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
        
        # Check for trigger match
        response = self.find_trigger_response(message.guild.id, message.content)
        if response:
            try:
                # Replace variables in response
                response = response.replace('{user}', message.author.mention)
                response = response.replace('{user_name}', message.author.display_name)
                response = response.replace('{server}', message.guild.name)
                response = response.replace('{channel}', message.channel.mention)
                
                await message.channel.send(response)
                self.logger.info(f"Trigger activated by {message.author} in {message.guild.name}")
            except Exception as e:
                self.logger.error(f"Error sending trigger response: {e}")
    
    @app_commands.command(name="createtrigger", description="Create a new message trigger")
    @app_commands.describe(
        trigger_message="The message that will activate the trigger",
        response_message="The automated response message"
    )
    async def create_trigger(self, interaction: discord.Interaction, trigger_message: str, response_message: str):
        """Create a new trigger"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
        
        # Validate inputs
        if len(trigger_message) > 200:
            await interaction.response.send_message("❌ Trigger message must be 200 characters or less.", ephemeral=True)
            return
        
        if len(response_message) > 2000:
            await interaction.response.send_message("❌ Response message must be 2000 characters or less.", ephemeral=True)
            return
        
        # Check if trigger already exists
        guild_triggers = self.get_guild_triggers(interaction.guild.id)
        if trigger_message.lower() in guild_triggers:
            await interaction.response.send_message("❌ A trigger with that message already exists.", ephemeral=True)
            return
        
        # Check trigger limit (max 50 per server)
        if len(guild_triggers) >= 50:
            await interaction.response.send_message("❌ This server has reached the maximum of 50 triggers.", ephemeral=True)
            return
        
        # Add the trigger
        success = self.add_trigger(interaction.guild.id, trigger_message, response_message, interaction.user.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Trigger Created",
                color=discord.Color.green()
            )
            embed.add_field(name="Trigger", value=f"`{trigger_message}`", inline=False)
            embed.add_field(name="Response", value=response_message[:1000] + ("..." if len(response_message) > 1000 else ""), inline=False)
            embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
            
            embed.set_footer(text="Available variables: {user}, {user_name}, {server}, {channel}")
            
            await interaction.response.send_message(embed=embed)
            self.logger.info(f"Trigger '{trigger_message}' created by {interaction.user} in {interaction.guild.name}")
        else:
            await interaction.response.send_message("❌ Failed to create trigger. Please try again.", ephemeral=True)
    
    @app_commands.command(name="removetrigger", description="Remove an existing trigger")
    @app_commands.describe(trigger_message="The trigger message to remove")
    async def remove_trigger_command(self, interaction: discord.Interaction, trigger_message: str):
        """Remove a trigger"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
            return
        
        # Check if trigger exists
        guild_triggers = self.get_guild_triggers(interaction.guild.id)
        trigger_key = trigger_message.lower()
        
        if trigger_key not in guild_triggers:
            await interaction.response.send_message("❌ No trigger found with that message.", ephemeral=True)
            return
        
        # Remove the trigger
        success = self.remove_trigger(interaction.guild.id, trigger_message)
        
        if success:
            embed = discord.Embed(
                title="✅ Trigger Removed",
                description=f"Trigger `{trigger_message}` has been removed.",
                color=discord.Color.red()
            )
            embed.add_field(name="Removed by", value=interaction.user.mention)
            
            await interaction.response.send_message(embed=embed)
            self.logger.info(f"Trigger '{trigger_message}' removed by {interaction.user} in {interaction.guild.name}")
        else:
            await interaction.response.send_message("❌ Failed to remove trigger. Please try again.", ephemeral=True)
    
    @app_commands.command(name="trigger-list", description="List all triggers in this server")
    async def trigger_list(self, interaction: discord.Interaction):
        """List all triggers"""
        
        guild_triggers = self.get_guild_triggers(interaction.guild.id)
        
        if not guild_triggers:
            await interaction.response.send_message("📝 No triggers have been created in this server yet.", ephemeral=True)
            return
        
        # Sort triggers by uses (most used first)
        sorted_triggers = sorted(
            guild_triggers.items(),
            key=lambda x: x[1].get('uses', 0),
            reverse=True
        )
        
        # Create paginated embeds if there are many triggers
        triggers_per_page = 10
        total_pages = (len(sorted_triggers) + triggers_per_page - 1) // triggers_per_page
        page = 1
        
        embed = discord.Embed(
            title="📝 Server Triggers",
            description=f"Page {page}/{total_pages} • Total: {len(sorted_triggers)} triggers",
            color=discord.Color.blue()
        )
        
        start_idx = 0
        end_idx = min(triggers_per_page, len(sorted_triggers))
        
        for i, (trigger_key, trigger_data) in enumerate(sorted_triggers[start_idx:end_idx], 1):
            original_trigger = trigger_data.get('original_trigger', trigger_key)
            response = trigger_data['response']
            uses = trigger_data.get('uses', 0)
            created_by = trigger_data.get('created_by')
            
            # Truncate long responses
            if len(response) > 100:
                response = response[:100] + "..."
            
            # Get creator info
            creator_text = f"<@{created_by}>" if created_by else "Unknown"
            
            embed.add_field(
                name=f"{start_idx + i}. `{original_trigger}`",
                value=f"**Response:** {response}\n**Uses:** {uses} • **Creator:** {creator_text}",
                inline=False
            )
        
        # Add usage statistics
        total_uses = sum(trigger_data.get('uses', 0) for trigger_data in guild_triggers.values())
        embed.set_footer(text=f"Total trigger activations: {total_uses}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="trigger.search", description="Search for triggers containing specific text")
    @app_commands.describe(search_term="Text to search for in trigger messages")
    async def trigger_search(self, interaction: discord.Interaction, search_term: str):
        """Search for triggers"""
        
        guild_triggers = self.get_guild_triggers(interaction.guild.id)
        
        if not guild_triggers:
            await interaction.response.send_message("📝 No triggers have been created in this server yet.", ephemeral=True)
            return
        
        # Search for triggers containing the search term
        search_lower = search_term.lower()
        matching_triggers = []
        
        for trigger_key, trigger_data in guild_triggers.items():
            original_trigger = trigger_data.get('original_trigger', trigger_key)
            if search_lower in trigger_key or search_lower in trigger_data['response'].lower():
                matching_triggers.append((original_trigger, trigger_data))
        
        if not matching_triggers:
            await interaction.response.send_message(f"🔍 No triggers found containing '{search_term}'.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔍 Trigger Search Results",
            description=f"Found {len(matching_triggers)} triggers containing '{search_term}'",
            color=discord.Color.blue()
        )
        
        for i, (trigger, trigger_data) in enumerate(matching_triggers[:10], 1):  # Limit to 10 results
            response = trigger_data['response']
            uses = trigger_data.get('uses', 0)
            
            # Truncate long responses
            if len(response) > 100:
                response = response[:100] + "..."
            
            embed.add_field(
                name=f"{i}. `{trigger}`",
                value=f"**Response:** {response}\n**Uses:** {uses}",
                inline=False
            )
        
        if len(matching_triggers) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(matching_triggers)} results")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="trigger.stats", description="Show trigger usage statistics")
    async def trigger_stats(self, interaction: discord.Interaction):
        """Show trigger statistics"""
        
        guild_triggers = self.get_guild_triggers(interaction.guild.id)
        
        if not guild_triggers:
            await interaction.response.send_message("📝 No triggers have been created in this server yet.", ephemeral=True)
            return
        
        # Calculate statistics
        total_triggers = len(guild_triggers)
        total_uses = sum(trigger_data.get('uses', 0) for trigger_data in guild_triggers.values())
        avg_uses = total_uses / total_triggers if total_triggers > 0 else 0
        
        # Find most used trigger
        most_used = max(
            guild_triggers.items(),
            key=lambda x: x[1].get('uses', 0)
        )
        
        # Find least used trigger
        least_used = min(
            guild_triggers.items(),
            key=lambda x: x[1].get('uses', 0)
        )
        
        embed = discord.Embed(
            title="📊 Trigger Statistics",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total Triggers", value=str(total_triggers), inline=True)
        embed.add_field(name="Total Uses", value=str(total_uses), inline=True)
        embed.add_field(name="Average Uses", value=f"{avg_uses:.1f}", inline=True)
        
        embed.add_field(
            name="Most Used Trigger",
            value=f"`{most_used[1].get('original_trigger', most_used[0])}` ({most_used[1].get('uses', 0)} uses)",
            inline=False
        )
        
        embed.add_field(
            name="Least Used Trigger",
            value=f"`{least_used[1].get('original_trigger', least_used[0])}` ({least_used[1].get('uses', 0)} uses)",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TriggerSystem(bot))
