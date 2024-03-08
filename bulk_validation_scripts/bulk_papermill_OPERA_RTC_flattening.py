import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Union, Dict, List
from urllib.parse import urlparse

import earthaccess
import pandas as pd
import papermill as pm
from opensarlab_lib import work_dir
from osgeo import gdal

gdal.UseExceptions()

current = Path("..").resolve()
sys.path.append(str(current))
import util.geo as util


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--site", type=str, required=True, help="Vermont, Delta Junction, Brazil"
    )
    parser.add_argument(
        "--orbital_path", type=int, required=True, help="135, 113, 94, 160, 39"
    )
    parser.add_argument(
        "--skip_download",
        default=False,
        action="store_true",
        help="Skip downloading and mosaicking of bursts and validate previously prepared data.",
    )
    return parser.parse_args()


def get_rtc_df(args: object) -> pd.DataFrame:
    opera_rtc_csv = Path.cwd().parent / "linking-data/opera_rtc_table.csv"

    # load dataframe with burst urls for site/calval module
    calval_module = "Flattening"
    df_rtc = pd.read_csv(opera_rtc_csv)
    return df_rtc.where(
        (df_rtc.Site == args.site)
        & (df_rtc.Orbital_Path == args.orbital_path)
        & (df_rtc.CalVal_Module == calval_module)
    ).dropna()


def get_static_df() -> pd.DataFrame:
    # load dataframe with static file URLs by burst ID
    opera_static_csv = Path.cwd().parent / "linking-data/opera_rtc_static_table.csv"
    return pd.read_csv(opera_static_csv)


def was_reported(acquisition_time: datetime, scene_id: str, args: object) -> bool:
    # limit scenes to those reported in Oct 2023 flattening validation
    if args.site == "Delta Junction":
        date_regex = r"(?<=_)\d{8}T\d{6}(?=_\d{8}T\d{6})"
        acquisition_time = re.search(date_regex, scene_id)
        try:
            acquisition_time = acquisition_time.group(0)
            acquisition_time = datetime.strptime(acquisition_time, "%Y%m%dT%H%M%S")
        except AttributeError:
            raise Exception(f"Acquisition timestamp not found in scene ID: {scene_id}")

        if args.orbital_path == 94:
            start_time = datetime.strptime("20201209T032007", "%Y%m%dT%H%M%S")
            end_time = datetime.strptime("20211216T032012", "%Y%m%dT%H%M%S")
        elif args.orbital_path == 160:
            start_time = datetime.strptime("20220507T161226", "%Y%m%dT%H%M%S")
            end_time = datetime.strptime("20230713T161236", "%Y%m%dT%H%M%S")
        return start_time <= acquisition_time <= end_time
    else:
        return True


def build_url_dict(df_rtc: pd.DataFrame, df_static: pd.DataFrame, dirs, scene_id: str) -> Union[Dict, None]:
    scene_burst_dict = {
        dirs["vh_burst_dir"]: df_rtc.where(df_rtc.S1_Scene_IDs == scene_id)
        .dropna()
        .vh_url.tolist()[0]
        .split(" "),
        dirs["vv_burst_dir"]: df_rtc.where(df_rtc.S1_Scene_IDs == scene_id)
        .dropna()
        .vv_url.tolist()[0]
        .split(" "),
        dirs["mask_burst_dir"]: [],
        dirs["inc_angle_burst_dir"]: [],
        dirs["local_inc_angle_burst_dir"]: [],
    }

    # sanitize RTC URLs
    scene_burst_dict[dirs["vh_burst_dir"]] = [
        url for url in scene_burst_dict[dirs["vh_burst_dir"]] if is_valid_url(url)
    ]
    scene_burst_dict[dirs["vh_burst_dir"]] = [
        url for url in scene_burst_dict[dirs["vh_burst_dir"]] if is_valid_url(url)
    ]

    # Get burst IDs
    opera_ids = list(
        df_rtc.where(df_rtc.S1_Scene_IDs == scene_id).dropna().opera_rtc_ids
    )[0]
    burst_id_regex = r"(?<=OPERA_L2_RTC-S1_)T\d{3}-\d{6}-IW[123]"
    burst_ids = re.findall(burst_id_regex, opera_ids)

    for burst in burst_ids:
        df_burst_static = df_static.where(df_static.burst_id == burst).dropna()
        try: 
            static_url_list = df_burst_static.product_urls.iloc[0].split(" ")
        except IndexError:
            continue

        # sanitize static URLs
        static_url_list = [url for url in static_url_list if is_valid_url(url)]
        for url in static_url_list:
            if "v1.0_mask.tif" in url:
                scene_burst_dict[dirs["mask_burst_dir"]].append(url)
            elif "v1.0_incidence_angle.tif" in url:
                scene_burst_dict[dirs["inc_angle_burst_dir"]].append(url)
            elif "v1.0_local_incidence_angle.tif" in url:
                scene_burst_dict[dirs["local_inc_angle_burst_dir"]].append(url)
    burst_count = len(scene_burst_dict[dirs["vh_burst_dir"]])
    for ds in scene_burst_dict:
        if len(scene_burst_dict[ds]) != burst_count:
            print(f"Found {len(scene_burst_dict[ds])} {ds} bursts, but there were {burst_count} vh bursts.")
            return None
    return scene_burst_dict


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except AttributeError:
        return False


