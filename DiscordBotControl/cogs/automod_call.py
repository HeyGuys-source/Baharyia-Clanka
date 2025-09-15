"""
Discord Bot Cog: AutoMod API Interface
Interfaces with Discord AutoMod API to enable automod badge and functionality.

To import in bot.py, add this line:
await bot.load_extension('automod_call')
"""

import discord
from discord.ext import commands, tasks
import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta

class AutoModCall(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        self.automod_status = {}
        
        # Start AutoMod monitoring
        self.automod_monitor.start()
    
    def cog_unload(self):
        self.automod_monitor.cancel()
    
    async def check_automod_status(self, guild):
        """Check AutoMod status for a guild"""
        try:
            # Fetch AutoMod rules for the guild
            rules = await guild.fetch_automod_rules()
            
            self.automod_status[guild.id] = {
                'enabled': len(rules) > 0,
                'rules_count': len(rules),
                'last_check': datetime.utcnow(),
                'rules': [{'name': rule.name, 'enabled': rule.enabled} for rule in rules]
            }
            
            return len(rules) > 0
            
        except discord.Forbidden:
            self.logger.warning(f"No permission to access AutoMod in {guild.name}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking AutoMod status in {guild.name}: {e}")
            return False
    
    async def enable_automod_integration(self, guild):
        """Enable AutoMod integration and get badge"""
        try:
            # Check if AutoMod is already enabled
            rules = await guild.fetch_automod_rules()
            
            if not rules:
                # Create basic AutoMod rules to enable badge
                await self.create_basic_automod_rules(guild)
            
            # Update status
            await self.check_automod_status(guild)
            
            self.logger.info(f"AutoMod integration enabled for {guild.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enabling AutoMod integration: {e}")
            return False
    
    async def create_basic_automod_rules(self, guild):
        """Create basic AutoMod rules to enable the feature"""
        try:
            # Rule 1: Block spam
            spam_rule = await guild.create_automod_rule(
                name="Spam Protection",
                event_type=discord.AutoModEventType.message_send,
                trigger=discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.spam
                ),
                actions=[
                    discord.AutoModRuleAction(
                        type=discord.AutoModRuleActionType.block_message,
                        metadata=discord.AutoModActionMetadata(
                            custom_message="Message blocked by AutoMod: Spam detected"
                        )
                    )
                ],
                enabled=True,
                exempt_roles=[],
                exempt_channels=[],
                reason="Basic spam protection enabled by bot"
            )
            
            # Rule 2: Block common inappropriate keywords
            keyword_rule = await guild.create_automod_rule(
                name="Keyword Filter",
                event_type=discord.AutoModEventType.message_send,
                trigger=discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.keyword,
                    keyword_filter=["spam", "scam", "hack", "free nitro"]
                ),
                actions=[
                    discord.AutoModRuleAction(
                        type=discord.AutoModRuleActionType.block_message,
                        metadata=discord.AutoModActionMetadata(
                            custom_message="Message blocked by AutoMod: Inappropriate content detected"
                        )
                    )
                ],
                enabled=True,
                exempt_roles=[],
                exempt_channels=[],
                reason="Basic keyword filtering enabled by bot"
            )
            
            self.logger.info(f"Created basic AutoMod rules for {guild.name}")
            return True
            
        except discord.Forbidden:
            self.logger.error(f"No permission to create AutoMod rules in {guild.name}")
            return False
        except Exception as e:
            self.logger.error(f"Error creating AutoMod rules: {e}")
            return False
    
    @tasks.loop(hours=1)
    async def automod_monitor(self):
        """Monitor AutoMod status across all guilds"""
        try:
            for guild in self.bot.guilds:
                await self.check_automod_status(guild)
                await asyncio.sleep(2)  # Rate limit
                
        except Exception as e:
            self.logger.error(f"Error in AutoMod monitor: {e}")
    
    @automod_monitor.before_loop
    async def before_automod_monitor(self):
        await self.bot.wait_until_ready()
        self.logger.info("AutoMod monitor started")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Auto-enable AutoMod when joining a new guild"""
        try:
            # Wait a bit for permissions to settle
            await asyncio.sleep(5)
            
            # Check if we have permission and enable AutoMod
            if guild.me.guild_permissions.manage_guild:
                await self.enable_automod_integration(guild)
                self.logger.info(f"Auto-enabled AutoMod for new guild: {guild.name}")
        except Exception as e:
            self.logger.error(f"Error auto-enabling AutoMod for {guild.name}: {e}")
    
    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule):
        """Log when AutoMod rules are created"""
        self.logger.info(f"AutoMod rule '{rule.name}' created in {rule.guild.name}")
        await self.check_automod_status(rule.guild)
    
    @commands.Cog.listener()
    async def on_automod_rule_update(self, rule):
        """Log when AutoMod rules are updated"""
        self.logger.info(f"AutoMod rule '{rule.name}' updated in {rule.guild.name}")
        await self.check_automod_status(rule.guild)
    
    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule):
        """Log when AutoMod rules are deleted"""
        self.logger.info(f"AutoMod rule '{rule.name}' deleted in {rule.guild.name}")
        await self.check_automod_status(rule.guild)
    
    @commands.Cog.listener()
    async def on_automod_action(self, execution):
        """Log AutoMod actions"""
        try:
            rule_name = execution.rule.name if execution.rule else "Unknown Rule"
            action_type = execution.action.type.name if execution.action else "Unknown Action"
            
            self.logger.info(
                f"AutoMod action in {execution.guild.name}: "
                f"Rule '{rule_name}' - Action: {action_type} - "
                f"User: {execution.user_id} - Channel: {execution.channel_id}"
            )
            
            # Update rule usage stats
            if execution.guild.id in self.automod_status:
                self.automod_status[execution.guild.id]['last_action'] = datetime.utcnow()
                
        except Exception as e:
            self.logger.error(f"Error logging AutoMod action: {e}")
    
    @commands.command(name='automod_status', hidden=True)
    @commands.is_owner()
    async def automod_status_command(self, ctx):
        """Check AutoMod status (Owner only)"""
        try:
            guild_status = self.automod_status.get(ctx.guild.id)
            
            if not guild_status:
                await self.check_automod_status(ctx.guild)
                guild_status = self.automod_status.get(ctx.guild.id, {})
            
            embed = discord.Embed(
                title="🛡️ AutoMod Status",
                color=discord.Color.green() if guild_status.get('enabled') else discord.Color.red()
            )
            
            status_emoji = "✅" if guild_status.get('enabled') else "❌"
            embed.add_field(name="Status", value=f"{status_emoji} {'Enabled' if guild_status.get('enabled') else 'Disabled'}")
            embed.add_field(name="Rules Count", value=str(guild_status.get('rules_count', 0)))
            
            if guild_status.get('last_check'):
                last_check = guild_status['last_check']
                embed.add_field(name="Last Check", value=f"<t:{int(last_check.timestamp())}:R>")
            
            if guild_status.get('last_action'):
                last_action = guild_status['last_action']
                embed.add_field(name="Last Action", value=f"<t:{int(last_action.timestamp())}:R>")
            
            # List rules
            rules = guild_status.get('rules', [])
            if rules:
                rules_text = "\n".join([f"• {rule['name']} {'✅' if rule['enabled'] else '❌'}" for rule in rules[:10]])
                if len(rules) > 10:
                    rules_text += f"\n... and {len(rules) - 10} more"
                embed.add_field(name="Active Rules", value=rules_text, inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking AutoMod status: {str(e)}")
    
    @commands.command(name='enable_automod', hidden=True)
    @commands.has_permissions(manage_guild=True)
    async def enable_automod_command(self, ctx):
        """Enable AutoMod integration"""
        try:
            success = await self.enable_automod_integration(ctx.guild)
            
            if success:
                embed = discord.Embed(
                    title="✅ AutoMod Enabled",
                    description="AutoMod integration has been enabled for this server.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Badge Status", value="AutoMod badge should now be visible")
                embed.add_field(name="Rules Created", value="Basic spam and keyword protection enabled")
            else:
                embed = discord.Embed(
                    title="❌ AutoMod Enable Failed",
                    description="Failed to enable AutoMod integration.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Common Issues", value="• Missing 'Manage Server' permission\n• AutoMod not available in this server")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error enabling AutoMod: {str(e)}")
    
    async def get_automod_analytics(self, guild):
        """Get AutoMod analytics and statistics"""
        try:
            rules = await guild.fetch_automod_rules()
            
            analytics = {
                'total_rules': len(rules),
                'enabled_rules': len([r for r in rules if r.enabled]),
                'rule_types': {},
                'last_updated': datetime.utcnow()
            }
            
            # Categorize rules by type
            for rule in rules:
                rule_type = rule.trigger.type.name if rule.trigger else 'unknown'
                analytics['rule_types'][rule_type] = analytics['rule_types'].get(rule_type, 0) + 1
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting AutoMod analytics: {e}")
            return None

async def setup(bot):
    await bot.add_cog(AutoModCall(bot))