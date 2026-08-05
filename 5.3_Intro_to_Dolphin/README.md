```bash

curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

uvx --with "opera-utils[disp] @ git+https://github.com/scottstanie/opera-utils.git@develop-scott" --from bowser-insar bowser setup-dolphin .
uvx --with "geozarr-toolkit" --with "opera-utils[disp] @ git+https://github.com/scottstanie/opera-utils.git@develop-scott" --from bowser-insar bowser tifs-to-geozarr bowser_rasters.json mx_dolphin.zarr
zip -0q -r mx_dolphin.zarr.zip  mx_dolphin.zarr
```
