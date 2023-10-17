import argparse
import contextlib
import os
import pandas as pd
import papermill as pm
from pathlib import Path
import subprocess
from typing import Union

from opensarlab_lib import work_dir


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=str, required=True, help='Delta Junction, Brazil')
    parser.add_argument('--orbital_path', type=int, required=True, help='94, 160, 170')
    parser.add_argument('--skip_download', default=False, action='store_true',
                        help="Skip downloading and mosaicking of bursts and validate previously prepared data.")
    parser.add_argument('--delete_intermediary', default=False, action='store_true',
                        help="Delete intermediary data: copies of original rasters, flattened rasters, flattened-tiled rasters, coregistration json results")
    return parser.parse_args()


def download_mosaic_data(parent_data_dir, args):
    calval_module = 'Coregistration'
    # Read S1 scene IDs from OPERA-RTC_CalVal_S1_Scene_IDs.csv
    s1_csv = Path.cwd().parent/'OPERA-RTC_CalVal_S1_Scene_IDs.csv'
    df = pd.read_csv(s1_csv)
    df = df.where((df.Site == args.site) & 
                  (df.Orbital_Path == args.orbital_path) & 
                  (df.CalVal_Module == calval_module)).dropna()
    if len(df) == 1:
        ids = df.iloc[0].S1_Scene_IDs
    elif len(df) > 1:
        raise Exception(f"Found multiple entries in {s1_csv} for {args.site}, orbital_path {args.orbital_path}, {calval_module}")
    else:
        raise Exception(f"Found no entries in {s1_csv} for {args.site}, orbital_path {args.orbital_path}, {calval_module}")
    scenes = ids.split(', ')[:4] # slice this list to test run a subset of scenes

    
    data_download_parameters = {
        "scene": "",
        "opera_dir": str(parent_data_dir), # parent directory in which OPERA RTC directories will be stored
        "keep_date_index": -1 # 0: oldest sample, -1: most recent sample, -2: 2nd to most recent sample, etc...
    }

    Path(data_download_parameters["opera_dir"]).mkdir(parents=True, exist_ok=True)

    for s in scenes:
        output_path = str(Path.cwd().parent/f'output_{s}_OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb')
        data_download_parameters['scene'] = s
        pm.execute_notebook(
            str(Path.cwd().parent/'OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb'),
            output_path,
            kernel_name='python3',
            parameters = data_download_parameters
        )
        Path(output_path).unlink()
        
        
def coregistration(parent_data_dir, args):           
    
    # True to delete mosaicked RTCs and static files, False to save
    delete_mosaics = False


    output_dir = parent_data_dir.parent/f"output_Coregistration"

    polarizations = ['vv', 'vh']

    # for i, d in enumerate(stack_dirs):
    for p in polarizations:  
        # comment out any file types in cleanup_list that you wish to save
        # uncomment those to delete
        
        if args.delete_intermediary:
            cleanup_list = (
                f"{p} amplitude data, "
                f"flattened {p} amplitude data, "
                f"flattened and tiled {p} amplitude data, "
                f"{p} tile correlation results, "
                f", " #don't remove if cleanup list empty
            )
        else:
            cleanup_list = ''
        
        parameters = {
            "polarization": p,
            "stack_dir": str(parent_data_dir),
            "delete_mosaics": delete_mosaics,
            "cleanup_list": cleanup_list,     
        }
        
        output_dir.mkdir(exist_ok=True)
        output = output_dir/f"output_{args.site.replace(' ', '_')}_{args.orbital_path}_{p}_OPERA_RTC_Coregistration.ipynb"
        
        with work_dir(Path.cwd().parent/"cross_correlation_relative_geolocation_evaluation"):
            pm.execute_notebook(
                'OPERA_RTC_Cross_Correlation.ipynb',
                output,
                kernel_name='python3',
                parameters = parameters
            )

            subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True)  


def main():
    args = parse_args()
    parent_data_dir = Path.cwd().parents[1]/f"OPERA_RTC_Coregistration_{args.site.replace(' ', '_')}_{args.orbital_path}/input_OPERA_data"
    if not args.skip_download:
        download_mosaic_data(parent_data_dir, args)
    coregistration(parent_data_dir, args)

    
if __name__ == '__main__':
    main()
    