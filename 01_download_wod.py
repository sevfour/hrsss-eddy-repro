"""Step 01: Download WOD per-year, per-platform NetCDF files.

Resumable: skips files already fully downloaded (size matches server
Content-Length). Logs progress. Full-depth files; subsetting to the top
10 m happens later in step 03.
"""
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C


def remote_size(url):
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length", 0))
    except Exception:
        return None


def _once(url, tmp, expected):
    got = tmp.stat().st_size if tmp.exists() else 0
    headers = {}
    if got and expected and got < expected:
        headers["Range"] = f"bytes={got}-"  # resume partial
    elif got and expected and got >= expected:
        return
    req = urllib.request.Request(url, headers=headers)
    mode = "ab" if headers else "wb"
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, mode) as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def download(url, dest, expected, retries=6):
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            _once(url, tmp, expected)
            if not expected or (tmp.exists() and tmp.stat().st_size >= expected):
                tmp.rename(dest)
                return
        except Exception as e:
            have = tmp.stat().st_size if tmp.exists() else 0
            print(f"           retry {attempt}/{retries} at {have/1e6:.0f} MB "
                  f"({type(e).__name__}: {e})", flush=True)
            time.sleep(min(30, 5 * attempt))
    raise RuntimeError(f"exhausted retries for {url}")


def main():
    total = len(C.YEARS) * len(C.PLATFORMS)
    n = 0
    t0 = time.time()
    for year in C.YEARS:
        for plat in C.PLATFORMS:
            n += 1
            fname = f"wod_{plat}_{year}.nc"
            url = f"{C.WOD_BASE}/{year}/{fname}"
            dest = C.WOD_DIR / fname
            exp = remote_size(url)
            if exp is None:
                print(f"[{n}/{total}] SKIP {fname} (not on server)", flush=True)
                continue
            if dest.exists() and dest.stat().st_size == exp:
                print(f"[{n}/{total}] have {fname} ({exp/1e6:.0f} MB)", flush=True)
                continue
            print(f"[{n}/{total}] GET  {fname} ({exp/1e6:.0f} MB) ...", flush=True)
            try:
                download(url, dest, exp)
                print(f"           done {fname}  (elapsed {time.time()-t0:.0f}s)", flush=True)
            except Exception as e:
                print(f"           FAIL {fname}: {e}", flush=True)
    print(f"All done in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
