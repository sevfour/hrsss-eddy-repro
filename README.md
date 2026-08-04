# hrsss-eddy-repro

Reproduction and extension of Mo et al. (2024), *A Global Assessment of
Eddy-Induced Salinity Anomalies and Salt Transport by Eddy Movement* (JGR
Oceans), assessing how much of the eddy-induced surface salinity signal a
high-resolution SSS mission could resolve.

Fig 2a/2b target: surface (10 m) salinity anomaly inside anticyclonic (S'_AE)
and cyclonic (S'_CE) eddies on a 2°×2° global grid, computed as
(inside-eddy mean) − (background mean).

## Pipeline

Scripts run in numbered order; each reads/writes intermediate products under
`out/` (see `config.py`).

| Step | Script | Purpose |
|------|--------|---------|
| 01 | `01_download_wod.py` / `01b_parallel_wod.py` | Download World Ocean Database NetCDF profiles (resumable) |
| 02 | `02_download_eddies.py` / `02b_chunked_download.py` | Download mesoscale eddy trajectory atlas |
| 03 | `03_extract_surface.py` | Subset profiles to the top 10 m |
| 04 | `04_collocate.py` | Tag each profile as eddy-interior (d<R) or background (d>2R) via nearest same-day eddy |
| 05 | `05_gridded_anomaly.py` | Compute gridded inside-minus-background salinity anomalies |
| 06 | `06_plot_maps.py` | Map figures (Fig 2a/2b analogues) |
| 07 | `07_histogram.py` / `08_histogram_combined.py` | Anomaly-magnitude histograms |

## Mission-relevance notes

- Eddy time scale ~30 days → decorrelation ~7 days (÷4 to resolve a period).
- Individual measurement accuracy: 0.2 pss.
- Resolvable fraction = % of |salinity anomalies| > 0.2/√7.
- Mean anomaly magnitude ≈ 0.113 psu ≈ 0.2/3 → resolved in ~3 days, better than
  the 7-day eddy decorrelation scale.
- Threshold accuracy for the mission concept: √7 × 0.113 ≈ 0.3 psu (0.2 psu baseline).

## Local-only

`data/` (inputs) and `out/` (intermediate products, figures) are gitignored and
stay local.
