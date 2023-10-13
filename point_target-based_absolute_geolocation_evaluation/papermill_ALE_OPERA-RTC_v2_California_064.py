import papermill as pm
from pathlib import Path
import subprocess

parent_data_dir = Path.cwd().parents[1]/"OPERA_RTC_ALE_California_64/input_OPERA_data"

data_dirs = list(parent_data_dir.glob('*'))

output_dirs = [p.parents[1]/f"output_OPERA_RTC_ALE_California_64/absolute_geolocation_evaluation_{p.name.split('RTC_')[1]}" 
               for p in data_dirs]

parameters = {
    "data_dir": "",
    "savepath": ""
}

for i, d in enumerate(data_dirs):
    parameters['data_dir'] = str(d)
    parameters['savepath'] = str(output_dirs[i])
    output_dirs[i].mkdir(parents=True, exist_ok=True)
    output = output_dirs[i]/f'output_{Path(d).name}_ALE_OPERA-RTC_v2.ipynb'
    pm.execute_notebook(
        'ALE_OPERA-RTC_v2.ipynb',
        output,
        kernel_name='python3',
        parameters = parameters
    )
    
    subprocess.run([f"jupyter nbconvert {output} --to pdf"], shell=True)    
    