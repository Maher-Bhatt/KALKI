import json
with open('c:/Jarvis/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == "def ddg_html_search(query, n=5):":
        new_lines.extend([
            "def _http_get(url, timeout=5):\n",
            "    import urllib.request\n",
            "    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})\n",
            "    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')\n",
            "\n",
            "def needs_web(text):\n",
            "    low = text.lower()\n",
            "    return any(k in low for k in ('search', 'who is', 'what is the latest', 'weather', 'news', 'price of'))\n",
            "\n",
            "def ddg_instant_answer(query):\n",
            "    try:\n",
            "        url = ('https://api.duckduckgo.com/?q=' + urllib.parse.quote(query) + '&format=json&no_html=1&skip_disambig=1')\n",
            "        import json\n",
            "        raw = _http_get(url, timeout=6)\n",
            "        data = json.loads(raw)\n",
            "    except Exception:\n",
            "        return None\n",
            "    abstract = (data.get('AbstractText') or '').strip()\n",
            "    if abstract:\n",
            "        return {'abstract': abstract, 'source': data.get('AbstractURL') or data.get('AbstractSource') or 'DuckDuckGo', 'topics': []}\n",
            "    related = data.get('RelatedTopics') or []\n",
            "    topics = []\n",
            "    for t in related[:6]:\n",
            "        if isinstance(t, dict) and t.get('Text'):\n",
            "            topics.append({'text': t['Text'], 'url': t.get('FirstURL', '')})\n",
            "    if topics:\n",
            "        return {'abstract': '', 'source': 'DuckDuckGo', 'topics': topics}\n",
            "    return None\n\n"
        ])
    new_lines.append(line)

with open('c:/Jarvis/server.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done")
