import glob
import os
import re
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import papermill as pm

# =============================================================================
# PART 1: PAPERMILL EXECUTION PIPELINE
# =============================================================================

# List of paths to OPERA-RTC mosaics
data_dirs_parent = "/home/jovyan/calval-RTC"

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

# Set output directories
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

    # Data prep notebook 1
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

    # Data prep notebook 2
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


# =============================================================================
# PART 2: AGGREGATE & SEASONALITY PLOTTING
# =============================================================================

# Load data from generated CSV files
csv_files = list(output_parent_dir.glob('*/*Results*.csv'))

if not csv_files:
    print("No CSV result files found in output_flattening_analyses.")
else:
    # Read and concatenate
    df_list = [pd.read_csv(csv_file) for csv_file in csv_files]
    df = pd.concat(df_list, ignore_index=True)

    # Extract Platform (S1A, S1B, S1C, S1D) directly from Granule / filename string
    def parse_platform(granule_str):
        match = re.search(r'S1[A-D]', str(granule_str))
        return match.group(0) if match else 'S1A'

    df['Platform'] = df['Granule'].apply(parse_platform)

    # Extract Date YYYYMMDD and compute Day of Year
    def parse_day_of_year(granule_str):
        match = re.search(r'20\d{6}', str(granule_str))
        if match:
            dt = pd.to_datetime(match.group(0), format="%Y%m%d")
            return dt.dayofyear
        try:
            dt = pd.to_datetime(str(granule_str)[27:35], format="%Y%m%d")
            return dt.dayofyear
        except Exception:
            return np.nan

    df['Day'] = df['Granule'].apply(parse_day_of_year)

    # Color mapping for Sentinel-1 platform
    color_map = {
        'S1A': 'blue',
        'S1B': 'black',
        'S1C': 'green',
        'S1D': 'red'
    }

    # Distinct non-overlapping colors for seasons & mean
    winter_color = 'purple'
    summer_color = 'darkorange'
    mean_color = 'deeppink'

    # -------------------------------------------------------------------------
    # 2a. Plot VH/VV Seasonality Analysis (Color-coded by Platform & Seasons)
    # -------------------------------------------------------------------------
    for pol_iter in ['VH', 'VV']:
        df_filtered = df[df['Polarization'] == pol_iter]

        fig, ax = plt.subplots(figsize=(8, 8))

        ax.set_ylim(-1.1, 1.1)
        ax.set_xlim(0, 365)

        # Plot scatter points per platform
        for platform in ['S1A', 'S1B', 'S1C', 'S1D']:
            df_plat = df_filtered[df_filtered['Platform'] == platform]
            if not df_plat.empty:
                ax.scatter(
                    df_plat['Day'].to_numpy(),
                    df_plat['Foreslope Median - Backslope Median'].to_numpy(),
                    color=color_map[platform],
                    label=platform,
                    alpha=0.75,
                    edgecolor='none'
                )

        # Shaded gray region from -1 to 1 (Requirement)
        ax.axhspan(-1, 1, color='gray', alpha=0.2, label='Requirement')

        # Season labels & boundaries
        ax.text(60, 0.75, 'Winter', ha='center', fontsize=11, fontweight='bold', color=winter_color)
        ax.text(200, 0.75, 'Summer', ha='center', fontsize=11, fontweight='bold', color=summer_color)
        ax.text(320, 0.75, 'Winter', ha='center', fontsize=11, fontweight='bold', color=winter_color)

        ax.axvline(x=80, color=winter_color, linestyle='--', linewidth=1.5)
        ax.axvline(x=280, color=winter_color, linestyle='--', linewidth=1.5)
        ax.axvline(x=160, color=summer_color, linestyle='--', linewidth=1.5)
        ax.axvline(x=240, color=summer_color, linestyle='--', linewidth=1.5)

        ax.set_xlabel("Day of year")
        ax.set_ylabel(fr"$\Delta$ {pol_iter} [dB]")
        ax.set_title(f'Seasonality Analysis ({pol_iter}: Foreslope - Backslope)')

        ax.grid(True)
        ax.legend(loc='upper right')
        plt.tight_layout()

        # Save figure
        output_fig = output_parent_dir / f'seasonality_analysis_{pol_iter}.png'
        plt.savefig(output_fig, dpi=300, transparent=True)
        plt.close()

    # -------------------------------------------------------------------------
    # 2b. Aggregate Plot for All Analyzed Sites (Color-coded by Platform & Mean)
    # -------------------------------------------------------------------------
    df_filtered_VH = df[df['Polarization'] == 'VH'].copy()
    df_filtered_VV = df[df['Polarization'] == 'VV'].copy()

    # Merge VV and VH on Granule to guarantee exact 1-to-1 scene alignment
    df_merged = pd.merge(
        df_filtered_VV,
        df_filtered_VH,
        on=['Granule', 'Platform', 'Day'],
        suffixes=('_VV', '_VH')
    )

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
        fr"$\Delta$ VH: {mean_VH:.3f} ± {mean_VH_std:.3f} dB"
        "\n"
        fr"$\Delta$ VV: {mean_VV:.3f} ± {mean_VV_std:.3f} dB"
    )

    ax.set_xlabel(fr"$\Delta$ VV [dB]")
    ax.set_ylabel(fr"$\Delta$ VH [dB]")
    fig.suptitle('All Sites (Foreslope - Backslope)')

    # Plot error bars per platform
    for platform in ['S1A', 'S1B', 'S1C', 'S1D']:
        df_plat = df_merged[df_merged['Platform'] == platform]
        if not df_plat.empty:
            x_val = df_plat['Foreslope Median - Backslope Median_VV'].to_numpy()
            y_val = df_plat['Foreslope Median - Backslope Median_VH'].to_numpy()
            x_err = (df_plat['Foreslope STD_VV'] - df_plat['Backslope STD_VV']).abs().to_numpy()
            y_err = (df_plat['Foreslope STD_VH'] - df_plat['Backslope STD_VH']).abs().to_numpy()

            plt.errorbar(
                x_val,
                y_val,
                xerr=x_err,
                yerr=y_err,
                barsabove=True,
                capsize=6,
                capthick=1.5,
                fmt='o',
                color=color_map[platform],
                ecolor=color_map[platform],
                linewidth=1.5,
                markersize=12,
                alpha=0.5,
                label=platform
            )

    # Plot overall mean error bar
    plt.errorbar(
        mean_VV,
        mean_VH,
        xerr=mean_VV_std,
        yerr=mean_VH_std,
        barsabove=True,
        capsize=8,
        capthick=2,
        fmt='o',
        color=mean_color,
        ecolor=mean_color,
        linewidth=2.5,
        markersize=18,
        label='Mean',
        zorder=10
    )

    ax.legend(loc='upper right')
    plt.tight_layout()

    # Save figure
    output_fig = output_parent_dir / 'aggregate_flattening_calvalPLOT.png'
    plt.savefig(output_fig, dpi=300, transparent=True)
    plt.close()

    # Report percentage of scenes that pass
    condition = df['Foreslope Median - Backslope Median'].abs() > 1
    count = condition.sum()
    pass_percentage = 100 - ((count / len(df)) * 100)
    print(f"Percentage of scenes which pass: {pass_percentage:.2f}%")
