# SVGTree Todo List

## Planned Features

- [ ] **File Preview (`--file-preview <file>`)**
    - Show the full directory tree as usual.
    - Embed a preview window for the specified file inside the SVG/PNG.
    - Support syntax highlighting for code files (using `pygments`?).
    - Support image thumbnail previews for image files.
    - **Implementation Idea**: Add a new SVG group/panel that renders the file content, possibly connected by a line to the file node in the tree.

- [ ] **Git Status Integration**
    - Color-code files based on their git status (modified, added, untracked).
    - Add status icons next to files (e.g., `M`, `A`, `?`).

- [ ] **Interactive SVG**
    - Make folder nodes clickable (collapsible/expandable) using embedded JavaScript in the SVG.
    - Add hover effects for file details (size, permissions).

- [ ] **Multiple Output Formats**
    - Add JSON export (`--json`) for use in other tools.
    - Add ASCII/ANSI text output for terminal printing.

- [ ] **Configuration Enhancements**
    - Allow per-folder config overrides (e.g., `.svgtree.toml` inside subdirectories).
    - Add a `--dry-run` mode to preview what files would be scanned without generating images.

- [ ] **Performance Optimization**
    - Implement parallel scanning for very large directories.
    - Cache font glyph extraction to speed up repeated runs.
