#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["asf-search", "pandas"]
# ///
"""Rank NISAR GSLC track/frames by usable stack depth for a dolphin time series.

Adapted from ``whirlwind-insar/aws-batch/discover_granules.py``, which does the
same catalog pull for GUNW. A GUNW is already a pair, so that script samples one
product per frame; for a dolphin stack we want the opposite -- the frames with
the most repeat passes.

Deduplication is the whole point, because the raw catalog count per frame is a
large overcount. The granule tail is
``<CRID>_<proc>_<coverage>_<joint>_<counter>``, and one acquisition shows up
repeatedly along three independent axes:

* **CRID** (``X05008`` -> ``X05009`` -> ``X05010`` -> ``P05023``): genuine
  reprocessing. Keep the newest.
* **coverage** ``F``/``P``: a Partial product covers only part of the frame.
  Never what you want for a stack, so Full is required.
* **proc** ``N``/``F``: Nominal scheduled processing vs a Forensic/on-demand
  run. Prefer Nominal.

Polarization is filtered too: phase linking needs the same channel at every
epoch, so a frame is only counted at the depth of its single best pol mode.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

GRANULE_RE = re.compile(
    r"NISAR_L2_\w+?_GSLC_(?P<cycle>\d+)_(?P<track>\d+)_(?P<direction>[AD])_"
    r"(?P<frame>\d+)_(?P<mode>[^_]+)_(?P<pol>[^_]{4})_(?P<band>[^_])_"
    r"(?P<start>\d{8}T\d{6})_(?P<end>\d{8}T\d{6})_"
    r"(?P<crid>[A-Z]\d+)_(?P<proc>[A-Z])_(?P<coverage>[A-Z])_(?P<joint>[A-Z])_"
    r"(?P<counter>\d+)"
)


def fetch_inventory(cache: Path, refresh: bool) -> pd.DataFrame:
    """Page through the ASF catalog for every NISAR GSLC product."""
    if cache.exists() and not refresh:
        df = pd.read_csv(cache, parse_dates=["start", "end"])
        print(f"Inventory: {len(df)} granules (cached {cache})", flush=True)
        return df

    import asf_search as asf

    print("Querying ASF for all NISAR GSLC products...", flush=True)
    results = asf.search(dataset=asf.DATASET.NISAR, processingLevel="GSLC")
    print(f"  {len(results)} granules returned", flush=True)

    rows = []
    for r in results:
        p = r.properties
        name = p["sceneName"]
        m = GRANULE_RE.match(name)
        if m is None:
            raise ValueError(f"Unparseable NISAR GSLC granule name: {name!r}")
        g = m.groupdict()
        rows.append(
            {
                "granule": name,
                "url": p["url"],
                "cycle": int(g["cycle"]),
                "track": int(g["track"]),
                "direction": g["direction"],
                "frame": int(g["frame"]),
                "mode": g["mode"],
                "pol": g["pol"],
                "crid": g["crid"],
                "proc": g["proc"],
                "coverage": g["coverage"],
                "start": pd.to_datetime(g["start"], format="%Y%m%dT%H%M%S"),
                "end": pd.to_datetime(g["end"], format="%Y%m%dT%H%M%S"),
            }
        )

    df = pd.DataFrame(rows)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    print(f"Wrote inventory -> {cache}", flush=True)
    return df


def dedupe(inv: pd.DataFrame) -> pd.DataFrame:
    """Collapse reprocessings so one acquisition in one pol appears once."""
    print(f"\nRaw catalog: {len(inv)} granules")
    print("  coverage:", inv["coverage"].value_counts().to_dict())
    print("  proc    :", inv["proc"].value_counts().to_dict())
    print("  CRID    :", inv["crid"].value_counts().to_dict())

    full = inv[inv["coverage"] == "F"]
    print(f"\nFull-coverage only: {len(inv)} -> {len(full)} granules")

    # Prefer Nominal processing, then the newest CRID. P (provisional) sorts
    # after X (beta) lexically, which is also newest-first, so a plain
    # descending sort on crid is correct.
    key = ["track", "direction", "frame", "pol", "start"]
    ranked = full.assign(_proc_rank=(full["proc"] != "N").astype(int)).sort_values(
        ["_proc_rank", "crid"], ascending=[True, False]
    )
    deduped = ranked.drop_duplicates(subset=key, keep="first").reset_index(drop=True)
    print(f"Dedup on {key}: {len(full)} -> {len(deduped)} distinct acquisitions")
    return deduped.drop(columns=["_proc_rank"])


def rank_stacks(deduped: pd.DataFrame, min_depth: int) -> pd.DataFrame:
    """One row per (track, direction, frame, pol), sorted by acquisition count.

    Polarization is part of the key: a stack must use one channel throughout,
    so a frame imaged in three pol modes is three candidate stacks, not one
    deep one.
    """
    rows = []
    for (track, direction, frame, pol), grp in deduped.groupby(
        ["track", "direction", "frame", "pol"]
    ):
        dates = sorted(grp["start"].dt.normalize().unique())
        if len(dates) < min_depth:
            continue
        gaps = pd.Series(dates).diff().dt.days.dropna()
        crids = sorted(grp["crid"].unique())
        rows.append(
            {
                "track": track,
                "direction": direction,
                "frame": frame,
                "pol": pol,
                "n_dates": len(dates),
                "first": pd.Timestamp(dates[0]).date(),
                "last": pd.Timestamp(dates[-1]).date(),
                "span_days": (dates[-1] - dates[0]).days,
                "max_gap_days": int(gaps.max()) if len(gaps) else 0,
                "n_12day": int((gaps == 12).sum()),
                "n_beta": int((grp["crid"].str[0] == "X").sum()),
                "n_prov": int((grp["crid"].str[0] == "P").sum()),
                "crids": "/".join(crids),
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["n_dates", "n_12day"], ascending=False).reset_index(
        drop=True
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inventory-csv", type=Path, default=Path("nisar_gslc_inventory.csv"))
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--min-depth", type=int, default=8)
    p.add_argument("--out", type=Path, default=Path("gslc_stack_depth.csv"))
    p.add_argument("--top", type=int, default=30)
    args = p.parse_args()

    inv = fetch_inventory(args.inventory_csv, args.refresh)
    deduped = dedupe(inv)
    ranked = rank_stacks(deduped, args.min_depth)

    ranked.to_csv(args.out, index=False)
    deduped.to_csv(args.out.with_name("nisar_gslc_deduped.csv"), index=False)
    print(f"\n{len(ranked)} track/frame/pol stacks with >= {args.min_depth} dates "
          f"-> {args.out}")
    print("depth histogram:", ranked["n_dates"].value_counts().sort_index().to_dict())
    with pd.option_context("display.width", 250, "display.max_columns", 25):
        print("\n" + ranked.head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()
