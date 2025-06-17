import subprocess
from pathlib import Path

import papermill as pm

# list of paths to OPERA-RTC mosaics on which to run ALE
data_dirs = [
    # "/home/jovyan/calval-RTC/OPERA_RTC_S1A_IW_SLC__1SDV_20230611T002830_20230611T002857_048931_05E256_1866",
]

output_dirs = [
    Path(p).parents[1] / f"output_ALE_{p.split('RTC_')[-1]}"
    for p in data_dirs
]

parameters = {"data_dir": "", "savepath": ""}

for i, d in enumerate(data_dirs):
    parameters["data_dir"] = d
    parameters["savepath"] = str(output_dirs[i])
    output_dirs[i].mkdir(exist_ok=True)
    output = (
        output_dirs[i] / f"output_{Path(d).name}_ALE.ipynb"
    )
    output_html = Path(output).with_suffix('.html')
    output_pdf = Path(output).with_suffix('.pdf')
    pm.execute_notebook(
        "ALE_OPERA-RTC.ipynb",
        output,
        kernel_name="python3",
        parameters=parameters,
    )

    subprocess.run([f"jupyter nbconvert {output} --to html"], shell=True)
    subprocess.run(
        [f"pandoc {output_html} -o {output_pdf} --pdf-engine=weasyprint"],
        shell=True,
    )
