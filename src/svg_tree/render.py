import os
import base64
import mimetypes
import svgwrite
from typing import List, Dict, Any
from fontTools.ttLib import TTFont

from .core import TreeEntry, flatten_tree
from .icons import get_font_path, ensure_font_exists, get_glyph_path, get_icon_and_color
from .export import export_png

def parse_font_weight(thickness: str) -> str:
    thickness = str(thickness).lower()
    mapping = {
        "thin": "100",
        "extralight": "200",
        "light": "300",
        "regular": "400",
        "medium": "500",
        "semibold": "600",
        "bold": "700",
        "extrabold": "800",
        "black": "900",
        "normal": "400"
    }
    return mapping.get(thickness, thickness)

def generate_svg(root_path: str, output_path: str, tree_nodes: List[TreeEntry], theme: Dict[str, Any], save_png: bool = False, png_scale: int = 1):
    ensure_font_exists()
    font_path = get_font_path()
    try:
        font = TTFont(font_path)
    except Exception as e:
        print(f"Could not load font from {font_path}: {e}")
        return

    # Extract Theme Variables
    layout = theme.get('layout', {})
    colors_cfg = theme.get('colors', {})
    font_cfg = theme.get('font', {})
    
    row_height = layout.get('row_height', 30)
    padding = layout.get('padding', 40)
    indent_unit = layout.get('indent_pixels', 24)
    font_size = layout.get('font_size', 14)
    
    # Font Logic
    family = font_cfg.get('family', 'monospace')
    f_type = font_cfg.get('type', '')
    thickness = font_cfg.get('thickness', 'Regular')
    custom_font_path = font_cfg.get('path')
    
    css_weight = parse_font_weight(thickness)
    
    # Construct smart font stack
    if f_type:
        font_stack = f'"{family} {f_type}", "{family}", monospace'
        css_family_name = f"{family} {f_type}"
    else:
        font_stack = f'"{family}", monospace'
        css_family_name = family

    font_face_rule = ""
    if custom_font_path:
        if os.path.exists(custom_font_path):
            try:
                mime_type, _ = mimetypes.guess_type(custom_font_path)
                if not mime_type:
                    mime_type = "font/ttf"
                
                with open(custom_font_path, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode('utf-8')
                    
                font_face_rule = f"""
                    @font-face {{
                        font-family: "{css_family_name}";
                        src: url("data:{mime_type};base64,{b64_data}") format("truetype");
                        font-weight: {css_weight};
                        font-style: normal;
                    }}
                """
                print(f"Embedded font from {custom_font_path}")
            except Exception as e:
                print(f"Error embedding font: {e}")
        else:
            print(f"Warning: Font path '{custom_font_path}' not found.")
    
    bg_color = colors_cfg.get('background', '#282c34')
    line_color = colors_cfg.get('lines', '#5c6370')
    text_file_color = colors_cfg.get('text_file', '#abb2bf')
    text_folder_color = colors_cfg.get('text_folder', '#61afef')

    visual_rows = list(flatten_tree(tree_nodes))
    
    # Calculate dimensions
    content_height = (len(visual_rows) + 1) * row_height
    total_height = content_height + (padding * 2)
    
    max_len = 0
    root_name = os.path.basename(os.path.abspath(root_path)) or root_path
    max_len = max(max_len, len(root_name) * 10 + 30)

    for node in visual_rows:
        w = (node.depth + 1) * indent_unit + (len(node.name) * 10) + 30
        if w > max_len:
            max_len = w
            
    total_width = max_len + (padding * 2) + 100 
    
    dwg = svgwrite.Drawing(output_path, size=(total_width, total_height), profile='full')
    
    # Background
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill=bg_color))
    
    # Font styles
    dwg.defs.add(dwg.style(f"""
        {font_face_rule}
        text {{ font-family: {font_stack}; font-size: {font_size}px; font-weight: {css_weight}; dominant-baseline: middle; }}
        .folder {{ font-weight: bold; fill: {text_folder_color}; }}
        .file {{ fill: {text_file_color}; }}
    """))
    
    y = padding + row_height / 2
    x_start = padding
    
    # Draw Root Node
    root_icon_char, root_color = get_icon_and_color(root_name, True, theme)
    root_icon_path = get_glyph_path(font, root_icon_char)
    
    scale = 16 / 2048 
    
    icon_group = dwg.g(transform=f"translate({x_start}, {y + 6}) scale({scale}, -{scale})")
    icon_group.add(dwg.path(d=root_icon_path, fill=root_color))
    dwg.add(icon_group)
    
    dwg.add(dwg.text(f"{root_name}", insert=(x_start + 24, y), class_="folder"))
    
    y += row_height

    for node in visual_rows:
        x_base = x_start
        for d, was_last in enumerate(node.parent_is_last):
            if not was_last:
                line_x = x_base + (d * indent_unit) + (indent_unit / 2) - 4
                dwg.add(dwg.line(
                    start=(line_x, y - row_height/2), 
                    end=(line_x, y + row_height/2), 
                    stroke=line_color, stroke_width=1
                ))
        
        current_indent_x = x_base + (node.depth * indent_unit) + (indent_unit / 2) - 4
        dwg.add(dwg.line(
            start=(current_indent_x, y),
            end=(current_indent_x + 12, y),
            stroke=line_color, stroke_width=1
        ))
        dwg.add(dwg.line(
            start=(current_indent_x, y - row_height/2),
            end=(current_indent_x, y),
            stroke=line_color, stroke_width=1
        ))

        icon_x = current_indent_x + 18
        icon_char, color = get_icon_and_color(node.name, node.is_dir, theme)
        icon_path = get_glyph_path(font, icon_char)
        icon_group = dwg.g(transform=f"translate({icon_x}, {y + 6}) scale({scale}, -{scale})")
        icon_group.add(dwg.path(d=icon_path, fill=color))
        dwg.add(icon_group)
        
        text_x = icon_x + 24
        text_cls = "folder" if node.is_dir else "file"
        dwg.add(dwg.text(node.name, insert=(text_x, y), class_=text_cls))
        
        y += row_height
        
    dwg.save()
    print(f"SVG tree generated at: {output_path}")

    if save_png:
        png_path = os.path.splitext(output_path)[0] + ".png"
        export_png(output_path, png_path, png_scale)
