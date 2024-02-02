import argparse
import contextlib
from datetime import datetime
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
from zipfile import ZipFile

from osgeo import gdal
gdal.UseExceptions()

from opensarlab_lib import work_dir

current = Path('..').resolve()
sys.path.append(str(current))
import util.geo as util


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
    # unzip linked_data.csv
    zip_path = Path.cwd().parent/"linking-data/opera_rtc_table.csv.zip"
    linked_data_csv = Path.cwd().parent/'linking-data/opera_rtc_table.csv'
    if not linked_data_csv.exists():
        with ZipFile(zip_path, 'r') as zObject: 
            zObject.extractall(path=zip_path.parent)
    
    # load burst urls for site/calval module
    calval_module = 'Coregistration'
    df = pd.read_csv(linked_data_csv)
    df = df.where((df.Site == args.site) & 
                  (df.Orbital_Path == args.orbital_path) & 
                  (df.CalVal_Module == calval_module)).dropna()
    
    scenes = list(df.S1_Scene_IDs)
    for s in tqdm(scenes):
        # define/create paths to data dirs
        rtc_dir = parent_data_dir/f"OPERA_L2-RTC_{s}_30_v1.0"
        vv_burst_dir = rtc_dir/"vv_bursts"
        vh_burst_dir = rtc_dir/"vh_bursts"
        
        # collect acquisition date
        date_regex = r"(?<=_)\d{8}T\d{6}(?=_\d{8}T\d{6})"
        acquisition_time = re.search(date_regex, s)
        try:
            acquisition_time = acquisition_time.group(0)
            acquisition_time = datetime.strptime(acquisition_time, '%Y%m%dT%H%M%S')
        except AttributeError:
            raise Exception(f"Acquisition timestamp not found in scene ID: {s}")      
          
        # limit scenes to those reported in Oct 2023
        if args.site == 'Delta Junction':  
            if args.orbital_path == 94:
                start_time = datetime.strptime("20201209T032007", '%Y%m%dT%H%M%S')
                end_time = datetime.strptime("20211216T032012", '%Y%m%dT%H%M%S')
            elif args.orbital_path == 160:
                start_time = datetime.strptime("20220507T161226", '%Y%m%dT%H%M%S')
                end_time = datetime.strptime("20230713T161236", '%Y%m%dT%H%M%S')
        else:
                start_time = datetime.strptime("20210606T090048", '%Y%m%dT%H%M%S')
                end_time = datetime.strptime("20220508T090052", '%Y%m%dT%H%M%S')
        if not start_time <= acquisition_time <= end_time:
            continue
          
        # create data directories                                         
        for pth in [rtc_dir, vv_burst_dir, vh_burst_dir]:
            pth.mkdir(exist_ok=True, parents=True)
        
        # download bursts
        vv_urls = df.where(df.S1_Scene_IDs==s).dropna().vv_url.tolist()[0].split(' ')
        vh_urls = df.where(df.S1_Scene_IDs==s).dropna().vh_url.tolist()[0].split(' ')
        path_dict = {vv_burst_dir: vv_urls, vh_burst_dir: vh_urls}
        print(f"Downloading bursts for S1 scene: {s}")
        for pth in path_dict:
            for burst in path_dict[pth]:
                try:
                    print(f"Burst: {burst.split('/')[-1]}")
                    response = request.urlretrieve(burst, pth/burst.split('/')[-1])
                except urllib.error.HTTPError:
                    print(f'Failed download: {burst}')
                    # raise
                    pass
                
        vv_bursts = list(vv_burst_dir.glob('*VV.tif'))
        vh_bursts = list(vh_burst_dir.glob('*VH.tif'))
        epsgs = util.get_projection_counts(vv_bursts)
        predominant_epsg = None if len(epsgs) == 1 else max(epsgs, key=epsgs.get)
        
        vv_merge_str = ''
        vh_merge_str = ''
        for bursts in [vv_bursts, vh_bursts]:
            for pth in bursts:
                #build merge strings
                if 'VV.tif' in str(pth):
                    vv_merge_str = f"{vv_merge_str} {str(pth)}" 
                elif 'VH.tif' in str(pth):
                    vh_merge_str = f"{vh_merge_str} {str(pth)}"
                    
                # project to predominant UTM (when necessary)
                if predominant_epsg:
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
        vv_output = rtc_dir/f"OPERA_L2_RTC-S1_VV_{s}_30_v1.0_mosaic.tif"
        vv_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vv_output} {vv_merge_str}"
        print(f"Merging bursts -> {vv_output}")
        subprocess.run([vv_merge_command], shell=True)  
        # merge vh bursts
        vh_output = rtc_dir/f"OPERA_L2_RTC-S1_VH_{s}_30_v1.0_mosaic.tif"
        vh_merge_command = f"gdal_merge.py -n {no_data_val} -a_nodata {no_data_val} -o {vh_output} {vh_merge_str}"
        print(f"Merging bursts -> {vh_output}")
        subprocess.run([vh_merge_command], shell=True)       
        
        
        
def coregistration(parent_data_dir, args):           
    
    # True to delete mosaicked RTCs and static files, False to save
    delete_mosaics = False


    output_dir = parent_data_dir.parent/f"output_Coregistration"

    polarizations = ['VV', 'VH']

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
            cleanup_list = ''
        
        parameters = {
            "polarization": p,
            "stack_dir": str(parent_data_dir),
            "delete_mosaics": delete_mosaics,
            "cleanup_list": cleanup_list,     
        }
        
        output_dir.mkdir(exist_ok=True)
        output = output_dir/f"output_{args.site.replace(' ', '_')}_{args.orbital_path}_{p}_OPERA_RTC_Coregistration.ipynb"
        
        with work_dir(Path.cwd().parent/"coregistration"):
            pm.execute_notebook(
                'coregistration.ipynb',
                output,
                kernel_name='python3',
                parameters = parameters
            )

            subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True)  


def main():
    args = parse_args()
    parent_data_dir = Path.cwd().parents[1]/f"OPERA_L2-RTC_CalVal/OPERA_RTC_Coregistration_{args.site.replace(' ', '_')}_{args.orbital_path}/input_OPERA_data"
    if not args.skip_download:
        download_mosaic_data(parent_data_dir, args)
    coregistration(parent_data_dir, args)

    
if __name__ == '__main__':
    main()
    