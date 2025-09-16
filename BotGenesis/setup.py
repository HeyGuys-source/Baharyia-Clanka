#!/usr/bin/env python3
"""
Advanced Discord Bot Setup Script
Automates the initial setup and configuration process.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def install_requirements():
    """Install required Python packages"""
    print("🔧 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies!")
        return False
    return True

def create_env_file():
    """Create .env file from template"""
    print("📝 Setting up environment configuration...")
    
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        choice = input("Do you want to overwrite it? (y/N): ").lower()
        if choice != 'y':
            return True
    
    # Get Discord token from user
    print("\n🤖 Discord Bot Setup:")
    print("1. Go to https://discord.com/developers/applications")
    print("2. Create a new application or select existing one")
    print("3. Go to 'Bot' section and copy the token")
    print("4. Make sure bot has necessary permissions")
    
    token = input("\nEnter your Discord bot token: ").strip()
    
    if not token:
        print("❌ No token provided!")
        return False
    
    # Create .env file
    env_content = f"""# Discord Bot Configuration
DISCORD_TOKEN={token}

# Database Configuration (Optional - uses built-in database if not specified)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=
DATABASE_NAME=discord_bot

# Bot Configuration
LOG_LEVEL=INFO
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Environment file created successfully!")
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False
    
    return True

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = ['logs', 'data', 'cogs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created successfully!")
    return True

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python version compatible: {sys.version}")
    return True

def display_next_steps():
    """Display next steps for the user"""
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Make sure your Discord bot has the following permissions:")
    print("   • View Channels")
    print("   • Send Messages") 
    print("   • Manage Messages")
    print("   • Embed Links")
    print("   • Use Slash Commands")
    print("   • Kick Members")
    print("   • Ban Members")
    print("   • Manage Roles")
    print("   • Manage Channels")
    print("   • Moderate Members")
    print("\n2. Invite your bot to a Discord server")
    print("\n3. Run the bot with: python main.py")
    print("\n4. Use /help in Discord to see available commands")
    print("\n5. Configure the bot with: /config_bot")
    print("\n📖 For detailed information, check README.md")

def main():
    """Main setup function"""
    print("🚀 Advanced Discord Moderation Bot Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Display next steps
    display_next_steps()

if __name__ == "__main__":
    main()