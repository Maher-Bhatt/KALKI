import re
src = open(r'e:\KALKI-main\app\ui\api\endpoints.js', encoding='utf-8', errors='ignore').read()
gets = sorted(set(re.findall(r"get\(\s*[`']([^`'?$]+)", src)))
posts = sorted(set(re.findall(r"post\(\s*[`']([^`'?$]+)", src)))
open(r'e:\KALKI-main\tools\_paths.txt', 'w').write('\n'.join(['GET ' + g for g in gets] + ['POST ' + p for p in posts]))
print(len(gets), 'GET', len(posts), 'POST')