def download_bursts_and_static(scene_burst_dict: dict):
    for pth, urls in scene_burst_dict.items():
        for url in urls:
            local_pth = pth / url.split("/")[-1]
            if not local_pth.exists():
                earthaccess.download(url, pth)


def merge_bursts(
    burst_pth_dict: Dict[str, List[str]],
    predominant_epsg: str,
    rtc_dir: os.PathLike,
    scene_id: str,
):
    vv_merge_str = ""
    vh_merge_str = ""
    mask_merge_str = ""
    local_inc_angle_merge_str = ""
    inc_angle_merge_str = ""

    for data_type, pths in burst_pth_dict.items():
        for pth in pths:
            # build merge strings
            if data_type == "vv_bursts":
                vv_merge_str = f"{vv_merge_str} {str(pth)}"
            elif data_type == "vh_bursts":
                vh_merge_str = f"{vh_merge_str} {str(pth)}"
            elif data_type == "mask_bursts":
                mask_merge_str = f"{mask_merge_str} {str(pth)}"
            elif data_type == "local_inc_angle_bursts":
                local_inc_angle_merge_str = f"{local_inc_angle_merge_str} {str(pth)}"
            elif data_type == "inc_angle_bursts":
                inc_angle_merge_str = f"{inc_angle_merge_str} {str(pth)}"

            # project to predominant UTM (when necessary)
            if predominant_epsg:
                util.reproject_data(pth, predominant_epsg)

    no_data_val = util.get_no_data_val(burst_pth_dict["vv_bursts"][0])
    # merge vv bursts
    vv_output = rtc_dir / f"OPERA_L2_RTC-S1_VV_{scene_id}_30_v1.0_mosaic.tif"
    vv_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vv_output} {vv_merge_str}"
    print(f"Merging bursts -> {vv_output}")
    subprocess.run([vv_merge_command], shell=True)

    # merge vh bursts
    vh_output = rtc_dir / f"OPERA_L2_RTC-S1_VH_{scene_id}_30_v1.0_mosaic.tif"
    vh_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vh_output} {vh_merge_str}"
    print(f"Merging bursts -> {vh_output}")
    subprocess.run([vh_merge_command], shell=True)

    # merge layover/shadow mask bursts
    mask_output = rtc_dir / f"OPERA_L2_RTC-S1_mask_{scene_id}_30_v1.0_mosaic.tif"
    mask_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {mask_output} {mask_merge_str}"
    print(f"Merging bursts -> {mask_output}")
    subprocess.run([mask_merge_command], shell=True)

    # merge local incidence angle bursts
    local_inc_angle_output = (
        rtc_dir / f"OPERA_L2_RTC-S1_local_incidence_angle_{scene_id}_30_v1.0_mosaic.tif"
    )
    local_inc_angle_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {local_inc_angle_output} {local_inc_angle_merge_str}"
    print(f"Merging bursts -> {local_inc_angle_output}")
    subprocess.run([local_inc_angle_merge_command], shell=True)

    # merge incidence angle bursts
    inc_angle_output = (
        rtc_dir / f"OPERA_L2_RTC-S1_incidence_angle_{scene_id}_30_v1.0_mosaic.tif"
    )
    inc_angle_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {inc_angle_output} {inc_angle_merge_str}"
    print(f"Merging bursts -> {inc_angle_output}")
    subprocess.run([inc_angle_merge_command], shell=True)


