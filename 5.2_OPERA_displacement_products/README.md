# 5.2 OPERA displacement products

**Goal:** use MintPy to display and analyze OPERA DISP-S1 products over the southern Central Valley, CA.

## Notebooks

1. `opera-disp-01-explore.ipynb` - find the frame covering Corcoran, understand the moving reference date, download a cropped subset, rebase it into a continuous time series, and check the quality layers.
2. `opera-disp-02-mintpy.ipynb` - fetch the DISP-S1 static (geometry) layers, convert the stack to MintPy format, fit velocity, and compare against the ASF displacement portal.

`utils.py` holds the one helper `opera-utils` does not provide yet: downloading the per-frame DISP-S1-STATIC layers and cropping them onto your subset's grid.

## Expected outcome

Understand what OPERA DISP-S1 products contain and how to access them; understand what is contained in the quality layers; know why the moving reference date makes rebasing mandatory; be able to reformat a stack for MintPy and interpret the result.

## Assessment

Homework 10: compare your result to the [OPERA Displacement Portal](https://displacement.asf.alaska.edu/#/?dispOverview=VEL&zoom=8.812&center=-119.934,36.430) and comment on the similarities and differences. 
The portal renders the `short wavelength displacement` layer and uses a different date range from the notebook. The [ASF displacement FAQ](https://docs.asf.alaska.edu/datasets/disp_faq/) explains the filtering and reference conventions; notebook 2 turns those differences into the homework questions.

## Superseded material

Similar material from last year:

- `opera-disp-01-plot-one-ridgecrest.ipynb` - streaming access over the 2019 Ridgecrest earthquake. It remains useful as a short, single-event example of unwrapping errors and the short-wavelength layer.
- `opera-disp-02-timeseries.ipynb` - superseded by the two notebooks above. Its geometry step pulls from `s3://earthscope-insar2025/`, which is no longer necessary now that DISP-S1-STATIC is a public ASF collection.
