"""
Discord Bot Cog: Port 3001 Enhanced Connectivity
Advanced script for Port 3001 connectivity and handling.

To import in bot.py, add this line:
await bot.load_extension('port3001')
"""

import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import logging
import json
from datetime import datetime

class Port3001(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.port = 3001
        self.base_url = f"http://localhost:{self.port}"
        self.session = None
        self.connection_status = False
        self.retry_count = 0
        self.max_retries = 5
        self.logger = logging.getLogger(__name__)
        
        # Start connection monitor
        self.connection_monitor.start()
        
    def cog_unload(self):
        self.connection_monitor.cancel()
        if self.session:
            asyncio.create_task(self.session.close())
    
    async def create_session(self):
        """Create aiohttp session with proper configuration"""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=60
            )
            # Use bot user ID if available, otherwise use a generic identifier
            user_agent = f'DiscordBot/{self.bot.user.id}' if self.bot.user else 'DiscordBot/Unknown'
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={'User-Agent': user_agent}
            )
    
    @tasks.loop(seconds=30)
    async def connection_monitor(self):
        """Monitor and maintain Port 3001 connection"""
        try:
            await self.create_session()
            
            # Health check endpoint
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.connection_status = True
                    self.retry_count = 0
                    self.logger.info(f"Port 3001 connection healthy: {data}")
                else:
                    await self.handle_connection_error(f"HTTP {response.status}")
                    
        except aiohttp.ClientError as e:
            await self.handle_connection_error(f"Client error: {e}")
        except asyncio.TimeoutError:
            await self.handle_connection_error("Connection timeout")
        except Exception as e:
            await self.handle_connection_error(f"Unexpected error: {e}")
    
    async def handle_connection_error(self, error_msg):
        """Handle connection errors with retry logic"""
        self.connection_status = False
        self.retry_count += 1
        self.logger.warning(f"Port 3001 connection error: {error_msg} (Retry {self.retry_count}/{self.max_retries})")
        
        if self.retry_count >= self.max_retries:
            self.logger.error("Max retries reached for Port 3001 connection")
            # Optionally notify bot owner
            if self.bot.owner_id:
                try:
                    owner = await self.bot.fetch_user(self.bot.owner_id)
                    await owner.send(f"⚠️ Port 3001 connection failed after {self.max_retries} retries: {error_msg}")
                except:
                    pass
    
    async def make_request(self, method, endpoint, **kwargs):
        """Make authenticated request to Port 3001"""
        await self.create_session()
        
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': f'Bot {self.bot.http.token}',
            'Content-Type': 'application/json'
        })
        
        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as response:
                if response.content_type == 'application/json':
                    return await response.json()
                return await response.text()
        except Exception as e:
            self.logger.error(f"Request failed to {endpoint}: {e}")
            raise
    
    @connection_monitor.before_loop
    async def before_connection_monitor(self):
        await self.bot.wait_until_ready()
        self.logger.info("Port 3001 connection monitor started")
    
    @commands.command(name='port_status', hidden=True)
    @commands.is_owner()
    async def port_status(self, ctx):
        """Check Port 3001 connection status"""
        status_emoji = "🟢" if self.connection_status else "🔴"
        embed = discord.Embed(
            title="Port 3001 Status",
            color=discord.Color.green() if self.connection_status else discord.Color.red()
        )
        embed.add_field(name="Status", value=f"{status_emoji} {'Connected' if self.connection_status else 'Disconnected'}")
        embed.add_field(name="Retry Count", value=f"{self.retry_count}/{self.max_retries}")
        embed.add_field(name="Last Check", value=datetime.now().strftime("%H:%M:%S"))
        await ctx.send(embed=embed)
    
    @commands.command(name='port_test', hidden=True)
    @commands.is_owner()
    async def port_test(self, ctx):
        """Test Port 3001 connection"""
        try:
            result = await self.make_request('GET', '/api/test')
            await ctx.send(f"✅ Port 3001 test successful: {result}")
        except Exception as e:
            await ctx.send(f"❌ Port 3001 test failed: {e}")

async def setup(bot):
    await bot.add_cog(Port3001(bot))