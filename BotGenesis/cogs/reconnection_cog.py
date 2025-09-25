import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional


class ReconnectionCog(commands.Cog):
    """
    A Discord bot cog that handles automatic reconnection logic when the bot's connection is dropped.
    
    Features:
    - Automatic connection monitoring
    - Exponential backoff retry mechanism
    - Comprehensive logging of connection events
    - Configurable retry parameters
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
        
        # Reconnection configuration
        self.max_retries = 10
        self.base_delay = 5  # Base delay in seconds
        self.max_delay = 300  # Maximum delay in seconds (5 minutes)
        self.retry_count = 0
        self.last_disconnect_time: Optional[datetime] = None
        self.is_reconnecting = False
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging for the reconnection cog."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] [RECONNECTION] %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.connection_monitor.is_running():
            self.connection_monitor.cancel()
        
    @tasks.loop(seconds=30)
    async def connection_monitor(self):
        """Monitor the bot's connection status."""
        if not self.bot.is_ready() or self.is_reconnecting:
            return
            
        # Check if we're connected and can reach Discord
        try:
            # Try to fetch the bot's user info as a connection test
            if self.bot.user:
                await asyncio.wait_for(self.bot.fetch_user(self.bot.user.id), timeout=10.0)
            
            # If we reach here and had previous disconnection issues, log recovery
            if self.retry_count > 0:
                self.logger.info(f"Connection successfully restored after {self.retry_count} retry attempts")
                self.retry_count = 0
                self.last_disconnect_time = None
                self.is_reconnecting = False
                
        except (discord.HTTPException, discord.ConnectionClosed, asyncio.TimeoutError, 
                discord.NotFound, discord.Forbidden, ConnectionError, OSError) as e:
            self.logger.warning(f"Connection issue detected: {type(e).__name__}: {e}")
            if not self.is_reconnecting:
                asyncio.create_task(self.handle_connection_error(e))
            
    @connection_monitor.before_loop
    async def before_connection_monitor(self):
        """Wait for the bot to be ready before starting the monitor."""
        await self.bot.wait_until_ready()
        self.logger.info("Connection monitoring started")
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Handle bot ready event."""
        if self.bot.user:
            self.logger.info(f"Bot connected as {self.bot.user} (ID: {self.bot.user.id})")
        else:
            self.logger.info("Bot connected (user info not available yet)")
        
        # Start connection monitoring if not already running
        if not self.connection_monitor.is_running():
            self.connection_monitor.start()
        
        # Reset retry count on successful connection
        if self.retry_count > 0:
            self.logger.info(f"Successfully reconnected after {self.retry_count} attempts")
            self.retry_count = 0
            self.last_disconnect_time = None
            self.is_reconnecting = False
            
    @commands.Cog.listener()
    async def on_disconnect(self):
        """Handle bot disconnect event."""
        self.last_disconnect_time = datetime.utcnow()
        self.logger.warning("Bot disconnected from Discord")
        
        # Start reconnection logic if not already reconnecting
        if not self.is_reconnecting:
            asyncio.create_task(self.handle_connection_error(Exception("Bot disconnected")))
        
    @commands.Cog.listener()
    async def on_resumed(self):
        """Handle bot resume event."""
        self.logger.info("Bot session resumed")
        
        # Reset retry count on successful resume
        if self.retry_count > 0:
            self.logger.info(f"Session resumed after {self.retry_count} reconnection attempts")
            self.retry_count = 0
            self.last_disconnect_time = None
            self.is_reconnecting = False
            
    @commands.Cog.listener()
    async def on_connect(self):
        """Handle bot connect event."""
        if self.retry_count > 0:
            self.logger.info(f"Reconnection attempt {self.retry_count} successful")
        else:
            self.logger.info("Initial connection established")
            
    async def handle_connection_error(self, error: Exception):
        """
        Handle connection errors with exponential backoff retry logic.
        
        Args:
            error: The exception that caused the connection error
        """
        if self.is_reconnecting:
            return  # Already handling reconnection
            
        self.is_reconnecting = True
        self.logger.error(f"Connection error detected: {type(error).__name__}: {error}")
        
        try:
            # Reset retry count at start of new reconnection attempt
            self.retry_count = 0
            
            # Retry loop with exponential backoff
            while not self.bot.is_ready() and self.retry_count < self.max_retries:
                self.retry_count += 1
                
                # Calculate delay with exponential backoff
                delay = min(self.base_delay * (2 ** (self.retry_count - 1)), self.max_delay)
                self.logger.info(f"Waiting {delay} seconds before reconnection attempt {self.retry_count}/{self.max_retries}")
                
                await asyncio.sleep(delay)
                
                # Check if bot has recovered during our wait
                if self.bot.is_ready():
                    self.logger.info(f"Bot recovered during backoff wait (attempt {self.retry_count})")
                    break
                
                try:
                    self.logger.info(f"Testing connection (attempt {self.retry_count}/{self.max_retries})")
                    # Test connection with a simple API call
                    if self.bot.user:
                        await asyncio.wait_for(self.bot.fetch_user(self.bot.user.id), timeout=10.0)
                        self.logger.info(f"Connection test successful on attempt {self.retry_count}")
                        break
                    else:
                        self.logger.warning("Bot user not available for connection test")
                        
                except Exception as test_error:
                    self.logger.error(f"Connection test failed on attempt {self.retry_count}: {type(test_error).__name__}: {test_error}")
                    # Continue loop for next retry
                    continue
            
            # Check final status
            if self.retry_count >= self.max_retries and not self.bot.is_ready():
                self.logger.critical(f"Max retry attempts ({self.max_retries}) exceeded. Manual intervention required.")
                # Start a slower periodic check instead of giving up completely
                asyncio.create_task(self._periodic_health_check())
            elif self.bot.is_ready():
                self.logger.info(f"Connection successfully restored after {self.retry_count} attempts")
                
        finally:
            # Always reset reconnection state
            self.is_reconnecting = False
            if self.bot.is_ready():
                self.retry_count = 0
                self.last_disconnect_time = None
                
    async def _periodic_health_check(self):
        """
        Perform periodic health checks after max retries exceeded.
        This runs at a slower interval to avoid overwhelming Discord's API.
        """
        self.logger.info("Starting periodic health check after max retries exceeded")
        
        while not self.bot.is_ready():
            await asyncio.sleep(60)  # Check every minute
            
            try:
                if self.bot.user:
                    await asyncio.wait_for(self.bot.fetch_user(self.bot.user.id), timeout=10.0)
                    self.logger.info("Periodic health check: Connection restored!")
                    self.retry_count = 0
                    self.last_disconnect_time = None
                    break
            except Exception as e:
                self.logger.debug(f"Periodic health check failed: {type(e).__name__}: {e}")
                continue
                
        self.logger.info("Periodic health check completed - connection restored")
            
    @commands.command(name="connection_status")
    @commands.has_permissions(administrator=True)
    async def connection_status(self, ctx):
        """
        Check the current connection status and statistics.
        
        Usage: !connection_status (requires administrator permissions)
        """
        embed = discord.Embed(
            title="🔗 Connection Status",
            color=discord.Color.green() if self.bot.is_ready() else discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        # Connection status
        status = "🟢 Connected" if self.bot.is_ready() else "🔴 Disconnected"
        embed.add_field(name="Status", value=status, inline=True)
        
        # Latency
        latency = round(self.bot.latency * 1000, 2)
        embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
        
        # Retry statistics
        embed.add_field(name="Current Retry Count", value=str(self.retry_count), inline=True)
        
        # Last disconnect time
        if self.last_disconnect_time:
            time_since = datetime.utcnow() - self.last_disconnect_time
            embed.add_field(
                name="Last Disconnect", 
                value=f"{time_since.total_seconds():.1f} seconds ago", 
                inline=True
            )
        else:
            embed.add_field(name="Last Disconnect", value="None recorded", inline=True)
            
        # Configuration
        embed.add_field(name="Max Retries", value=str(self.max_retries), inline=True)
        embed.add_field(name="Base Delay", value=f"{self.base_delay}s", inline=True)
        
        await ctx.send(embed=embed)
        
    @commands.command(name="reconnect_config")
    @commands.has_permissions(administrator=True)
    async def reconnect_config(self, ctx, max_retries: Optional[int] = None, base_delay: Optional[int] = None, max_delay: Optional[int] = None):
        """
        Configure reconnection parameters.
        
        Usage: !reconnect_config [max_retries] [base_delay] [max_delay]
        
        Args:
            max_retries: Maximum number of retry attempts (default: 10)
            base_delay: Base delay between retries in seconds (default: 5)
            max_delay: Maximum delay between retries in seconds (default: 300)
        """
        updated = []
        
        if max_retries is not None:
            if 1 <= max_retries <= 50:
                self.max_retries = max_retries
                updated.append(f"Max retries: {max_retries}")
            else:
                await ctx.send("❌ Max retries must be between 1 and 50")
                return
                
        if base_delay is not None:
            if 1 <= base_delay <= 60:
                self.base_delay = base_delay
                updated.append(f"Base delay: {base_delay}s")
            else:
                await ctx.send("❌ Base delay must be between 1 and 60 seconds")
                return
                
        if max_delay is not None:
            if 60 <= max_delay <= 3600:
                self.max_delay = max_delay
                updated.append(f"Max delay: {max_delay}s")
            else:
                await ctx.send("❌ Max delay must be between 60 and 3600 seconds")
                return
                
        if updated:
            embed = discord.Embed(
                title="✅ Reconnection Configuration Updated",
                description="\n".join(updated),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await ctx.send(embed=embed)
            self.logger.info(f"Reconnection config updated by {ctx.author}: {', '.join(updated)}")
        else:
            # Show current configuration
            embed = discord.Embed(
                title="🔧 Current Reconnection Configuration",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Max Retries", value=str(self.max_retries), inline=True)
            embed.add_field(name="Base Delay", value=f"{self.base_delay}s", inline=True)
            embed.add_field(name="Max Delay", value=f"{self.max_delay}s", inline=True)
            await ctx.send(embed=embed)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(ReconnectionCog(bot))
    

async def teardown(bot):
    """Teardown function to remove the cog from the bot."""
    await bot.remove_cog("ReconnectionCog")