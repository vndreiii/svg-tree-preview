import os
import base64
import mimetypes
import svgwrite
import pathspec
from typing import List, Dict, Any, Optional, Tuple
from fontTools.ttLib import TTFont

from .core import TreeEntry, flatten_tree
from .icons import get_font_path, ensure_font_exists, get_glyph_path, get_icon_and_color
from .export import export_png
from .preview import get_file_content_preview

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

def generate_svg(root_path: str, output_path: str, tree_nodes: List[TreeEntry], theme: Dict[str, Any], save_png: bool = False, png_scale: int = 1, preview_patterns: Optional[str] = None):
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
    
    # Parse Preview Patterns
    preview_spec = None
    if preview_patterns:
        patterns = [p.strip() for p in preview_patterns.split(",")]
        preview_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    # --- Pre-calculation Pass ---
    visual_rows = list(flatten_tree(tree_nodes))
    render_plan: List[Tuple[TreeEntry, Any, float]] = [] 
    
    max_len = 0
    root_name = os.path.basename(os.path.abspath(root_path)) or root_path
    max_len = max(max_len, len(root_name) * 10 + 30)
    
    for node in visual_rows:
        preview_group = None
        extra_height = 0
        
        is_match = False
        if not node.is_dir and preview_spec:
            if preview_spec.match_file(node.name) or preview_spec.match_file(node.path):
                is_match = True
        
        if is_match:
            try:
                preview_group = get_file_content_preview(node.path)
                bg_rect = preview_group.elements[0]
                extra_height = float(bg_rect['height']) + 10 
            except Exception as e:
                print(f"Preview generation failed for {node.name}: {e}")
                extra_height = 0
        
        render_plan.append((node, preview_group, extra_height))
        
        w = (node.depth + 1) * indent_unit + (len(node.name) * 10) + 30
        if w > max_len:
            max_len = w
            
    if any(p[1] for p in render_plan):
        max_len = max(max_len + 450, max_len)

    total_content_height = sum(row_height + p[2] for p in render_plan) + row_height # + root
    total_height = total_content_height + (padding * 2)
    total_width = max_len + (padding * 2) + 100 
    
    dwg = svgwrite.Drawing(output_path, size=(total_width, total_height), profile='full')
    
    # Background
    bg_color = colors_cfg.get('background', '#282c34')
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill=bg_color))
    
    # Styles
    family = font_cfg.get('family', 'monospace')
    f_type = font_cfg.get('type', '')
    thickness = font_cfg.get('thickness', 'Regular')
    custom_font_path = font_cfg.get('path')
    css_weight = parse_font_weight(thickness)
    
    if f_type:
        font_stack = f'"{family} {f_type}", "{family}", monospace'
        css_family_name = f"{family} {f_type}"
    else:
        font_stack = f'"{family}", monospace'
        css_family_name = family

    font_face_rule = ""
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            mime_type, _ = mimetypes.guess_type(custom_font_path)
            if not mime_type: mime_type = "font/ttf"
            with open(custom_font_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
            font_face_rule = f"""@font-face {{ font-family: "{css_family_name}"; src: url("data:{mime_type};base64,{b64_data}") format("truetype"); font-weight: {css_weight}; font-style: normal; }}"""
        except Exception: pass

    line_color = colors_cfg.get('lines', '#5c6370')
    text_file_color = colors_cfg.get('text_file', '#abb2bf')
    text_folder_color = colors_cfg.get('text_folder', '#61afef')

    dwg.defs.add(dwg.style(f"""
        {font_face_rule}
        text {{ font-family: {font_stack}; font-size: {font_size}px; font-weight: {css_weight}; dominant-baseline: middle; }}
        .folder {{ font-weight: bold; fill: {text_folder_color}; }}
        .file {{ fill: {text_file_color}; }}
    """))
    
    # --- Drawing ---
    y = padding + row_height / 2
    x_start = padding
    
    # Root Node
    root_icon_char, root_color = get_icon_and_color(root_name, True, theme)
    root_icon_path = get_glyph_path(font, root_icon_char)
    scale = 16 / 2048 
    
    current_y_top = padding
    root_grp = dwg.g(transform=f"translate(0, {current_y_top})")
    
    # Fix: Center icon vertically in the row
    rel_y = row_height / 2
    icon_group = dwg.g(transform=f"translate({x_start}, {rel_y + 4}) scale({scale}, -{scale})")
    icon_group.add(dwg.path(d=root_icon_path, fill=root_color))
        
    root_grp.add(icon_group)
    root_grp.add(dwg.text(f"{root_name}", insert=(x_start + 24, rel_y), class_="folder"))
    
    dwg.add(root_grp)
    current_y_top += row_height

    for i, (node, preview_group, extra_h) in enumerate(render_plan):
        row_h = row_height + extra_h
        
        row_grp = dwg.g(transform=f"translate(0, {current_y_top})")
        
        rel_y = row_height / 2 
        x_base = x_start
        
        # Lines
        for d, was_last in enumerate(node.parent_is_last):
            if not was_last:
                line_x = x_base + (d * indent_unit) + (indent_unit / 2) - 4
                row_grp.add(dwg.line(
                    start=(line_x, 0), 
                    end=(line_x, row_h), 
                    stroke=line_color, stroke_width=1
                ))
        
        current_indent_x = x_base + (node.depth * indent_unit) + (indent_unit / 2) - 4
        
        row_grp.add(dwg.line(
            start=(current_indent_x, rel_y),
            end=(current_indent_x + 12, rel_y),
            stroke=line_color, stroke_width=1
        ))
        
        row_grp.add(dwg.line(
            start=(current_indent_x, 0),
            end=(current_indent_x, rel_y),
            stroke=line_color, stroke_width=1
        ))
        
        if not node.is_last_child:
             row_grp.add(dwg.line(
                start=(current_indent_x, rel_y),
                end=(current_indent_x, row_h),
                stroke=line_color, stroke_width=1
             ))

        # Icon
        icon_x = current_indent_x + 18
        icon_char, color = get_icon_and_color(node.name, node.is_dir, theme)
        icon_path = get_glyph_path(font, icon_char)
        
        icon_sub = dwg.g(transform=f"translate({icon_x}, {rel_y + 4}) scale({scale}, -{scale})")
        icon_sub.add(dwg.path(d=icon_path, fill=color))
            
        row_grp.add(icon_sub)
        
        # Text
        text_x = icon_x + 24
        text_cls = "folder" if node.is_dir else "file"
        row_grp.add(dwg.text(node.name, insert=(text_x, rel_y), class_=text_cls))
        
        # Preview
        if preview_group:
            preview_x = text_x + 20
            preview_y = row_height # Start below text row
            container = dwg.g(transform=f"translate({preview_x}, {preview_y})")
            container.add(preview_group)
            row_grp.add(dwg.path(d=f"M {text_x + 10} {rel_y + 10} L {text_x + 10} {preview_y + 10} L {preview_x} {preview_y + 10}",
                             stroke=line_color, fill="none", stroke_width=1, stroke_dasharray="2,2"))
            row_grp.add(container)
        
        dwg.add(row_grp)
        current_y_top += row_h
        
    dwg.save()
    print(f"SVG tree generated at: {output_path}")

    if save_png:
        png_path = os.path.splitext(output_path)[0] + ".png"
        export_png(output_path, png_path, png_scale)
