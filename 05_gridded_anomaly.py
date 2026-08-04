"""Step 05: Grid the tagged profiles onto a 2x2 deg grid and compute the surface
salinity anomalies of Fig 2a/2b:

  S_BG(x,y) = mean SSS of background profiles in bin
  S_AE(x,y) = mean SSS of interior AE profiles in bin
  S_CE(x,y) = mean SSS of interior CE profiles in bin
  S'_AE = S_AE - S_BG      (Fig 2a)
  S'_CE = S_CE - S_BG      (Fig 2b)

Saves anomaly_grid.nc with S'_AE, S'_CE and the profile counts per bin.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def bin_mean(df, value="sss", min_count=1):
    """Mean of `value` per 2x2 bin -> (nlat, nlon) array + count.
    Bins with fewer than `min_count` samples are set to NaN so a single
    outlier profile cannot define a bin."""
    ix = np.digitize(df["lon"].values, C.LON_EDGES) - 1
    iy = np.digitize(df["lat"].values, C.LAT_EDGES) - 1
    nlon = C.LON_CENTERS.size
    nlat = C.LAT_CENTERS.size
    ok = (ix >= 0) & (ix < nlon) & (iy >= 0) & (iy < nlat)
    ix, iy, val = ix[ok], iy[ok], df[value].values[ok]
    ssum = np.zeros((nlat, nlon))
    cnt = np.zeros((nlat, nlon))
    np.add.at(ssum, (iy, ix), val)
    np.add.at(cnt, (iy, ix), 1.0)
    mean = np.divide(ssum, cnt, out=np.full_like(ssum, np.nan),
                     where=cnt >= min_count)
    return mean, cnt


def main():
    df = pd.read_parquet(C.TAGGED)
    # Loose physical-validity bound only (removes fill values / non-physical
    # spikes). Keeps genuinely fresh ocean; the paper imposes no salinity-value
    # cut, so this stays wide and lets the per-bin min-count do the real work.
    n0 = len(df)
    df = df[(df["sss"] >= C.SSS_VALID_MIN) & (df["sss"] <= C.SSS_VALID_MAX)]
    print(f"salinity validity filter [{C.SSS_VALID_MIN},{C.SSS_VALID_MAX}] psu: "
          f"kept {len(df)}/{n0}")

    # Equatorial band excluded (tropical instability waves, per paper).
    nb = len(df)
    df = df[df["lat"].abs() >= C.EQUATOR_BAND_DEG]
    print(f"equator band |lat|<{C.EQUATOR_BAND_DEG} excluded: kept {len(df)}/{nb}")

    bg = df[df["klass"] == "background"]
    ae = df[(df["klass"] == "interior") & (df["polarity"] == "AE")]
    ce = df[(df["klass"] == "interior") & (df["polarity"] == "CE")]

    S_bg, n_bg = bin_mean(bg, min_count=C.MIN_BACKGROUND)
    S_ae, n_ae = bin_mean(ae, min_count=C.MIN_INTERIOR)
    S_ce, n_ce = bin_mean(ce, min_count=C.MIN_INTERIOR)

    Sp_ae = S_ae - S_bg
    Sp_ce = S_ce - S_bg

    ds = xr.Dataset(
        data_vars=dict(
            Sp_AE=(("lat", "lon"), Sp_ae),
            Sp_CE=(("lat", "lon"), Sp_ce),
            S_bg=(("lat", "lon"), S_bg),
            n_bg=(("lat", "lon"), n_bg),
            n_AE=(("lat", "lon"), n_ae),
            n_CE=(("lat", "lon"), n_ce),
        ),
        coords=dict(lat=C.LAT_CENTERS, lon=C.LON_CENTERS),
        attrs=dict(
            title="Eddy-induced surface salinity anomaly (Mo et al. 2024 Fig 2a/2b)",
            surface_max_depth_m=C.SURFACE_MAX_DEPTH,
            grid_res_deg=C.GRID_RES,
        ),
    )
    ds.to_netcdf(C.ANOM_NC)

    def stats(name, a):
        v = a[np.isfinite(a)]
        print(f"  {name}: bins={v.size}, mean={v.mean():+.3f}, "
              f"median={np.median(v):+.3f}, std={v.std():.3f}, "
              f"[{v.min():+.2f},{v.max():+.2f}] psu")

    print(f"wrote {C.ANOM_NC}")
    print(f"populated bins: AE={np.sum(np.isfinite(Sp_ae))}, "
          f"CE={np.sum(np.isfinite(Sp_ce))} of {Sp_ae.size}")
    stats("S'_AE (Fig2a)", Sp_ae)
    stats("S'_CE (Fig2b)", Sp_ce)


if __name__ == "__main__":
    main()
