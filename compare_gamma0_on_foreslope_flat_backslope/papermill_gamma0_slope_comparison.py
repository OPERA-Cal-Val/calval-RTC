import papermill as pm
from pathlib import Path
import subprocess

# list of paths to OPERA-RTC mosaics on which to run gamma0 comparisons on foreslopes, flat areas, and backslopes
data_dirs = [
    "/home/jovyan/calval-RTC/amazon_slope_compare/OPERA_RTC_S1A_IW_SLC__1SDV_20210516T092213_20210516T092241_037911_047968_C84C",
]

log = True # True: log scale, False: power scale
save = True # True: save plots as pngs, False: don't save plots

parameters_prep_1 = {
    "data_dir": ""
}

parameters_prep_2 = {
    "data_dir": ""
}

parameters_prep_3 = {
    "data_dir": "",
    "resolution": 30.0
}

parameters_slope_compare = {
    "data_dir": "",
    "log": log
    "save": save 
}

output_dirs_prep_1 = [Path(f"{p}_prepped_for_calval") for p in data_dirs]
output_dirs_prep_2 = [Path(p).parent/"Tree_Cover" for p in output_dirs_prep_1]

for i, d in enumerate(data_dirs):
    
    ### data prep notebook 1 ###
    parameters_prep_1['data_dir'] = d
    
    output_dirs_prep_1[i].mkdir(exist_ok=True)
    output_1 = output_dirs_prep_1[i]/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb'
    pm.execute_notebook(
        'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb',
        output_1,
        kernel_name='python3',
        parameters = parameters_prep_1
    )
    subprocess.run([f"jupyter nbconvert {output_1} --to pdf"], shell=True) 
    
    ### data prep notebook 2 ###
    parameters_prep_2['data_dir'] = str(output_dirs_prep_1[i])
    output_dirs_prep_2[i].mkdir(exist_ok=True)
    output_2 = output_dirs_prep_2[i]/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb'
    pm.execute_notebook(
        'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb',
        output_2,
        kernel_name='python3',
        parameters = parameters_prep_2
    )
    subprocess.run([f"jupyter nbconvert {output_2} --to pdf"], shell=True) 
    
    ### data prep notebook 3 ###
    parameters_prep_3['data_dir'] = str(output_dirs_prep_2[i])
    output_3 = output_dirs_prep_2[i]/f'output_{Path(d).name}_Prep_OPERA_RTC_CalVal_Slope_Compare_Part_3.ipynb'
    pm.execute_notebook(
        'data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_3.ipynb',
        output_3,
        kernel_name='python3',
        parameters = parameters_prep_3
    )
    subprocess.run([f"jupyter nbconvert {output_3} --to pdf"], shell=True) 
    
    ### Gamma0 Comparisons ###
    parameters_slope_compare['data_dir'] = str(output_dirs_prep_2[i])
    output_gamma0_compare = output_dirs_prep_2[i]/f'output_{Path(d).name}_Backscatter_Distributions_by_Slope.ipynb'
    pm.execute_notebook(
        'gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb',
        output_gamma0_compare,
        kernel_name='python3',
        parameters = parameters_slope_compare
    )
    subprocess.run([f"jupyter nbconvert {output_gamma0_compare} --to pdf"], shell=True) 
    