# Overview

An advanced Discord moderation bot built with discord.py that provides comprehensive server management capabilities. The bot features 30+ commands organized into three main categories: moderation (20 commands), administration (10 commands), and a specialized echo system. It includes 24/7 uptime monitoring, database integration for persistent data storage, and a modular cog-based architecture for maintainability.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Discord.py Framework**: Uses discord.py library with application commands (slash commands) for modern Discord interaction
- **Cog-based Organization**: Modular design with separate cogs for different functionality areas (moderation, administration, echo, utility)
- **Rich Embed System**: Consistent embed formatting across all commands with timestamps, footers, and color coding

## Backend Architecture
- **Asynchronous Python**: Built on asyncio for handling concurrent Discord events and database operations
- **Command System**: Hybrid approach supporting both traditional prefix commands and modern slash commands
- **Error Handling**: Comprehensive error management with user-friendly feedback and logging
- **Permission-based Access Control**: Role and permission-based command restrictions (administrator-only features)

## Data Storage Solutions
- **PostgreSQL Integration**: Primary database using asyncpg for connection pooling and async operations
- **Database Schema**: Guild settings table for server-specific configurations (log channels, permissions)
- **Fallback System**: Graceful degradation when database is unavailable

## Authentication and Authorization
- **Discord OAuth**: Bot authentication through Discord developer portal and bot tokens
- **Permission Hierarchy**: Command restrictions based on Discord server permissions (administrator, moderator roles)
- **Guild-specific Settings**: Per-server configuration and permission management

## Monitoring and Reliability
- **Keepalive Web Server**: Built-in HTTP server (aiohttp) for uptime monitoring and health checks
- **Comprehensive Logging**: File-based and console logging with different log levels
- **Process Monitoring**: System resource monitoring using psutil for bot statistics

# External Dependencies

## Discord Integration
- **Discord API**: Core bot functionality through discord.py library
- **Gateway Connection**: Real-time event handling for Discord server events
- **Webhook Support**: Advanced message delivery and logging capabilities

## Database Services
- **PostgreSQL**: Primary database for persistent data storage (guild settings, user data, logs)
- **Connection Pooling**: asyncpg library for efficient database connection management

## Infrastructure Services
- **Web Server**: aiohttp for serving status pages and health checks
- **Environment Management**: python-dotenv for configuration management
- **System Monitoring**: psutil for system resource tracking and bot statistics

## Development Dependencies
- **Setup Automation**: Custom setup script for bot configuration and dependency installation
- **Logging Infrastructure**: Python logging module with file rotation and multiple handlers
- **Error Tracking**: Comprehensive exception handling and error reporting system