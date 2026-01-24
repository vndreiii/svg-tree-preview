import os
import html
import pathspec
from typing import List, Dict, Any, Optional
from fontTools.ttLib import TTFont

from .core import TreeEntry
from .icons import get_font_path, ensure_font_exists, get_glyph_path, get_icon_and_color
from .preview import get_html_preview

CSS_TEMPLATE = """
<style>
    body {{
        background-color: {bg_color};
        color: {text_file};
        font-family: {font_family}, monospace;
        padding: 20px;
    }}
    ul {{ 
        list-style-type: none;
        padding-left: 20px;
        margin: 0;
        border-left: 1px solid {line_color};
    }}
    ul.root {{ border-left: none; padding-left: 0; }}
    li {{ margin: 4px 0; }}
    
    .row {{
        display: flex;
        align-items: center;
        padding: 2px 5px;
        border-radius: 4px;
        cursor: pointer;
    }}
    .row:hover {{ background-color: rgba(255, 255, 255, 0.1); }}
    
    .icon {{
        width: 16px;
        height: 16px;
        margin-right: 8px;
        display: inline-block;
    }}
    
    .folder-name {{ color: {text_folder}; font-weight: bold; }}
    .file-name {{ color: {text_file}; }}
    
    .children {{ display: none; }}
    .children.open {{ display: block; }}
    
    /* Preview Styles */
    .preview-container {{
        margin-left: 24px;
        margin-top: 5px;
        margin-bottom: 10px;
        padding: 10px;
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid {line_color};
        border-radius: 5px;
    }}
    .preview-code pre {{ margin: 0; font-size: 12px; overflow-x: auto; }}
</style>
"""

JS = """
<script>
    function toggle(id) {
        var el = document.getElementById(id);
        if (el) {
            el.classList.toggle('open');
        }
    }
</script>
"""

def _render_icon(font, char, color):
    # Convert font glyph path to SVG string
    path_data = get_glyph_path(font, char)
    # Nerd fonts are usually 2048 units. We transform it to fit in 16x16 viewbox?
    # Or just use viewBox="0 0 2048 2048" and flip it (scale 1, -1)
    # SVG is Y-down. Font is Y-up.
    # We need a transform.
    return f'''
    <svg class="icon" viewBox="0 0 2048 2048" style="fill: {color}">
        <g transform="scale(1, -1) translate(0, -1700)"> 
            <path d="{path_data}" />
        </g>
    </svg>
    '''
    # Note: Translate Y -1700 is an approximation to align baseline. 
    # Proper way is reading font metrics (ascent/descent). 
    # For Nerd Fonts, 2048 em, typical baseline shift is needed.

def _node_to_html(node: TreeEntry, font, theme, preview_spec, id_counter):
    node_id = f"node-{id_counter[0]}"
    id_counter[0] += 1
    
    icon_char, color = get_icon_and_color(node.name, node.is_dir, theme)
    icon_html = _render_icon(font, icon_char, color)
    
    text_class = "folder-name" if node.is_dir else "file-name"
    
    # Check preview
    preview_html = ""
    if not node.is_dir and preview_spec:
        if preview_spec.match_file(node.name) or preview_spec.match_file(node.path):
            content = get_html_preview(node.path)
            if content:
                preview_html = f'<div class="preview-container">{content}</div>'

    html_out = "<li>"
    
    # Row click
    click_attr = f'onclick="toggle(\'{node_id}\')"' if node.is_dir else ""
    
    html_out += f'<div class="row" {click_attr}>'
    html_out += icon_html
    html_out += f'<span class="{text_class}">{html.escape(node.name)}</span>'
    html_out += "</div>"
    
    if node.is_dir and node.children:
        html_out += f'<ul id="{node_id}" class="children">'
        for child in node.children:
            html_out += _node_to_html(child, font, theme, preview_spec, id_counter)
        html_out += "</ul>"
    elif preview_html:
        html_out += preview_html
        
    html_out += "</li>"
    return html_out

def generate_html(root_path: str, output_path: str, tree_nodes: List[TreeEntry], theme: Dict[str, Any], preview_patterns: Optional[str] = None):
    ensure_font_exists()
    font_path = get_font_path()
    try:
        font = TTFont(font_path)
    except Exception as e:
        print(f"Could not load font: {e}")
        return

    # Theme vars
    colors = theme.get('colors', {})
    font_cfg = theme.get('font', {})
    
    css = CSS_TEMPLATE.format(
        bg_color=colors.get('background', '#282c34'),
        text_file=colors.get('text_file', '#abb2bf'),
        text_folder=colors.get('text_folder', '#61afef'),
        line_color=colors.get('lines', '#5c6370'),
        font_family=font_cfg.get('family', 'monospace')
    )
    
    # Parse patterns
    preview_spec = None
    if preview_patterns:
        patterns = [p.strip() for p in preview_patterns.split(",")]
        preview_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tree: {html.escape(os.path.basename(root_path))}</title>
    {css}
    {JS}
</head>
<body>
    <h3>{html.escape(os.path.basename(root_path))}</h3>
    <ul class="root">
"""
    
    id_counter = [0]
    for node in tree_nodes:
        content += _node_to_html(node, font, theme, preview_spec, id_counter)
        
    content += """
    </ul>
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print(f"HTML tree generated at: {output_path}")
