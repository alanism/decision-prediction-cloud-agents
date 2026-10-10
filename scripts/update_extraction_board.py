"""Render the fixed-denominator extraction board; never change statuses implicitly."""
from pathlib import Path
import json,html
R=Path(__file__).resolve().parents[1]
data=json.loads((R/'docs/extraction/tasks.json').read_text())
assert data['denominator']==len(data['tasks'])==10
count=sum(t['status']=='done' for t in data['tasks'])
out='<!doctype html><meta charset="utf-8"><title>Cloud extraction progress</title><style>body{font:17px system-ui;background:#fdfcf3;color:#151515;max-width:1100px;margin:40px auto;padding:20px}article{border:1px solid #aaa;padding:14px;margin:14px 0}h1{font:38px Georgia}small{color:#555}</style><h1>Decision ≥ Prediction Cloud Agents</h1><p>'+str(count)+'/10 extraction tasks complete ('+str(count*10)+'%). Fixed denominator.</p><p>'+html.escape(data['scope'])+'</p>'
for status in ('in_progress','blocked','todo','done'):
 out+='<h2>'+html.escape(status.replace('_',' ').title())+'</h2>'
 for task in data['tasks']:
  if task['status']==status:
   out+='<article><b>'+html.escape(task['id']+' · '+task['title'])+'</b><p>'+html.escape('; '.join(task['evidence']))+'</p><small>'+html.escape(task.get('blocker',''))+'</small></article>'
(R/'docs/extraction/KANBAN.html').write_text(out)
print(str(count)+'/10 extraction tasks complete')
