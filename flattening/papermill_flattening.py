import papermill as pm
from pathlib import Path
import re
import subprocess

# list of paths to OPERA-RTC mosaics on which to run gamma0 comparisons on foreslopes, flat areas, and backslopes
data_dirs = [
    "/home/jovyan/calval-RTC/OPERA_RTC_S1A_IW_SLC__1SDV_20230707T015044_20230707T015112_049311_05EDF6_1A68",
]

log = True # True: log scale, False: power scale

parameters_prep_1 = {
    "data_dir": ""
}

parameters_prep_2 = {
    "data_dir": ""
}

parameters_slope_compare = {
    "data_dir": "",
    "log": log,
}


input_dirs_prep_2 = [Path(p).parent/f"{Path(p).stem}_prepped_for_slope_comparison" for p in data_dirs]

input_dirs_gamma0_compare = [Path(p).parent/f"{Path(p).name}_Tree_Cover" for p in input_dirs_prep_2]

for i, d in enumerate(data_dirs):
    opera_id = d.split('/')[-1]
    output_dir = Path(d).parent/f"Output_Tree_Cover_Slope_Comparisons_{opera_id}"
    output_dir.mkdir(exist_ok=True)
    
    ####### data prep notebook 1 #######
    parameters_prep_1['data_dir'] = d
    output_1 = output_dir/f'output_{Path(d).name}_prep_flattening_part_1.ipynb'
    pm.execute_notebook(
        'data_prep/prep_flattening_part_1.ipynb',
        output_1,
        kernel_name='python3',
        parameters = parameters_prep_1
    )
    subprocess.run([f"jupyter nbconvert {output_1} --to pdf"], shell=True) 
    
    ####### data prep notebook 2 #######
    parameters_prep_2['data_dir'] = str(input_dirs_prep_2[i])
    output_2 = output_dir/f'output_{Path(d).name}_prep_flattening_part_2.ipynb'
    pm.execute_notebook(
        'data_prep/prep_flattening_part_2.ipynb',
        output_2,
        kernel_name='python3',
        parameters = parameters_prep_2
    )
    subprocess.run([f"jupyter nbconvert {output_2} --to pdf"], shell=True) 
    
    ####### Gamma0 Comparisons #######
    parameters_slope_compare['data_dir'] = str(input_dirs_gamma0_compare[i])
    output_gamma0_compare = output_dir/f'output_{Path(d).name}_flattening_analysis.ipynb'
    pm.execute_notebook(
        'flattening_analysis/flattening_analysis.ipynb',
        output_gamma0_compare,
        kernel_name='python3',
        parameters = parameters_slope_compare
    )
    subprocess.run([f"jupyter nbconvert {output_gamma0_compare} --to pdf"], shell=True) 
    