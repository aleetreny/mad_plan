import sys
with open('c:/Users/nacho/Documents/mad_plan/frontend_new/src/hooks/useMadPlanData.ts', 'r', encoding='utf-8') as f:
    text = f.read()

import re
text = re.sub(r'const targetHost.*? = .*?;', 'const targetHost = \'\';', text)
text = re.sub(r\"setError\('.*?'\);\", \"setError('Datos no encontrados. Asegurate de que los JSON originales estén accesibles en /outputs');\", text)
text = re.sub(r'setEvents\(\[\{.*?\}\]\);', 'setEvents([]);', text, flags=re.DOTALL)
text = re.sub(r'setNews\(\[\{.*?\}\]\);', 'setNews([]);', text, flags=re.DOTALL)

with open('c:/Users/nacho/Documents/mad_plan/frontend_new/src/hooks/useMadPlanData.ts', 'w', encoding='utf-8') as f:
    f.write(text)
