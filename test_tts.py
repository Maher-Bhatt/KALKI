import asyncio
import edge_tts
import pygame
import time
import tempfile

async def main():
    print("Generating audio...")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    communicate = edge_tts.Communicate("Hello, testing audio", "en-US-BrianMultilingualNeural")
    await communicate.save(tmp)
    print("Saved:", tmp)
    pygame.mixer.init()
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.quit()
    print("Done")

asyncio.run(main())
