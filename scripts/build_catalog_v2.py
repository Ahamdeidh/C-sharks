#!/usr/bin/env python3
"""Build catalog v2 from Illumination_Modeling + PSR_Volatile_Estimates (+ existing site points).
Usage: python build_catalog_v2.py ILLUM_ROOT PSR_ROOT SITES_JSON OUT_JSON
Needs: numpy, tifffile. Raster values = consecutive 12-h increments (days = value/2)."""
import sys, os, re, glob, json, math, struct, collections
import numpy as np, tifffile
R = 1737400.0
illum_root, psr_root, sites_json, out_json = sys.argv[1:5]

def fwd(lat, lon):
    rho = 2*R*math.tan(math.radians(90+lat)/2); l = math.radians(lon)
    return rho*math.sin(l), rho*math.cos(l)
def inv(x, y):
    rho = math.hypot(x, y); return -90+math.degrees(2*math.atan(rho/(2*R))), math.degrees(math.atan2(x, y))

# ---- rasters
prods, arrays, extents = [], {}, {}
for f in sorted(glob.glob(os.path.join(illum_root, '**', '*.tif*'), recursive=True)):
    if f.endswith('.xml'): continue
    b = os.path.basename(f); m = re.match(r'(.+?)_MaxConsecDaysOfSun(\+Earth)?_Midsummer(\d{4})GT', b)
    if not m: continue
    area, earth, year = m.group(1), bool(m.group(2)), int(m.group(3))
    pg = tifffile.TiffFile(f).pages[0]; a = pg.asarray(); ps = pg.tags['ModelPixelScaleTag'].value[0]
    tp = pg.tags['ModelTiepointTag'].value; h, w = a.shape
    ext = [tp[3], tp[4]-h*ps, tp[3]+w*ps, tp[4]]  # xmin,ymin,xmax,ymax (m)
    measure = 'sun_plus_earth' if earth else 'sun_only'
    arrays[(area, measure, year)] = (a, ext, ps); extents[area] = ext
    d = a.astype(float)/2.0
    prods.append(dict(file=b, area=area, year=year, measure=measure, width=w, height=h, pixel_size_m=ps,
        extent_xy_m=[round(v, 1) for v in ext],
        days=dict(max=float(d.max()), mean=round(float(d.mean()), 3), median=float(np.median(d)),
                  p90=float(np.percentile(d, 90)), frac_pixels_gt0=round(float((a > 0).mean()), 4))))

# ---- areas summary (per area/measure: multi-year mean of the per-year mean)
areas = {}
for area in sorted(extents):
    ser = {}
    for meas in ('sun_only', 'sun_plus_earth'):
        yrs = sorted(y for (a, m, y) in arrays if a == area and m == meas)
        if yrs:
            ser[meas] = dict(years=yrs, mean_days_by_year=[next(p['days']['mean'] for p in prods if p['area']==area and p['measure']==meas and p['year']==y) for y in yrs])
            ser[meas]['mean_days_all_years'] = round(float(np.mean(ser[meas]['mean_days_by_year'])), 3)
    x0, y0, x1, y1 = extents[area]; lat, lon = inv((x0+x1)/2, (y0+y1)/2)
    areas[area] = dict(extent_xy_m=[round(v, 1) for v in extents[area]], center_lat_lon=[round(lat, 3), round(lon, 3)], series=ser)

# ---- cross-check: site-point attributes vs raster pixel (value/2) incl. 2 km max
sites = json.load(open(sites_json))['features']; chk = collections.defaultdict(list)
for ft in sites:
    p = ft['properties']; x, y = fwd(float(p['Latitude']), float(p['Longitude']))
    for area, (x0, y0, x1, y1) in extents.items():
        if not (x0 <= x <= x1 and y0 <= y <= y1): continue
        for key, (a, ext, ps) in arrays.items():
            if key[0] != area: continue
            yy = key[2]; attr = p.get(('SunDays' if key[1] == 'sun_only' else 'SunEarth') + str(yy-2000)) if yy != 25 or key[1] == 'sun_only' else p.get('Sun_Earth2')
            if attr is None: continue
            c, r = int((x-ext[0])/ps), int((ext[3]-y)/ps); rad = int(2000/ps)
            win = a[max(0, r-rad):r+rad+1, max(0, c-rad):c+rad+1]
            chk[key[1]].append((float(attr), float(a[r, c])/2, float(win.max())/2))
validation = {}
for meas, rows in chk.items():
    arr = np.array(rows)
    validation[meas] = dict(n=len(rows), attr_equals_pixel_pct=round(100*float((arr[:,0]==arr[:,1]).mean()), 1),
        attr_equals_2km_max_pct=round(100*float((arr[:,0]==arr[:,2]).mean()), 1),
        mean_abs_diff_vs_pixel=round(float(np.abs(arr[:,0]-arr[:,1]).mean()), 2),
        mean_abs_diff_vs_2km_max=round(float(np.abs(arr[:,0]-arr[:,2]).mean()), 2))

