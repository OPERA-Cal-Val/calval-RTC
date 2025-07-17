import glob
import os
import subprocess
from pathlib import Path

import papermill as pm

# Specify parent directory of OPERA-RTC mosaics on which to run RLE
data_dirs_parent = "/home/jovyan/calval-RTC"

# parent directory containing OPERA-RTC mosaics on which to run ALE
data_dirs = [
    d for d in glob.glob(os.path.join(data_dirs_parent, "OPERA_RTC_S1*"))
    if os.path.isdir(d)
]

output_dir = Path(data_dirs_parent) / 'output_ALE'
output_dir.mkdir(exist_ok=True)
output_dirs = [
    output_dir / f"{p.split('RTC_')[-1]}"
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
        "ALE.ipynb",
        output,
        kernel_name="python3",
        parameters=parameters,
    )

    subprocess.run([f"jupyter nbconvert {output} --to html"], shell=True)
    subprocess.run(
        [f"pandoc {output_html} -o {output_pdf} --pdf-engine=weasyprint"],
        shell=True,
    )
