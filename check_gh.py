import urllib.request, json
url = 'https://api.github.com/repos/Maher-Bhatt/KALKI/actions/runs'
req = urllib.request.Request(url)
req.add_header('User-Agent', 'Python script')
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        if data['workflow_runs']:
            latest = data['workflow_runs'][0]
            print(f"Latest Run: {latest['name']} (ID: {latest['id']})")
            print(f"Status: {latest['status']}")
            print(f"Conclusion: {latest['conclusion']}")
            print(f"Created At: {latest['created_at']}")
            print(f"HTML URL: {latest['html_url']}")
except Exception as e:
    print('Error:', e)