# ---- sun_plus_earth vs sun_only logical check
cmp = []
for (area, meas, yr), (a, ext, ps) in arrays.items():
    if meas == 'sun_plus_earth' and (area, 'sun_only', yr) in arrays:
        s = arrays[(area, 'sun_only', yr)][0]; cmp.append(float((a > s).mean()))
sun_earth_check = dict(pairs=len(cmp), mean_fraction_pixels_where_sun_plus_earth_exceeds_sun_only=round(float(np.mean(cmp)), 4))

# ---- PSR polygons (minimal .shp polygon reader)
def read_dbf(p):
    f = open(p, 'rb').read(); n, hl, rl = struct.unpack('<xxxxIHH', f[:12]); fl = []; o = 32
    while f[o] != 0x0D: fl.append((f[o:o+11].split(b'\0')[0].decode(), f[o+16])); o += 32
    out = []
    for i in range(n):
        r = f[hl+i*rl+1:hl+(i+1)*rl]; d = {}; q = 0
        for nm, l in fl:
            v = r[q:q+l].decode('latin1').strip(); q += l
            try: v = float(v)
            except: pass
            d[nm] = v
        out.append(d)
    return out
def read_shp(p):
    f = open(p, 'rb').read(); o = 100; out = []
    while o < len(f):
        clen = struct.unpack('>i', f[o+4:o+8])[0]*2; rec = f[o+8:o+8+clen]; o += 8+clen
        if struct.unpack('<i', rec[:4])[0] != 5: out.append(None); continue
        bb = struct.unpack('<4d', rec[4:36]); npart, npts = struct.unpack('<2i', rec[36:44])
        parts = struct.unpack('<%di' % npart, rec[44:44+4*npart]); q = 44+4*npart
        pts = np.frombuffer(rec[q:q+16*npts], '<f8').reshape(-1, 2); ring = pts[parts[0]:(parts[1] if npart > 1 else npts)]
        x, y = ring[:, 0], ring[:, 1]; cr = x*np.roll(y, -1)-np.roll(x, -1)*y; A = cr.sum()/2
        cx = ((x+np.roll(x, -1))*cr).sum()/(6*A) if A else x.mean(); cy = ((y+np.roll(y, -1))*cr).sum()/(6*A) if A else y.mean()
        out.append(dict(bbox=bb, centroid=(float(cx), float(cy)), geom_area_m2=float(abs(A))))
    return out
psr_dbf = glob.glob(os.path.join(psr_root, '**', 'PSR_volatile_abundance_final.dbf'), recursive=True)[0]
recs, geoms = read_dbf(psr_dbf), read_shp(psr_dbf[:-4]+'.shp')
keep = ['Id_1', 'meanAge', 'SW_10per', 'SW_30per', 'MM_10per', 'MM_30per', 'Com_low', 'Com_high', 'Asteroids',
        'Influx_low', 'Influx_hig', 'PS_1wt', 'IV_1wt', 'MEAN', 'Sub_Esat', 'Sub_loss', 'Volatiles_', 'Volatiles1', 'Rego_Thick', 'Reg_Th_max', 'Reg_T_56wt']
psr = []
for r, g in zip(recs, geoms):
    if not g: continue
    cx, cy = g['centroid']; lat, lon = inv(cx, cy)
    inside = [a for a, (x0, y0, x1, y1) in extents.items() if x0 <= cx <= x1 and y0 <= cy <= y1]
    psr.append(dict(id=r.get('Id_1'), centroid_xy_m=[round(cx, 1), round(cy, 1)], lat_lon=[round(lat, 3), round(lon, 3)],
                    geom_area_m2=round(g['geom_area_m2'], 1), shape_area_field=r.get('Shape_Area'), areas_containing_centroid=inside,
                    fields={k: r.get(k) for k in keep}))
for a in areas: areas[a]['psr_polygons_in_extent'] = sum(1 for p in psr if a in p['areas_containing_centroid'])

out = dict(title='Lunar South Pole Illumination + PSR Reference Catalog v2', version='2.0',
    crs='Moon 2000 south-pole stereographic (R=1,737,400 m); xy in metres', units_note='days = raster value / 2 (raster counts 12-h increments, per supplied READ_ME)',
    provenance_warning='User-supplied archives; primary upstream provenance and field definitions NOT verified. Do not label as NASA-authored without confirmation.',
    counts=dict(rasters=len(prods), areas=len(areas), psr_polygons=len(psr)),
    validation_vs_site_point_attributes=validation, sun_plus_earth_vs_sun_only=sun_earth_check,
    areas=areas, raster_products=prods, psr_polygons=psr)
json.dump(out, open(out_json, 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out['counts']), json.dumps(validation), json.dumps(sun_earth_check))
