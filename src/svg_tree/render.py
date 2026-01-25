import os
import base64
import mimetypes
import svgwrite
import pathspec
from typing import List, Dict, Any, Optional, Tuple, Callable
from fontTools.ttLib import TTFont
from concurrent.futures import ProcessPoolExecutor

from .core import TreeEntry, flatten_tree
from .icons import get_font_path, ensure_font_exists, get_glyph_path, get_icon_and_color
from .export import export_png
from .preview import get_preview_data, build_svg_preview_from_data, sanitize_text

def parse_font_weight(thickness: str) -> str:
    thickness = str(thickness).lower()
    mapping = {
        "thin": "100", "extralight": "200", "light": "300", "regular": "400",
        "medium": "500", "semibold": "600", "bold": "700", "extrabold": "800",
        "black": "900", "normal": "400"
    }
    return mapping.get(thickness, thickness)

def generate_svg(root_path: str, output_path: str, tree_nodes: List[TreeEntry], theme: Dict[str, Any], save_png: bool = False, png_scale: int = 1, preview_patterns: Optional[str] = None, on_progress: Optional[Callable[[], None]] = None):
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
    
    preview_spec = None
    if preview_patterns:
        patterns = [p.strip() for p in preview_patterns.split(",")]
        preview_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    # --- Parallel Preview Pass ---
    visual_rows = list(flatten_tree(tree_nodes))
    preview_tasks = []
    for node in visual_rows:
        if not node.is_dir and preview_spec and (preview_spec.match_file(node.name) or preview_spec.match_file(node.path)):
            preview_tasks.append((node.path, 'svg'))
        else:
            preview_tasks.append(None)

    preview_results = [None] * len(visual_rows)
    to_process = [(i, task[0], task[1]) for i, task in enumerate(preview_tasks) if task]
    
    if to_process:
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(get_preview_data, path, mode) for _, path, mode in to_process]
            for (idx, _, _), future in zip(to_process, futures):
                if on_progress: on_progress()
                preview_results[idx] = future.result()

    # --- Pre-calculation Pass ---
    render_plan: List[Tuple[TreeEntry, Any, float, float]] = [] 
    max_len = 0
    root_name = os.path.basename(os.path.abspath(root_path)) or root_path
    max_len = max(max_len, len(root_name) * 10 + 30)
    
    for i, node in enumerate(visual_rows):
        data = preview_results[i]
        preview_group, extra_h, extra_w = None, 0, 0
        if data:
            try:
                preview_group = build_svg_preview_from_data(data)
                extra_h = float(data['height']) + 10
                extra_w = float(data['width']) + 40
            except Exception as e:
                print(f"Preview fail for {node.name}: {e}")
        
        render_plan.append((node, preview_group, extra_h, extra_w))
        row_content_width = (node.depth + 1) * indent_unit + 30 + (len(node.name) * 11) + extra_w
        max_len = max(max_len, row_content_width)
            
    total_height = sum(row_height + p[2] for p in render_plan) + row_height + (padding * 2)
    total_width = max_len + (padding * 2) + 60
    dwg = svgwrite.Drawing(output_path, size=(total_width, total_height), profile='full')
    
    # Background and Styles
    bg_color = colors_cfg.get('background', '#282c34')
    dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill=bg_color))
    
    family, f_type, thickness = font_cfg.get('family', 'monospace'), font_cfg.get('type', ''), font_cfg.get('thickness', 'Regular')
    custom_font_path, css_weight = font_cfg.get('path'), parse_font_weight(thickness)
    font_stack = f'"{family} {f_type}", "{family}", monospace' if f_type else f'"{family}", monospace'
    css_family_name = f"{family} {f_type}" if f_type else family

    font_face_rule = ""
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            mime_type, _ = mimetypes.guess_type(custom_font_path)
            if not mime_type: mime_type = "font/ttf"
            with open(custom_font_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
            font_face_rule = f"@font-face {{ font-family: \"{css_family_name}\"; src: url(\"data:{mime_type};base64,{b64_data}\") format(\"truetype\"); font-weight: {css_weight}; font-style: normal; }}" 
        except: pass

    line_color = colors_cfg.get('lines', '#5c6370')
    text_file_color, text_folder_color = colors_cfg.get('text_file', '#abb2bf'), colors_cfg.get('text_folder', '#61afef')
    dwg.defs.add(dwg.style(f"{font_face_rule}\ntext {{ font-family: {font_stack}; font-size: {font_size}px; font-weight: {css_weight}; dominant-baseline: middle; }}\n.folder {{ font-weight: bold; fill: {text_folder_color}; }}\n.file {{ fill: {text_file_color}; }}"))
    
    # Pre-define all needed icons in <defs>
    all_icons_needed = {get_icon_and_color(root_name, True, theme)[0]}
    for node, _, _, _ in render_plan: all_icons_needed.add(get_icon_and_color(node.name, node.is_dir, theme)[0])
    
    def get_icon_id(char): return f"icon-{ord(char)}"
    for icon_char in all_icons_needed:
        symbol = dwg.symbol(id=get_icon_id(icon_char), viewBox="0 0 2048 2048")
        symbol.add(dwg.path(d=get_glyph_path(font, icon_char), transform="scale(1, -1) translate(0, -1700)"))
        dwg.defs.add(symbol)

    # --- Drawing ---
    x_start, current_y_top = padding, padding
    root_icon_char, root_color = get_icon_and_color(root_name, True, theme)
    root_grp, rel_y = dwg.g(transform=f"translate(0, {current_y_top})"), row_height / 2
    root_grp.add(dwg.use(href=f"#{get_icon_id(root_icon_char)}", insert=(x_start, rel_y - 8), size=(16, 16), fill=root_color))
    root_grp.add(dwg.text(sanitize_text(root_name), insert=(x_start + 24, rel_y), class_="folder"))
    dwg.add(root_grp)
    current_y_top += row_height

    for node, preview_group, extra_h, _ in render_plan:
        if on_progress: on_progress()
        row_h = row_height + extra_h
        row_grp, rel_y = dwg.g(transform=f"translate(0, {current_y_top})"), row_height / 2
        for d, was_last in enumerate(node.parent_is_last):
            if not was_last:
                line_x = x_start + (d * indent_unit) + (indent_unit / 2) - 4
                row_grp.add(dwg.line(start=(line_x, 0), end=(line_x, row_h), stroke=line_color, stroke_width=1))
        
        cur_x = x_start + (node.depth * indent_unit) + (indent_unit / 2) - 4
        row_grp.add(dwg.line(start=(cur_x, rel_y), end=(cur_x + 12, rel_y), stroke=line_color, stroke_width=1))
        row_grp.add(dwg.line(start=(cur_x, 0), end=(cur_x, rel_y), stroke=line_color, stroke_width=1))
        if not node.is_last_child: row_grp.add(dwg.line(start=(cur_x, rel_y), end=(cur_x, row_h), stroke=line_color, stroke_width=1))

        icon_x = cur_x + 18
        icon_char, color = get_icon_and_color(node.name, node.is_dir, theme)
        row_grp.add(dwg.use(href=f"#{get_icon_id(icon_char)}", insert=(icon_x, rel_y - 8), size=(16, 16), fill=color))
        row_grp.add(dwg.text(sanitize_text(node.name), insert=(icon_x + 24, rel_y), class_="folder" if node.is_dir else "file"))
        
        if preview_group:
            preview_x, preview_y = icon_x + 48, row_height
            container = dwg.g(transform=f"translate({preview_x}, {preview_y})")
            container.add(preview_group)
            row_grp.add(dwg.path(d=f"M {icon_x + 34} {rel_y + 10} L {icon_x + 34} {preview_y + 10} L {preview_x} {preview_y + 10}", stroke=line_color, fill="none", stroke_width=1, stroke_dasharray="2,2"))
            row_grp.add(container)
        
        dwg.add(row_grp)
        current_y_top += row_h
        
    dwg.save()
    if save_png:
        export_png(output_path, os.path.splitext(output_path)[0] + ".png", png_scale)
