"""Step 03: Read WOD files, apply QC, extract each profile's surface (<=10 m)
salinity. Output one row per qualified profile -> profiles_surf.parquet.

WOD NetCDF (ragged/"OSD-style") stores many casts per file. Layout varies by
platform but the ragged convention is: a per-cast list of counts
(`Salinity_row_size`) indexing into a flat `Salinity` / `z` value array, with
per-cast `lat`, `lon`, `time`. We handle that convention and fall back to any
CF-ragged structure with 'Salinity' + 'z'.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def _cast_times(ds, n):
    """Return pandas datetimes per cast, coping with WOD 'days since' time."""
    if "time" in ds:
        t = ds["time"].values
        try:
            return pd.to_datetime(t)
        except Exception:
            pass
    # WOD sometimes uses date (YYYYMMDD) integer
    for k in ("date", "Date"):
        if k in ds:
            return pd.to_datetime(ds[k].values.astype("int64").astype(str),
                                  format="%Y%m%d", errors="coerce")
    return pd.to_datetime(np.full(n, "NaT"))


def qc_and_surface(z, s):
    """Apply paper QC to one cast's depth/salinity arrays; return surface salinity
    (mean of samples <=10 m) or None if it fails QC."""
    m = np.isfinite(z) & np.isfinite(s)
    z, s = z[m], s[m]
    if z.size < C.QC_MIN_UNIQUE_UPPER200:
        return None
    order = np.argsort(z)
    z, s = z[order], s[order]
    if z.min() > C.QC_MIN_SHALLOW:          # need a sample shallower than 20 m
        return None
    if z.max() < C.QC_MIN_DEEP:             # need a sample deeper than 100 m
        return None
    upper = z <= 200.0
    if np.unique(z[upper]).size < C.QC_MIN_UNIQUE_UPPER200:
        return None
    # sampling-interval checks
    def max_gap(lo, hi):
        zz = z[(z >= lo) & (z <= hi)]
        return np.max(np.diff(zz)) if zz.size > 1 else np.inf
    if max_gap(0, 100) > C.QC_MAX_GAP_0_100:
        return None
    if max_gap(100, 200) > C.QC_MAX_GAP_100_200:
        return None
    surf = s[z <= C.SURFACE_MAX_DEPTH]
    if surf.size == 0:
        return None
    return float(np.nanmean(surf))


def _offsets(row_size):
    ends = np.cumsum(row_size)
    return ends - row_size, ends


def iter_casts(ds):
    """Yield (lat, lon, time, z_array, s_array) per cast from a WOD dataset.

    WOD ragged format: EACH variable has its own *_row_size and its own flat
    obs array. z and Salinity therefore have independent offsets. We pair them
    per cast only when the salinity level-count equals the z level-count
    (WOD reports salinity either at all z-levels of the cast or not at all).
    """
    if "Salinity" not in ds.variables or "Salinity_row_size" not in ds.variables:
        raise ValueError("no Salinity in this file")
    zvar = "z" if "z" in ds.variables else ("Depth" if "Depth" in ds.variables else None)
    if zvar is None or f"{zvar}_row_size" not in ds.variables:
        raise ValueError("no z/z_row_size in this file")

    s_rs = np.nan_to_num(ds["Salinity_row_size"].values, nan=0).astype("int64")
    z_rs = np.nan_to_num(ds[f"{zvar}_row_size"].values, nan=0).astype("int64")
    n = s_rs.size
    sal = ds["Salinity"].values
    z = ds[zvar].values
    lat = ds["lat"].values if "lat" in ds else ds["latitude"].values
    lon = ds["lon"].values if "lon" in ds else ds["longitude"].values
    times = _cast_times(ds, n)
    qflag = ds["Salinity_WODflag"].values if "Salinity_WODflag" in ds.variables else None

    z_start, _ = _offsets(z_rs)
    s_start, _ = _offsets(s_rs)
    for i in range(n):
        ns, nz = s_rs[i], z_rs[i]
        if ns == 0 or ns != nz:          # no salinity, or cannot align to z-levels
            continue
        za, sa = z_start[i], s_start[i]
        zi = z[za:za + nz].astype(float)
        si = sal[sa:sa + ns].astype(float)
        if qflag is not None:
            fi = qflag[sa:sa + ns]
            si = np.where(fi == 0, si, np.nan)  # keep only WOD-accepted (flag 0)
        yield float(lat[i]), float(lon[i]), times[i], zi, si


def process_file(path):
    rows = []
    try:
        ds = xr.open_dataset(path, decode_times=True)
    except Exception as e:
        print(f"  cannot open {path.name}: {e}", flush=True)
        return rows
    try:
        for lat, lon, t, zi, si in iter_casts(ds):
            if not (np.isfinite(lat) and np.isfinite(lon)) or pd.isna(t):
                continue
            surf = qc_and_surface(zi, si)
            if surf is None:
                continue
            rows.append((lat, ((lon + 180) % 360) - 180, pd.Timestamp(t), surf))
    except ValueError as e:
        print(f"  skip {path.name}: {e}", flush=True)
    finally:
        ds.close()
    return rows


def main():
    files = sorted(C.WOD_DIR.glob("wod_*.nc"))
    print(f"{len(files)} WOD files to process", flush=True)
    all_rows = []
    for i, f in enumerate(files, 1):
        r = process_file(f)
        all_rows.extend(r)
        print(f"[{i}/{len(files)}] {f.name}: +{len(r)} profiles "
              f"(total {len(all_rows)})", flush=True)
    df = pd.DataFrame(all_rows, columns=["lat", "lon", "time", "sss"])
    df = df.dropna()
    df.to_parquet(C.PROFILES_SURF)
    print(f"wrote {len(df)} profiles -> {C.PROFILES_SURF}", flush=True)


if __name__ == "__main__":
    main()
