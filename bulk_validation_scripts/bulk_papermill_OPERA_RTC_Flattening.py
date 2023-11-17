import argparse
import contextlib
import os
import pandas as pd
import papermill as pm
from pathlib import Path
import re
import subprocess
import sys
from typing import Union
from tqdm.auto import tqdm
from urllib import request
import urllib.error
from zipfile import ZipFile

from osgeo import gdal
gdal.UseExceptions()

from opensarlab_lib import work_dir

current = Path('..').resolve()
sys.path.append(str(current))
import util.geo as util


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=str, required=True, help='Vermont, Delta Junction, Brazil')
    parser.add_argument('--orbital_path', type=int, required=True, help='135, 113, 94, 160, 39')
    parser.add_argument('--skip_download', default=False, action='store_true',
                        help="Skip downloading and mosaicking of bursts and validate previously prepared data.")
    return parser.parse_args()


def download_mosaic_data(input_data_dir, args):

    
    opera_rtc_csv_zip_path = Path.cwd().parent/"linking-data/opera_rtc_table.csv.zip"
    opera_rtc_csv = Path.cwd().parent/'linking-data/opera_rtc_table.csv'
    if not opera_rtc_csv.exists():
        with ZipFile(opera_rtc_csv_zip_path, 'r') as zObject: 
            zObject.extractall(path=opera_rtc_csv_zip_path.parent)

    # load dataframe with burst urls for site/calval module
    calval_module = 'Flattening'
    df_rtc = pd.read_csv(opera_rtc_csv)
    df_rtc = df_rtc.where((df_rtc.Site == args.site) & 
                  (df_rtc.Orbital_Path == args.orbital_path) & 
                  (df_rtc.CalVal_Module == calval_module)).dropna()
    
    # load dataframe with static file URLs by burst ID
    opera_static_csv_zip_path = Path.cwd().parent/"linking-data/opera_rtc_static_table.csv.zip"
    opera_static_csv = Path.cwd().parent/'linking-data/opera_rtc_static_table.csv'    
    if not opera_static_csv.exists():
        with ZipFile(opera_static_csv_zip_path, 'r') as zObject: 
            zObject.extractall(path=opera_static_csv_zip_path.parent) 
    df_static = pd.read_csv(opera_static_csv)      
    
    
    for scene_id in df_rtc.S1_Scene_IDs[]:
        # define/create paths to data dirs
        rtc_dir = input_data_dir/f"OPERA_L2-RTC_{scene_id}_30_v1.0"
        vv_burst_dir = rtc_dir/"vv_bursts"
        vh_burst_dir = rtc_dir/"vh_bursts"
        inc_angle_burst_dir = rtc_dir/"ellipsoidal_inc_angle_bursts"
        local_inc_angle_burst_dir = rtc_dir/"local_inc_angle_bursts"
        mask_burst_dir = rtc_dir/"layover_shadow_bursts"
        for pth in [rtc_dir, vv_burst_dir, vh_burst_dir, inc_angle_burst_dir, 
                    local_inc_angle_burst_dir, mask_burst_dir]:
            pth.mkdir(exist_ok=True, parents=True)

        scene_burst_dict = {
            vh_burst_dir: df_rtc.where(df_rtc.S1_Scene_IDs==scene_id).dropna().vh_url.tolist()[0].split(' '),
            vv_burst_dir: df_rtc.where(df_rtc.S1_Scene_IDs==scene_id).dropna().vv_url.tolist()[0].split(' '),
            mask_burst_dir: [],
            inc_angle_burst_dir: [],
            local_inc_angle_burst_dir: []
        }

        # Get burst IDs
        opera_ids = list(df_rtc.where(df_rtc.S1_Scene_IDs == scene_id).dropna().opera_rtc_ids)[0]
        burst_id_regex = r"(?<=OPERA_L2_RTC-S1_)T\d{3}-\d{6}-IW[123]"
        burst_ids = re.findall(burst_id_regex, opera_ids)

        for burst in burst_ids:
            df_burst_static = df_static.where(df_static.burst_id == burst).dropna()
            static_url_list = df_burst_static.product_urls.iloc[0].split(' ')
            for url in static_url_list:
                if "v1.0_mask.tif" in url:
                    scene_burst_dict[mask_burst_dir].append(url)
                elif "v1.0_incidence_angle.tif" in url:
                    scene_burst_dict[inc_angle_burst_dir].append(url)
                elif "v1.0_local_incidence_angle.tif" in url:
                    scene_burst_dict[local_inc_angle_burst_dir].append(url)
        burst_count = len(scene_burst_dict[vh_burst_dir])
        for ds in scene_burst_dict:
            if len(scene_burst_dict[ds]) != burst_count:
                raise Exception(f"Found {len(scene_burst_dict[ds])} {ds} bursts, but there were {burst_count} vh bursts.")

        # download bursts
        for pth in scene_burst_dict:
            for burst in scene_burst_dict[pth]:
                if not (pth/burst.split('/')[-1]).exists():
                    try:
                        response = request.urlretrieve(burst, pth/burst.split('/')[-1])
                    except urllib.error.HTTPError:
                        print(burst)
                        raise

        # Collect paths to downloaded bursts
        vv_bursts = list(vv_burst_dir.glob('*VV.tif'))
        vh_bursts = list(vh_burst_dir.glob('*VH.tif'))
        mask_bursts = list(mask_burst_dir.glob('*mask.tif'))
        local_inc_angle_bursts = list(local_inc_angle_burst_dir.glob('*local_incidence_angle.tif'))
        inc_angle_bursts = list(inc_angle_burst_dir.glob('*incidence_angle.tif'))

        epsgs = util.get_projection_counts(vv_bursts)
        predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)

        vv_merge_str = ''
        vh_merge_str = ''
        mask_merge_str = ''
        local_inc_angle_merge_str = ''
        inc_angle_merge_str = ''
        for bursts in [vv_bursts, vh_bursts, mask_bursts, local_inc_angle_bursts, inc_angle_bursts]:
            for pth in bursts:
                #build merge strings
                if 'VV.tif' in str(pth):
                    vv_merge_str = f"{vv_merge_str} {str(pth)}" 
                elif 'VH.tif' in str(pth):
                    vh_merge_str = f"{vh_merge_str} {str(pth)}"
                elif 'mask.tif' in str(pth):
                    mask_merge_str = f"{mask_merge_str} {str(pth)}"
                elif 'incidence_angle.tif' in str(pth):
                    if 'local' in str(pth):
                        local_inc_angle_merge_str = f"{local_inc_angle_merge_str} {str(pth)}"
                    else:
                        inc_angle_merge_str = f"{inc_angle_merge_str} {str(pth)}"

                # project to predominant UTM (when necessary)
                if predominant_epsg:
                    print(pth)
                    src_SRS = util.get_projection(str(pth))
                    if src_SRS != predominant_epsg:
                        res = util.get_res(pth)
                        no_data_val = util.get_no_data_val(pth)
                        temp = pth.parent/f"temp_{pth.stem}.tif"
                        pth.rename(temp)

                        warp_options = {
                            "dstSRS":f"EPSG:{predominant_epsg}", "srcSRS":f"EPSG:{src_SRS}",
                            "targetAlignedPixels":True,
                            "xRes":res, "yRes":res,
                            "dstNodata": no_data_val
                        }
                        gdal.Warp(str(pth), str(temp), **warp_options)
                        temp.unlink()

        no_data_val = util.get_no_data_val(vv_bursts[0])
        # merge vv bursts
        vv_output = rtc_dir/f"OPERA_L2_RTC-S1_VV_{scene_id}_30_v1.0_mosaic.tif"
        vv_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vv_output} {vv_merge_str}"
        print(f"Merging bursts -> {vv_output}")
        subprocess.run([vv_merge_command], shell=True)  

        # merge vh bursts
        vh_output = rtc_dir/f"OPERA_L2_RTC-S1_VH_{scene_id}_30_v1.0_mosaic.tif"
        vh_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vh_output} {vh_merge_str}"
        print(f"Merging bursts -> {vh_output}")
        subprocess.run([vh_merge_command], shell=True)      

        # merge layover/shadow mask bursts
        mask_output = rtc_dir/f"OPERA_L2_RTC-S1_mask_{scene_id}_30_v1.0_mosaic.tif"
        mask_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {mask_output} {mask_merge_str}"
        print(f"Merging bursts -> {mask_output}")
        subprocess.run([mask_merge_command], shell=True) 

        # merge local incidence angle bursts
        local_inc_angle_output = rtc_dir/f"OPERA_L2_RTC-S1_local_incidence_angle_{scene_id}_30_v1.0_mosaic.tif"
        local_inc_angle_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {local_inc_angle_output} {local_inc_angle_merge_str}"
        print(f"Merging bursts -> {local_inc_angle_output}")
        subprocess.run([local_inc_angle_merge_command], shell=True) 

        # merge incidence angle bursts
        inc_angle_output = rtc_dir/f"OPERA_L2_RTC-S1_incidence_angle_{scene_id}_30_v1.0_mosaic.tif"
        inc_angle_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {inc_angle_output} {inc_angle_merge_str}"
        print(f"Merging bursts -> {inc_angle_output}")
        subprocess.run([inc_angle_merge_command], shell=True)
    
        
