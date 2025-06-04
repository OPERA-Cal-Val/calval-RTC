import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import shapely.wkt
from osgeo import gdal

gdal.UseExceptions()


def landcover_100_tile_intersections(bounds):
    """
    bounds: Tuple of lon lat bounds in the format (left, bottom, right, top)

    return: Tuple of int bounds,longitudes floored and latitudes ceilinged, to the nearest multiple of 20
            (left, bottom, right, top)

    """
    return (
        int(np.floor(bounds[0] / 20) * 20),
        int(np.ceil(bounds[1] / 20) * 20),
        int(np.floor(bounds[2] / 20) * 20),
        int(np.ceil(bounds[3] / 20) * 20),
    )


def get_corner_coords(img_path: Union[Path, str]) -> Union[List[str], None]:
    """
    Takes: a string or posix path to geographic dataset

    Returns: a list whose 1st element are the upperLeft coords and
             whose 2nd element are the lowerRight coords or None
             if none found
    """
    img_path = str(img_path)
    try:
        info = gdal.Info(img_path, options=["-json"])
    except TypeError:
        raise FileNotFoundError
    try:
        return [
            info["cornerCoordinates"]["upperLeft"],
            info["cornerCoordinates"]["lowerRight"],
        ]
    except KeyError:
        return None


def get_acquisition_time(scene_id: str) -> datetime:
    # collect acquisition date
    date_regex = r"(?<=_)\d{8}T\d{6}(?=_\d{8}T\d{6})"
    acquisition_time = re.search(date_regex, scene_id)
    try:
        acquisition_time = acquisition_time.group(0)
        return datetime.strptime(acquisition_time, "%Y%m%dT%H%M%S")
    except AttributeError:
        raise Exception(f"Acquisition timestamp not found in scene ID: {s}")


def get_projection(img_path: Union[Path, str]) -> Union[str, None]:
    """
    Takes: a string or posix path to a product in a UTM projection

    Returns: the projection (as a string) or None if none found
    """
    img_path = str(img_path)
    try:
        info = gdal.Info(img_path, format="json")["coordinateSystem"]["wkt"]
    except KeyError:
        return None
    except TypeError:
        raise FileNotFoundError

    regex = r'ID\["EPSG",[0-9]{4,5}\]\]$'
    results = re.search(regex, info)
    if results:
        return results.group(0).split(",")[1][:-2]
    else:
        return None


def reproject_data(pth: Union[str, os.PathLike], predominant_epsg: str):
    """
    pth: a path to a GeoTiff
    predominant_epsg: a string epsg

    Checks EPSG of input pth and projects to predominant_epsg if necessary
    """
    src_SRS = get_projection(str(pth))
    if src_SRS != predominant_epsg:
        res = get_res(pth)
        no_data_val = get_no_data_val(pth)
        temp = pth.parent / f"temp_{pth.stem}.tif"
        pth.rename(temp)

        warp_options = {
            "dstSRS": f"EPSG:{predominant_epsg}",
            "srcSRS": f"EPSG:{src_SRS}",
            "targetAlignedPixels": True,
            "xRes": res,
            "yRes": res,
            "dstNodata": no_data_val,
        }
        gdal.Warp(str(pth), str(temp), **warp_options)
        temp.unlink()


def get_projection_counts(tiff_paths: List[Union[os.PathLike, str]]) -> Dict:
    """
    Takes: List of string or os.PathLike paths to geotiffs

    Returns: Dictionary key: epsg, value: number of tiffs in that epsg
    """
    epsgs = []
    for p in tiff_paths:
        epsgs.append(get_projection(p))

    epsgs = dict(Counter(epsgs))
    return epsgs


def poly_from_minx_miny_maxx_maxy(
    coords: List[Union[float, int]]
) -> shapely.geometry.polygon.Polygon:
    """
    Takes: List of bounding box coordinates in format [minx, miny, maxx, maxy]

    Returns: shapely Polygon of bounding box
    """
    return shapely.wkt.loads(
        (
            f"POLYGON(({coords[0]} {coords[1]}, "
            f"{coords[0]} {coords[3]}, "
            f"{coords[2]} {coords[3]}, "
            f"{coords[2]} {coords[1]}, "
            f"{coords[0]} {coords[1]}))"
        )
    )


def get_res(tif_pth: Union[os.PathLike, str]) -> float:
    """
    Takes: path to a GeoTiff

    Returns: Geotiff resolution
    """
    f = gdal.Open(str(tif_pth))
    return f.GetGeoTransform()[1]


def get_no_data_val(tif_pth: Union[os.PathLike, str]) -> Union[np.nan, float, int]:
    """
    Takes: path to a GeoTiff

    Returns: GeoTiff's no-data value or numpy.nan if not defined
    """

    f = gdal.Open(str(tif_pth))
    return (
        np.nan
        if not f.GetRasterBand(1).GetNoDataValue()
        else f.GetRasterBand(1).GetNoDataValue()
    )


def merge_bursts(
    scene_id: str,
    burst_paths: List[Union[str, os.PathLike]],
    output: Union[str, os.PathLike],
):
    """
    Takes:
        scene_id: Sentinel-1 scene ID
        burst_paths: List of paths to bursts to be merged
        output: output path of merged GeoTiff

    Merges all bursts in `burst_paths`, saving to path `output`
    """

    # build a string of bursts to merge
    merge_str = ""
    for pth in burst_paths:
        merge_str += f" {str(pth)}"

    # merge bursts
    no_data_val = get_no_data_val(burst_paths[0])
    merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {output} {merge_str}"
    print(f"Merging bursts -> {output}")
    subprocess.run([merge_command], shell=True)
