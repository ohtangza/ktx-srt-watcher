"""Extend a validated watch by at most one minute; no reservation or payment."""
import json, os, urllib.request
from pathlib import Path
from . import remote

def main():
    checked=json.loads((Path.home()/'actions-runner-ktx'/'last-timetable-check.json').read_text())
    cfg=remote.fetch_config()
    original=json.dumps(cfg,ensure_ascii=False)
    changed=0
    def minute(t):
        h,m=map(int,t.split(':')); return h*60+m
    for rec in checked:
        old=rec['watch']; candidates=rec['candidates']
        if not candidates: continue
        target=next((w for w in cfg['watches'] if w['id']==old['id']),None)
        if target!=old: raise RuntimeError('Watch changed since validation; refusing overwrite')
        first=candidates[0]['departure']
        if minute(first)-minute(old['time_max'])==1:
            if old.get('auto_reserve'): raise RuntimeError('Reservation-enabled watch cannot be adjusted')
            target['time_max']=first; changed+=1
    if changed!=1: raise RuntimeError('Expected exactly one one-minute adjustment')
    base='https://api.cloudflare.com/client/v4/accounts/'+os.environ['CF_ACCOUNT_ID']+'/storage/kv/namespaces/'+os.environ['CF_STATE_NAMESPACE']+'/values/'
    def put(key,value):
        req=urllib.request.Request(base+key,data=value.encode(),method='PUT',headers={'Authorization':'Bearer '+os.environ['CLOUDFLARE_API_TOKEN'],'Content-Type':'text/plain'})
        with urllib.request.urlopen(req,timeout=30) as response:
            result=json.load(response)
        if not result.get('success'): raise RuntimeError('KV update failed')
    put('config:before-one-minute-adjustment',original)
    put('config',json.dumps(cfg,ensure_ascii=False))
    out=Path.home()/'actions-runner-ktx'/'watch-adjustment.json'
    out.write_text(json.dumps({'updated':changed,'config':cfg},ensure_ascii=False,indent=2));out.chmod(0o600)
if __name__=='__main__':main()
