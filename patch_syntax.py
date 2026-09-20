def main():
    with open('app/server.py', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace("\\'host\\'", "'host'")
    content = content.replace("\\'{title}\\'", "'{title}'")

    with open('app/server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Syntax error fixed 3")

if __name__ == "__main__":
    main()
