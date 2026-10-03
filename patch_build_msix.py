import re

with open('app/build_tools/build_msix.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('APP_NAME = "KALKI"', 'APP_NAME = "KALKI"\nPACKAGE_NAME = "MaherBhatt.Kalki"\nDISPLAY_NAME = "Kalki"')
content = content.replace('PUBLISHER_NAME = "CN=KALKI_Developer"', 'PUBLISHER_NAME = "CN=5077752A-5182-4523-A5DB-4EBB2626926D"')
content = content.replace('PUBLISHER_DISPLAY_NAME = "KALKI Developer"', 'PUBLISHER_DISPLAY_NAME = "Maher Bhatt"')

content = content.replace('Identity = SubElement(Package, "Identity", {\\n        "Name": APP_NAME,', 'Identity = SubElement(Package, "Identity", {\\n        "Name": PACKAGE_NAME,')

content = content.replace('SubElement(Properties, "DisplayName").text = APP_NAME', 'SubElement(Properties, "DisplayName").text = DISPLAY_NAME')

content = content.replace('"DisplayName": APP_NAME,', '"DisplayName": DISPLAY_NAME,')

# Fix the bug I introduced earlier
content = content.replace('        "--hidden-import=spotipy": "",\n        "--hidden-import=plyer": "",\n', '')

with open('app/build_tools/build_msix.py', 'w', encoding='utf-8') as f:
    f.write(content)
