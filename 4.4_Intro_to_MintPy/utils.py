"""Utilities for MintPy tutorial notebooks.
Author: Changyang Hu, Zhang Yunjun, Aug 2026.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint
from urllib.parse import urlparse

import asf_search as asf
import tqdm

# Ensure ! commands find the conda environment's executables
os.environ['PATH'] = os.pathsep.join([os.path.dirname(sys.executable), os.environ.get('PATH', '')])

for _var, _sub in [('PROJ_DATA', 'share/proj'), ('GDAL_DATA', 'share/gdal')]:
    if _var not in os.environ:
        _path = os.path.join(sys.prefix, _sub)
        if os.path.isdir(_path):
            os.environ[_var] = _path

def get_local_path():
    """Directory containing this utils.py (used by smallbaselineApp_aria.ipynb)."""
    return os.path.dirname(os.path.realpath(__file__))


def write_config_file(out_file, CONFIG_TXT, mode='a'): 
    """Write configuration files for MintPy to process NISAR sample products"""
    if not os.path.isfile(out_file) or mode == 'w':
        with open(out_file, "w") as fid:
            fid.write(CONFIG_TXT)
        print('write configuration to file: {}'.format(out_file))
    else:
        with open(out_file, "a") as fid:
            fid.write("\n" + CONFIG_TXT)
        print('add the following to file: \n{}'.format(CONFIG_TXT))


def download_nisar_gunw(
    ifg_dir,
    wsen,
    start_date,
    end_date,
    short_name="NISAR_L2_GUNW_BETA_V1",
    flight_direction="DESCENDING",
    track_frame="113_D_079",
    product_type="GUNW",
    max_results=250,
    use_existing_data=True,
):
    """Search ASF for NISAR GUNW products and download .h5 files to ifg_dir.

    Uses Earthdata credentials from ~/.netrc (no interactive login).
    """

    ifg_dir = Path(ifg_dir)
    ifg_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"^(?!.*QA_STATS).*")

    # prepare inputs format
    w, s, e, n = wsen
    wkt_polygon = f"POLYGON (({w} {s}, {e} {s}, {e} {n}, {w} {n}, {w} {s}))"
    print(wkt_polygon)
    start_date = datetime.strptime(start_date.replace('-',''), '%Y%m%d')
    end_date = datetime.strptime(end_date.replace('-',''), '%Y%m%d')

    existing_h5 = sorted(ifg_dir.glob("NISAR*.h5"))
    if use_existing_data and existing_h5:
        print(f"Found {len(existing_h5)} existing NISAR GUNW file(s) in {ifg_dir}")
        print("Skip ASF download (set use_existing_data=False to force re-download).")
        return existing_h5

    netrc = Path.home() / ".netrc"
    if not netrc.is_file():
        raise FileNotFoundError(
            f"Missing {netrc}. Create it with Earthdata Login credentials, e.g.\n"
            "  machine urs.earthdata.nasa.gov\n"
            "  login YOUR_USERNAME\n"
            "  password YOUR_PASSWORD\n"
            "Then: chmod 600 ~/.netrc"
        )

    # ASFSession + requests will read credentials from ~/.netrc
    session = asf.ASFSession()
    opts = asf.ASFSearchOptions(
        **{
            "maxResults": max_results,
            "intersectsWith": wkt_polygon,
            "flightDirection": flight_direction,
            "start": start_date,
            "end": end_date,
            "shortName": [short_name],
            # when supported by your asf_search / CMR, you can also use:
            # "processingLevel": [product_type],
            # "dataset": ["NISAR"],
            "session": session,
        }
    )
    response = asf.search(opts=opts)

    # collect .h5 product URLs (exclude QA_STATS; keep requested track/frame)
    if hasattr(response, "find_urls"):
        h5_files = response.find_urls(
            extension=".h5", pattern=pattern.pattern, directAccess=False
        )
        h5_files = [u for u in h5_files if track_frame in u]
    else:
        h5_files = [
            r.properties["url"]
            for r in response
            if r.properties.get("fileName", "").endswith(".h5")
            and track_frame in r.properties["fileName"]
            and pattern.match(r.properties["fileName"])
        ]

    print(f"Found {len(h5_files)} {product_type} products:")
    pprint(h5_files)
    if not h5_files:
        raise RuntimeError(
            "No matching NISAR GUNW products found. "
            "Adjust wsen / short_name / track_frame / date_range, "
            "or browse https://search.asf.alaska.edu/#/"
        )

    n = len(h5_files)
    for i, url in enumerate(h5_files, start=1):
        download_url_with_progress(url, ifg_dir, session, idx=i, total=n)

    existing_h5 = sorted(ifg_dir.glob("NISAR*.h5"))
    print(f"Downloaded to {ifg_dir}: {len(existing_h5)} NISAR*.h5 file(s)")
    return existing_h5


def download_url_with_progress(url, out_dir, session, idx, total):
    """Download one URL with file-level and byte-level progress."""
    filename = Path(urlparse(url).path).name
    outfile = Path(out_dir) / filename
    prefix = f"[{idx}/{total}] "
    if outfile.is_file() and outfile.stat().st_size > 0:
        print(f"{prefix}skip existing: {filename}")
        return

    print(f"{prefix}downloading {filename} ...")
    resp = asf.download._try_get_response(session=session, url=url)
    total_bytes = int(resp.headers.get("Content-Length") or 0)
    pbar = tqdm.tqdm(
        total=total_bytes or None,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=filename[:48],
        leave=True,
    )

    downloaded = 0
    tmpfile = outfile.with_suffix(outfile.suffix + ".part")
    with open(tmpfile, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if pbar is not None:
                pbar.update(len(chunk))
            elif total_bytes:
                pct = 100.0 * downloaded / total_bytes
                print(
                    f"\r{prefix}{downloaded/1e6:.1f}/{total_bytes/1e6:.1f} MB ({pct:5.1f}%)",
                    end="",
                    flush=True,
                )

    if pbar is not None:
        pbar.close()
    elif total_bytes:
        print()
    tmpfile.replace(outfile)
    print(f"{prefix}done: {filename} ({downloaded/1e6:.1f} MB)")
    return