def flatten(input_data_dir): 
    parent_data_dir = input_data_dir.parent
    
    data_dirs = list(input_data_dir.glob('*'))
    data_dirs = [str(d) for d in data_dirs if d.is_dir() and d.name.startswith('OPERA_L2-RTC')]
    
    print(data_dirs)

    log = True # True: log scale, False: power scale

    parameters_prep_1 = {
        "data_dir": ""
    }

    parameters_prep_2 = {
        "data_dir": ""
    }

    parameters_slope_compare = {
        "data_dir": "",
        "output_dir": "",
        "log": log,
    }
    
    output_parent_dir = parent_data_dir/"output_flattening_analyses"
    output_parent_dir.mkdir(exist_ok=True)
    
    intermediary_parent_dir = parent_data_dir/f"intermediary_flattening_data"
    intermediary_parent_dir.mkdir(exist_ok=True)    

    input_dirs_prep_2 = [intermediary_parent_dir/f"{Path(p).stem}_prepped_for_slope_comparison" for p in data_dirs]
    input_dirs_gamma0_compare = [intermediary_parent_dir/f"{Path(p).name}_Tree_Cover" for p in input_dirs_prep_2]

    with work_dir(Path.cwd().parent/"compare_gamma0_on_foreslope_flat_backslope"):
        for i, d in enumerate(data_dirs):
            opera_id = d.split('/')[-1]
            output_dir = output_parent_dir/f"Output_Tree_Cover_Slope_Comparisons_{opera_id}"
            output_dir.mkdir(exist_ok=True)

            ####### data prep notebook 1 #######
            parameters_prep_1['data_dir'] = d
            output_1 = output_dir/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb'
            pm.execute_notebook(
                'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb',
                output_1,
                kernel_name='python3',
                parameters = parameters_prep_1
            )
            subprocess.run([f"jupyter nbconvert {output_1} --to pdf"], shell=True) 

            ####### data prep notebook 2 #######
            parameters_prep_2['data_dir'] = str(input_dirs_prep_2[i])
            output_2 = output_dir/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb'
            pm.execute_notebook(
                'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb',
                output_2,
                kernel_name='python3',
                parameters = parameters_prep_2
            )
            subprocess.run([f"jupyter nbconvert {output_2} --to pdf"], shell=True) 

            ####### Gamma0 Comparisons #######
            parameters_slope_compare['data_dir'] = str(input_dirs_gamma0_compare[i])
            parameters_slope_compare['output_dir'] = str(output_dir)
            output_gamma0_compare = output_dir/f'output_{Path(d).name}_Backscatter_Distributions_by_Slope.ipynb'
            pm.execute_notebook(
                'gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb',
                output_gamma0_compare,
                kernel_name='python3',
                parameters = parameters_slope_compare
            )
            subprocess.run([f"jupyter nbconvert {output_gamma0_compare} --to pdf"], shell=True)
    
