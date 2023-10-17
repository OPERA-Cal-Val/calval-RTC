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
    parser.add_argument('--site', type=str, required=True, help='California, Oklahoma')
    parser.add_argument('--orbital_path', type=int, required=True, help='34, 64, 107')
    parser.add_argument('--skip_download', default=False, action='store_true')
    return parser.parse_args()


def download_mosaic_data(parent_data_dir, args):
    calval_module = 'Absolute Geolocation Evaluation'
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
        raise Exception(f"Found no entries in {s1_csv} for {site}, orbital_path {orbital_path}, {calval_module}")
    scenes = ids.split(', ') # slice this list to test run a subset of scenes

    
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
        
        
def absolute_geolocation_evaluation(parent_data_dir, args):
    data_dirs = [p for p in parent_data_dir.glob('*') if '.' not in str(p)]
    output_dirs = [p.parents[1]/f"output_OPERA_RTC_ALE_{args.site}_{args.orbital_path}/absolute_geolocation_evaluation_{p.name.split('RTC_')[1]}" 
                   for p in data_dirs]

    parameters = {
        "data_dir": "",
        "savepath": ""
    }

    with work_dir(Path.cwd().parent/"point_target-based_absolute_geolocation_evaluation"):
        for i, d in enumerate(data_dirs):
            parameters['data_dir'] = str(d)
            parameters['savepath'] = str(output_dirs[i])
            output_dirs[i].mkdir(parents=True, exist_ok=True)
            output = output_dirs[i]/f'output_{Path(d).name}_ALE_OPERA-RTC_v2.ipynb'
            pm.execute_notebook(
                Path.cwd()/'ALE_OPERA-RTC_v2.ipynb',
                output,
                kernel_name='python3',
                parameters = parameters
            )

            subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True) 


def main():
    args = parse_args()
    parent_data_dir = Path.cwd().parents[1]/f"OPERA_RTC_ALE_{args.site}_{args.orbital_path}/input_OPERA_data"
    if not args.skip_download:
        download_mosaic_data(parent_data_dir, args)
    absolute_geolocation_evaluation(parent_data_dir, args)

    
if __name__ == '__main__':
    main()
    