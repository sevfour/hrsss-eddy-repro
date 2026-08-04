"""Step 08: Combined distribution histogram — all eddy bins pooled (AE + CE
together) from the 2x2 deg gridded surface salinity anomalies of Fig 2a/2b,
with reference lines at -0.2 and +0.2 pss.
"""
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def make(lat_band=None, out_name="fig2_histogram_combined.png"):
    ds = xr.open_dataset(C.ANOM_NC)
    ae2d = ds["Sp_AE"].values
    ce2d = ds["Sp_CE"].values
    title_extra = ""
    if lat_band is not None:
        lo, hi = lat_band
        latmask = (np.abs(ds["lat"].values) >= lo) & (np.abs(ds["lat"].values) <= hi)
        ae2d = ae2d[latmask, :]
        ce2d = ce2d[latmask, :]
        title_extra = f"\nmid-latitudes {lo}°–{hi}° N/S"
    combined = np.concatenate([ae2d.ravel(), ce2d.ravel()])
    combined = combined[np.isfinite(combined)]

    # Detection floor for the eddy-mean anomaly: single-pass SSS accuracy 0.2 pss
    # beaten down by N independent looks over the eddy's coherent lifetime.
    # N=7 independent samples -> 0.2/sqrt(7).
    SSS_ACC = 0.2
    N_LOOKS = 7
    thr = SSS_ACC / np.sqrt(N_LOOKS)

    frac_out = np.mean(np.abs(combined) > thr) * 100

    from matplotlib.lines import Line2D

    bins = np.linspace(-0.5, 0.5, 61)  # 1/60 pss resolution
    fig, ax = plt.subplots(figsize=(8, 5))
    # purple -- matches the red (AE) + blue (CE) alpha-composite overlap color
    n, _, _ = ax.hist(combined, bins=bins, color="#715ABD", alpha=0.9)
    ax.axvline(0, color="k", lw=0.8, ls="--")
    # detection-floor lines at +/- 0.2/sqrt(7) pss
    ax.axvline(-thr, color="crimson", lw=1.4, ls="-")
    ax.axvline(thr, color="crimson", lw=1.4, ls="-")
    ax.text(thr + 0.01, n.max() * 0.98,
            f"±0.2/√{N_LOOKS} = ±{thr:.3f} pss", color="crimson",
            ha="left", va="bottom", fontsize=8)

    ax.set_xlabel("surface (10 m) salinity anomaly per 2°×2° bin (pss)")
    ax.set_ylabel("number of grid bins")
    ax.set_title("Combined distribution of eddy-induced surface salinity anomalies\n"
                 "(based on Mo et al. 2024 Fig 2a/2b)" + title_extra)
    ax.grid(True, color="0.85", lw=0.6)
    ax.set_axisbelow(True)  # grid behind the bars

    # legend on the left; the % line has no marker handle
    hist_handle = ax.get_legend_handles_labels()[0]
    hist_handle = hist_handle[0] if hist_handle else Line2D([], [], color="#715ABD", lw=6)
    blank = Line2D([], [], linestyle="none", marker="")
    # Combined pools AE(+) and CE(-), so the SIGNED mean is near zero (they
    # cancel). The meaningful quantity here is the anomaly MAGNITUDE.
    amag = np.abs(combined)
    ax.legend([hist_handle, blank],
              [f"mean|·| {amag.mean():.3f}, median|·| {np.median(amag):.3f}, "
               f"std {combined.std():.3f}",
               f"{frac_out:.1f}% of |anomalies| > 0.2/√{N_LOOKS} pss"],
              loc="upper left", fontsize=7.5, framealpha=0.9, handletextpad=0.5)
    out = C.OUT / out_name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def main():
    make()


if __name__ == "__main__":
    make()
