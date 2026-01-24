import os
import base64
import mimetypes
import svgwrite
from PIL import Image
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.styles import get_style_by_name

# Register extra mime types
mimetypes.add_type("image/jxl", ".jxl")
mimetypes.add_type("image/webp", ".webp")

# Configuration for previews
PREVIEW_WIDTH = 400 # Max container width
CODE_FONT_SIZE = 12
LINE_HEIGHT = 16
MAX_LINES = 20

def get_file_content_preview(file_path: str) -> svgwrite.container.Group:
    """
    Generates an SVG Group containing the preview of the file.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    
    # 1. Image Preview
    # Check common image types
    if mime_type and (mime_type.startswith('image/') or file_path.lower().endswith(('.jxl', '.webp'))):
        return _generate_image_preview(file_path)
    
    # 2. Code/Text Preview (Fallback)
    return _generate_code_preview(file_path)

def _generate_image_preview(file_path: str) -> svgwrite.container.Group:
    group = svgwrite.container.Group()
    try:
        # Get actual dimensions using Pillow
        # For SVGs, Pillow might fail or requires librsvg/cairo linkage. 
        # We try/except this specifically.
        try:
            with Image.open(file_path) as img:
                orig_w, orig_h = img.size
        except Exception:
            # Fallback for SVGs or weird formats
            orig_w, orig_h = 100, 100
            
        # Calculate scale to fit in box
        max_w, max_h = 350, 250
        ratio = min(1.0, min(max_w / orig_w, max_h / orig_h)) # Scale down only
        
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        
        # Read data for embedding
        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type: 
            mime_type = "image/png" # Fallback
            
        uri = f"data:{mime_type};base64,{data}"
        
        # Container Box (slightly larger than image)
        padding = 10
        box_w = new_w + (padding * 2)
        box_h = new_h + (padding * 2)
        
        # Draw background
        rect = svgwrite.shapes.Rect(size=(box_w, box_h), fill="#21252b", stroke="#3e4451", rx=4, ry=4)
        group.add(rect)
        
        # Draw image
        img_node = svgwrite.image.Image(href=uri, insert=(padding, padding), size=(new_w, new_h))
        group.add(img_node)
        
    except Exception as e:
        group.add(svgwrite.text.Text(f"Error previewing image: {e}", fill="red", font_size=10, insert=(0, 10)))
        # Add a dummy rect so render.py doesn't crash on height check
        # Fix: Access internal list to insert at 0
        rect = svgwrite.shapes.Rect(size=(200, 20), fill="none")
        rect['height'] = 20 # Explicitly set for reader
        group.elements.insert(0, rect)
        
    return group

def _generate_code_preview(file_path: str) -> svgwrite.container.Group:
    group = svgwrite.container.Group()
    
    # Background Box
    bg = svgwrite.shapes.Rect(fill="#282c34", stroke="#3e4451", rx=5, ry=5)
    group.add(bg)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = "".join(f.readlines()[:MAX_LINES]) # Limit lines
            
        try:
            lexer = get_lexer_for_filename(file_path)
        except:
            lexer = TextLexer()
            
        y = LINE_HEIGHT
        x = 10
        
        # Style (Monokai-ish)
        style = get_style_by_name('monokai')
        
        text_group = svgwrite.container.Group()
        
        lines = code.splitlines()
        max_width = 0
        
        for i, line in enumerate(lines):
            tokens = lexer.get_tokens(line)
            
            # Create one text element per line
            # We rely on SVG to handle horizontal spacing via tspans
            text_elem = svgwrite.text.Text("", insert=(x, y), 
                                           font_family="monospace", font_size=CODE_FONT_SIZE)
            text_elem['xml:space'] = 'preserve'
            
            for ttype, value in tokens:
                color = '#' + (style.style_for_token(ttype)['color'] or 'abb2bf')
                tspan = svgwrite.text.TSpan(value, fill=color)
                text_elem.add(tspan)
                
            text_group.add(text_elem)
            
            # Approximate width calculation for background box only
            # Using 0.7 as a safer multiplier for monospace
            line_len = len(line) * (CODE_FONT_SIZE * 0.7)
            if line_len > max_width:
                max_width = line_len
            
            y += LINE_HEIGHT
            
        # Update background size with padding
        box_w = max(max_width + 30, 200)
        box_h = y + 10
        bg['width'] = box_w
        bg['height'] = box_h
        
        # Clipping: Ensure text doesn't overflow background
        # We need a unique ID for the clip path
        clip_id = f"clip_{os.urandom(4).hex()}"
        
        # We need to add the clip path definition to the group's defs?
        # svgwrite Element.defs is not always available on Groups if not attached to Drawing?
        # But we can add it to the group itself if we treat it as a container.
        # Actually, adding 'defs' to a Group works in svgwrite.
        
        clip = svgwrite.masking.ClipPath(id=clip_id)
        clip.add(svgwrite.shapes.Rect(size=(box_w, box_h), rx=5, ry=5))
        # Add clip definition directly to the group (SVG allows this)
        group.add(clip)
        
        text_group['clip-path'] = f"url(#{clip_id})"
        
        group.add(text_group)
        
    except Exception as e:
        group.add(svgwrite.text.Text(f"Error reading file: {e}", fill="red", insert=(10, 20)))
        bg['width'] = 200
        bg['height'] = 40
        
    return group