#     # list of paths to OPERA-RTC mosaics on which to run gamma0 comparisons on foreslopes, flat areas, and backslopes
#     data_dirs = [
#         "/home/jovyan/calval-RTC/OPERA_RTC_S1A_IW_SLC__1SDV_20230707T015044_20230707T015112_049311_05Edf_rtc6_1A68",
#     ]

#     log = True # True: log scale, False: power scale

#     parameters_prep_1 = {
#         "data_dir": ""
#     }

#     parameters_prep_2 = {
#         "data_dir": ""
#     }

#     parameters_slope_compare = {
#         "data_dir": "",
#         "log": log,
#     }


#     input_dirs_prep_2 = [Path(p).parent/f"{Path(p).stem}_prepped_for_slope_comparison" for p in data_dirs]

#     input_dirs_gamma0_compare = [Path(p).parent/f"{Path(p).name}_Tree_Cover" for p in input_dirs_prep_2]

#     for i, d in enumerate(data_dirs):
#         opera_id = d.split('/')[-1]
#         output_dir = Path(d).parent/f"Output_Tree_Cover_Slope_Comparisons_{opera_id}"
#         output_dir.mkdir(exist_ok=True)

#         ####### data prep notebook 1 #######
#         parameters_prep_1['data_dir'] = d
#         output_1 = output_dir/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb'
#         pm.execute_notebook(
#             'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb',
#             output_1,
#             kernel_name='python3',
#             parameters = parameters_prep_1
#         )
#         subprocess.run([f"jupyter nbconvert {output_1} --to pdf_rtc"], shell=True) 

#         ####### data prep notebook 2 #######
#         parameters_prep_2['data_dir'] = str(input_dirs_prep_2[i])
#         output_2 = output_dir/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb'
#         pm.execute_notebook(
#             'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb',
#             output_2,
#             kernel_name='python3',
#             parameters = parameters_prep_2
#         )
#         subprocess.run([f"jupyter nbconvert {output_2} --to pdf_rtc"], shell=True) 

#         ####### Gamma0 Comparisons #######
#         parameters_slope_compare['data_dir'] = str(input_dirs_gamma0_compare[i])
#         output_gamma0_compare = output_dir/f'output_{Path(d).name}_Backscatter_Distributions_by_Slope.ipynb'
#         pm.execute_notebook(
#             'gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb',
#             output_gamma0_compare,
#             kernel_name='python3',
#             parameters = parameters_slope_compare
#         )
#         subprocess.run([f"jupyter nbconvert {output_gamma0_compare} --to pdf_rtc"], shell=True) 


def main():
    args = parse_args()
    parent_data_dir = Path.cwd().parents[1]/f"OPERA_RTC_Flattening_{args.site.replace(' ', '_')}_{args.orbital_path}"
    input_data_dir = parent_data_dir/"input_OPERA_data"
    input_data_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_download:
        download_mosaic_data(input_data_dir, args)
    flatten(input_data_dir)

    
if __name__ == '__main__':
    main()
    