def flatten(input_data_dir: os.PathLike):
    parent_data_dir = input_data_dir.parent

    data_dirs = list(input_data_dir.glob("*"))
    data_dirs = [
        str(d) for d in data_dirs if d.is_dir() and d.name.startswith("OPERA_L2-RTC")
    ]

    print(data_dirs)

    log = True  # True: log scale, False: power scale

    parameters_prep_1 = {"data_dir": ""}

    parameters_prep_2 = {"data_dir": ""}

    parameters_slope_compare = {
        "data_dir": "",
        "output_dir": "",
        "log": log,
    }

    output_parent_dir = parent_data_dir / "output_flattening_analyses"
    output_parent_dir.mkdir(exist_ok=True)

    intermediary_parent_dir = parent_data_dir / "intermediary_flattening_data"
    intermediary_parent_dir.mkdir(exist_ok=True)

    input_dirs_prep_2 = [
        intermediary_parent_dir / f"{Path(p).stem}_prepped_for_slope_comparison"
        for p in data_dirs
    ]
    input_dirs_gamma0_compare = [
        intermediary_parent_dir / f"{Path(p).name}_Tree_Cover"
        for p in input_dirs_prep_2
    ]

    with work_dir(Path.cwd().parent / "flattening"):
        for i, d in enumerate(data_dirs):
            opera_id = d.split("/")[-1]
            output_dir = (
                output_parent_dir / f"Output_Tree_Cover_Slope_Comparisons_{opera_id}"
            )
            output_dir.mkdir(exist_ok=True)

            # data prep notebook 1
            parameters_prep_1["data_dir"] = d
            output_1 = (
                output_dir / f"output_{Path(d).name}_prep_flattening_part_1.ipynb"
            )
            pm.execute_notebook(
                "data_prep/prep_flattening_part_1.ipynb",
                output_1,
                kernel_name="python3",
                parameters=parameters_prep_1,
            )
            subprocess.run([f"jupyter nbconvert {output_1} --to pdf"], shell=True)

            # data prep notebook 2
            parameters_prep_2["data_dir"] = str(input_dirs_prep_2[i])
            output_2 = (
                output_dir / f"output_{Path(d).name}_prep_flattening_part_2.ipynb"
            )
            pm.execute_notebook(
                "data_prep/prep_flattening_part_2.ipynb",
                output_2,
                kernel_name="python3",
                parameters=parameters_prep_2,
            )
            subprocess.run([f"jupyter nbconvert {output_2} --to pdf"], shell=True)

            # Gamma0 Comparisons
            parameters_slope_compare["data_dir"] = str(input_dirs_gamma0_compare[i])
            parameters_slope_compare["output_dir"] = str(output_dir)
            output_gamma0_compare = (
                output_dir / f"output_{Path(d).name}_flattening_analysis.ipynb"
            )
            pm.execute_notebook(
                "flattening_analysis/flattening_analysis.ipynb",
                output_gamma0_compare,
                kernel_name="python3",
                parameters=parameters_slope_compare,
            )
            subprocess.run(
                [f"jupyter nbconvert {output_gamma0_compare} --to pdf"], shell=True
            )


def main():
    args = parse_args()
    parent_data_dir = (
        Path.cwd().parents[1]
        / f"OPERA_L2-RTC_CalVal/OPERA_RTC_Flattening_{args.site.replace(' ', '_')}_{args.orbital_path}"
    )
    input_data_dir = parent_data_dir / "input_OPERA_data"
    input_data_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_download:
        # collect CalVal data access info
        df_rtc = get_rtc_df(args)
        df_static = get_static_df()
        scenes = list(df_rtc.S1_Scene_IDs)

        earthaccess.login()
        for scene_id in scenes:
            acquisition_time = util.get_acquisition_time(scene_id)
            if not was_reported(acquisition_time, scene_id, args):
                print(f"skipping scene: {scene_id}")
                continue

            # define/create paths to data dirs
            rtc_dir = input_data_dir / f"OPERA_L2-RTC_{scene_id}_30_v1.0"
            dirs = {
                "rtc_dir": rtc_dir,
                "vv_burst_dir": rtc_dir / "vv_bursts",
                "vh_burst_dir": rtc_dir / "vh_bursts",
                "inc_angle_burst_dir": rtc_dir / "ellipsoidal_inc_angle_bursts",
                "local_inc_angle_burst_dir": rtc_dir / "local_inc_angle_bursts",
                "mask_burst_dir": rtc_dir / "layover_shadow_bursts",
            }
            for pth in dirs.values():
                pth.mkdir(exist_ok=True, parents=True)

            # build a dict containing urls to bursts for a given scene by data type
            scene_burst_dict = build_url_dict(df_rtc, df_static, dirs, scene_id)
            if not scene_burst_dict:
                print(f"skipping scene: {scene_id}")
                continue

            # download data
            print(f"Downloading RTC bursts and static data for S1 scene: {scene_id}")
            download_bursts_and_static(scene_burst_dict)

            # collect paths to downloaded data
            vv_bursts = list(dirs["vv_burst_dir"].glob("*VV.tif"))
            vh_bursts = list(dirs["vh_burst_dir"].glob("*VH.tif"))
            mask_bursts = list(dirs["mask_burst_dir"].glob("*mask.tif"))
            local_inc_angle_bursts = list(
                dirs["local_inc_angle_burst_dir"].glob("*local_incidence_angle.tif")
            )
            inc_angle_bursts = list(
                dirs["inc_angle_burst_dir"].glob("*incidence_angle.tif")
            )

            # reproject bursts to predominant CRS (if necessary) and merge into full S1 scenes
            epsgs = util.get_projection_counts(vv_bursts)
            predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)
            merge_bursts(
                {
                    "vv_bursts": vv_bursts,
                    "vh_bursts": vh_bursts,
                    "mask_bursts": mask_bursts,
                    "local_inc_angle_bursts": local_inc_angle_bursts,
                    "inc_angle_bursts": inc_angle_bursts,
                },
                predominant_epsg,
                rtc_dir,
                scene_id,
            )
    flatten(input_data_dir)


if __name__ == "__main__":
    main()
