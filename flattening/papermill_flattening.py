import glob
import os
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import papermill as pm

# list of paths to OPERA-RTC mosaics on which to run gamma0 comparisons on foreslopes, flat areas, and backslopes
data_dirs_parent = "/home/jovyan/calval-RTC"

# parent directory containing OPERA-RTC mosaics on which to run ALE
data_dirs = [
    d for d in glob.glob(os.path.join(data_dirs_parent, "OPERA_RTC_S1*"))
    if os.path.isdir(d)
]

log = True  # True: log scale, False: power scale

parameters_prep_1 = {"data_dir": ""}

parameters_prep_2 = {"data_dir": ""}

parameters_slope_compare = {
    "data_dir": "",
    "output_dir": "",
    "log": log,
}

# set output directories
output_parent_dir = Path("output_flattening_analyses")
output_parent_dir.mkdir(exist_ok=True)

intermediary_parent_dir = Path("intermediary_flattening_data")
intermediary_parent_dir.mkdir(exist_ok=True)

for i, d in enumerate(data_dirs):
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
    output_1_html = Path(output_1).with_suffix('.html')
    output_1_pdf = Path(output_1).with_suffix('.pdf')
    if not output_1_pdf.exists():
        pm.execute_notebook(
            "data_prep/prep_flattening_part_1.ipynb",
            output_1,
            kernel_name="python3",
            parameters=parameters_prep_1,
        )
        subprocess.run([f"jupyter nbconvert {output_1} --to html"], shell=True)
        subprocess.run(
            [
                f"pandoc {output_1_html} "
                f"-o {output_1_pdf} "
                "--pdf-engine=weasyprint"
            ],
            shell=True,
        )
    else:
        print(f'Data prep1 already run on scene {d}')

    # data prep notebook 2
    parameters_prep_2["data_dir"] = str(input_dirs_prep_2[i])
    output_2 = output_dir / f"output_{Path(d).name}_prep_flattening_part_2.ipynb"
    output_2_html = Path(output_2).with_suffix('.html')
    output_2_pdf = Path(output_2).with_suffix('.pdf')
    if not output_2_pdf.exists():
        pm.execute_notebook(
            "data_prep/prep_flattening_part_2.ipynb",
            output_2,
            kernel_name="python3",
            parameters=parameters_prep_2,
        )
        subprocess.run([f"jupyter nbconvert {output_2} --to html"], shell=True)
        subprocess.run(
            [
                f"pandoc {output_2_html} "
                f"-o {output_2_pdf} "
                "--pdf-engine=weasyprint"
            ],
            shell=True,
        )
    else:
        print(f'Data prep2 already run on scene {d}')

    # Gamma0 Comparisons
    parameters_slope_compare["data_dir"] = str(input_dirs_gamma0_compare[i])
    parameters_slope_compare["output_dir"] = str(output_dir)
    output_gamma0_compare = (
        output_dir / f"output_{Path(d).name}_flattening_analysis.ipynb"
    )
    output_gamma0_compare_html = Path(
        output_gamma0_compare
    ).with_suffix('.html')
    output_gamma0_compare_pdf = Path(
        output_gamma0_compare
    ).with_suffix('.pdf')
    if not output_gamma0_compare_pdf.exists():
        pm.execute_notebook(
            "flattening_analysis/flattening_analysis.ipynb",
            output_gamma0_compare,
            kernel_name="python3",
            parameters=parameters_slope_compare,
        )
        subprocess.run(
            [f"jupyter nbconvert {output_gamma0_compare} --to html"],
            shell=True,
        )
        subprocess.run(
            [
                f"pandoc {output_gamma0_compare_html} "
                f"-o {output_gamma0_compare_pdf} "
                "--pdf-engine=weasyprint"
            ],
            shell=True,
        )
    else:
        print(f'Full flattening CalVal already run on scene {d}')


# plot difference between foreslope and backslope backscatter
# as a function of day of year

# Load data
csv_files = output_parent_dir.glob('*/*Results*.csv')

# Read and concatenate
df_list = [pd.read_csv(csv_file) for csv_file in csv_files]
df = pd.concat(df_list, ignore_index=True)

# Convert to datetime
dt_series = [i[27:35] for i in df['Granule'].to_list()]
dt_series = pd.to_datetime(dt_series, format="%Y%m%d")
# Get day of year
day_of_year = dt_series.dayofyear.tolist()
df['Day'] = day_of_year

