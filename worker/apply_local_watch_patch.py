"""Apply a locally authorized, privately stored watch patch after validation."""
import json, os, urllib.request
from pathlib import Path
from . import remote
from .adapters.korail import KorailProvider
from .models import Watch

def main():
    folder=Path.home()/'actions-runner-ktx'
    patches=json.loads((folder/'authorized-watch-patch.json').read_text())
    checked={r['watch']['id']:r for r in json.loads((folder/'last-timetable-check.json').read_text())}
    cfg=remote.fetch_config(); original=json.dumps(cfg,ensure_ascii=False)
    state=remote.fetch_state(); p=KorailProvider(state.get('korail_device_profile'),state.get('korail_android_id'))
    p.login(os.environ['KORAIL_ID'],os.environ['KORAIL_PW'])
    existing=p.existing_reservation_keys()
    if existing is None: raise RuntimeError('Existing ticket/hold lookup unavailable; no settings changed')
    for patch in patches:
        current=next(w for w in cfg['watches'] if w['id']==patch['id'])
        record=checked[patch['id']]
        if current!=record['watch']: raise RuntimeError('Watch changed since validation')
        changes=patch['changes']
        if set(changes)-{'time_min','time_max','allowed_departures','allowed_train_nos','auto_reserve','active'}: raise RuntimeError('Unsupported setting change')
        verified={(r['departure'],r['train_no']) for r in record['candidates']}
        if not all(any((t,n) in verified for t in changes['allowed_departures']) for n in changes['allowed_train_nos']): raise RuntimeError('Train was not verified')
        current.update(changes);Watch.model_validate(current)
    cfg.setdefault('settings',{})['allow_waiting_list']=False
    base='https://api.cloudflare.com/client/v4/accounts/'+os.environ['CF_ACCOUNT_ID']+'/storage/kv/namespaces/'+os.environ['CF_STATE_NAMESPACE']+'/values/'
    def put(key,value):
        req=urllib.request.Request(base+key,data=value.encode(),method='PUT',headers={'Authorization':'Bearer '+os.environ['CLOUDFLARE_API_TOKEN'],'Content-Type':'text/plain'})
        with urllib.request.urlopen(req,timeout=30) as response: result=json.load(response)
        if not result.get('success'): raise RuntimeError('KV write failed')
    put('config:before-authorized-update',original)
    put('config',json.dumps(cfg,ensure_ascii=False))
    out=folder/'last-watch-update.json';out.write_text(json.dumps(cfg,ensure_ascii=False,indent=2));out.chmod(0o600)
if __name__=='__main__':main()
