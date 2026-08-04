"""Step 02: Obtain the META3.1exp DT eddy trajectory atlas (AVISO+/CNES).

META3.1exp DT ships as two NetCDF files (delayed-time):
  META3.1exp_DT_allsat_Anticyclonic_long_19930101_20220209.nc
  META3.1exp_DT_allsat_Cyclonic_long_19930101_20220209.nc
each with per-observation records: time, longitude, latitude,
effective_radius (or speed_radius), amplitude, track, ...

AVISO+ is a SEPARATE service from Copernicus Marine. Two ways to get the files:
  (A) Place them manually in data/eddies/  (any *.nc with 'yclonic' in the name).
  (B) Set env AVISO_USER / AVISO_PASS and let this script try FTP/HTTPS.

This script verifies the files are present & readable and reports their fields.
"""
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C

# AVISO public HTTPS gateway (anonymous, no credentials required).
# The paper uses the fully-tracked "long" trajectory files. This set spans
# 1993-01-01 .. 2020-03-07, covering the paper's 1993-2019 window.
AVISO_GW = ("https://data.aviso.altimetry.fr/aviso-gateway/data/"
            "META3.1exp_DT/META3.1exp_DT_allsat")
FILES = [
    "META3.1exp_DT_allsat_Anticyclonic_long_19930101_20200307.nc",
    "META3.1exp_DT_allsat_Cyclonic_long_19930101_20200307.nc",
]


def _remote_size(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length", 0))
    except Exception:
        return 0


def _fetch_until_complete(url, dest, expected, max_rounds=200):
    """The AVISO gateway drops long connections. Keep resuming with
    `curl -C -` until the file on disk reaches `expected` bytes. Each round
    that makes progress resets the stall counter."""
    import time
    last = dest.stat().st_size if dest.exists() else 0
    stalls = 0
    for rnd in range(1, max_rounds + 1):
        have = dest.stat().st_size if dest.exists() else 0
        if expected and have >= expected:
            print(f"    complete: {have/1e9:.2f} GB", flush=True)
            return True
        print(f"    round {rnd}: have {have/1e9:.2f}/"
              f"{expected/1e9:.2f} GB, resuming ...", flush=True)
        # --speed-time/-limit aborts a stalled connection so we retry fast;
        # -C - resumes from current byte offset.
        subprocess.run(
            ["curl", "-sS", "-C", "-", "--connect-timeout", "30",
             "--speed-limit", "10000", "--speed-time", "60",
             "-o", str(dest), url],
        )
        now = dest.stat().st_size if dest.exists() else 0
        if now <= last:
            stalls += 1
            if stalls >= 10:
                print(f"    no progress after {stalls} rounds; giving up", flush=True)
                return False
            time.sleep(min(30, 5 * stalls))
        else:
            stalls = 0
        last = now
    return dest.exists() and expected and dest.stat().st_size >= expected


def try_download():
    """Download the two 'long' trajectory files via the public gateway,
    resuming through the server's frequent connection drops."""
    ok = True
    for f in FILES:
        dest = C.EDDY_DIR / f
        url = f"{AVISO_GW}/{f}"
        expected = _remote_size(url)
        print(f"downloading {f}  (expected {expected/1e9:.2f} GB) ...", flush=True)
        if _fetch_until_complete(url, dest, expected):
            print(f"  done {f}", flush=True)
        else:
            print(f"  INCOMPLETE {f}", flush=True)
            ok = False
    return ok


def verify():
    import xarray as xr
    found = sorted(C.EDDY_DIR.glob("*.nc"))
    if not found:
        print("No eddy NetCDF files in", C.EDDY_DIR)
        print("Place META3.1exp_DT Anticyclonic + Cyclonic files there, or set "
              "AVISO_USER/AVISO_PASS.")
        return False
    for f in found:
        polarity = ("AE" if "nticyclon" in f.name else
                    "CE" if "yclon" in f.name else "?")
        ds = xr.open_dataset(f)
        print(f"\n{f.name}  [{polarity}]")
        print("  dims:", dict(ds.sizes))
        print("  vars:", list(ds.variables)[:20])
        ds.close()
    return True


if __name__ == "__main__":
    try_download()
    verify()
