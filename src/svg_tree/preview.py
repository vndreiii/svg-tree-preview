import os
import html
import base64
import mimetypes
import svgwrite
from PIL import Image
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name

# Register extra mime types
mimetypes.add_type("image/jxl", ".jxl")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/wav", ".wav")

# Configuration for previews
PREVIEW_WIDTH = 400 # Max container width
CODE_FONT_SIZE = 12
LINE_HEIGHT = 16
MAX_LINES = 20

def is_binary(file_path):
    """Check if file is binary by looking for null bytes."""
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            return b'\0' in chunk
    except:
        return True

def _read_b64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_file_content_preview(file_path: str) -> svgwrite.container.Group:
    """
    Generates an SVG Group containing the preview of the file.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Image Preview
    if mime_type and (mime_type.startswith('image/') or ext in ('.jxl', '.webp')):
        return _generate_image_preview(file_path)
        
    # 2. Treat as Code (Force .ts to code)
    if ext == '.ts':
        return _generate_code_preview(file_path)

    # 3. Audio/Video (Placeholder for SVG)
    if mime_type and (mime_type.startswith('video/') or mime_type.startswith('audio/')):
        return _generate_placeholder_preview(file_path, "Media File")

    # 4. Binary Check
    if is_binary(file_path):
        return _generate_placeholder_preview(file_path, "Binary File")
    
    # 5. Code/Text Preview
    return _generate_code_preview(file_path)

def get_html_preview(file_path: str) -> str:
    """
    Generates an HTML snippet previewing the file.
    """
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        # 1. Image
        if mime_type and (mime_type.startswith('image/') or ext in ('.jxl', '.webp')):
            data = _read_b64(file_path)
            if not mime_type: mime_type = "image/png"
            return f'<div class="preview-image"><img src="data:{mime_type};base64,{data}" style="max-width: 100%; max-height: 300px; border-radius: 5px;"></div>'

        # 2. Force .ts to Code
        if ext == '.ts':
            pass # Continue to code section below
        
        # 3. Video
        elif mime_type and mime_type.startswith('video/'):
            data = _read_b64(file_path)
            return f'<div class="preview-media"><video controls src="data:{mime_type};base64,{data}" style="max-width: 100%; max-height: 300px;"></video></div>'

        # 4. Audio
        elif mime_type and mime_type.startswith('audio/'):
            data = _read_b64(file_path)
            return f'<div class="preview-media"><audio controls src="data:{mime_type};base64,{data}"></audio></div>'

        # 5. Binary Check
        elif is_binary(file_path):
            return f'<div class="preview-error">Binary File ({os.path.getsize(file_path)} bytes)</div>'

        # 6. Code
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = "".join(f.readlines()[:MAX_LINES])
            
        try:
            lexer = get_lexer_for_filename(file_path)
        except:
            lexer = TextLexer()
            
        formatter = HtmlFormatter(style='monokai', noclasses=True, wrapcode=True)
        return f'<div class="preview-code">{highlight(code, lexer, formatter)}</div>'
        
    except Exception as e:
        return f'<div class="preview-error">Error: {html.escape(str(e))}</div>'

def _generate_placeholder_preview(file_path: str, text: str) -> svgwrite.container.Group:
    group = svgwrite.container.Group()
    font_size = 12
    char_width = 8
    padding = 10
    box_w = (len(text) * char_width) + (padding * 2.5)
    box_h = 30
    
    rect = svgwrite.shapes.Rect(size=(box_w, box_h), fill="#21252b", stroke="#3e4451", rx=4, ry=4)
    rect['width'] = box_w
    rect['height'] = box_h
    group.add(rect)
    
    txt = svgwrite.text.Text(text, insert=(padding, 18), fill="#abb2bf", font_family="monospace", font_size=font_size)
    group.add(txt)
    return group

def _generate_image_preview(file_path: str) -> svgwrite.container.Group:
    group = svgwrite.container.Group()
    try:
        try:
            with Image.open(file_path) as img:
                orig_w, orig_h = img.size
        except Exception:
            orig_w, orig_h = 100, 100
            
        max_w, max_h = 350, 250
        ratio = min(1.0, min(max_w / orig_w, max_h / orig_h))
        
        new_w = int(orig_w * ratio)
        new_h = int(orig_h * ratio)
        
        data = _read_b64(file_path)
        
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type: 
            mime_type = "image/png"
            
        uri = f"data:{mime_type};base64,{data}"
        
        padding = 10
        box_w = new_w + (padding * 2)
        box_h = new_h + (padding * 2)
        
        rect = svgwrite.shapes.Rect(size=(box_w, box_h), fill="#21252b", stroke="#3e4451", rx=4, ry=4)
        group.add(rect)
        
        img_node = svgwrite.image.Image(href=uri, insert=(padding, padding), size=(new_w, new_h))
        group.add(img_node)
        
    except Exception as e:
        group.add(svgwrite.text.Text(f"Error: {e}", fill="red", font_size=10, insert=(0, 10)))
        rect = svgwrite.shapes.Rect(size=(200, 20), fill="none")
        rect['height'] = 20
        group.elements.insert(0, rect)
        
    return group

def _generate_code_preview(file_path: str) -> svgwrite.container.Group:
    group = svgwrite.container.Group()
    bg = svgwrite.shapes.Rect(fill="#282c34", stroke="#3e4451", rx=5, ry=5)
    group.add(bg)
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = "".join(f.readlines()[:MAX_LINES])
            
        try:
            lexer = get_lexer_for_filename(file_path)
        except:
            lexer = TextLexer()
            
        y = LINE_HEIGHT
        x = 10
        style = get_style_by_name('monokai')
        text_group = svgwrite.container.Group()
        
        lines = code.splitlines()
        max_width = 0
        
        for i, line in enumerate(lines):
            tokens = lexer.get_tokens(line)
            text_elem = svgwrite.text.Text("", insert=(x, y), 
                                           font_family="monospace", font_size=CODE_FONT_SIZE)
            text_elem['xml:space'] = 'preserve'
            
            for ttype, value in tokens:
                color = '#' + (style.style_for_token(ttype)['color'] or 'abb2bf')
                tspan = svgwrite.text.TSpan(value, fill=color)
                text_elem.add(tspan)
                
            text_group.add(text_elem)
            
            line_len = len(line) * (CODE_FONT_SIZE * 0.7)
            if line_len > max_width:
                max_width = line_len
            
            y += LINE_HEIGHT
            
        box_w = max(max_width + 30, 200)
        box_h = y + 10
        bg['width'] = box_w
        bg['height'] = box_h
        
        clip_id = f"clip_{os.urandom(4).hex()}"
        clip = svgwrite.masking.ClipPath(id=clip_id)
        clip.add(svgwrite.shapes.Rect(size=(box_w, box_h), rx=5, ry=5))
        group.add(clip)
        
        text_group['clip-path'] = f"url(#{clip_id})"
        group.add(text_group)
        
    except Exception as e:
        group.add(svgwrite.text.Text(f"Error: {e}", fill="red", insert=(10, 20)))
        bg['width'] = 200
        bg['height'] = 40
        
    return group