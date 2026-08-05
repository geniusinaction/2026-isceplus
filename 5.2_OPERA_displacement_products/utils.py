"""Download and crop OPERA DISP-S1 static layers for the course notebooks."""

from __future__ import annotations

from pathlib import Path

import requests
import rioxarray
import xarray as xr
from rasterio.enums import Resampling

STATIC_COLLECTION = "OPERA_L3_DISP-S1-STATIC_V1"
CMR_GRANULE_URL = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
LAYERS = ("line_of_sight_enu", "dem", "layover_shadow_mask")


def find_static_layer_urls(frame_id: int) -> dict[str, str]:
    """Look up the DISP-S1-STATIC GeoTIFF URLs for one frame via a CMR search.

    Parameters
    ----------
    frame_id : int
        DISP-S1 frame ID.

    Returns
    -------
    dict[str, str]
        Maps layer name to its HTTPS URL.

    """
    response = requests.get(
        CMR_GRANULE_URL,
        params={
            "short_name": STATIC_COLLECTION,
            "attribute[]": f"int,FRAME_NUMBER,{frame_id}",
            "page_size": 1,
        },
        timeout=60,
    )
    response.raise_for_status()
    items = response.json()["items"]
    if not items:
        msg = f"No {STATIC_COLLECTION} granule found for frame {frame_id}"
        raise ValueError(msg)

    urls = {}
    for related in items[0]["umm"]["RelatedUrls"]:
        url = related["URL"]
        if not url.startswith("https") or not url.endswith(".tif"):
            continue
        for layer in LAYERS:
            if url.endswith(f"_{layer}.tif"):
                urls[layer] = url

    missing = set(LAYERS) - set(urls)
    if missing:
        msg = f"CMR result for frame {frame_id} is missing layers: {sorted(missing)}"
        raise ValueError(msg)
    return urls


def download_static_layers(
    frame_id: int, like: Path | str, output_dir: Path | str = "geometry"
) -> Path:
    """Download the static layers for a frame and crop them to a downloaded subset.

    `opera_utils.disp.mintpy.create_static_layers` assumes the geometry rasters are
    already on the same grid as the displacement stack, so the crop is not optional.

    Parameters
    ----------
    frame_id : int
        DISP-S1 frame ID.
    like : Path or str
        Any one of the downloaded DISP-S1 NetCDF subsets. Its grid defines the crop.
    output_dir : Path or str
        Where to write the cropped GeoTIFFs. Pass this to `disp_nc_to_mintpy` as
        `geometry_dir`.

    Returns
    -------
    Path
        `output_dir`, containing the three cropped GeoTIFFs.

    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with xr.open_dataset(like, engine="h5netcdf") as ds_like:
        # A single-date subset opens with `time` already squeezed away. Drop any
        # length-one dimensions rather than assuming one shape.
        template = ds_like.displacement.squeeze(drop=True)
        if template.ndim != 2:
            msg = f"Expected a 2-D template after squeezing {like}, got {template.dims}"
            raise ValueError(msg)
        template = template.rio.write_crs(ds_like.spatial_ref.attrs["crs_wkt"])

    output_layers = {
        layer: "los_enu" if layer == "line_of_sight_enu" else layer for layer in LAYERS
    }
    outpaths = {
        layer: output_dir / f"F{frame_id}_{output_layer}.tif"
        for layer, output_layer in output_layers.items()
    }
    if all(path.exists() for path in outpaths.values()):
        for path in outpaths.values():
            print(f"Skipped (exists): {path}")
        return output_dir

    from opera_utils.credentials import get_earthdata_username_password

    session = requests.Session()
    session.auth = get_earthdata_username_password()
    urls = find_static_layer_urls(frame_id)
    for layer, url in urls.items():
        # opera-utils 0.25.x expects the historical ``*_los_enu.tif`` name.
        # Keep that local name even though ASF calls the asset
        # ``*_line_of_sight_enu.tif``.
        outpath = outpaths[layer]
        if outpath.exists():
            print(f"Skipped (exists): {outpath}")
            continue

        raw = output_dir / Path(url).name
        try:
            with session.get(url, stream=True, timeout=(30, 300)) as response:
                response.raise_for_status()
                with raw.open("wb") as stream:
                    for chunk in response.iter_content(chunk_size=1 << 20):
                        stream.write(chunk)

            # Preserve categorical labels in the mask. Bilinear interpolation is
            # appropriate for the smoothly varying LOS vectors and DEM.
            resampling = (
                Resampling.nearest
                if layer == "layover_shadow_mask"
                else Resampling.bilinear
            )
            with rioxarray.open_rasterio(raw) as da:
                cropped = da.rio.reproject_match(template, resampling=resampling)
                cropped.rio.to_raster(outpath)
        finally:
            raw.unlink(missing_ok=True)

        print(f"Wrote {outpath}  {cropped.shape}")

    return output_dir
