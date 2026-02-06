import os
import html
import base64
import mimetypes
import svgwrite
import re
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
CODE_FONT_SIZE = 12
LINE_HEIGHT = 16
MAX_PREVIEW_SIZE = 999 * 1024 * 1024 

# XML-compatible character filter
_RE_XML_ILLEGAL = re.compile(
    r'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])'
    r'|'
    r'([%s-%s])' % (chr(0xd800), chr(0xdbff)) + 
    r'|'
    r'([%s-%s])' % (chr(0xdc00), chr(0xdfff))
)

def sanitize_text(text: str) -> str:
    """Removes control characters that are invalid in XML/SVG."""
    if not isinstance(text, str):
        text = str(text)
    return _RE_XML_ILLEGAL.sub('', text)

def _get_token_lines(tokens):
    """
    Processes a stream of (ttype, value) tokens and groups them into lines.
    Handles internal newlines in token values and flattens any nested structures.
    """
    lines = []
    current_line = []
    
    def process_token(ttype, value):
        nonlocal current_line
        if isinstance(value, (list, tuple)):
            for sub_t in value:
                if isinstance(sub_t, (list, tuple)) and len(sub_t) == 2:
                    process_token(sub_t[0], sub_t[1])
            return

        val_str = str(value)
        if '\n' in val_str:
            parts = val_str.split('\n')
            for i, part in enumerate(parts):
                if part:
                    current_line.append((ttype, part))
                if i < len(parts) - 1:
                    lines.append(current_line)
                    current_line = []
        else:
            if val_str:
                current_line.append((ttype, val_str))

    for t in tokens:
        if isinstance(t, (list, tuple)) and len(t) == 2:
            process_token(t[0], t[1])
            
    if current_line:
        lines.append(current_line)
    return lines

def is_binary(file_path):
    """Check if file is binary by looking for null bytes."""
    try:
        if os.path.getsize(file_path) == 0:
            return False
        with open(file_path, 'rb') as f:
            chunk = f.read(8192)
            return b'\0' in chunk
    except:
        return True

def _read_b64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _read_text_preview(file_path: str) -> str:
    """Reads the entire text file content within MAX_PREVIEW_SIZE."""
    try:
        if os.path.getsize(file_path) > MAX_PREVIEW_SIZE:
            return ""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sanitize_text(f.read())
    except Exception:
        return ""

def get_preview_data(file_path: str, mode: str = 'svg'):
    """
    Parallel-friendly function that returns picklable data for a preview.
    mode: 'svg' or 'html'
    """
    try:
        if mode == 'html':
            return get_html_preview(file_path)
        
        # SVG Mode: Return structured data
        mime_type, _ = mimetypes.guess_type(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)

        # 1. Image (No size limit)
        if mime_type and (mime_type.startswith('image/') or ext in ('.jxl', '.webp')):
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                return {
                    'type': 'image',
                    'width': w,
                    'height': h,
                    'data': _read_b64(file_path),
                    'mime': mime_type or "image/png"
                }
            except:
                pass

        # 2. Size Check for other types
        if file_size > MAX_PREVIEW_SIZE:
            return {'type': 'placeholder', 'text': f"Large {mime_type or 'File'}", 'width': 150, 'height': 30}

        # 3. Media Placeholder
        if mime_type and (mime_type.startswith('video/') or mime_type.startswith('audio/')):
            return {'type': 'placeholder', 'text': "Media File", 'width': 120, 'height': 30}

        # 4. Binary Check
        if is_binary(file_path):
            return {'type': 'placeholder', 'text': "Binary File", 'width': 120, 'height': 30}

        # 5. Code/Text
        code = _read_text_preview(file_path)
        if not code:
            return None

        try:
            lexer = get_lexer_for_filename(file_path)
        except:
            lexer = TextLexer()

        style = get_style_by_name('monokai')
        try:
            tokens = list(lexer.get_tokens(code))
        except:
            tokens = list(TextLexer().get_tokens(code))

        token_lines = _get_token_lines(tokens)
        
        # Prepare structured lines
        render_lines = []
        max_w = 0
        for row in token_lines:
            line_parts = []
            line_w = 0
            for ttype, value in row:
                clean_val = sanitize_text(value)
                try:
                    style_dict = style.style_for_token(ttype)
                    color = '#' + (style_dict['color'] or 'abb2bf')
                except:
                    color = '#abb2bf'
                
                line_parts.append((color, clean_val))
                line_w += len(clean_val) * (CODE_FONT_SIZE * 0.72)
            
            render_lines.append(line_parts)
            max_w = max(max_w, line_w)

        return {
            'type': 'code',
            'lines': render_lines,
            'width': max_w + 20,
            'height': (len(render_lines) * LINE_HEIGHT) + 10
        }

    except Exception as e:
        return {'type': 'placeholder', 'text': f"Error: {sanitize_text(str(e))}", 'width': 200, 'height': 30}

