import papermill as pm
from pathlib import Path
import subprocess

# list of paths to OPERA-RTC mosaics on which to run absolute geolocation evaluation
data_dirs = [
    # "/home/jovyan/calval-RTC/OPERA_RTC_S1A_IW_SLC__1SDV_20230611T002830_20230611T002857_048931_05E256_1866",
]

output_dirs = [Path.cwd()/f"absolute_geolocation_{p.split('RTC_')[1]}" for p in data_dirs]


parameters = {
    "data_dir": ""
}

for i, d in enumerate(data_dirs):
    parameters['data_dir'] = d
    output_dirs[i].mkdir(exist_ok=True)
    output = output_dirs[i]/f'output_{Path(d).name}_absolute_location_evaluation.ipynb'
    pm.execute_notebook(
        'absolute_location_evaluation.ipynb',
        output,
        kernel_name='python3',
        parameters = parameters
    )
    

    subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True)    
    