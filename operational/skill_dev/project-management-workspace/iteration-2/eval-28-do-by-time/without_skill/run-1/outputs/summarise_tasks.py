import json
p='/Users/avarilewang/.claude/projects/-Users-avarilewang-Documents-agentSkills-operational/f189e309-2a60-4970-bfee-8251e6ecc1ba/tool-results/mcp-cyb-data-query_records-1793678139036.txt'
d=json.load(open(p))
if isinstance(d,list): d=json.loads(d[0]['text'])
for r in d['records']:
    f=r['fields']
    pr=f.get('fldG7fZN9XhOa0lMy33')
    if pr=='finished_validating' or (f.get('fldVlGp4CjCeiNLC6cb') or '')>='2026-11-01':
        print(r['id'],'|',pr,'|',f.get('fldMTuydiWUFAgtqAPX'),'|',(f.get('fld3ZGyfGzogzwHt5Md') or {}).get('title'),'|',(f.get('fld6X3nrMTQlYiV5XSa') or {}).get('title'),'|start',f.get('fldj3Xb1g9nUX4iFqE0'),'|fin',f.get('fldn95wbkTqefn18WdO'),'|upd',f.get('fldVlGp4CjCeiNLC6cb'),'|',f.get('fldGqUoXO7oyq6ufX2Y'))
