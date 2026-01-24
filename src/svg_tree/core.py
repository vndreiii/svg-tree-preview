import os
import pathspec
from typing import List, Generator, Optional, Callable

class TreeEntry:
    def __init__(self, name: str, path: str, depth: int, is_dir: bool, is_last_child: bool = False, parent_is_last: List[bool] = None):
        self.name = name
        self.path = path
        self.depth = depth
        self.is_dir = is_dir
        self.is_last_child = is_last_child
        self.parent_is_last = parent_is_last or []
        self.children: List['TreeEntry'] = []

def build_tree(
    root_path: str, 
    max_depth: int, 
    spec: Optional[pathspec.PathSpec],
    current_depth: int = 0,
    parent_is_last: List[bool] = None,
    on_progress: Optional[Callable[[], None]] = None
) -> List[TreeEntry]:
    
    if current_depth > max_depth:
        return []
    
    if parent_is_last is None:
        parent_is_last = []

    entries = []
    try:
        with os.scandir(root_path) as it:
            raw_entries = sorted(list(it), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []

    filtered_entries = []
    
    for entry in raw_entries:
        if spec:
             if spec.match_file(entry.path):
                 continue
             if spec.match_file(entry.name):
                 continue

        filtered_entries.append(entry)

    for i, entry in enumerate(filtered_entries):
        if on_progress:
            on_progress()

        is_last = (i == len(filtered_entries) - 1)
        is_dir = entry.is_dir()
        child_parent_is_last = parent_is_last + [is_last]
        
        node = TreeEntry(
            name=entry.name,
            path=entry.path,
            depth=current_depth,
            is_dir=is_dir,
            is_last_child=is_last,
            parent_is_last=parent_is_last
        )
        
        if is_dir:
            node.children = build_tree(entry.path, max_depth, spec, current_depth + 1, child_parent_is_last, on_progress=on_progress)
            
        entries.append(node)
        
    return entries

def flatten_tree(nodes: List[TreeEntry]) -> Generator[TreeEntry, None, None]:
    for node in nodes:
        yield node
        if node.children:
            yield from flatten_tree(node.children)
