path = 'c:/Users/nacho/Documents/mad_plan/frontend_new/vite.config.ts'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('req.originalUrl.replace', '(req.originalUrl || \"\").replace')
with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
