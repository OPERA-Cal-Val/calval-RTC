import argparse
import os
import pandas as pd
import papermill as pm
from pathlib import Path
import subprocess
import sys
from typing import Union
from tqdm.auto import tqdm
from urllib import request
from zipfile import ZipFile

from osgeo import gdal
gdal.UseExceptions()

from opensarlab_lib import work_dir

current = Path('..').resolve()
sys.path.append(str(current))
import util.geo as util


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=str, required=True, help='California, Oklahoma')
    parser.add_argument('--orbital_path', type=int, required=True, help='34, 64, 107')
    parser.add_argument('--skip_download', default=False, action='store_true',
                        help="Skip downloading and mosaicking of bursts and validate previously prepared data.")
    return parser.parse_args()


def download_mosaic_data(parent_data_dir, args):
    # unzip linked_data.csv
    zip_path = Path.cwd().parent/"linking-data/opera_rtc_table.csv.zip"
    linked_data_csv = Path.cwd().parent/'linking-data/opera_rtc_table.csv'
    if not linked_data_csv.exists():
        with ZipFile(zip_path, 'r') as zObject: 
            zObject.extractall(path=zip_path.parent)
    
    # load burst urls for site/calval module
    calval_module = 'Absolute Geolocation Evaluation'
    df = pd.read_csv(linked_data_csv)
    df = df.where((df.Site == "California") & 
                  (df.Orbital_Path == 64) & 
                  (df.CalVal_Module == calval_module)).dropna()
    
    scenes = list(df.S1_Scene_IDs)
    for s in tqdm(scenes):
        # define/create paths to data dirs
        rtc_dir = parent_data_dir/f"OPERA_L2-RTC_{s}_30_v1.0"
        rtc_dir.mkdir(exist_ok=True, parents=True)
        vv_burst_dir = rtc_dir/"vv_bursts"
        vv_burst_dir.mkdir(exist_ok=True, parents=True)

        # download burst
        vv_urls = df.where(df.S1_Scene_IDs==s).dropna().vv_url.tolist()[0].split(' ')
        for burst in vv_urls:
            response = request.urlretrieve(burst, vv_burst_dir/burst.split('/')[-1])

        vv_bursts = list(vv_burst_dir.glob('*VV.tif'))
        epsgs = util.get_projection_counts(vv_bursts)
        predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)

        if predominant_epsg:
            # project bursts to predominant UTM, when necessary
            for pth in vv_bursts:
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

        # build a string of bursts to merge
        merge_str = ''
        for pth in vv_bursts:
            merge_str = f"{merge_str} {str(pth)}"

        # merge bursts
        no_data_val = util.get_no_data_val(vv_bursts[0])
        output = rtc_dir/f"OPERA_L2_RTC-S1_VV_{s}_30_v1.0_mosaic.tif"
        merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {output} {merge_str}"
        print(f"Merging bursts -> {output}")
        subprocess.run([merge_command], shell=True) 
        
        
def absolute_geolocation_evaluation(parent_data_dir, args):
    data_dirs = [p for p in parent_data_dir.glob('*') if not str(p.name).startswith('.')]

    output_dirs = [p.parents[1]/f"output_OPERA_RTC_ALE_{args.site}_{args.orbital_path}/absolute_geolocation_evaluation_{p.name.split('RTC_')[1]}" 
                   for p in data_dirs]

    parameters = {
        "data_dir": "",
        "savepath": ""
    }

    with work_dir(Path.cwd().parent/"absolute_geolocation_evaluation"):
        for i, d in enumerate(tqdm(data_dirs)):
            print(f"Performing Absolute Geolocation Evaluation on {d}")
            parameters['data_dir'] = str(d)
            parameters['savepath'] = str(output_dirs[i])
            output_dirs[i].mkdir(parents=True, exist_ok=True)
            output = output_dirs[i]/f'output_{Path(d).name}_absolute_location_evaluation.ipynb'
            pm.execute_notebook(
                Path.cwd()/'absolute_location_evaluation.ipynb',
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
    