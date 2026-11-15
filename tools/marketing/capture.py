"""Capture real KALKI screens from the demo studio for the Store, social posts and video."""
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]

import os
import sys
import time
from PIL import Image
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:10031"
OUT = str(REPO / "marketing" / "store" / "screenshots")
THEMES = sys.argv[1:] or ["light", "dark"]


def settle(page, seconds=1.5):
    page.wait_for_timeout(int(seconds * 1000))


def open_app(page, theme, route="#/ask"):
    page.goto(f"{BASE}/{route}")
    page.wait_for_selector(".shell, #app", timeout=20000)
    page.evaluate("t => { document.documentElement.dataset.theme = t; document.documentElement.dataset.motion = 'off'; }", theme)
    settle(page, 2.5)


def scene_ask_home(page, theme):
    open_app(page, theme, "#/ask")


def scene_ask_chat(page, theme):
    open_app(page, theme, "#/ask")
    box = page.locator(".comp textarea").first
    box.click()
    box.fill("Plan my Saturday: I want to work out, finish the quarterly report and see friends in the evening.")
    box.press("Enter")
    page.wait_for_timeout(6000)


def scene_today(page, theme):
    open_app(page, theme, "#/today")
    settle(page, 3)


def scene_voice(page, theme):
    open_app(page, theme, "#/ask")
    page.evaluate("window.dispatchEvent(new CustomEvent('kalki:voice-toggle'))")
    settle(page, 2.5)
    page.locator(".vm-pill", has_text="What should I focus on today?").click()
    deadline = time.time() + 25
    while time.time() < deadline and page.evaluate("document.querySelector('.vm')?.dataset.state") != "speaking":
        page.wait_for_timeout(300)
    settle(page, 1.2)


def scene_onboarding(page, theme):
    open_app(page, theme, "#/ask")
    page.evaluate("import('/ui/features/firstrun.js').then(m => m.showFirstRun({}))")
    settle(page, 1.5)
    page.get_by_role("button", name="Let's begin").click()
    settle(page, 0.8)
    page.locator(".ob input.input").first.fill("Aarav")
    page.get_by_role("button", name="Continue").click()
    settle(page, 1.5)


def scene_notes(page, theme):
    open_app(page, theme, "#/today")
    settle(page, 2)
    page.get_by_role("button", name="All notes").click()
    settle(page, 2)


def scene_security(page, theme):
    open_app(page, theme, "#/security")
    settle(page, 3)


def scene_screentime(page, theme):
    open_app(page, theme, "#/settings/screentime")
    settle(page, 3)


SCENES = [
    ("01_ask_home", scene_ask_home), ("02_conversation", scene_ask_chat), ("03_today_briefing", scene_today),
    ("04_voice_mode", scene_voice), ("05_onboarding", scene_onboarding), ("06_notes", scene_notes),
    ("07_security_checkup", scene_security), ("08_screen_time", scene_screentime),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--autoplay-policy=no-user-gesture-required"])
        for theme in THEMES:
            hi_dir = os.path.join(OUT, theme, "3840x2160")
            lo_dir = os.path.join(OUT, theme, "1920x1080")
            os.makedirs(hi_dir, exist_ok=True)
            os.makedirs(lo_dir, exist_ok=True)
            ctx = browser.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2,
                                      color_scheme="dark" if theme == "dark" else "light", permissions=["microphone"])
            for name, scene in SCENES:
                page = ctx.new_page()
                try:
                    scene(page, theme)
                    hi = os.path.join(hi_dir, name + ".png")
                    page.screenshot(path=hi)
                    Image.open(hi).resize((1920, 1080), Image.LANCZOS).save(os.path.join(lo_dir, name + ".png"), optimize=True)
                    print("captured", theme, name, flush=True)
                except Exception as e:
                    print("FAILED", theme, name, str(e).splitlines()[0][:200], flush=True)
                finally:
                    page.close()
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
