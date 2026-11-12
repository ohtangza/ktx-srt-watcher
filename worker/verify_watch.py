"""Read-only schedule validation; never logs routes, dates, times or credentials."""
import json, os
from pathlib import Path
from datetime import datetime
from . import remote
from .adapters.korail import KorailProvider, _build_passengers, _fmt_time
from .models import Watch
from .logsafe import wid

def main():
    cfg=remote.fetch_config() or {}; state=remote.fetch_state()
    p=KorailProvider(state.get('korail_device_profile'),state.get('korail_android_id'))
    p.login(os.environ['KORAIL_ID'],os.environ['KORAIL_PW'])
    private_results=[]
    for raw in cfg.get('watches',[]):
        w=Watch.model_validate(raw)
        if not w.active: continue
        rows=p._client.trains.search(w.from_,w.to,depart_after=datetime.fromisoformat(w.date+'T'+w.time_min),passengers=_build_passengers(w.passengers),include_no_seats=True)
        matches=[r for r in rows if w.time_min<=_fmt_time(r.dep_time)<=w.time_max]
        accepted=[r for r in matches if r.train_type_name in w.train_types]
        def minutes(t):
            h,m=(str(t) if ':' in str(t) else _fmt_time(t)).split(':')[:2]; return int(h)*60+int(m)
        eligible=[r for r in rows if r.train_type_name in w.train_types]
        next_offset=min((minutes(r.dep_time)-minutes(w.time_min) for r in eligible),default=None)
        durations=[(minutes(r.arr_time)-minutes(r.dep_time))%1440 for r in accepted]
        private_results.append({'watch':raw,'candidates':[{'train_no':str(r.train_no),'type':r.train_type_name,'departure':_fmt_time(r.dep_time),'arrival':_fmt_time(r.arr_time),'general_available':r.has_general_seat(),'special_available':r.has_special_seat()} for r in eligible[:3]]})
        print(json.dumps({'watch':wid(w.id),'active':w.active,'auto_reserve':w.auto_reserve,'window_matches':len(matches),'accepted_matches':len(accepted),'next_eligible_offset_min':next_offset,'matched_duration_min':durations,'matched_types':sorted({r.train_type_name for r in matches}),'available_matches':sum(r.has_general_seat() or r.has_special_seat() for r in accepted)},ensure_ascii=False))
    out=Path.home()/'actions-runner-ktx'/'last-timetable-check.json'
    out.write_text(json.dumps(private_results,ensure_ascii=False,indent=2))
    out.chmod(0o600)
if __name__=='__main__': main()
