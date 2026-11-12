from types import SimpleNamespace
from unittest.mock import Mock, patch
from worker.models import Watch
from worker.adapters.korail import KorailProvider
from worker import reservations

def watch():
    return Watch(id='test',provider='korail',**{'from':'A','to':'B'},date='2099-01-01',time_min='10:43',time_max='10:50',train_types=['KTX'],allowed_departures=['10:43','10:50'],allowed_train_nos=['1','3'],auto_reserve=True)

def test_exact_departures_exclude_intermediate_train():
    p=KorailProvider()
    rows=[SimpleNamespace(dep_time=t,arr_time='120000',train_no=n,train_type_name='KTX',dep_name='A',arr_name='B',has_general_seat=lambda:True,has_special_seat=lambda:False) for n,t in [('1','104300'),('2','104600'),('3','105000')]]
    p._client=SimpleNamespace(trains=SimpleNamespace(search=lambda *a,**k:rows))
    assert [r.train_no for r in p.search(watch())]==['1','3']

def test_existing_alternative_blocks_new_hold():
    p=SimpleNamespace(existing_reservation_keys=lambda:{'3|20990101'})
    with patch.object(reservations,'_reserve_first') as reserve:
        reservations.try_auto_reserve(watch(),p,{},[])
        reserve.assert_not_called()

def test_unavailable_existing_lookup_fails_closed():
    p=SimpleNamespace(existing_reservation_keys=lambda:None)
    with patch.object(reservations,'_reserve_first') as reserve:
        reservations.try_auto_reserve(watch(),p,{},[])
        reserve.assert_not_called()

def test_confirmed_no_existing_hold_allows_one_attempt_group():
    p=SimpleNamespace(existing_reservation_keys=lambda:set())
    with patch.object(reservations,'_reserve_first',return_value=(None,None,None)) as reserve:
        reservations.try_auto_reserve(watch(),p,{},[])
        reserve.assert_called_once()
