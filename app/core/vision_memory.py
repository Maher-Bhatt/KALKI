"""
KALKI Vision Memory — Local Screen Capture & OCR
Takes periodic screenshots, runs local OCR, and saves text into semantic memory.
Opt-in required. Disabled by default for privacy.
"""

import os
import time
import threading
import datetime
from PIL import ImageGrab
import pytesseract

import config
import semantic_memory

# If pytesseract is not in PATH, Windows users typically need to set it:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

_vision_thread = None

def _vision_loop():
    while getattr(config, "VISION_RECALL_ENABLED", False):
        try:
            # 1. Capture screen
            img = ImageGrab.grab()
            
            # 2. Run local OCR
            text = pytesseract.image_to_string(img).strip()
            
            if text and len(text) > 10:
                # 3. Store in semantic memory with timestamp tag
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                memory_text = f"[SCREENSHOT {now_str}]\n{text}"
                semantic_memory.add_memory(memory_text, source="vision")
                
                # 4. Cleanup old memories based on retention policy
                retention_days = getattr(config, "VISION_RETENTION_DAYS", 7)
                cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)
                
                # Find and remove vision nodes older than cutoff
                with semantic_memory._lock:
                    memories = semantic_memory._load()
                    to_keep = []
                    for m in memories:
                        if m.get("source") == "vision":
                            try:
                                # Extract timestamp
                                ts_str = m["text"].split("]")[0].replace("[SCREENSHOT ", "")
                                ts = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                                if ts >= cutoff:
                                    to_keep.append(m)
                            except:
                                to_keep.append(m)
                        else:
                            to_keep.append(m)
                    
                    if len(to_keep) < len(memories):
                        semantic_memory._save(to_keep)
                        
        except Exception as e:
            # Log error but don't spam. Wait next interval.
            pass
            
        # Sleep for 60 seconds
        time.sleep(60)

def start_vision_memory():
    global _vision_thread
    if getattr(config, "VISION_RECALL_ENABLED", False):
        if not _vision_thread or not _vision_thread.is_alive():
            _vision_thread = threading.Thread(target=_vision_loop, daemon=True)
            _vision_thread.start()
