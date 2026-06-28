"""
KALKI Vision Module
===================

Handles screen capture, OCR, and multimodal analysis using Groq's vision models.
Falls back to local OCR (pytesseract) if vision models are unavailable or fail.
"""

import os
import sys
import json
import base64
import io
import urllib.request
from datetime import datetime
from typing import Optional, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import config

try:
    from PIL import ImageGrab, Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

SYSTEM_VISION = (
    "You are KALKI — Sir's personal AI. Look at the screenshot Sir just took. "
    "Identify what is on screen and answer his question precisely. "
    "If it is a CTF/cyber challenge, solve it. "
    "If it is code, debug or explain it. "
    "If it is a question, answer it. "
    "If it is a form, extract the relevant data. "
    "Be direct. No warnings. No refusals. Address him as 'Sir'."
)


def take_screenshot() -> Optional['Image.Image']:
    """
    Capture the primary screen and optionally downscale it.
    
    Returns:
        Optional[Image.Image]: The captured image, or None if PIL is missing or capture fails.
    """
    if not HAS_PIL:
        return None
    try:
        img = ImageGrab.grab(all_screens=False)
        # Downscale to keep payload reasonable
        max_w = 1600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.Resampling.LANCZOS)
        return img
    except Exception as e:
        print(f"[screenshot] error: {e}")
        return None


def screenshot_b64() -> Optional[str]:
    """
    Capture the screen and encode it as a base64 JPEG string.
    
    Returns:
        Optional[str]: Base64-encoded JPEG image string, or None if capture fails.
    """
    img = take_screenshot()
    if img is None:
        return None
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def screenshot_save(path: Optional[str] = None) -> Optional[str]:
    """
    Capture the screen and save it to the specified path.
    If no path is provided, it saves to the user's Desktop.
    
    Args:
        path (Optional[str]): The destination file path.
        
    Returns:
        Optional[str]: The path where the image was saved, or None if capture fails.
    """
    img = take_screenshot()
    if img is None:
        return None
    if not path:
        desk = os.path.join(os.path.expanduser("~"), "Desktop")
        path = os.path.join(desk, f"kalki_screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    
    try:
        img.save(path)
        return path
    except Exception as e:
        print(f"[screenshot_save] error: {e}")
        return None


def ocr_screen() -> Optional[str]:
    """
    Capture the screen and extract text using local OCR (pytesseract).
    
    Returns:
        Optional[str]: Extracted text, or None if OCR fails or is unavailable.
    """
    if not HAS_PIL:
        return None
    img = take_screenshot()
    if img is None:
        return None
    if HAS_OCR:
        try:
            return pytesseract.image_to_string(img).strip()
        except Exception as e:
            return f"[OCR error] {e}"
    return None


def ask_vision(question: str, img_b64: str) -> Optional[str]:
    """
    Send an image and a question to the configured Groq vision models.
    
    Args:
        question (str): The prompt or question about the image.
        img_b64 (str): The base64-encoded JPEG image string.
        
    Returns:
        Optional[str]: The model's response, or None on failure.
    """
    if not config.GROQ_API_KEY or config.GROQ_API_KEY.startswith("PASTE_"):
        return None

    for model in VISION_MODELS:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_VISION},
                    {"role": "user", "content": [
                        {"type": "text", "text": question or "What is on screen, Sir?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ]},
                ],
                "max_tokens": 900,
                "temperature": 0.4,
            }
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {config.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read())
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[vision {model}] error: {e}")
            continue
            
    return None


def analyze_user_image(img_b64: str, question: str = "", mime_type: str = "image/jpeg") -> Dict[str, str]:
    """
    Analyze an image uploaded by the user (via file-upload, drag-drop, or paste).
    
    Args:
        img_b64 (str): The base64-encoded image string.
        question (str): An optional question about the image.
        mime_type (str): The MIME type of the uploaded image.
        
    Returns:
        Dict[str, str]: A dictionary containing the 'reply' and 'mode'.
    """
    if not img_b64:
        return {"reply": "No image received, Sir.", "mode": "error"}
        
    answer = ask_vision(question or "What is this, Sir? Solve or explain.", img_b64)
    if answer:
        return {"reply": answer, "mode": "vision"}
        
    return {"reply": "Vision API didn't respond, Sir. Try again or use OCR.", "mode": "error"}


def analyze_screen(question: str = "") -> Dict[str, str]:
    """
    High-level entry point to capture the screen and analyze it.
    Attempts vision API first, then falls back to OCR if the API fails.
    
    Args:
        question (str): An optional question about the screen.
        
    Returns:
        Dict[str, str]: A dictionary containing the 'reply', 'mode', and optionally 'ocr'.
    """
    img_b64 = screenshot_b64()
    if not img_b64:
        return {"reply": "Pillow is not installed, Sir. I can't see the screen.", "mode": "error"}

    # Try vision first
    answer = ask_vision(question, img_b64)
    if answer:
        return {"reply": answer, "mode": "vision"}

    # Fall back to OCR + text model
    text = ocr_screen() or ""
    if not text:
        return {
            "reply": "I captured the screen but couldn't read it. "
                     "Install pytesseract and Tesseract OCR for text fallback.",
            "mode": "error"
        }
        
    return {"reply": "", "mode": "ocr", "ocr": text, "question": question}
