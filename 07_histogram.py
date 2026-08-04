"""Step 07: The deliverable -- distribution histogram of the 2x2 deg gridded
surface salinity-anomaly values from Fig 2a (AE) and Fig 2b (CE), overlaid.
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def make(lat_band=None, out_name="fig2_histogram.png"):
    ds = xr.open_dataset(C.ANOM_NC)
    ae2d = ds["Sp_AE"].values
    ce2d = ds["Sp_CE"].values
    title_extra = ""
    if lat_band is not None:
        lo, hi = lat_band
        # keep only rows with |lat| in [lo, hi]
        latmask = (np.abs(ds["lat"].values) >= lo) & (np.abs(ds["lat"].values) <= hi)
        ae2d = ae2d[latmask, :]
        ce2d = ce2d[latmask, :]
        title_extra = f"\nmid-latitudes {lo}°–{hi}° N/S"
    ae = ae2d.ravel()
    ce = ce2d.ravel()
    ae = ae[np.isfinite(ae)]
    ce = ce[np.isfinite(ce)]

    # Detection floor for the eddy-mean anomaly: daily 0.2 pss single-snapshot
    # accuracy beaten down by sampling over the 7-day eddy decorrelation time
    # (7 independent daily looks) -> 0.2/sqrt(7).
    SSS_ACC = 0.2
    N_LOOKS = 7
    thr = SSS_ACC / np.sqrt(N_LOOKS)

    ae_det = np.mean(np.abs(ae) > thr) * 100
    ce_det = np.mean(np.abs(ce) > thr) * 100

    # Red (AE) + blue (CE); alpha-composited overlap reads as purple (~#8269B9).
    # Also physically intuitive: red = salty/positive, blue = fresh/negative,
    # matching the AE/CE sign convention and the RdBu maps.
    AE_COLOR = "#E23B3B"
    CE_COLOR = "#1E3AE0"

    bins = np.linspace(-0.5, 0.5, 61)  # 1/60 pss resolution
    fig, ax = plt.subplots(figsize=(8, 5))
    nae, _, _ = ax.hist(ae, bins=bins, alpha=0.6, color=AE_COLOR, density=False,
            label=(f"AE: mean {ae.mean():+.3f}, median {np.median(ae):+.3f}, "
                   f"std {ae.std():.3f}\n"
                   f"       {ae_det:.1f}% of |anomalies| > 0.2/√{N_LOOKS} pss"))
    nce, _, _ = ax.hist(ce, bins=bins, alpha=0.6, color=CE_COLOR, density=False,
            label=(f"CE: mean {ce.mean():+.3f}, median {np.median(ce):+.3f}, "
                   f"std {ce.std():.3f}\n"
                   f"       {ce_det:.1f}% of |anomalies| > 0.2/√{N_LOOKS} pss"))
    ax.axvline(0, color="k", lw=0.8, ls="--")
    # detection-floor lines at +/- 0.2/sqrt(7) pss
    ax.axvline(-thr, color="crimson", lw=1.4, ls="-")
    ax.axvline(thr, color="crimson", lw=1.4, ls="-")
    ymax = max(nae.max(), nce.max())
    ax.text(thr + 0.01, ymax * 0.98,
            f"±0.2/√{N_LOOKS} = ±{thr:.3f} pss", color="crimson",
            ha="left", va="bottom", fontsize=8)

    ax.set_xlabel("surface (10 m) salinity anomaly per 2°×2° bin (pss)")
    ax.set_ylabel("number of grid bins")
    ax.set_title("Distribution of eddy-induced surface salinity anomalies\n"
                 "(based on Mo et al. 2024 Fig 2a/2b)" + title_extra)
    ax.grid(True, color="0.85", lw=0.6)
    ax.set_axisbelow(True)  # grid behind the bars

    ax.legend(loc="upper left", fontsize=6.5, framealpha=0.9)
    out = C.OUT / out_name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    make()


if __name__ == "__main__":
    make()
