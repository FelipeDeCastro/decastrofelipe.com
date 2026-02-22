#!/usr/bin/env python3
"""
Cleanup script to make Webflow-exported code human-readable and editable.

What it does:
- Prettifies HTML with proper indentation
- Unminifies CSS with correct nesting
- Removes non-functional Webflow metadata attributes
- Cleans up verbose vendor-prefixed inline transforms (keeps standard transform)
- Formats embedded <style> blocks
- Renames .min.css → .css and updates references

What it preserves:
- data-w-id attributes (used by Webflow JS for interactions/animations)
- data-wf-ignore attributes (used by video elements)
- id="w-node-..." (used for CSS grid placement)
- All Webflow JS files (they handle animations and interactions)
- All functional data-* attributes for sliders, collapse, etc.
"""

import re
import os
import glob

WORKSPACE = os.path.dirname(os.path.abspath(__file__))

# ─── CSS Unminifier ───────────────────────────────────────────────────────────

def unminify_css(css):
    """Unminify CSS with proper indentation and line breaks."""
    result = []
    indent = 0
    i = 0
    in_comment = False
    
    while i < len(css):
        # Handle comments
        if css[i:i+2] == '/*':
            end = css.find('*/', i + 2)
            if end == -1:
                end = len(css)
            else:
                end += 2
            comment = css[i:end]
            result.append('  ' * indent + comment)
            i = end
            continue
        
        # Skip whitespace
        if css[i] in ' \t\n\r':
            i += 1
            continue
        
        # Closing brace
        if css[i] == '}':
            indent = max(0, indent - 1)
            result.append('  ' * indent + '}')
            result.append('')  # blank line after rule
            i += 1
            continue
        
        # Read until we hit {, }, or ;
        chunk = ''
        while i < len(css) and css[i] not in '{};':
            chunk += css[i]
            i += 1
        
        chunk = chunk.strip()
        
        if i < len(css) and css[i] == '{':
            # This is a selector or @-rule
            result.append('  ' * indent + chunk + ' {')
            indent += 1
            i += 1  # skip {
        elif i < len(css) and css[i] == ';':
            # This is a property
            if chunk:
                result.append('  ' * indent + chunk + ';')
            i += 1  # skip ;
        elif i < len(css) and css[i] == '}':
            # Property without semicolon before closing brace
            if chunk:
                result.append('  ' * indent + chunk + ';')
            indent = max(0, indent - 1)
            result.append('  ' * indent + '}')
            result.append('')
            i += 1
        elif chunk:
            result.append('  ' * indent + chunk)
    
    # Clean up multiple blank lines
    text = '\n'.join(result)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip() + '\n'


# ─── Inline Style Cleaner ─────────────────────────────────────────────────────

def clean_inline_style(style_value):
    """Clean verbose vendor-prefixed transforms, keeping only the standard one."""
    # Remove vendor-prefixed transforms
    cleaned = re.sub(r'-webkit-transform:\s*[^;]+;\s*', '', style_value)
    cleaned = re.sub(r'-moz-transform:\s*[^;]+;\s*', '', cleaned)
    cleaned = re.sub(r'-ms-transform:\s*[^;]+;\s*', '', cleaned)
    
    # Clean up extra semicolons/spaces
    cleaned = re.sub(r';\s*;', ';', cleaned)
    cleaned = re.sub(r'^\s*;\s*', '', cleaned)
    cleaned = cleaned.strip().rstrip(';').strip()
    
    return cleaned


# ─── Embedded <style> Formatter ───────────────────────────────────────────────

def format_embedded_style(match):
    """Format an embedded <style> block's CSS content."""
    attrs = match.group(1) or ''
    css_content = match.group(2)
    
    # Clean vendor-prefixed transforms in the CSS too
    css_content = re.sub(
        r'-webkit-transform:\s*[^;]+;\s*', '', css_content
    )
    css_content = re.sub(
        r'-moz-transform:\s*[^;]+;\s*', '', css_content
    )
    css_content = re.sub(
        r'-ms-transform:\s*[^;]+;\s*', '', css_content
    )
    
    formatted = unminify_css(css_content)
    
    # Indent CSS content inside <style>
    indented_css = '\n'.join('    ' + line if line.strip() else '' for line in formatted.split('\n'))
    
    return f'<style{attrs}>\n{indented_css}\n  </style>'


# ─── HTML Prettifier ───────────────────────────────────────────────────────────

