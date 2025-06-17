import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZipFile

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
    parser.add_argument(
        "--site", type=str, required=True, help="Delta Junction, Brazil"
    )
    parser.add_argument("--orbital_path", type=int, required=True, help="94, 160, 170")
    parser.add_argument(
        "--skip_download",
        default=False,
        action="store_true",
        help="Skip downloading and mosaicking of bursts and validate previously prepared data.",
    )
    parser.add_argument(
        "--delete_intermediary",
        default=False,
        action="store_true",
        help="Delete intermediary data",
    )
    return parser.parse_args()


def get_scene_df(args: object) -> pd.DataFrame:
    # unzip linked_data.csv
    zip_path = Path.cwd().parent / "linking-data/opera_rtc_table.csv.zip"
    linked_data_csv = Path.cwd().parent / "linking-data/opera_rtc_table.csv"
    if not linked_data_csv.exists():
        with ZipFile(zip_path, "r") as zObject:
            zObject.extractall(path=zip_path.parent)

    # load burst urls for site/calval module
    calval_module = "Relative Location Evaluation (RLE)"
    df = pd.read_csv(linked_data_csv)
    return df.where(
        (df.Site == args.site)
        & (df.Orbital_Path == args.orbital_path)
        & (df.CalVal_Module == calval_module)
    ).dropna()


def was_reported(acquisition_time: datetime, args: object) -> bool:
    # limit scenes to those reported in Oct 2023 RLE validation
    if args.site == "Delta Junction":
        if args.orbital_path == 94:
            start_time = datetime.strptime("20201209T032007", "%Y%m%dT%H%M%S")
            end_time = datetime.strptime("20211216T032012", "%Y%m%dT%H%M%S")
        elif args.orbital_path == 160:
            start_time = datetime.strptime("20220507T161226", "%Y%m%dT%H%M%S")
            end_time = datetime.strptime("20230713T161236", "%Y%m%dT%H%M%S")
    else:
        start_time = datetime.strptime("20210606T090048", "%Y%m%dT%H%M%S")
        end_time = datetime.strptime("20220508T090052", "%Y%m%dT%H%M%S")

    return start_time <= acquisition_time <= end_time


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def RLE(parent_data_dir: os.PathLike, args: object):

    # True to delete mosaicked RTCs and static files, False to save
    delete_mosaics = False

    output_dir = parent_data_dir.parent / "output_RLE"

    polarizations = ["VV", "VH"]

    # for i, d in enumerate(stack_dirs):
    for p in polarizations:

        if args.delete_intermediary:
            cleanup_list = (
                f"{p} amplitude data, "
                f"flattened {p} amplitude data, "
                f"flattened and tiled {p} amplitude data, "
                f"{p} tile correlation results, "
            )
        else:
            cleanup_list = ""

        parameters = {
            "polarization": p,
            "stack_dir": str(parent_data_dir),
            "delete_mosaics": delete_mosaics,
            "cleanup_list": cleanup_list,
        }

        output_dir.mkdir(exist_ok=True)
        output = (
            output_dir
            / f"output_{args.site.replace(' ', '_')}_{args.orbital_path}_{p}_OPERA_RTC_RLE.ipynb"
        )
        output_html = Path(output).with_suffix('.html')
        output_pdf = Path(output).with_suffix('.pdf')

        with work_dir(Path.cwd().parent / "RLE"):
            pm.execute_notebook(
                "RLE.ipynb",
                output,
                kernel_name="python3",
                parameters=parameters,
            )

            subprocess.run(
                [f"jupyter nbconvert {output} --to html"],
                shell=True,
            )
            subprocess.run(
                [
                    f"pandoc {output_html} "
                    f"-o {output_pdf} "
                    "--pdf-engine=weasyprint"
                ],
                shell=True,
            )


def main():
    args = parse_args()
    parent_data_dir = (
        Path.cwd().parents[1]
        / f"OPERA_L2-RTC_CalVal/OPERA_RTC_Coregistration_{args.site.replace(' ', '_')}_{args.orbital_path}/input_OPERA_data"
    )
    if not args.skip_download:
        # collect CalVal data access info
        df = get_scene_df(args)
        scenes = list(df.S1_Scene_IDs)

        # download CalVal bursts and mosaic into full S1 scenes
        earthaccess.login()
        for scene_id in tqdm(scenes):
            # define/create paths to data dirs
            rtc_dir = parent_data_dir / f"OPERA_L2-RTC_{scene_id}_30_v1.0"
            vv_burst_dir = rtc_dir / "vv_bursts"
            vh_burst_dir = rtc_dir / "vh_bursts"

            vh_output = rtc_dir / f"OPERA_L2_RTC-S1_VH_{scene_id}_30_v1.0_mosaic.tif"
            vv_output = rtc_dir / f"OPERA_L2_RTC-S1_VV_{scene_id}_30_v1.0_mosaic.tif"

            acquisition_time = util.get_acquisition_time(scene_id)
            if not was_reported(acquisition_time, args) or (
                vh_output.exists() and vv_output.exists()
            ):
                continue

            # create data directories
            for pth in [rtc_dir, vv_burst_dir, vh_burst_dir]:
                pth.mkdir(exist_ok=True, parents=True)

            # download bursts
            vh_urls = (
                df.where(df.S1_Scene_IDs == scene_id)
                .dropna()
                .vh_url.tolist()[0]
                .split(" ")
            )
            vv_urls = (
                df.where(df.S1_Scene_IDs == scene_id)
                .dropna()
                .vv_url.tolist()[0]
                .split(" ")
            )

            # sanitize URLs
            vh_urls = [url for url in vh_urls if is_valid_url(url)]
            vv_urls = [url for url in vv_urls if is_valid_url(url)]

            # download bursts
            path_dict = {vv_burst_dir: vv_urls, vh_burst_dir: vh_urls}
            print(f"Downloading bursts for S1 scene: {scene_id}")
            for pth in path_dict:
                for burst_url in path_dict[pth]:
                    earthaccess.download(burst_url, pth)
            vv_bursts = list(vv_burst_dir.glob("*VV.tif"))
            vh_bursts = list(vh_burst_dir.glob("*VH.tif"))

            # reproject all bursts to predominant CRS
            epsgs = util.get_projection_counts(vv_bursts)
            predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)
            if predominant_epsg:
                for bursts in [vv_bursts, vh_bursts]:
                    for pth in bursts:
                        util.reproject_data(pth, predominant_epsg)

            # merge VH and VV bursts into a single scenes
            for output, bursts in {vv_output: vv_bursts, vh_output: vh_bursts}.items():
                util.merge_bursts(scene_id, bursts, output)

    RLE(parent_data_dir, args)


if __name__ == "__main__":
    main()
