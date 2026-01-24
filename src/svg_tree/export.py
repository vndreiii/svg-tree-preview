import shutil
import subprocess
import cairosvg

def convert_with_inkscape(svg_path: str, png_path: str, scale: int):
    try:
        # Inkscape CLI: inkscape input.svg -o output.png --export-dpi=...
        # Standard SVG DPI is usually 96.
        dpi = 96 * scale
        subprocess.run(["inkscape", svg_path, "-o", png_path, "--export-dpi", str(dpi)], check=True)
        print(f"PNG tree generated at: {png_path} (via Inkscape @ {scale}x)")
    except subprocess.CalledProcessError as e:
        print(f"Inkscape failed: {e}")
        print("Falling back to internal renderer...")
        raise e
    except FileNotFoundError:
        print("Inkscape not found.")
        raise

def export_png(svg_path: str, png_path: str, scale: int):
    # Priority: Inkscape -> CairoSVG
    used_inkscape = False
    if shutil.which("inkscape"):
        try:
            convert_with_inkscape(svg_path, png_path, scale)
            used_inkscape = True
        except Exception:
            pass
    
    if not used_inkscape:
        try:
            with open(svg_path, 'rb') as svg_file:
                cairosvg.svg2png(file_obj=svg_file, write_to=png_path, scale=scale)
            print(f"PNG tree generated at: {png_path} (via CairoSVG @ {scale}x)")
        except Exception as e:
            print(f"Error generating PNG: {e}")
