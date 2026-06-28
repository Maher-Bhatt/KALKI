from playwright.sync_api import sync_playwright
import time
import json

def main():
    logs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.on("console", lambda msg: print(f"CONSOLE {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"JS ERROR: {err}"))
        
        page.goto("http://localhost:8888", wait_until="domcontentloaded")
        time.sleep(2)
        print("Playwright run finished.")
        browser.close()

if __name__ == "__main__":
    main()
