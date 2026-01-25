import os
import html
import pathspec
from typing import List, Dict, Any, Optional, Callable
from fontTools.ttLib import TTFont
from concurrent.futures import ProcessPoolExecutor

from .core import TreeEntry, flatten_tree
from .icons import get_font_path, ensure_font_exists, get_glyph_path, get_icon_and_color
from .preview import get_preview_data

CSS_TEMPLATE = """
<style>
    body {{ background-color: {bg_color}; color: {text_file}; font-family: {font_family}, monospace; padding: 20px; }}
    ul {{ list-style-type: none; padding-left: 20px; margin: 0; border-left: 1px solid {line_color}; }}
    ul.root {{ border-left: none; padding-left: 0; }}
    li {{ margin: 4px 0; }}
    .row {{ display: flex; align-items: center; padding: 2px 5px; border-radius: 4px; cursor: pointer; }}
    .row:hover {{ background-color: rgba(255, 255, 255, 0.1); }}
    .icon {{ width: 16px; height: 16px; margin-right: 8px; display: inline-block; }}
    .folder-name {{ color: {text_folder}; font-weight: bold; }}
    .file-name {{ color: {text_file}; }}
    .children {{ display: none; }}
    .children.open {{ display: block; }}
    .preview-container {{ margin-left: 24px; margin-top: 5px; margin-bottom: 10px; padding: 10px; background: rgba(0, 0, 0, 0.2); border: 1px solid {line_color}; border-radius: 5px; }}
    .preview-code pre {{ margin: 0; font-size: 12px; overflow-x: auto; }}
</style>
"""

JS = "<script>function toggle(id) { var el = document.getElementById(id); if (el) el.classList.toggle('open'); }</script>"

def _node_to_html(node: TreeEntry, theme, id_counter, preview_data, on_progress):
    if on_progress: on_progress()
    node_id = f"node-{id_counter[0]}"
    id_counter[0] += 1
    icon_char, color = get_icon_and_color(node.name, node.is_dir, theme)
    icon_id = f"icon-{ord(icon_char)}"
    
    icon_html = f'<svg class="icon" style="fill: {color}"><use href="#{icon_id}" /></svg>'
    text_class = "folder-name" if node.is_dir else "file-name"
    
    preview_html = ""
    content = preview_data.get(node.path)
    if content:
        preview_html = f'<div class="preview-container">{content}</div>'

    html_out = f'<li><div class="row" {"onclick=\"toggle(\\'" + node_id + "\\')\"" if node.is_dir else ""}>{icon_html}<span class="{text_class}">{html.escape(node.name)}</span></div>'
    if node.is_dir and node.children:
        html_out += f'<ul id="{node_id}" class="children">'
        for child in node.children:
            html_out += _node_to_html(child, theme, id_counter, preview_data, on_progress)
        html_out += "</ul>"
    elif preview_html:
        html_out += preview_html
    html_out += "</li>"
    return html_out

def generate_html(root_path: str, output_path: str, tree_nodes: List[TreeEntry], theme: Dict[str, Any], preview_patterns: Optional[str] = None, on_progress: Optional[Callable[[], None]] = None):
    ensure_font_exists()
    font_path = get_font_path()
    try: font = TTFont(font_path)
    except Exception as e:
        print(f"Font error: {e}")
        return

    # Parallel Preview Pass
    preview_spec = None
    if preview_patterns:
        patterns = [p.strip() for p in preview_patterns.split(",")]
        preview_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    all_nodes = list(flatten_tree(tree_nodes))
    to_process = [n.path for n in all_nodes if not n.is_dir and preview_spec and (preview_spec.match_file(n.name) or preview_spec.match_file(n.path))]
    
    preview_map = {}
    if to_process:
        with ProcessPoolExecutor() as executor:
            futures = [executor.submit(get_preview_data, path, 'html') for path in to_process]
            for path, future in zip(to_process, futures):
                if on_progress: on_progress()
                res = future.result()
                if res: preview_map[path] = res

    colors, font_cfg = theme.get('colors', {}), theme.get('font', {})
    css = CSS_TEMPLATE.format(bg_color=colors.get('background', '#282c34'), text_file=colors.get('text_file', '#abb2bf'), text_folder=colors.get('text_folder', '#61afef'), line_color=colors.get('lines', '#5c6370'), font_family=font_cfg.get('family', 'monospace'))

    icon_defs = '<svg style="display: none;"><defs>'
    used_icons = set()
    def collect_icons(nodes):
        for node in nodes:
            char, _ = get_icon_and_color(node.name, node.is_dir, theme)
            if char not in used_icons:
                icon_defs_local = f'<symbol id="icon-{ord(char)}" viewBox="0 0 2048 2048"><g transform="scale(1, -1) translate(0, -1700)"><path d="{get_glyph_path(font, char)}" /></g></symbol>'
                nonlocal icon_defs
                icon_defs += icon_defs_local
                used_icons.add(char)
            if node.children: collect_icons(node.children)
    collect_icons(tree_nodes)
    icon_defs += '</defs></svg>'

    content = f"<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>Tree: {html.escape(os.path.basename(root_path))}</title>{css}{JS}</head><body>{icon_defs}<h3>{html.escape(os.path.basename(root_path))}</h3><ul class=\"root\">"
    id_counter = [0]
    for node in tree_nodes: content += _node_to_html(node, theme, id_counter, preview_map, on_progress)
    content += "</ul></body></html>"
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(content)
