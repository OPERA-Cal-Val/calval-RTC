import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import earthaccess
import pandas as pd
import papermill as pm
from opensarlab_lib import work_dir
from osgeo import gdal
from tqdm.auto import tqdm

gdal.UseExceptions()

current = Path("..").resolve()
sys.path.append(str(current))
import util.geo as util


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=str, required=True, help="California")
    parser.add_argument("--orbital_path", type=int, required=True, help="64")
    parser.add_argument(
        "--skip_download",
        default=False,
        action="store_true",
        help="Skip downloading and mosaicking of bursts and validate previously prepared data.",
    )
    return parser.parse_args()


def get_scene_df() -> pd.DataFrame:
    linked_data_csv = Path.cwd().parent / "linking-data/opera_rtc_table.csv"

    # load burst urls for site/calval module
    calval_module = "Absolute Geolocation Evaluation"
    df = pd.read_csv(linked_data_csv)
    return df.where(
        (df.Site == "California")
        & (df.Orbital_Path == 64)
        & (df.CalVal_Module == calval_module)
    ).dropna()


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def download_bursts(
    scene_id: str, df: pd.DataFrame, rtc_dir: os.PathLike
) -> List[os.PathLike]:
    # Create data directories
    vv_burst_dir = rtc_dir / "vv_bursts"
    vv_burst_dir.mkdir(exist_ok=True, parents=True)

    # Find VV URLs for scene_id
    vv_urls = (
        df.where(df.S1_Scene_IDs == scene_id).dropna().vv_url.tolist()[0].split(" ")
    )

    # sanitize URLs
    vv_urls = [url for url in vv_urls if is_valid_url(url)]

    # download bursts
    print(f"Downloading bursts for S1 scene: {scene_id}")
    for burst_url in vv_urls:
        earthaccess.download(burst_url, vv_burst_dir)

    # return paths to downloaded bursts
    return list(vv_burst_dir.glob("*VV.tif"))


def absolute_geolocation_evaluation(parent_data_dir: os.PathLike, args: object):
    data_dirs = [
        p for p in parent_data_dir.glob("*") if not str(p.name).startswith(".")
    ]

    output_dirs = [
        p.parents[1]
        / f"output_OPERA_RTC_ALE_{args.site}_{args.orbital_path}/absolute_geolocation_evaluation_{p.name.split('RTC_')[1]}"
        for p in data_dirs
    ]

    parameters = {"data_dir": "", "savepath": ""}

    with work_dir(Path.cwd().parent / "absolute_geolocation_evaluation"):
        for i, d in enumerate(tqdm(data_dirs)):
            print(f"Performing Absolute Geolocation Evaluation on {d}")
            parameters["data_dir"] = str(d)
            parameters["savepath"] = str(output_dirs[i])
            output_dirs[i].mkdir(parents=True, exist_ok=True)
            output = (
                output_dirs[i]
                / f"output_{Path(d).name}_absolute_location_evaluation.ipynb"
            )
            pm.execute_notebook(
                Path.cwd() / "absolute_location_evaluation.ipynb",
                output,
                kernel_name="python3",
                parameters=parameters,
            )

            subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True)


def main():
    args = parse_args()
    parent_data_dir = (
        Path.cwd().parents[1]
        / f"OPERA_L2-RTC_CalVal/OPERA_RTC_ALE_{args.site}_{args.orbital_path}/input_OPERA_data"
    )
    if not args.skip_download:
        # collect CalVal data access info
        df = get_scene_df()
        scenes = list(df.S1_Scene_IDs)

        # download CalVal bursts and mosaic into full S1 scenes
        earthaccess.login()
        for scene_id in tqdm(scenes):
            rtc_dir = parent_data_dir / f"OPERA_L2-RTC_{scene_id}_30_v1.0"
            rtc_dir.mkdir(exist_ok=True, parents=True)
            output = rtc_dir / f"OPERA_L2_RTC-S1_VV_{scene_id}_30_v1.0_mosaic.tif"
            if output.exists():
                continue
            vv_bursts = download_bursts(scene_id, df, rtc_dir)

            # reproject all bursts to predominant CRS
            epsgs = util.get_projection_counts(vv_bursts)
            predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)
            if predominant_epsg:
                for pth in vv_bursts:
                    util.reproject_data(pth, predominant_epsg)

            # merge bursts into a single scene
            util.merge_bursts(scene_id, vv_bursts, output)

    absolute_geolocation_evaluation(parent_data_dir, args)


if __name__ == "__main__":
    main()
