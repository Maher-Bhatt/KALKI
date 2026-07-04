import os
import time
import threading
import json
import urllib.request
import urllib.parse

import config

_running = False
_thread = None

def _telegram_loop():
    global _running
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    allowed_user = str(getattr(config, "TELEGRAM_USER_ID", "")).strip()
    
    if not token or not allowed_user:
        print("[TELEGRAM] Missing token or user ID. Telegram remote disabled.")
        return
        
    print(f"[TELEGRAM] Polling started for user {allowed_user}...")
    offset = 0
    
    while _running:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30&offset={offset}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=35) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            if not data.get("ok"):
                time.sleep(2)
                continue
                
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue
                    
                sender_id = str(msg.get("from", {}).get("id", ""))
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                
                if sender_id != allowed_user:
                    print(f"[TELEGRAM] Unauthorized message from {sender_id}: {text}")
                    continue
                    
                if not text:
                    continue
                    
                print(f"[TELEGRAM] Received: {text}")
                
                # Send to KALKI /api/chat
                try:
                    payload = {
                        "messages": [{"role": "user", "content": text}],
                        "source": "telegram"
                    }
                    kalki_req = urllib.request.Request(
                        f"http://localhost:{config.PORT}/api/chat",
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(kalki_req, timeout=30) as k_res:
                        k_data = json.loads(k_res.read().decode("utf-8"))
                        reply = k_data.get("reply", "")
                        
                    # Send response back to Telegram
                    if reply:
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        send_payload = {"chat_id": chat_id, "text": reply}
                        s_req = urllib.request.Request(
                            send_url,
                            data=json.dumps(send_payload).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        urllib.request.urlopen(s_req, timeout=10)
                        
                except Exception as e:
                    print(f"[TELEGRAM] Error communicating with KALKI: {e}")
                    
        except Exception as e:
            # Catch timeouts and network errors silently
            time.sleep(5)
            
def start_telegram_bot():
    global _running, _thread
    if _running: return
    
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return
        
    _running = True
    _thread = threading.Thread(target=_telegram_loop, daemon=True)
    _thread.start()
