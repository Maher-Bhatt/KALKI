import re
with open('c:/Jarvis/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

pat = r'def build_system_prompt\(\):.*?return \(\n\s*SYSTEM_PROMPT_BASE\n\s*\+\s*hardware_prompt_block\(\)\n\s*\+\s*get_memory_prompt\(\)\n\s*\+\s*f[^)]*\n\s*\+\s*f[^)]*\n\s*\)\n\s*if abstract:\n\s*return \{\n\s*"abstract": abstract,'
rep = '''def build_system_prompt():
    now = datetime.now()
    return (
        SYSTEM_PROMPT_BASE
        + hardware_prompt_block()
        + get_memory_prompt()
        + f"\\n\\nCURRENT TIME: {now.strftime('%I:%M %p')}"
        + f"\\nCURRENT DATE: {now.strftime('%A, %B %d, %Y')}"
    )

def _http_get(url, timeout=5):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')

def needs_web(text):
    low = text.lower()
    return any(k in low for k in ("search", "who is", "what is the latest", "weather", "news", "price of"))

def ddg_instant_answer(query):
    """Try DuckDuckGo's JSON instant answer API."""
    try:
        url = ("https://api.duckduckgo.com/?q="
               + urllib.parse.quote(query)
               + "&format=json&no_html=1&skip_disambig=1")
        raw = _http_get(url, timeout=6)
        data = json.loads(raw)
    except Exception:
        return None

    abstract = (data.get("AbstractText") or "").strip()
    if abstract:
        return {
            "abstract": abstract,'''

new_content = re.sub(pat, rep, content, flags=re.DOTALL)
with open('c:/Jarvis/server.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Done")
