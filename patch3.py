import re
import sys

def main():
    with open('app/server.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. ask_ai_stream fallback logic
    old_ask_stream_except = """    except urllib.error.HTTPError as e:
        if e.code == 429:
            log(f"Rate limit hit on {chosen}, falling back to alternative...")
            has_gemini = bool(getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"))
            has_openai = bool(getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"))
            fallback = "gemini-2.5-flash" if has_gemini else "gpt-4o-mini" if has_openai else "ollama"
            if fallback != chosen:
                STATE["model"] = fallback
                for token in ask_ai_stream(user_messages): yield token
                return
        log(f"Cloud stream HTTP Error for {chosen}: {e}")
        yield f"API link failed, Sir: {e}"
    except Exception as e:
        log(f"Cloud stream failed for {chosen}: {e}")
        yield f"API link failed, Sir: {e}\""""

    new_ask_stream_except = """    except Exception as e:
        log(f"Cloud stream failed for {chosen}: {e}")
        has_gemini = bool(getattr(config, "GEMINI_API_KEY", "") and not getattr(config, "GEMINI_API_KEY", "").startswith("PASTE_"))
        has_openai = bool(getattr(config, "OPENAI_API_KEY", "") and not getattr(config, "OPENAI_API_KEY", "").startswith("PASTE_"))
        fallback = "gemini-2.5-flash" if has_gemini and not chosen.startswith("gemini") else "gpt-4o-mini" if has_openai and not chosen.startswith("gpt") else "ollama"
        if fallback != chosen and not getattr(ask_ai_stream, "_fallback_active", False):
            ask_ai_stream._fallback_active = True
            log(f"Falling back from {chosen} to {fallback}...")
            STATE["model"] = fallback
            try:
                for token in ask_ai_stream(user_messages): yield token
            finally:
                ask_ai_stream._fallback_active = False
            return
        raise RuntimeError(f"Provider {chosen} failed: {e}")"""
    
    if old_ask_stream_except in content:
        content = content.replace(old_ask_stream_except, new_ask_stream_except)
    else:
        print("Could not find ask_ai_stream exception block to replace.")

    # 2. ask_ai return string to raise
    old_ask_return = """        if groq_err == "no API key set":
            return ("I need an AI provider before I can answer. Open Settings, choose AI Models, "
                    "and add your free Groq API key. Alternatively, check your network connection for the DeepSeek fallback.")
        return (f"I could not reach an AI provider ({groq_err[:140]}). "
                f"Check the connection and API key in Settings, then try again.")"""
                
    new_ask_return = """        if groq_err == "no API key set":
            raise RuntimeError("I need an AI provider before I can answer. Open Settings, choose AI Models, and add your free Groq API key. Alternatively, check your network connection for the DeepSeek fallback.")
        raise RuntimeError(f"I could not reach an AI provider ({groq_err[:140]}). Check the connection and API key in Settings, then try again.")"""

    if old_ask_return in content:
        content = content.replace(old_ask_return, new_ask_return)
    else:
        print("Could not find ask_ai return block to replace.")

    # 3. /api/chat stream exception catch
    old_chat_stream = """            if stream_req:
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                
                full_reply = []
                start_time = time.time()
                for token in ask_ai_stream(messages):
                    full_reply.append(token)
                    self.wfile.write(f"data: {json.dumps({'token': token})}\\n\\n".encode())
                    self.wfile.flush()"""

    new_chat_stream = """            if stream_req:
                start_time = time.time()
                generator = ask_ai_stream(messages)
                try:
                    first_token = next(generator)
                except StopIteration:
                    first_token = ""
                except Exception as e:
                    self._json({"ok": False, "error": str(e)})
                    return
                    
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.end_headers()
                
                full_reply = []
                if first_token:
                    full_reply.append(first_token)
                    self.wfile.write(f"data: {json.dumps({'token': first_token})}\\n\\n".encode())
                    self.wfile.flush()
                for token in generator:
                    full_reply.append(token)
                    self.wfile.write(f"data: {json.dumps({'token': token})}\\n\\n".encode())
                    self.wfile.flush()"""

    if old_chat_stream in content:
        content = content.replace(old_chat_stream, new_chat_stream)
    else:
        print("Could not find /api/chat stream loop to replace.")

    # 4. /api/chat non-stream exception catch
    old_chat_nostream = """                try:
                    # Prepend recent conversation so KALKI remembers context.
                    convo = load_history()[-8:] + messages
                    reply = ask_ai(convo)
                except Exception as e:
                    reply = f"My link hiccuped, Sir — say that again? ({str(e)[:80]})"
                
                reply = maybe_add_joke_offer(user_text, reply)"""

    new_chat_nostream = """                try:
                    # Prepend recent conversation so KALKI remembers context.
                    convo = load_history()[-8:] + messages
                    reply = ask_ai(convo)
                except Exception as e:
                    self._json({"ok": False, "error": str(e)})
                    return
                
                reply = maybe_add_joke_offer(user_text, reply)"""

    if old_chat_nostream in content:
        content = content.replace(old_chat_nostream, new_chat_nostream)
    else:
        print("Could not find /api/chat non-stream loop to replace.")
        
    with open('app/server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Backend API Error Fix patched!")

if __name__ == "__main__":
    main()
