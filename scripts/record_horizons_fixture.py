#!/usr/bin/env python3
"""Record per-site Sun/Earth JPL Horizons fixtures (requires network access)."""
from __future__ import annotations
import argparse, json, sys, requests
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.horizons_service import HorizonsService, HORIZONS_API_URL

SITES = {
    "shackleton": ("Shackleton Rim", -89.9, 0.0, 4.2),
    "malapert": ("Malapert Massif", -85.0, 0.0, 2.0),
    "connecting-ridge": ("Connecting Ridge", -89.0, 35.0, 1.5),
    "de-gerlache": ("de Gerlache Rim", -88.0, 35.0, 2.0),
    "haworth": ("Haworth Rim", -87.5, 15.0, 2.0),
}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sites', nargs='+', choices=SITES, default=list(SITES))
    ap.add_argument('--start', default='2026-11-14 12:00', help='UTC, YYYY-MM-DD HH:MM')
    ap.add_argument('--stop', default='2026-11-20 12:00', help='UTC, YYYY-MM-DD HH:MM')
    ap.add_argument('--step-hours', type=int, default=6)
    ap.add_argument('--output-dir', default='backend/data/fixtures/horizons')
    args=ap.parse_args()
    start=datetime.strptime(args.start,'%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    stop=datetime.strptime(args.stop,'%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True)
    service=HorizonsService()
    for key in args.sites:
        name,lat,lon,elev=SITES[key]
        kwargs=dict(lat=lat,lon=lon,elevation_km=elev,start_time_utc=start,stop_time_utc=stop,step_hours=args.step_hours)
        def query(target):
            params=service.build_query_params(target_id=target,**kwargs)
            response=requests.get(HORIZONS_API_URL,params=params,timeout=45,headers={'Accept':'application/json'})
            response.raise_for_status()
            raw=response.json().get('result','')
            service.parse_horizons_csv(raw)  # validate returned CSV before saving
            return {'status_code':response.status_code,'result':raw}
        sun=query('10'); earth=query('399')
        payload={'metadata':{'source':'NASA/JPL Horizons API; recorded by scripts/record_horizons_fixture.py','url':'https://ssd-api.jpl.nasa.gov/horizons.api','documentation':'https://ssd.jpl.nasa.gov/horizons/manual.html','retrieved_at_utc':datetime.now(timezone.utc).isoformat(),'site':name,'coordinates':{'lat_deg':lat,'lon_deg':lon,'elevation_km':elev},'time_window':{'start_utc':args.start,'stop_utc':args.stop,'step_hours':args.step_hours},'reference_frame':'airless apparent topocentric azimuth/elevation','quantities':'apparent azimuth/elevation'},'sun_query':sun,'earth_query':earth}
        path=out/f'{key}.json'; path.write_text(json.dumps(payload,indent=2),encoding='utf-8'); print(path)
if __name__=='__main__': main()
