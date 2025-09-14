"""
Advanced Configuration System for Discord Bot
Supports YAML configuration with environment variable substitution
"""

import os
import yaml
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors"""
    pass

class Settings:
    """Advanced configuration management system"""
    
    def __init__(self, config_path: str = "config.yaml", alt_config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.alt_config_path = Path(alt_config_path)
        self._config: Dict[str, Any] = {}
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from YAML or JSON file with environment variable substitution"""
        config_file = None
        
        # Try YAML first, then JSON
        if self.config_path.exists():
            config_file = self.config_path
            loader_func = self._load_yaml
        elif self.alt_config_path.exists():
            config_file = self.alt_config_path  
            loader_func = self._load_json
        else:
            raise ConfigurationError(f"Configuration file not found: {self.config_path} or {self.alt_config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substitute environment variables
            content = self._substitute_env_vars(content)
            
            # Load the configuration
            if config_file.suffix.lower() == '.yaml' or config_file.suffix.lower() == '.yml':
                self._config = yaml.safe_load(content)
            else:
                self._config = json.loads(content)
                
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Invalid configuration format in {config_file}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_file}: {e}")
    
    def _load_yaml(self, content: str) -> Dict[str, Any]:
        """Load YAML content"""
        return yaml.safe_load(content)
    
    def _load_json(self, content: str) -> Dict[str, Any]:
        """Load JSON content"""
        return json.loads(content)
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in configuration content"""
        # Pattern to match ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            
            # Get environment variable or use default
            value = os.getenv(var_name, default_value)
            return value
        
        return re.sub(pattern, replacer, content)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'bot.token')"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_required(self, key: str) -> Any:
        """Get required configuration value, raise error if missing"""
        value = self.get(key)
        if value is None or value == "":
            raise ConfigurationError(f"Required configuration key '{key}' is missing or empty")
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final key
        config[keys[-1]] = value
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._load_configuration()
    
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary"""
        return self._config.copy()
    
    def save(self, path: Optional[str] = None) -> None:
        """Save current configuration to file"""
        save_path = Path(path) if path else self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                if save_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self._config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration to {save_path}: {e}")

# Global settings instance
settings = Settings()

# Convenience functions for common configuration access
def get_bot_token() -> str:
    """Get Discord bot token"""
    return settings.get_required('bot.token')

def get_colors() -> Dict[str, str]:
    """Get color scheme configuration"""
    return settings.get('colors', {
        'primary': '#ba4628',
        'secondary': '#56f87b',
        'error': '#ff4757',
        'warning': '#ffa502',
        'success': '#2ed573',
        'info': '#5352ed'
    })

def get_admin_roles() -> list:
    """Get admin role names"""
    return settings.get('permissions.admin_roles', ['Admin', 'Administrator', 'Owner', 'Moderator'])

def get_server_config() -> Dict[str, Any]:
    """Get server configuration"""
    return settings.get('server', {'port': 3001, 'host': '0.0.0.0'})

def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration"""
    return settings.get('logging', {
        'level': 'INFO',
        'log_channel_id': '',
        'file_logging': {
            'enabled': True,
            'max_size': '10 MB',
            'backup_count': 5
        }
    })