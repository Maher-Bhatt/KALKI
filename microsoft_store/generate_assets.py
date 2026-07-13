"""
Generate all required MSIX Store visual assets from kalki_logo.png.

Usage:
    py microsoft_store\generate_assets.py

Output:
    microsoft_store/assets/  (all required .png files)
"""
from PIL import Image
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH    = os.path.join(PROJECT_ROOT, "assets", "kalki_logo.png")
ASSETS_DIR   = os.path.join(PROJECT_ROOT, "microsoft_store", "assets")

os.makedirs(ASSETS_DIR, exist_ok=True)

img = Image.open(LOGO_PATH).convert("RGBA")

# All required MSIX visual asset sizes
ASSETS = {
    # Core assets referenced in AppxManifest.xml
    "StoreLogo.png":          (50, 50),
    "Square44x44Logo.png":    (44, 44),
    "Square71x71Logo.png":    (71, 71),
    "Square150x150Logo.png":  (150, 150),
    "Wide310x150Logo.png":    (310, 150),
    "SplashScreen.png":       (620, 300),

    # Target sizes for taskbar, Start menu, notification area
    "Square44x44Logo.targetsize-16_altform-unplated.png":  (16, 16),
    "Square44x44Logo.targetsize-24_altform-unplated.png":  (24, 24),
    "Square44x44Logo.targetsize-32_altform-unplated.png":  (32, 32),
    "Square44x44Logo.targetsize-48_altform-unplated.png":  (48, 48),
    "Square44x44Logo.targetsize-256_altform-unplated.png": (256, 256),

    # Store listing tiles
    "LargeTile.png":  (310, 310),
    "SmallTile.png":  (71, 71),

    # Badge logo (for lock screen notifications)
    "BadgeLogo.png":  (24, 24),
}

BACKGROUND_COLOR = (26, 26, 46, 255)  # #1a1a2e

for name, (w, h) in ASSETS.items():
    if w != h:
        # Non-square: center logo on colored canvas
        scale = min(w, h)
        logo_resized = img.resize((scale, scale), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), BACKGROUND_COLOR)
        x_offset = (w - scale) // 2
        y_offset = (h - scale) // 2
        canvas.paste(logo_resized, (x_offset, y_offset), logo_resized)
        canvas.save(os.path.join(ASSETS_DIR, name), "PNG")
    else:
        resized = img.resize((w, h), Image.LANCZOS)
        resized.save(os.path.join(ASSETS_DIR, name), "PNG")

    print(f"  OK  {name} ({w}x{h})")

print(f"\nGenerated {len(ASSETS)} assets in: {ASSETS_DIR}")
