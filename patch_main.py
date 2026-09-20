def main():
    with open('app/ui/main.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the boot() call at the bottom
    content = content.replace("else boot();", "else boot().catch(e => { const b = document.getElementById('boot'); if (b) b.innerHTML = '<div style=\"color:red\">' + e.message + '<br>' + e.stack + '</div>'; });")

    with open('app/ui/main.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print("main.js patched")

if __name__ == "__main__":
    main()
