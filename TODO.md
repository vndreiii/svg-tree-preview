# SVGTree Todo List

## Planned Features

- [x] **File Preview (`--file-preview <file>`)**
    - Show the full directory tree as usual.
    - Embed a preview window for the specified file inside the SVG/PNG.
    - Support syntax highlighting for code files (using `pygments`?).
    - Support image thumbnail previews for image files.
    - **Implementation Idea**: Add a new SVG group/panel that renders the file content, possibly connected by a line to the file node in the tree.

- [ ] **Git Status Integration**
    - Color-code files based on their git status (modified, added, untracked).
    - Add status icons next to files (e.g., `M`, `A`, `?`).

- [x] **HTML Output (`--html`)**
    - Generate a self-contained HTML file instead of (or in addition to) SVG.
    - **Benefits**:
        - CSS handles layout reflow automatically.
        - Richer file previews (modals, syntax highlighting libraries).
        - Search/Filter functionality.

- [x] **Exclusive PNG Output (`--png`)**
    - Now generates only the PNG file (cleaning up the temporary SVG) when the flag is used.

- [ ] **Multiple Output Formats**
    - Add JSON export (`--json`) for use in other tools.
    - Add ASCII/ANSI text output for terminal printing.

- [ ] **Configuration Enhancements**
    - Allow per-folder config overrides (e.g., `.svgtree.toml` inside subdirectories).
    - Add a `--dry-run` mode to preview what files would be scanned without generating images.

- [x] **Performance Optimization**
    - [ ] Implement parallel scanning for very large directories.
    - [x] Cache font glyph extraction to speed up repeated runs.