# plot VH/VV separately
for pol_iter in ['VH', 'VV']:
    df_filtered = df[df['Polarization'] == pol_iter]

    fig, ax = plt.subplots(figsize=(8,8))

    ax.set_ylim(-1.1, 1.1)
    ax.set_xlim(0, 365)

    plt.scatter(
        df_filtered['Day'].to_numpy(),
        df_filtered['Foreslope Median - Backslope Median'].to_numpy(), 
        color='red',
        label=pol_iter)

    # Shaded gray region from -1 to 1
    ax.axhspan(-1, 1, color='gray', alpha=0.2, label='Requirement')

    # Season labels (approximate days for Northern Hemisphere)
    ax.text(60, 0.75, 'Winter', ha='center', fontsize=10, color='blue')
    ax.text(200, 0.75, 'Summer', ha='center', fontsize=10, color='green')
    ax.text(320, 0.75, 'Winter', ha='center', fontsize=10, color='blue')
    ax.axvline(x=160, color='green', linestyle='--')
    ax.axvline(x=240, color='green', linestyle='--')
    ax.axvline(x=80, color='blue', linestyle='--')
    ax.axvline(x=280, color='blue', linestyle='--')

    ax.set_xlabel("Day of year")
    ax.set_ylabel(fr"$\Delta$ {pol_iter} [dB]")
    ax.set_title('Seasonality Analysis (Foreslope - Backslope)')

    ax.grid(True)
    ax.legend()
    plt.tight_layout()

    # Save figure
    output_fig = f'seasonality_analysis_{pol_iter}.png'
    plt.savefig(output_fig, dpi=300, transparent=True)
    plt.close()
    

# plot difference between foreslope and backslope backscatter
# as an aggregate for all analyzed sites
# Compute statistics from aggregate of ALE measurements
df_filtered_VH = df[df['Polarization'] == 'VH']
df_filtered_VV = df[df['Polarization'] == 'VV']
mean_VH = np.mean(df_filtered_VH['Foreslope Median - Backslope Median'])
mean_VH_std = np.sqrt(np.sum(
    (df_filtered_VH['Foreslope STD'] - df_filtered_VH['Backslope STD']) ** 2
))
mean_VV = np.mean(df_filtered_VV['Foreslope Median - Backslope Median'])
mean_VV_std = np.sqrt(np.sum(
    (df_filtered_VV['Foreslope STD'] - df_filtered_VV['Backslope STD']) ** 2
))

# Create plot
fig, ax = plt.subplots(figsize=(8, 8))
requirement = plt.Rectangle(
    (-1.0, -1.0),
    2,
    2,
    facecolor=(0.5, 0.5, 0.5, 0.2),
    edgecolor='black',
    label='Requirement'
)
ax.add_patch(requirement)

ax.grid(True)
ax.set_xlim(-2, 2)
ax.set_ylim(-2, 2)
ax.axhline(0, color='black')
ax.axvline(0, color='black')

ax.set_title(
    fr"$\Delta$ VH: {mean_VH:.3f} ± {mean_VH_std:.3f} dB,\n"
    fr"$\Delta$ VV: {mean_VV:.3f} ± {mean_VV_std:.3f} dB"
)

ax.set_xlabel(fr"$\Delta$ VV [dB]")
ax.set_ylabel(fr"$\Delta$ VH [dB]")
fig.suptitle('All Sites (Foreslope - Backslope)')

# Plot error bars for each scene
# Element-wise RSS of Foreslope - Backslope std
rss_diff_VH = np.abs(
    df_filtered_VH['Foreslope STD'] - df_filtered_VH['Backslope STD']
)
rss_diff_VV = np.abs(
    df_filtered_VV['Foreslope STD'] - df_filtered_VV['Backslope STD']
)

plt.errorbar(
    df_filtered_VV['Foreslope Median - Backslope Median'].to_numpy(),
    df_filtered_VH['Foreslope Median - Backslope Median'].to_numpy(),
    xerr=rss_diff_VV.to_numpy(),
    yerr=rss_diff_VH.to_numpy(),
    barsabove=True,
    capsize=8,
    capthick=2,
    fmt='o',
    color='gray',
    linewidth=2,
    markersize=20,
    ecolor='gray',
    alpha=0.5
)

# Plot mean error bar
plt.errorbar(
    mean_VV,
    mean_VH,
    xerr=mean_VV_std,
    yerr=mean_VH_std,
    barsabove=True,
    capsize=8,
    capthick=2,
    fmt='ro',
    linewidth=2,
    markersize=20
)

# Save figure
output_fig = 'aggregate_flattening_calvalPLOT.png'
plt.savefig(output_fig, dpi=300, transparent=True)
plt.close()


# Report percentage of scenes that pass
condition = df['Foreslope Median - Backslope Median'].abs() > 1
count = condition.sum()
pass_percentage = 100 - ((count / len(df)) * 100)

print(f"Percentage of scenes which pass: {pass_percentage:.2f}%")
