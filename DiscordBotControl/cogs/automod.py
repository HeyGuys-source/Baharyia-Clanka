"""
Discord Bot Cog: Comprehensive AutoMod Configuration
Advanced AutoMod configuration with extensive options and permissions.

To import in bot.py, add this line:
await bot.load_extension('automod')
"""

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from typing import List, Optional
from datetime import datetime, timedelta

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.automod_config_file = "automod_config.json"
        self.automod_configs = self.load_automod_configs()
    
    def load_automod_configs(self):
        """Load AutoMod configurations"""
        try:
            if os.path.exists(self.automod_config_file):
                with open(self.automod_config_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Error loading AutoMod configs: {e}")
            return {}
    
    def save_automod_configs(self):
        """Save AutoMod configurations"""
        try:
            with open(self.automod_config_file, 'w') as f:
                json.dump(self.automod_configs, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving AutoMod configs: {e}")
    
    def get_guild_config(self, guild_id):
        """Get AutoMod config for a guild"""
        return self.automod_configs.get(str(guild_id), {
            'enabled': False,
            'spam_protection': True,
            'link_protection': False,
            'caps_protection': False,
            'mention_spam': False,
            'keyword_filter': [],
            'allowed_links': [],
            'max_mentions': 5,
            'caps_percentage': 70,
            'exempt_roles': [],
            'exempt_channels': [],
            'log_channel': None,
            'actions': {
                'delete_message': True,
                'timeout_user': False,
                'warn_user': True,
                'timeout_duration': 300  # 5 minutes
            }
        })
    
    def set_guild_config(self, guild_id, config):
        """Set AutoMod config for a guild"""
        self.automod_configs[str(guild_id)] = config
        self.save_automod_configs()
    
    async def create_automod_rule(self, guild, rule_name, trigger_type, trigger_data, actions, exempt_roles=None, exempt_channels=None):
        """Create an AutoMod rule"""
        try:
            # Check if rule already exists
            existing_rules = await guild.fetch_automod_rules()
            for rule in existing_rules:
                if rule.name == rule_name:
                    await rule.delete(reason="Updating AutoMod rule")
                    break
            
            # Prepare actions
            automod_actions = []
            
            if actions.get('delete_message', True):
                automod_actions.append(
                    discord.AutoModRuleAction(type=discord.AutoModRuleActionType.block_message)
                )
            
            if actions.get('timeout_user', False):
                automod_actions.append(
                    discord.AutoModRuleAction(
                        type=discord.AutoModRuleActionType.timeout,
                        metadata=discord.AutoModActionMetadata(
                            duration_seconds=actions.get('timeout_duration', 300)
                        )
                    )
                )
            
            # Create trigger based on type
            if trigger_type == 'keyword':
                trigger = discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.keyword,
                    keyword_filter=trigger_data
                )
            elif trigger_type == 'spam':
                trigger = discord.AutoModTrigger(type=discord.AutoModRuleTriggerType.spam)
            elif trigger_type == 'mention_spam':
                trigger = discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.mention_spam,
                    mention_total_limit=trigger_data.get('max_mentions', 5)
                )
            else:
                return False, f"Unknown trigger type: {trigger_type}"
            
            # Create the rule
            rule = await guild.create_automod_rule(
                name=rule_name,
                event_type=discord.AutoModEventType.message_send,
                trigger=trigger,
                actions=automod_actions,
                enabled=True,
                exempt_roles=exempt_roles or [],
                exempt_channels=exempt_channels or [],
                reason=f"AutoMod rule created by bot"
            )
            
            return True, f"Rule '{rule_name}' created successfully"
            
        except discord.Forbidden:
            return False, "Missing permissions to create AutoMod rules"
        except Exception as e:
            self.logger.error(f"Error creating AutoMod rule: {e}")
            return False, f"Error creating rule: {str(e)}"
    
    @app_commands.command(name="automod", description="Configure comprehensive AutoMod settings")
    @app_commands.describe(
        feature="AutoMod feature to configure",
        enabled="Enable or disable the feature",
        value="Configuration value (varies by feature)",
        log_channel="Channel for AutoMod logs"
    )
    @app_commands.choices(feature=[
        app_commands.Choice(name="Spam Protection", value="spam_protection"),
        app_commands.Choice(name="Link Protection", value="link_protection"),
        app_commands.Choice(name="Caps Protection", value="caps_protection"),
        app_commands.Choice(name="Mention Spam", value="mention_spam"),
        app_commands.Choice(name="Overall Enable/Disable", value="enabled")
    ])
    async def automod_config(
        self,
        interaction: discord.Interaction,
        feature: app_commands.Choice[str],
        enabled: bool,
        value: int = None,
        log_channel: discord.TextChannel = None
    ):
        """Configure AutoMod settings"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            guild_config = self.get_guild_config(interaction.guild.id)
            feature_name = feature.value
            
            # Update configuration
            if feature_name == "enabled":
                guild_config['enabled'] = enabled
            elif feature_name in guild_config:
                guild_config[feature_name] = enabled
                
                # Handle feature-specific values
                if feature_name == "mention_spam" and value:
                    guild_config['max_mentions'] = max(1, min(value, 50))
                elif feature_name == "caps_protection" and value:
                    guild_config['caps_percentage'] = max(1, min(value, 100))
            
            # Update log channel if provided
            if log_channel:
                guild_config['log_channel'] = log_channel.id
            
            # Save configuration
            self.set_guild_config(interaction.guild.id, guild_config)
            
            # Apply AutoMod rules if enabled
            if guild_config['enabled'] and enabled:
                success, message = await self.apply_automod_rules(interaction.guild, guild_config)
                if not success:
                    await interaction.followup.send(f"⚠️ Configuration saved but failed to apply rules: {message}", ephemeral=True)
                    return
            
            # Create response embed
            embed = discord.Embed(
                title="✅ AutoMod Configuration Updated",
                color=discord.Color.green()
            )
            
            feature_display = feature.name
            status = "Enabled" if enabled else "Disabled"
            
            embed.add_field(name="Feature", value=feature_display, inline=True)
            embed.add_field(name="Status", value=status, inline=True)
            
            if value and feature_name in ["mention_spam", "caps_protection"]:
                embed.add_field(name="Value", value=str(value), inline=True)
            
            if log_channel:
                embed.add_field(name="Log Channel", value=log_channel.mention, inline=False)
            
            await interaction.followup.send(embed=embed)
            
            self.logger.info(f"AutoMod {feature_display} {status} by {interaction.user} in {interaction.guild.name}")
            
        except Exception as e:
            self.logger.error(f"Error configuring AutoMod: {e}")
            await interaction.followup.send("❌ An error occurred while configuring AutoMod.", ephemeral=True)
    
    async def apply_automod_rules(self, guild, config):
        """Apply AutoMod rules based on configuration"""
        try:
            # Get exempt roles and channels
            exempt_roles = [guild.get_role(role_id) for role_id in config.get('exempt_roles', []) if guild.get_role(role_id)]
            exempt_channels = [guild.get_channel(ch_id) for ch_id in config.get('exempt_channels', []) if guild.get_channel(ch_id)]
            
            actions = config.get('actions', {})
            
            # Spam Protection
            if config.get('spam_protection', True):
                success, msg = await self.create_automod_rule(
                    guild, "Bot Spam Protection", "spam", None, actions, exempt_roles, exempt_channels
                )
                if not success:
                    return False, f"Spam protection: {msg}"
            
            # Mention Spam Protection
            if config.get('mention_spam', False):
                mention_data = {'max_mentions': config.get('max_mentions', 5)}
                success, msg = await self.create_automod_rule(
                    guild, "Bot Mention Spam Protection", "mention_spam", mention_data, actions, exempt_roles, exempt_channels
                )
                if not success:
                    return False, f"Mention spam: {msg}"
            
            # Keyword Filter
            keywords = config.get('keyword_filter', [])
            if keywords:
                success, msg = await self.create_automod_rule(
                    guild, "Bot Keyword Filter", "keyword", keywords, actions, exempt_roles, exempt_channels
                )
                if not success:
                    return False, f"Keyword filter: {msg}"
            
            return True, "All rules applied successfully"
            
        except Exception as e:
            return False, str(e)
    
    @app_commands.command(name="automod.keywords", description="Manage keyword filter")
    @app_commands.describe(
        action="Add or remove keywords",
        keywords="Keywords to add/remove (separated by commas)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Keywords", value="add"),
        app_commands.Choice(name="Remove Keywords", value="remove"),
        app_commands.Choice(name="List Keywords", value="list"),
        app_commands.Choice(name="Clear All", value="clear")
    ])
    async def automod_keywords(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        keywords: str = None
    ):
        """Manage keyword filter"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        current_keywords = guild_config.get('keyword_filter', [])
        
        if action.value == "list":
            if not current_keywords:
                await interaction.response.send_message("📝 No keywords are currently filtered.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🚫 Filtered Keywords",
                description=", ".join([f"`{kw}`" for kw in current_keywords]),
                color=discord.Color.orange()
            )
            embed.set_footer(text=f"Total: {len(current_keywords)} keywords")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if action.value == "clear":
            guild_config['keyword_filter'] = []
            self.set_guild_config(interaction.guild.id, guild_config)
            
            embed = discord.Embed(
                title="✅ Keywords Cleared",
                description="All filtered keywords have been removed.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        if not keywords:
            await interaction.response.send_message("❌ Please provide keywords to add or remove.", ephemeral=True)
            return
        
        # Parse keywords
        keyword_list = [kw.strip().lower() for kw in keywords.split(',') if kw.strip()]
        
        if action.value == "add":
            # Add keywords (avoid duplicates)
            new_keywords = [kw for kw in keyword_list if kw not in current_keywords]
            guild_config['keyword_filter'].extend(new_keywords)
            
            # Limit to 100 keywords
            if len(guild_config['keyword_filter']) > 100:
                guild_config['keyword_filter'] = guild_config['keyword_filter'][:100]
            
            embed = discord.Embed(
                title="✅ Keywords Added",
                description=f"Added {len(new_keywords)} new keywords to the filter.",
                color=discord.Color.green()
            )
            
        elif action.value == "remove":
            # Remove keywords
            removed_count = 0
            for kw in keyword_list:
                if kw in current_keywords:
                    guild_config['keyword_filter'].remove(kw)
                    removed_count += 1
            
            embed = discord.Embed(
                title="✅ Keywords Removed",
                description=f"Removed {removed_count} keywords from the filter.",
                color=discord.Color.green()
            )
        
        # Save configuration
        self.set_guild_config(interaction.guild.id, guild_config)
        
        # Update AutoMod rules if enabled
        if guild_config.get('enabled', False):
            await self.apply_automod_rules(interaction.guild, guild_config)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="automod.exempt", description="Manage AutoMod exemptions")
    @app_commands.describe(
        type="Type of exemption",
        action="Add or remove exemptions",
        target="Role or channel to exempt"
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Role", value="role"),
            app_commands.Choice(name="Channel", value="channel")
        ],
        action=[
            app_commands.Choice(name="Add", value="add"),
            app_commands.Choice(name="Remove", value="remove"),
            app_commands.Choice(name="List", value="list")
        ]
    )
    async def automod_exempt(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        action: app_commands.Choice[str],
        target: str = None
    ):
        """Manage AutoMod exemptions"""
        
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("❌ You need 'Manage Server' permission to use this command.", ephemeral=True)
            return
        
        guild_config = self.get_guild_config(interaction.guild.id)
        exempt_key = f"exempt_{type.value}s"
        current_exempts = guild_config.get(exempt_key, [])
        
        if action.value == "list":
            if not current_exempts:
                await interaction.response.send_message(f"📝 No {type.value}s are currently exempted.", ephemeral=True)
                return
            
            # Get objects and create list
            if type.value == "role":
                objects = [interaction.guild.get_role(rid) for rid in current_exempts]
                objects = [obj.mention for obj in objects if obj]
            else:
                objects = [interaction.guild.get_channel(cid) for cid in current_exempts]
                objects = [obj.mention for obj in objects if obj]
            
            embed = discord.Embed(
                title=f"🔓 Exempt {type.value.title()}s",
                description="\n".join(objects) if objects else "None found",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not target:
            await interaction.response.send_message(f"❌ Please mention a {type.value} to {action.value}.", ephemeral=True)
            return
        
        # Parse target ID
        target_id = ''.join(filter(str.isdigit, target))
        if not target_id:
            await interaction.response.send_message(f"❌ Invalid {type.value} format.", ephemeral=True)
            return
        
        target_id = int(target_id)
        
        # Verify target exists
        if type.value == "role":
            target_obj = interaction.guild.get_role(target_id)
            if not target_obj:
                await interaction.response.send_message("❌ Role not found.", ephemeral=True)
                return
        else:
            target_obj = interaction.guild.get_channel(target_id)
            if not target_obj:
                await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
                return
        
        # Perform action
        if action.value == "add":
            if target_id not in current_exempts:
                guild_config[exempt_key].append(target_id)
                result = f"Added {target_obj.mention} to exemptions"
            else:
                result = f"{target_obj.mention} is already exempted"
        else:  # remove
            if target_id in current_exempts:
                guild_config[exempt_key].remove(target_id)
                result = f"Removed {target_obj.mention} from exemptions"
            else:
                result = f"{target_obj.mention} is not currently exempted"
        
        # Save and update
        self.set_guild_config(interaction.guild.id, guild_config)
        
        if guild_config.get('enabled', False):
            await self.apply_automod_rules(interaction.guild, guild_config)
        
        embed = discord.Embed(
            title="✅ Exemptions Updated",
            description=result,
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="automod.status", description="View AutoMod configuration status")
    async def automod_status(self, interaction: discord.Interaction):
        """View AutoMod status"""
        
        guild_config = self.get_guild_config(interaction.guild.id)
        
        embed = discord.Embed(
            title="🛡️ AutoMod Configuration",
            color=discord.Color.blue()
        )
        
        # Overall status
        overall_status = "✅ Enabled" if guild_config.get('enabled', False) else "❌ Disabled"
        embed.add_field(name="Overall Status", value=overall_status, inline=True)
        
        # Features
        features = [
            ("Spam Protection", guild_config.get('spam_protection', True)),
            ("Link Protection", guild_config.get('link_protection', False)),
            ("Caps Protection", guild_config.get('caps_protection', False)),
            ("Mention Spam", guild_config.get('mention_spam', False))
        ]
        
        feature_text = "\n".join([f"{'✅' if enabled else '❌'} {name}" for name, enabled in features])
        embed.add_field(name="Features", value=feature_text, inline=True)
        
        # Settings
        settings_text = f"Max Mentions: {guild_config.get('max_mentions', 5)}\n"
        settings_text += f"Caps Limit: {guild_config.get('caps_percentage', 70)}%\n"
        settings_text += f"Keywords: {len(guild_config.get('keyword_filter', []))}"
        embed.add_field(name="Settings", value=settings_text, inline=True)
        
        # Log channel
        log_channel_id = guild_config.get('log_channel')
        log_channel = interaction.guild.get_channel(log_channel_id) if log_channel_id else None
        log_text = log_channel.mention if log_channel else "Not set"
        embed.add_field(name="Log Channel", value=log_text, inline=False)
        
        # Exemptions
        exempt_roles = len(guild_config.get('exempt_roles', []))
        exempt_channels = len(guild_config.get('exempt_channels', []))
        exemption_text = f"Roles: {exempt_roles} • Channels: {exempt_channels}"
        embed.add_field(name="Exemptions", value=exemption_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AutoMod(bot))