def get_html_preview(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    try:
        file_size = os.path.getsize(file_path)
        if mime_type and (mime_type.startswith('image/') or ext in ('.jxl', '.webp')):
            # No size limit for images here either
            data = _read_b64(file_path)
            if not mime_type: mime_type = "image/png"
            return f'<div class="preview-image"><img src="data:{mime_type};base64,{data}" style="max-width: 100%; border-radius: 5px;"></div>'
        
        if ext == '.ts': pass
        elif mime_type and mime_type.startswith('video/'):
            if file_size > MAX_PREVIEW_SIZE:
                return f'<div class="preview-error">Video too large ({file_size} bytes)</div>'
            data = _read_b64(file_path)
            return f'<div class="preview-media"><video controls src="data:{mime_type};base64,{data}" style="max-width: 100%;"></video></div>'
        elif mime_type and mime_type.startswith('audio/'):
            if file_size > MAX_PREVIEW_SIZE:
                return f'<div class="preview-error">Audio too large ({file_size} bytes)</div>'
            data = _read_b64(file_path)
            return f'<div class="preview-media"><audio controls src="data:{mime_type};base64,{data}"></audio></div>'
        elif is_binary(file_path):
            return f'<div class="preview-error">Binary File ({file_size} bytes)</div>'
        
        code = _read_text_preview(file_path)
        if not code: return ""
        try: lexer = get_lexer_for_filename(file_path)
        except: lexer = TextLexer()
        formatter = HtmlFormatter(style='monokai', noclasses=True, wrapcode=True)
        return f'<div class="preview-code">{highlight(code, lexer, formatter)}</div>'
    except Exception as e:
        return f'<div class="preview-error">Error: {html.escape(str(e))}</div>'

def build_svg_preview_from_data(data: dict) -> svgwrite.container.Group:
    """Reconstructs an SVG Group from pre-calculated data."""
    group = svgwrite.container.Group()
    if not data:
        return group

    box_w, box_h = data['width'], data['height']
    
    # Background
    if data['type'] == 'code':
        bg = svgwrite.shapes.Rect(size=(box_w, box_h), fill="#282c34", stroke="#3e4451", rx=5, ry=5)
    else:
        bg = svgwrite.shapes.Rect(size=(box_w, box_h), fill="#21252b", stroke="#3e4451", rx=4, ry=4)
    group.add(bg)

    if data['type'] == 'placeholder':
        txt = svgwrite.text.Text(data['text'], insert=(10, 18), fill="#abb2bf", font_family="monospace", font_size=12)
        group.add(txt)
    
    elif data['type'] == 'image':
        uri = f"data:{data['mime']};base64,{data['data']}"
        img_node = svgwrite.image.Image(href=uri, insert=(10, 10), size=(data['width']-20, data['height']-20))
        group.add(img_node)
        
    elif data['type'] == 'code':
        y = LINE_HEIGHT
        for line in data['lines']:
            text_elem = svgwrite.text.Text("", insert=(10, y), font_family="monospace", font_size=CODE_FONT_SIZE)
            text_elem['xml:space'] = 'preserve'
            for color, val in line:
                text_elem.add(svgwrite.text.TSpan(val, fill=color))
            group.add(text_elem)
            y += LINE_HEIGHT
            
    return group