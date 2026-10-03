import re

with open('app/build_tools/build_msix.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('    Identity = SubElement(Package, "Identity", {\n        "Name": APP_NAME,', '    Identity = SubElement(Package, "Identity", {\n        "Name": PACKAGE_NAME,')

with open('app/build_tools/build_msix.py', 'w', encoding='utf-8') as f:
    f.write(content)
