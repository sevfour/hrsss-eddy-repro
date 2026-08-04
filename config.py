"""Shared configuration for the Mo et al. (2024) Fig 2a/2b reproduction.

Fig 2a = surface (10 m) salinity anomaly inside anticyclonic eddies (S'_AE)
Fig 2b = surface (10 m) salinity anomaly inside cyclonic eddies   (S'_CE)
on a 2x2 degree global grid, computed as (inside-eddy mean) - (background mean).
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WOD_DIR = DATA / "wod"
EDDY_DIR = DATA / "eddies"
OUT = ROOT / "out"
for d in (DATA, WOD_DIR, EDDY_DIR, OUT):
    d.mkdir(parents=True, exist_ok=True)

# intermediate products
PROFILES_SURF = OUT / "profiles_surf.parquet"   # step 03 output
TAGGED = OUT / "tagged.parquet"                  # step 04 output
ANOM_NC = OUT / "anomaly_grid.nc"                # step 05 output (S'_AE, S'_CE)

# ---------------------------------------------------------------- scope
# Paper: 1993-2019, all WOD platforms, global. Surface (top 10 m) only.
YEARS = list(range(1993, 2020))
PLATFORMS = ["ctd", "pfl", "osd", "xbt", "apb", "drb", "gld", "mrb"]

WOD_BASE = "https://www.ncei.noaa.gov/data/oceans/ncei/wod"

# ---------------------------------------------------------------- method params
SURFACE_MAX_DEPTH = 10.0   # m; "surface (10 m)" layer of Fig 2a/2b
GRID_RES = 2.0             # degrees (2x2 bins)

# QC thresholds (paper section 2)
QC_MIN_SHALLOW = 20.0      # must have a salinity sample shallower than 20 m
QC_MIN_DEEP = 100.0        # ... and one deeper than 100 m
QC_MIN_UNIQUE_UPPER200 = 10  # >=10 unique values in upper 200 m
QC_MAX_GAP_0_100 = 15.0    # max sampling interval 0-100 m
QC_MAX_GAP_100_200 = 25.0  # max sampling interval 100-200 m

# collocation (paper: d normalized by eddy radius R)
INTERIOR_DR = 1.0          # interior:  d < 1.0 * R
BACKGROUND_DR = 2.0        # background: d > 2.0 * R

# gridding: require enough profiles per 2x2 bin so a single outlier can't
# dominate a bin mean (suppresses ship-track stripes / brackish contamination)
MIN_INTERIOR = 10          # min interior profiles (per polarity) per bin
MIN_BACKGROUND = 10        # min background profiles per bin

# Loose physical-validity bound on surface salinity. NOT from the paper (the
# paper's QC is about vertical resolution + WOD accepted flags). This only
# removes non-physical values / fill values; it deliberately keeps genuinely
# fresh ocean (Arctic, tropical rain, marginal seas). Per-bin min-count above
# handles real outlier suppression.
SSS_VALID_MIN = 2.0
SSS_VALID_MAX = 42.0

# Equatorial exclusion band: the paper excludes eddies within 5S-5N (tropical
# instability waves, not mesoscale eddies) and blanks this band in Fig 2.
EQUATOR_BAND_DEG = 5.0

# equator exclusion is NOT applied to salinity anomalies in Fig 2
# (only eddy velocities in Fig 1 exclude 5S-5N).

# 2x2 grid edges / centers
import numpy as np
LON_EDGES = np.arange(-180, 180 + GRID_RES, GRID_RES)
LAT_EDGES = np.arange(-90, 90 + GRID_RES, GRID_RES)
LON_CENTERS = 0.5 * (LON_EDGES[:-1] + LON_EDGES[1:])
LAT_CENTERS = 0.5 * (LAT_EDGES[:-1] + LAT_EDGES[1:])
