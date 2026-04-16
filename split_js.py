import re

html_path = r'd:\Gamify\templates\index.html'
js_path = r'd:\Gamify\static\app.js'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the <script> ... </script> block
match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if not match:
    print("No <script> block found!")
    exit(1)

js_content = match.group(1)

# Write JS to file
with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js_content.strip() + '\n')

# Replace the inline script with a link to the external file
new_content = content.replace(
    '<script>' + match.group(1) + '</script>',
    '<script src="{{ url_for(\'static\', filename=\'app.js\') }}"></script>'
)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

# Count lines
js_lines = js_content.strip().count('\n') + 1
print(f'Successfully extracted {js_lines} lines of JS to static/app.js')
