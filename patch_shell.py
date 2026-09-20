import re

def main():
    with open('app/ui/features/shell.js', 'r', encoding='utf-8') as f:
        content = f.read()

    old = "  { id: 'workbench', label: 'Workbench', icon: 'workbench' },"
    new = "  { id: 'workbench', label: 'Workbench', icon: 'workbench' },\n  { id: 'oversight', label: 'Oversight', icon: 'alert' },"

    if old in content:
        content = content.replace(old, new)
        with open('app/ui/features/shell.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("shell.js patched.")
    else:
        print("Could not find workbench in shell.js")

if __name__ == "__main__":
    main()
