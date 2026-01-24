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
    render_plan: List[Tuple[TreeEntry, Any, float]] = [] # node, preview_group, height_consumed
    
    content_height = row_height # Root node
    max_len = 0
    root_name = os.path.basename(os.path.abspath(root_path)) or root_path
    max_len = max(max_len, len(root_name) * 10 + 30)
    
    for node in visual_rows:
        preview_group = None
        extra_height = 0
        
        # Check for preview match
        is_match = False
        if not node.is_dir and preview_spec:
            # Check both name and relative path? 
            # pathspec normally checks paths.
            # But users might want "*.py". pathspec handles wildcards well.
            # Let's check name for convenience + path
            if preview_spec.match_file(node.name) or preview_spec.match_file(node.path):
                is_match = True
        
        if is_match:
            try:
                preview_group = get_file_content_preview(node.path)
                # Hacky: access the 'height' of the background rect (element 0)
                # We assume preview.py structure: Group -> [Rect, ...]
                bg_rect = preview_group.elements[0]
                extra_height = float(bg_rect['height']) + 10 # + Margin
            except Exception as e:
                print(f"Preview generation failed for {node.name}: {e}")
                extra_height = 0
        
        render_plan.append((node, preview_group, extra_height))
        content_height += row_height + extra_height
        
        # Width calc
        w = (node.depth + 1) * indent_unit + (len(node.name) * 10) + 30
        if w > max_len:
            max_len = w
            
    # Allow extra width for previews (approx 450px) if any exist
    if any(p[1] for p in render_plan):
        max_len = max(max_len + 450, max_len)

    total_height = content_height + (padding * 2)
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

    for node, preview_group, extra_h in render_plan:
        x_base = x_start
        
        # --- DRAW LINES ---
        for d, was_last in enumerate(node.parent_is_last):
            if not was_last:
                line_x = x_base + (d * indent_unit) + (indent_unit / 2) - 4
                # Line height needs to cover the row + any extra preview height for THIS row
                # Wait, vertical lines for PARENTS should extend through this node's preview space too?
                # Yes. If a parent is open, its line goes down past my children.
                # Here, we are drawing the line segment for THIS row.
                # It should extend `row_height + extra_h`.
                
                segment_h = row_height + extra_h
                dwg.add(dwg.line(
                    start=(line_x, y - row_height/2), 
                    end=(line_x, y - row_height/2 + segment_h), 
                    stroke=line_color, stroke_width=1
                ))
        
        current_indent_x = x_base + (node.depth * indent_unit) + (indent_unit / 2) - 4
        dwg.add(dwg.line(
            start=(current_indent_x, y),
            end=(current_indent_x + 12, y),
            stroke=line_color, stroke_width=1
        ))
        
        # Vertical connector for THIS node (up to parent)
        dwg.add(dwg.line(
            start=(current_indent_x, y - row_height/2),
            end=(current_indent_x, y),
            stroke=line_color, stroke_width=1
        ))
        
        # If this node has children (it's a folder and not last), it might need a line going down?
        # But `flatten_tree` order handles that by the next node drawing the "parent" line.
        # However, if *I* have a preview (files only, usually), I don't have children.
        # But if I am not the last child, I need to draw the vertical line for MYSELF extending down past my preview?
        # No, that's handled by the `parent_is_last` logic of the *next* sibling?
        # Actually, the logic above: `if not was_last` draws the parent lines.
        # Does the current node need a line extending through its own preview?
        # Only if it's not the last child.
        # But `node.parent_is_last` lists *parents*. It doesn't include "am I last?".
        # `node.is_last_child` tells us.
        
        if not node.is_last_child:
             # Draw line extending down through my preview
             segment_h = extra_h + (row_height / 2) # extend to bottom of row + preview?
             # actually we need to reach the next row's top.
             dwg.add(dwg.line(
                start=(current_indent_x, y),
                end=(current_indent_x, y + (row_height/2) + extra_h),
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
        
        # --- DRAW PREVIEW ---
        if preview_group:
            # Position preview below file, indented
            preview_x = text_x + 20
            preview_y = y + (row_height / 2) + 5
            
            # Create a transform group for positioning
            container = dwg.g(transform=f"translate({preview_x}, {preview_y})")
            container.add(preview_group)
            
            # Optional: Connector line from file to preview
            dwg.add(dwg.path(d=f"M {text_x + 10} {y + 10} L {text_x + 10} {preview_y + 10} L {preview_x} {preview_y + 10}",
                             stroke=line_color, fill="none", stroke_width=1, stroke_dasharray="2,2"))
            
            dwg.add(container)
        
        y += row_height + extra_h
        
    dwg.save()
    print(f"SVG tree generated at: {output_path}")

    if save_png:
        png_path = os.path.splitext(output_path)[0] + ".png"
        export_png(output_path, png_path, png_scale)