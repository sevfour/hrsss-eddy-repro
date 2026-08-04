"""Step 04: Collocate each surface profile with the nearest eddy observed on the
same day, following Mo et al. (2024) sec. 2.

For each profile:
  - gather all eddy observations (both polarities) on the profile's date
  - find the nearest eddy center (great-circle distance)
  - d/R = distance / eddy effective radius
  - tag: 'interior' if d < R (record polarity AE/CE); 'background' if d > 2R
  - discard the annulus R <= d <= 2R

Efficiency: eddies are indexed by day; per day a cKDTree is built in a local
azimuthal-equidistant-ish scaling (deg lon scaled by cos(lat)) for fast NN,
then the true great-circle distance is computed for the candidate.

Output: tagged.parquet with columns lat, lon, time, sss, klass, polarity.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

R_EARTH_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R_EARTH_KM * np.arcsin(np.sqrt(a))


def load_eddies():
    """Load META3.1exp eddy observations into a DataFrame:
    time(date), lon(-180..180), lat, radius_km, polarity(AE/CE)."""
    frames = []
    for f in sorted(C.EDDY_DIR.glob("*.nc")):
        polarity = ("AE" if "nticyclon" in f.name else
                    "CE" if "yclon" in f.name else None)
        if polarity is None:
            continue
        ds = xr.open_dataset(f)
        # variable-name flexibility across META versions
        def pick(*names):
            return next((n for n in names if n in ds.variables), None)
        vlon = pick("longitude", "lon")
        vlat = pick("latitude", "lat")
        vtime = pick("time")
        # Paper defines R as the radius of the maximum circum-average speed
        # contour -> speed_radius (fall back to effective_radius / other names).
        vrad = pick("speed_radius", "effective_radius", "radius_effective",
                    "effective_contour_radius", "radius")
        lon = ((ds[vlon].values + 180) % 360) - 180
        lat = ds[vlat].values
        time = pd.to_datetime(ds[vtime].values).normalize()
        rad = ds[vrad].values.astype(float)
        # META radii are in metres -> km
        if np.nanmedian(rad) > 1000:
            rad = rad / 1000.0
        frames.append(pd.DataFrame(
            {"time": time, "lon": lon, "lat": lat, "radius_km": rad,
             "polarity": polarity}))
        ds.close()
        print(f"  loaded {len(frames[-1])} {polarity} eddy-obs from {f.name}",
              flush=True)
    if not frames:
        raise SystemExit("No eddy files found in data/eddies/. Run step 02.")
    return pd.concat(frames, ignore_index=True)


def main():
    prof = pd.read_parquet(C.PROFILES_SURF).reset_index(drop=True)
    prof["date"] = pd.to_datetime(prof["time"]).dt.normalize()
    eddies = load_eddies()
    eddies["date"] = eddies["time"]

    eddy_by_day = {d: g for d, g in eddies.groupby("date")}
    print(f"{len(prof)} profiles, {len(eddies)} eddy-obs, "
          f"{len(eddy_by_day)} eddy-days", flush=True)

    klass = np.full(len(prof), "", dtype=object)
    polar = np.full(len(prof), "", dtype=object)

    # positional groups: index labels are 0..N-1 after reset_index
    for d, pos in prof.groupby("date").groups.items():
        eg = eddy_by_day.get(d)
        if eg is None or len(eg) == 0:
            continue
        pos = np.asarray(pos)                 # positional row indices into prof
        pg = prof.iloc[pos]
        # scaled planar coords for KD-tree (cos-lat correction at mean lat)
        clat = np.cos(np.radians(eg["lat"].values.mean()))
        tree = cKDTree(np.c_[eg["lon"].values * clat, eg["lat"].values])
        q = np.c_[pg["lon"].values * clat, pg["lat"].values]
        _, nn = tree.query(q, k=1)
        e_near = eg.iloc[nn]
        dist = haversine_km(pg["lat"].values, pg["lon"].values,
                            e_near["lat"].values, e_near["lon"].values)
        dr = dist / e_near["radius_km"].values
        interior = dr < C.INTERIOR_DR
        background = dr > C.BACKGROUND_DR
        klass[pos[interior]] = "interior"
        klass[pos[background]] = "background"
        polar[pos[interior]] = e_near["polarity"].values[interior]

    prof["klass"] = klass
    prof["polarity"] = polar
    tagged = prof[prof["klass"] != ""].copy()
    tagged.to_parquet(C.TAGGED)
    print(f"tagged {len(tagged)} profiles "
          f"(interior={np.sum(klass=='interior')}, "
          f"background={np.sum(klass=='background')}) -> {C.TAGGED}", flush=True)


if __name__ == "__main__":
    main()
