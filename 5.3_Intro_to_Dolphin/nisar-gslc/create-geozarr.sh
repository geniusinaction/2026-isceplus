curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

uvx --with "opera-utils[disp] @ git+https://github.com/scottstanie/opera-utils.git@develop-scott" --from bowser-insar bowser setup-dolphin mx_dolphin
uvx --with "geozarr-toolkit" --with "rasterio>=1.5" --with "opera-utils[disp] @ git+https://github.com/scottstanie/opera-utils.git@develop-scott" --from bowser-insar==0.4.0 bowser tifs-to-geozarr bowser_rasters.json mx_dolphin.zarr
zip -0q -r mx_dolphin.zarr.zip  mx_dolphin.zarr