import glob
import os
import re
import subprocess
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import papermill as pm
from papermill.exceptions import PapermillExecutionError

# Specify parent directory of OPERA-RTC mosaics on which to run ALE
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

# =============================================================================
# PART 1: PAPERMILL EXECUTION PIPELINE
# =============================================================================

for i, d in enumerate(data_dirs):
    parameters["data_dir"] = d
    parameters["savepath"] = str(output_dirs[i])
    output_dirs[i].mkdir(exist_ok=True)
    output = (
        output_dirs[i] / f"output_{Path(d).name}_ALE.ipynb"
    )
    output_html = Path(output).with_suffix('.html')
    output_pdf = Path(output).with_suffix('.pdf')

    if not output_pdf.exists():
        try:
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
        except PapermillExecutionError as e:
            print(f'ALE analysis of {d} failed, move onto next file')
            pass
    else:
        print(f'ALE already run on scene {d}')


# =============================================================================
# PART 2: AGGREGATE ALE PLOTTING (COLOR-CODED BY PLATFORM)
# =============================================================================

# Load data
ale_csv_file = next(output_dir.glob('*_ALE30-Results.csv'), None)

if ale_csv_file and ale_csv_file.exists():
    df = pd.read_csv(ale_csv_file)
    df["Date"] = pd.to_datetime(df[["Year", "Month", "Day"]])

    # Extract Platform (S1A, S1B, S1C, S1D) directly from Granule string
    def parse_platform(granule_str):
        match = re.search(r'S1[A-D]', str(granule_str))
        return match.group(0) if match else 'S1A'

    df['Platform'] = df['Granule'].apply(parse_platform)

    # Color mapping for Sentinel-1 platform
    color_map = {
        'S1A': 'blue',
        'S1B': 'black',
        'S1C': 'green',
        'S1D': 'red'
    }

    mean_color = 'deeppink'

    # Compute statistics from aggregate of ALE measurements
    mean_easting = np.mean(df['Easting_Bias'])
    mean_easting_std = np.mean(df['sig_Easting_Bias'])
    mean_northing = np.mean(df['Northing_Bias'])
    mean_northing_std = np.mean(df['sig_Northing_Bias'])

    # -------------------------------------------------------------------------
    # 2a. Aggregate 2D Geolocation Error Plot
    # -------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8, 8))
    requirement = plt.Rectangle(
        (-6.0, -6.0),
        12,
        12,
        facecolor=(0.5, 0.5, 0.5, 0.2),
        edgecolor='black',
        label='Requirement'
    )
    ax.add_patch(requirement)

    ax.grid(True)
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.axhline(0, color='black')
    ax.axvline(0, color='black')

    ax.set_title(
        f"Easting: {mean_easting:.3f} ± {mean_easting_std:.3f} m,\n"
        f"Northing: {mean_northing:.3f} ± {mean_northing_std:.3f} m"
    )

    ax.set_xlabel('Easting error (m)')
    ax.set_ylabel('Northing error (m)')
    fig.suptitle('Aggregate Absolute Geolocation Error')

    # Plot error bars for each platform
    for platform in ['S1A', 'S1B', 'S1C', 'S1D']:
        df_plat = df[df['Platform'] == platform]
        if not df_plat.empty:
            plt.errorbar(
                df_plat['Easting_Bias'].to_numpy(),
                df_plat['Northing_Bias'].to_numpy(),
                xerr=df_plat['sig_Easting_Bias'].to_numpy(),
                yerr=df_plat['sig_Northing_Bias'].to_numpy(),
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

    # Plot mean error bar
    plt.errorbar(
        mean_easting,
        mean_northing,
        xerr=mean_easting_std,
        yerr=mean_northing_std,
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
    ale_csv_fig = output_dir / 'aggregate_ALE_GeolocationPLOT.png'
    plt.savefig(ale_csv_fig, dpi=300, transparent=True)
    plt.close()

    # -------------------------------------------------------------------------
    # 2b. Time-Series Offsets Plot (Northing / Easting)
    # -------------------------------------------------------------------------
    for ale_dim in ['Northing', 'Easting']:
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.set_ylim(-10, 10)

        # Plot error bars per platform
        for platform in ['S1A', 'S1B', 'S1C', 'S1D']:
            df_plat = df[df['Platform'] == platform]
            if not df_plat.empty:
                ax.errorbar(
                    df_plat["Date"],
                    df_plat[f"{ale_dim}_Bias"],
                    yerr=df_plat[f"sig_{ale_dim}_Bias"],
                    fmt="o",
                    color=color_map[platform],
                    ecolor=color_map[platform],
                    capsize=4,
                    capthick=1,
                    alpha=0.75,
                    label=platform
                )

        # Shaded gray region from -6 to 6 (Requirement)
        ax.axhspan(-6, 6, color='gray', alpha=0.2, label='Requirement')

        ax.set_xlabel("Time")
        ax.set_ylabel(f"{ale_dim} [m]")

        # Set major x-ticks every 6 months
        locator = mdates.MonthLocator(interval=6)
        formatter = mdates.DateFormatter("%b %Y")
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        plt.xticks(rotation=45)

        ax.grid(True)
        ax.legend(loc='upper right')
        plt.tight_layout()

        # Save figure
        output_fig = output_dir / f'aggregate_{ale_dim}.png'
        plt.savefig(output_fig, dpi=300, transparent=True)
        plt.close()

    # Report percentage of scenes that pass
    condition = (df['Easting_Bias'].abs() > 6) | (df['Northing_Bias'].abs() > 6)
    count = condition.sum()
    pass_percentage = 100 - ((count / len(df)) * 100)

    print(f"Percentage of scenes which pass: {pass_percentage:.2f}%")
else:
    print("No aggregate ALE CSV results found.")
