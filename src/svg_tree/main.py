import os
import argparse
import sys
import pathspec

from .config import load_theme
from .core import build_tree
from .render import generate_svg
from .html import generate_html
from .export import export_png

def main():
    parser = argparse.ArgumentParser(description="Generate a pretty SVG tree of a directory.")
    parser.add_argument("root", nargs="?", default=".", help="Root directory to scan")
    parser.add_argument("-o", "--output", default="tree.svg", help="Output file path")
    parser.add_argument("-d", "--depth", type=int, default=2, help="Max recursion depth (default: 2)")
    parser.add_argument("-e", "--exclude", help="Comma-separated exclude patterns (e.g. '*.jpg, .git')")
    parser.add_argument("-s", "--size", type=int, default=1, choices=range(1, 9), help="PNG Scale factor (1-8x)")
    parser.add_argument("-p", "--file-preview", help="Preview content of files matching patterns (e.g. '*.py, README.md')")
    parser.add_argument("--png", action="store_true", help="Generate PNG output instead of SVG")
    parser.add_argument("--html", action="store_true", help="Generate HTML output instead of SVG")
    parser.add_argument("--theme", help="Path to a custom TOML theme file")
    
    args = parser.parse_args()
    
    root = os.path.abspath(args.root)
    theme = load_theme(args.theme)
    
    spec = None
    if args.exclude:
        patterns = [p.strip() for p in args.exclude.split(",")]
        spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
        
    print(f"Scanning {root} (depth={args.depth})...")
    nodes = build_tree(root, args.depth, spec)
    
    if args.html:
        out = args.output
        if out.endswith('.svg') or out.endswith('.png'):
            out = os.path.splitext(out)[0] + ".html"
        generate_html(root, out, nodes, theme, preview_patterns=args.file_preview)
        
    elif args.png:
        # Handle PNG output exclusively
        final_out = args.output
        if final_out.endswith('.svg'):
            final_out = os.path.splitext(final_out)[0] + ".png"
            
        # Create temp SVG path
        svg_tmp = final_out + ".tmp.svg"
        
        # Generate SVG (silently if possible, but generate_svg prints)
        generate_svg(root, svg_tmp, nodes, theme, save_png=False, preview_patterns=args.file_preview)
        
        # Convert
        export_png(svg_tmp, final_out, args.size)
        
        # Cleanup
        if os.path.exists(svg_tmp):
            os.remove(svg_tmp)
            
    else:
        # Standard SVG output
        generate_svg(root, args.output, nodes, theme, save_png=False, preview_patterns=args.file_preview)

if __name__ == "__main__":
    main()