def prettify_html(html):
    """Format HTML with proper indentation."""
    # Remove the Webflow "Last Published" comment
    html = re.sub(r'<!--\s*Last Published:.*?-->', '', html)
    
    # Remove non-functional Webflow metadata from <html> tag
    html = re.sub(r'\s+data-wf-domain="[^"]*"', '', html)
    html = re.sub(r'\s+data-wf-page="[^"]*"', '', html)
    html = re.sub(r'\s+data-wf-site="[^"]*"', '', html)
    
    # Remove non-functional Webflow metadata from forms
    html = re.sub(r'\s+data-wf-page-id="[^"]*"', '', html)
    html = re.sub(r'\s+data-wf-element-id="[^"]*"', '', html)
    
    # Clean up verbose inline transform styles
    def clean_style_attr(match):
        style = match.group(1)
        cleaned = clean_inline_style(style)
        if not cleaned:
            return ''
        return f' style="{cleaned}"'
    
    html = re.sub(r'\s+style="((?:[^"\\]|\\.)*)"', clean_style_attr, html)
    
    # Remove empty style attributes
    html = re.sub(r'\s+style=""', '', html)
    
    # Format embedded <style> blocks
    html = re.sub(
        r'<style([^>]*)>(.*?)</style>',
        format_embedded_style,
        html,
        flags=re.DOTALL
    )
    
    # Insert newlines between tags, but preserve script content
    # Step 1: Split </script> boundaries  
    html = re.sub(r'</script>\s*<', '</script>\n<', html)
    
    # Step 2: Split self-closing tag boundaries before scripts (e.g., /><script)
    html = re.sub(r'/>\s*<script', '/>\n<script', html)
    
    # Step 3: For non-script content, split tags onto separate lines
    parts = re.split(r'(<script[^>]*>.*?</script>)', html, flags=re.DOTALL)
    
    processed_parts = []
    for i, part in enumerate(parts):
        if re.match(r'<script[^>]*>', part):
            processed_parts.append(part)
        else:
            part = re.sub(r'>\s*<', '>\n<', part)
            processed_parts.append(part)
    
    html = ''.join(processed_parts)
    
    # Final pass: ensure no tags are stuck together
    html = re.sub(r'>\s*<', '>\n<', html)
    # But this may have broken script content - restore it
    # Re-protect script blocks
    def protect_script_content(match):
        # Undo any newlines we added inside <script>...</script>
        content = match.group(0)
        tag_end = content.index('>') + 1
        close_start = content.rindex('</')
        opening_tag = content[:tag_end]
        inner = content[tag_end:close_start]
        closing_tag = content[close_start:]
        # Remove any newlines in inner content that we might have added
        inner = inner.replace('\n', '')
        return opening_tag + inner + closing_tag
    
    html = re.sub(r'<script[^>]*>[^<]+</script>', protect_script_content, html)
    
    # Indent the HTML
    lines = html.split('\n')
    indented = []
    indent = 0
    
    # Void elements that don't need closing tags
    void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                     'link', 'meta', 'param', 'source', 'track', 'wbr'}
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Is it a closing tag?
        is_closing = stripped.startswith('</')
        
        # Is it self-closing (/>) or a void element?
        is_void = stripped.endswith('/>')
        if not is_void:
            tag_match = re.match(r'<(\w+)', stripped)
            if tag_match and tag_match.group(1).lower() in void_elements:
                is_void = True
        
        # Is it a doctype or comment?
        is_special = stripped.startswith('<!') or stripped.startswith('<?')
        
        # Does line contain both opening and closing of same tag?
        has_inline_close = bool(re.match(r'<(\w+)[^>]*>.*</\1>$', stripped, re.DOTALL))
        
        if is_closing:
            indent = max(0, indent - 1)
            indented.append('  ' * indent + stripped)
        elif is_special or is_void or has_inline_close:
            indented.append('  ' * indent + stripped)
        else:
            indented.append('  ' * indent + stripped)
            if stripped.startswith('<') and not stripped.startswith('</'):
                tag_match = re.match(r'<(\w+)', stripped)
                if tag_match:
                    tag_name = tag_match.group(1).lower()
                    if tag_name not in void_elements:
                        indent += 1
    
    result = '\n'.join(indented) + '\n'
    
    # Final cleanup: remove excessive blank lines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def process_css_files():
    """Unminify and rename CSS files."""
    css_files = [
        os.path.join(WORKSPACE, 'assets/6303bbde7e8891552c333a00/css/decastrofelipe.webflow.shared.098991e7a.min.css'),
        os.path.join(WORKSPACE, 'assets/css/decastrofelipe.webflow.shared.098991e7a.min.css'),
    ]
    
    for filepath in css_files:
        if os.path.exists(filepath):
            filename = os.path.relpath(filepath, WORKSPACE)
            print(f'  Processing {filename}...')
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.strip():
                formatted = unminify_css(content)
                new_path = filepath.replace('.min.css', '.css')
                
                with open(new_path, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                
                if new_path != filepath:
                    os.remove(filepath)
                    print(f'    ✓ Unminified → {os.path.basename(new_path)}')
                else:
                    print(f'    ✓ Unminified')
            else:
                print(f'    ⚠ Empty file, skipping')


def process_html_files():
    """Prettify all HTML files."""
    html_files = sorted(glob.glob(os.path.join(WORKSPACE, '*.html')))
    
    for filepath in html_files:
        filename = os.path.basename(filepath)
        print(f'  Processing {filename}...')
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        formatted = prettify_html(content)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(formatted)
        
        print(f'    ✓ Formatted')


def update_css_references():
    """Update HTML files to reference the renamed CSS files."""
    old_name = 'decastrofelipe.webflow.shared.098991e7a.min.css'
    new_name = 'decastrofelipe.webflow.shared.098991e7a.css'
    
    html_files = glob.glob(os.path.join(WORKSPACE, '*.html'))
    for filepath in html_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_name in content:
            content = content.replace(old_name, new_name)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'    ✓ {os.path.basename(filepath)}')


if __name__ == '__main__':
    print('=' * 60)
    print('  Cleaning up Webflow code for human readability')
    print('=' * 60)
    print()
    
    print('[1/3] Unminifying CSS...')
    process_css_files()
    print()
    
    print('[2/3] Prettifying HTML...')
    process_html_files()
    print()
    
    print('[3/3] Updating CSS references...')
    update_css_references()
    print()
    
    print('=' * 60)
    print('  Done! All files are now human-readable.')
    print('=' * 60)
