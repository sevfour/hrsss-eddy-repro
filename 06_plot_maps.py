"""Step 06: Remake Fig 2a and 2b for visual verification against the paper.

Two global maps of surface (10 m) salinity anomaly, RdBu_r, +/-0.3 pss, Robinson
projection -- matching the paper's colour scale.
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def panel(ax, lon, lat, data, title, vlim):
    ax.set_global()
    ax.add_feature(cfeature.LAND, facecolor="0.7", zorder=2)
    pm = ax.pcolormesh(lon, lat, data, cmap="RdBu_r", vmin=-vlim, vmax=vlim,
                       shading="auto", transform=ccrs.PlateCarree(), zorder=1)
    ax.set_title(title, fontsize=12)
    ax.coastlines(linewidth=0.4, zorder=3)
    return pm


def make(vlim=0.3, out_name="fig2ab_check.png", mask_below=None, lat_band=None,
         show_suptitle=True):
    ds = xr.open_dataset(C.ANOM_NC)
    lon, lat = ds["lon"].values, ds["lat"].values
    ae = ds["Sp_AE"].values
    ce = ds["Sp_CE"].values
    title = "Reproduction of Mo et al. (2024) Fig 2a/2b"
    sub_extra = ""
    if mask_below is not None:
        # blank bins whose |anomaly| is below the detection floor
        ae = np.where(np.abs(ae) >= mask_below, ae, np.nan)
        ce = np.where(np.abs(ce) >= mask_below, ce, np.nan)
        sub_extra = "\n|anomalies| > 0.2/√7 pss"
    if lat_band is not None:
        # blank everything outside the mid-latitude band
        lo, hi = lat_band
        keep = (np.abs(lat) >= lo) & (np.abs(lat) <= hi)
        ae = np.where(keep[:, None], ae, np.nan)
        ce = np.where(keep[:, None], ce, np.nan)
        title += f"\nmid-latitudes {lo}°–{hi}° N/S"

    fig, axes = plt.subplots(
        2, 1, figsize=(10, 9),
        subplot_kw=dict(projection=ccrs.Robinson(central_longitude=200)),
    )
    pm = panel(axes[0], lon, lat, ae,
               "a. Surface (10 m) salinity anomalies within anticyclonic eddies (AE)"
               + sub_extra, vlim)
    panel(axes[1], lon, lat, ce,
          "b. Surface (10 m) salinity anomalies within cyclonic eddies (CE)"
          + sub_extra, vlim)

    cbar = fig.colorbar(pm, ax=axes, orientation="vertical", shrink=0.7,
                        extend="both", pad=0.02)
    cbar.set_label("surface (10 m) salinity anomaly per 2°×2° bin (pss)")
    if show_suptitle:
        fig.suptitle(title, y=0.97)
    out = C.OUT / out_name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    make(vlim=0.3, out_name="fig2ab_check.png")


def main():  # backwards-compatible entry point
    make()
