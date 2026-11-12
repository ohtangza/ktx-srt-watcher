"""Read-only schedule validation; never logs routes, dates, times or credentials."""
import json, os
from datetime import datetime
from . import remote
from .adapters.korail import KorailProvider, _build_passengers, _fmt_time
from .models import Watch
from .logsafe import wid

def main():
    cfg=remote.fetch_config() or {}; state=remote.fetch_state()
    p=KorailProvider(state.get('korail_device_profile'),state.get('korail_android_id'))
    p.login(os.environ['KORAIL_ID'],os.environ['KORAIL_PW'])
    for raw in cfg.get('watches',[]):
        w=Watch.model_validate(raw)
        if not w.active: continue
        rows=p._client.trains.search(w.from_,w.to,depart_after=datetime.fromisoformat(w.date+'T'+w.time_min),passengers=_build_passengers(w.passengers),include_no_seats=True)
        matches=[r for r in rows if w.time_min<=_fmt_time(r.dep_time)<=w.time_max]
        accepted=[r for r in matches if r.train_type_name in w.train_types]
        print(json.dumps({'watch':wid(w.id),'active':w.active,'auto_reserve':w.auto_reserve,'window_matches':len(matches),'accepted_matches':len(accepted),'matched_types':sorted({r.train_type_name for r in matches}),'available_matches':sum(r.has_general_seat() or r.has_special_seat() for r in accepted)},ensure_ascii=False))
if __name__=='__main__': main()
