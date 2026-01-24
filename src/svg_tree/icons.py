import os
import sys
import requests
from typing import Tuple, Dict, Any
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen

from .consts import ICONS, EXT_MAP, FONT_URL

def get_font_path() -> str:
    xdg_config = os.environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    return os.path.join(xdg_config, 'svgtree', 'assets', 'SymbolsNerdFont-Regular.ttf')

def ensure_font_exists():
    font_path = get_font_path()
    if not os.path.exists(font_path):
        os.makedirs(os.path.dirname(font_path), exist_ok=True)
        print(f"Downloading Nerd Font symbols to {font_path}...")
        try:
            r = requests.get(FONT_URL)
            r.raise_for_status()
            with open(font_path, 'wb') as f:
                f.write(r.content)
            print("Font downloaded.")
        except Exception as e:
            print(f"Error downloading font: {e}")
            sys.exit(1)

def get_glyph_path(font: TTFont, unicode_char: str) -> str:
    cmap = font.getBestCmap()
    code_point = ord(unicode_char)
    if code_point not in cmap: return ""
    glyph_name = cmap[code_point]
    glyph_set = font.getGlyphSet()
    if glyph_name not in glyph_set: return ""
    pen = SVGPathPen(glyph_set)
    glyph = glyph_set[glyph_name]
    glyph.draw(pen)
    return pen.getCommands()

def get_icon_and_color(name: str, is_dir: bool, theme: Dict[str, Any]) -> Tuple[str, str]:
    file_colors = theme.get('file_colors', {})
    colors_cfg = theme.get('colors', {})
    
    if is_dir:
        return ICONS['folder'], file_colors.get('folder', colors_cfg.get('text_folder', '#0000FF'))
    
    ext = os.path.splitext(name)[1].lower()
    
    if name == '.gitignore' or name == '.git':
        return ICONS['git'], file_colors.get('git', '#FF0000')
    
    icon_key = EXT_MAP.get(ext, 'default')
    icon_char = ICONS.get(icon_key, ICONS['default'])
    
    if name.startswith('.'):
        color = file_colors.get('hidden', '#555555')
    else:
        color = file_colors.get(icon_key, colors_cfg.get('icon_default', '#CCCCCC'))
        
    return icon_char, color
