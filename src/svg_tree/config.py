import os
import sys
import tomllib
from typing import Dict, Any, Optional

def load_theme(user_theme_path: Optional[str] = None) -> Dict[str, Any]:
    # 1. Determine paths
    xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    config_dir = os.path.join(xdg_config, 'svgtree')
    xdg_default_theme = os.path.join(config_dir, 'default-theme.toml')
    
    bundled_theme_path = None
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        bundled_theme_path = os.path.join(sys._MEIPASS, 'default-theme.toml')
    else:
        # Dev / Script mode fallback
        candidate = os.path.join(os.getcwd(), 'default-theme.toml')
        if os.path.exists(candidate):
            bundled_theme_path = candidate
        else:
            # Fallback to looking relative to this file's parent package
            # If this file is src/svg_tree/config.py, we want root/default-theme.toml
            # ../../../default-theme.toml
            bundled_theme_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../default-theme.toml")

    # Load base theme (XDG takes precedence over bundled default if it exists)
    path_to_load = xdg_default_theme if os.path.exists(xdg_default_theme) else bundled_theme_path
    
    theme = {}
    if path_to_load and os.path.exists(path_to_load):
        try:
            with open(path_to_load, "rb") as f:
                theme = tomllib.load(f)
        except Exception as e:
            print(f"Warning: Could not load theme from {path_to_load}: {e}")

    # 2. Merge User Theme (Flag)
    if user_theme_path:
        if os.path.exists(user_theme_path):
            try:
                with open(user_theme_path, "rb") as f:
                    user_theme = tomllib.load(f)
                    for section, values in user_theme.items():
                        if section in theme and isinstance(values, dict):
                            theme[section].update(values)
                        else:
                            theme[section] = values
            except Exception as e:
                print(f"Error loading user theme {user_theme_path}: {e}")
                sys.exit(1)
        else:
            print(f"Error: User theme file {user_theme_path} not found.")
            sys.exit(1)
            
    return theme
