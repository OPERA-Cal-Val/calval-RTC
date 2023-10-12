import papermill as pm
from pathlib import Path

# list of Sentinel-1 scene IDs for which to download and mosaic bursts
scenes = [
    # "S1A_IW_SLC__1SDV_20230523T003658_20230523T003725_048654_05DA0F_0047", 
    
]

parameters = {
    "scene": "",
    "opera_dir": str(Path.cwd()), # directory in which OPERA RTC output directories will be stored
    "keep_date_index": -1 # 0: oldest sample, -1: most recent sample, -2: 2nd to most recent sample, etc...

}

for s in scenes:
    parameters['scene'] = s
    pm.execute_notebook(
        'OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb',
        f'output_{s}_OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb',
        kernel_name='python3',
        parameters = parameters
    )
    