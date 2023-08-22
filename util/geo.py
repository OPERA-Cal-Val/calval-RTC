from pathlib import Path
import re
from typing import List, Union

import numpy as np
from osgeo import gdal
import shapely.wkt

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
        int(np.ceil(bounds[3] / 20) * 20)
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
        info = gdal.Info(img_path, options=['-json'])
    except TypeError:
        raise FileNotFoundError
    try:
        return [info['cornerCoordinates']['upperLeft'], info['cornerCoordinates']['lowerRight']]
    except KeyError:
        return None
    
def get_projection(img_path: Union[Path, str]) -> Union[str, None]:
    """
    Takes: a string or posix path to a product in a UTM projection

    Returns: the projection (as a string) or None if none found
    """
    img_path = str(img_path)
    try:
        info = gdal.Info(img_path, format='json')['coordinateSystem']['wkt']
    except KeyError:
        return None
    except TypeError:
        raise FileNotFoundError

    regex = 'ID\["EPSG",[0-9]{4,5}\]\]$'
    results = re.search(regex, info)
    if results:
        return results.group(0).split(',')[1][:-2]
    else:
        return None
    
def poly_from_minx_miny_maxx_maxy(coords):
    return shapely.wkt.loads((f"POLYGON(({coords[0]} {coords[1]}, "
                              f"{coords[0]} {coords[3]}, "
                              f"{coords[2]} {coords[3]}, "
                              f"{coords[2]} {coords[1]}, "
                              f"{coords[0]} {coords[1]}))"))