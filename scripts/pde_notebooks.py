"""The cases use the same explicit FEM language exposed in calculation cells."""
from bridge_case import notebook as bridge
from wing_case import notebook as wing
from quartz_case import notebook as quartz
from gear_case import notebook as gear


def notebooks(text,calc):
    return [bridge(text,calc),wing(text,calc),quartz(text,calc),gear(text,calc)]
