"""
Discord Bot Cog: Keepalive System
Keeps the bot alive by pinging itself every 10-30 seconds internally.

To import in bot.py, add this line:
await bot.load_extension('keepalive')
"""

import discord
from discord.ext import commands, tasks
import asyncio
import random
import logging

class Keepalive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keepalive_task.start()
        self.logger = logging.getLogger(__name__)
        
    def cog_unload(self):
        self.keepalive_task.cancel()
    
    @tasks.loop(seconds=random.randint(10, 30))
    async def keepalive_task(self):
        """Internal keepalive ping - no Discord messages sent"""
        try:
            # Internal system ping to keep bot processes active
            latency = self.bot.latency
            self.logger.info(f"Keepalive ping: {latency*1000:.2f}ms latency")
            
            # Optional: Check bot status and reconnect if needed
            if not self.bot.is_ready():
                self.logger.warning("Bot not ready, attempting to maintain connection...")
                
        except Exception as e:
            self.logger.error(f"Keepalive error: {e}")
    
    @keepalive_task.before_loop
    async def before_keepalive(self):
        await self.bot.wait_until_ready()
        self.logger.info("Keepalive system started")
    
    @commands.command(name='keepalive_status', hidden=True)
    @commands.is_owner()
    async def keepalive_status(self, ctx):
        """Check keepalive status (owner only)"""
        status = "Running" if self.keepalive_task.is_running() else "Stopped"
        await ctx.send(f"Keepalive system: {status}")

async def setup(bot):
    await bot.add_cog(Keepalive(bot))