import subprocess
from pathlib import Path

import papermill as pm

# list of paths to OPERA-RTC mosaics on which to run gamma0 comparisons on foreslopes, flat areas, and backslopes
data_dirs = [
    "/home/jovyan/calval-RTC/OPERA_RTC_S1A_IW_SLC__1SDV_20230707T015044_20230707T015112_049311_05EDF6_1A68",
]

log = True  # True: log scale, False: power scale

parameters_prep_1 = {"data_dir": ""}

parameters_prep_2 = {"data_dir": ""}

parameters_slope_compare = {
    "data_dir": "",
    "output_dir": "",
    "log": log,
}

for i, d in enumerate(data_dirs):
    parent_data_dir = Path(d).parents[1]
    output_parent_dir = parent_data_dir / "output_flattening_analyses"
    output_parent_dir.mkdir(exist_ok=True)

    intermediary_parent_dir = parent_data_dir / "intermediary_flattening_data"
    intermediary_parent_dir.mkdir(exist_ok=True)

    input_dirs_prep_2 = [
        intermediary_parent_dir / f"{Path(p).stem}_prepped_for_slope_comparison"
        for p in data_dirs
    ]
    input_dirs_gamma0_compare = [
        intermediary_parent_dir / f"{Path(p).name}_Tree_Cover"
        for p in input_dirs_prep_2
    ]

    opera_id = d.split("/")[-1]
    output_dir = output_parent_dir / f"Output_Tree_Cover_Slope_Comparisons_{opera_id}"
    output_dir.mkdir(exist_ok=True)

    # data prep notebook 1
    parameters_prep_1["data_dir"] = d
    output_1 = output_dir / f"output_{Path(d).name}_prep_flattening_part_1.ipynb"
    pm.execute_notebook(
        "data_prep/prep_flattening_part_1.ipynb",
        output_1,
        kernel_name="python3",
        parameters=parameters_prep_1,
    )
    subprocess.run([f"jupyter nbconvert {output_1} --to pdf"], shell=True)

    # data prep notebook 2
    parameters_prep_2["data_dir"] = str(input_dirs_prep_2[i])
    output_2 = output_dir / f"output_{Path(d).name}_prep_flattening_part_2.ipynb"
    pm.execute_notebook(
        "data_prep/prep_flattening_part_2.ipynb",
        output_2,
        kernel_name="python3",
        parameters=parameters_prep_2,
    )
    subprocess.run([f"jupyter nbconvert {output_2} --to pdf"], shell=True)

    # Gamma0 Comparisons
    parameters_slope_compare["data_dir"] = str(input_dirs_gamma0_compare[i])
    parameters_slope_compare["output_dir"] = str(output_dir)
    output_gamma0_compare = (
        output_dir / f"output_{Path(d).name}_flattening_analysis.ipynb"
    )
    pm.execute_notebook(
        "flattening_analysis/flattening_analysis.ipynb",
        output_gamma0_compare,
        kernel_name="python3",
        parameters=parameters_slope_compare,
    )
    subprocess.run([f"jupyter nbconvert {output_gamma0_compare} --to pdf"], shell=True)
