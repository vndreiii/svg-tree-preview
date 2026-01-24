# SVGTreePreview

A beautiful, high-performance CLI tool to generate **SVG** and **PNG** directory trees with Nerd Font icons and comprehensive theming support.

<!--
Source - https://stackoverflow.com/q
Posted by zjffdu, modified by community. See post 'Timeline' for change history
Retrieved 2026-01-24, License - CC BY-SA 4.0
-->

<img src="https://git.killuaa.dev/vndreiii/svg-tree-preview/raw/branch/main/SVGTreePreview.png" title="" alt="what the project looks like, it shows a file structure" width="642">

## Features

* **Beautiful Visuals**: Generates clean, scalable SVGs with precise, connected tree lines.
* **Zero-Config Icons**: Automatically downloads and vectorizes Nerd Font icons (cached in `~/.config/svgtree/assets`)—no font installation required for the final viewer.
* **Custom Theming**: Fully customizable colors, layout, and font properties via TOML.
* **Font Embedding**: Embed any TTF/OTF font directly into the SVG for pixel-perfect portability.
* **Smart PNG Export**: High-quality rasterization using **Inkscape** (preferred) or **CairoSVG** with adjustable scaling (up to 8x).
* **Modern CLI**: Supports `.gitignore` style patterns for exclusions and respects XDG specifications for config.

## Installation

### Prerequisites

- Python 3.8+
- (Optional) Inkscape for superior PNG quality.

### From Source

1. Clone the repository.
2. Run the self-contained installation script:

```bash
chmod +x install.sh
./install.sh
```

**The script will:**

1. Create a temporary virtual environment.
2. Install all necessary build dependencies.
3. Bundle `svgtree` into a standalone binary using PyInstaller.
4. Install the binary to `~/.local/bin/`.
5. Deploy the default theme to `~/.config/svgtree/default-theme.toml`.

## Usage

```bash
svgtree [ROOT_DIR] [OPTIONS]
```

### Options

| Short | Long        | Description                                                  |
|:----- |:----------- |:------------------------------------------------------------ |
| `-o`  | `--output`  | Output SVG path (default: `tree.svg`)                        |
| `-d`  | `--depth`   | Max recursion depth (default: 2)                             |
| `-e`  | `--exclude` | Comma-separated exclude patterns (e.g. `.git, node_modules`) |
| `-s`  | `--size`    | PNG scale factor from 1 to 8 (default: 1)                    |
|       | `--png`     | Additionally export to PNG                                   |
|       | `--theme`   | Path to a custom TOML theme file                             |
| `-h`  | `--help`    | Show all available commands                                  |

### Examples

**Basic scan of the current directory:**

```bash
svgtree .
```

**High-resolution 4x PNG with exclusions:**

```bash
svgtree ~ -o home.svg -d 3 -e ".git, .cache, node_modules" --png -s 4
```

**Using a custom theme:**

```bash
svgtree . --theme ~/.config/svgtree/light-theme.toml
```

## Theming

Themes are managed via TOML files. The tool follows the XDG specification and looks for its default theme at `~/.config/svgtree/default-theme.toml`.

### Here's an example of a custom theme for light mode.

```toml
# SVG Tree Theme Configuration

[colors]
# The main background color of the image
background = "#ffffff"
# Color of the tree structure lines
lines = "#9ca3af"
# Default text color for files
text_file = "#1f2937"
# Text color for folders
text_folder = "#2563eb"
# Default color for icons if not specified in [file_colors]
icon_default = "#1f2937"

[layout]
# Height of each row in pixels
row_height = 30
# Font size in pixels
font_size = 14
# Padding around the entire tree in pixels
padding = 40
# Indentation per depth level in pixels
indent_pixels = 24

[font]
# Font family string
family = "VT323"

[file_colors]
# Specific colors for file types (keys match internal type names or extensions)
folder = "#2563eb"        # Blue for folders
image = "#7c3aed"         # Purple for images
code = "#059669"          # Green for code
python = "#d97706"        # Amber for Python
js = "#d97706"            # Amber for JavaScript
html = "#dc2626"          # Red for HTML
git = "#dc2626"           # Red for Git
hidden = "#6b7280"        # Gray for hidden files
pdf = "#ea580c"           # Orange for PDFs
archive = "#0891b2"       # Cyan for archives (zip, tar, etc)
audio = "#7c3aed"         # Purple for audio
video = "#7c3aed"         # Purple for video
font = "#ea580c"          # Orange for fonts
db = "#dc2626"            # Red for databases
exec = "#dc2626"          # Red for executables (exe, bin)
text = "#1f2937"          # Dark gray for text files
```

The `[font]` section allows for advanced typography:

```toml
[font]
family = "Adwaita"
type = "Mono"
thickness = "Bold"
path = "/path/to/font.ttf"  # This will embed the font into the SVG/PNG
```

## License

GNU General Public License v3 (GPLv3)