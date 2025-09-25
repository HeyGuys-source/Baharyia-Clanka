#!/usr/bin/env python3
"""
Advanced Discord Moderation Bot
A comprehensive Discord bot with moderation, administration, and utility features.
"""

import discord
from discord.ext import commands
import os
import asyncio
import asyncpg
import aiohttp
import logging
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedModerationBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        self.db_pool = None
        self.start_time = datetime.utcnow()
        self.session = None
        
    async def setup_database(self):
        """Initialize database connection pool"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if database_url:
                self.db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=10)
            else:
                self.db_pool = await asyncpg.create_pool(
                    host=os.getenv('PGHOST', 'localhost'),
                    port=int(os.getenv('PGPORT', 5432)),
                    user=os.getenv('PGUSER', 'postgres'),
                    password=os.getenv('PGPASSWORD', ''),
                    database=os.getenv('PGDATABASE', 'discord_bot'),
                    min_size=1,
                    max_size=10
                )
            logger.info("Database connection pool established")
            
            # Create tables if they don't exist
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS warnings (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        guild_id BIGINT NOT NULL,
                        moderator_id BIGINT NOT NULL,
                        reason TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS mutes (
                        user_id BIGINT PRIMARY KEY,
                        guild_id BIGINT NOT NULL,
                        end_time TIMESTAMP,
                        reason TEXT
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS guild_settings (
                        guild_id BIGINT PRIMARY KEY,
                        log_channel_id BIGINT,
                        mute_role_id BIGINT,
                        auto_mod BOOLEAN DEFAULT FALSE,
                        settings JSONB DEFAULT '{}'
                    )
                ''')
                
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
    
    async def setup_hook(self):
        """Setup hook called when bot starts"""
        try:
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Load all cogs
            cogs_to_load = [
                'cogs.moderation',
                'cogs.administration', 
                'cogs.echo',
                'cogs.utility',
                'cogs.forum_reactions',
                'cogs.reconnection_cog'
                y
            ]
            
            for cog in cogs_to_load:
                try:
                    await self.load_extension(cog)
                    logger.info(f"Loaded cog: {cog}")
                except Exception as e:
                    logger.error(f"Failed to load cog {cog}: {e}")
            
            # Setup database
            await self.setup_database()
            
            # Sync slash commands
            await self.tree.sync()
            logger.info("Slash commands synced")
            
        except Exception as e:
            logger.error(f"Setup hook failed: {e}")
    
    async def close(self):
        """Cleanup when bot shuts down"""
        if self.session:
            await self.session.close()
        if self.db_pool:
            await self.db_pool.close()
        await super().close()
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"{self.user} has connected to Discord!")
        logger.info(f"Bot is in {len(self.guilds)} guilds")
        
        # Set status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server | !help"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    async def on_command_error(self, ctx, error):
        """Global error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You don't have permission to use this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description="I don't have the required permissions to execute this command.",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"Unhandled error: {error}")
            embed = discord.Embed(
                title="❌ Error",
                description="An unexpected error occurred.",
                color=0xff0000
            )
            await ctx.send(embed=embed)

# Create bot instance
bot = AdvancedModerationBot()

if __name__ == "__main__":
    try:
        # Import keepalive to start web server
        from keepalive import keep_alive
        keep_alive()
        
        # Run bot
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("DISCORD_TOKEN environment variable not set")
            exit(1)
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
