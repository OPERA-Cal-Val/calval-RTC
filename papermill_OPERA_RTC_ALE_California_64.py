import contextlib
import os
import pandas as pd
import papermill as pm
from pathlib import Path
import subprocess
from typing import Union

@contextlib.contextmanager
def work_dir(work_pth: Union[Path, str]):
    """
    Usage:
    with work_dir(work_pth):
        do_things()
    """
    cwd = Path.cwd()
    os.chdir(work_pth)
    try:
        yield
    finally:
        os.chdir(cwd)

s1_csv = Path.cwd()/"OPERA-RTC_CalVal_S1_Scene_IDs.csv"
site = 'California'
orbital_path = 64
calval_module = 'Absolute Geolocation Evaluation'

df = pd.read_csv(s1_csv)
df = df.where((df.Site == site) & 
              (df.Orbital_Path == orbital_path) & 
              (df.CalVal_Module == calval_module)).dropna()
if len(df) == 1:
    ids = df.iloc[0].S1_Scene_IDs
else:
    raise Exception(f"Found multiple entries in {s1_csv} for {site}, orbital_path {orbital_path}, {calval_module}")

# list of Sentinel-1 scene IDs for which to download and mosaic bursts
scenes = ids.split(', ')[:2]

parameters = {
    "scene": "",
    "opera_dir": str(Path.cwd().parent/f"OPERA_RTC_ALE_California_{orbital_path}/input_OPERA_data"), # parent directory in which OPERA RTC directories will be stored
    "keep_date_index": -1 # 0: oldest sample, -1: most recent sample, -2: 2nd to most recent sample, etc...

}

Path(parameters["opera_dir"]).mkdir(parents=True, exist_ok=True)

for s in scenes:
    parameters['scene'] = s
    pm.execute_notebook(
        'OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb',
        f'output_{s}_OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb',
        kernel_name='python3',
        parameters = parameters
    )

with work_dir(Path.cwd()/'point_target-based_absolute_geolocation_evaluation'):
    subprocess.run([f"python papermill_ALE_OPERA-RTC_v2_California_064.py"], shell=True) 
