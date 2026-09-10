"""Global surface MDA8 ozone dashboard (1990-2022).

Reads only the small aggregated products written by the MATLAB
post-processing pipeline. Never touches the raw BME estimates, the 0.1 deg
G5NR downscaling tree, or the validation outputs.
"""
from . import config, export, io, plots, theme, timeseries  # noqa: F401

__all__ = ["config", "export", "io", "plots", "theme", "timeseries"]
