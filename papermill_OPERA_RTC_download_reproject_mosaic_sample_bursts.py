import os
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import papermill as pm

# list of Sentinel-1 scene IDs for which to download and mosaic bursts
scenes = [
    # "S1A_IW_SLC__1SDV_20230523T003658_20230523T003725_048654_05DA0F_0047", 
    
]

FILE_PATTERNS = [
    "OPERA_L2_RTC-S1_inc_angle",
    "OPERA_L2_RTC-S1_local_inc_angle",
    "OPERA_L2_RTC-S1_ls_mask",
    "OPERA_L2_RTC-S1_VH",
    "OPERA_L2_RTC-S1_VV"
]

base_dir = str(Path.cwd())


parameters = {
    "scene": "",
    "prod_version": 1.0,
    "opera_dir": base_dir,  # Directory for OPERA RTC output directories
    "keep_date_index": -1   # 0: oldest, -1: most recent, etc.
}


# Step 1: Download and merge RTC/RTC-STATIC product bursts by acquisition
for s in scenes:
    parameters["scene"] = s
    try:
        pm.execute_notebook(
            "OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb",
            f"output_{s}_OPERA_RTC_download_reproject_mosaic_"
            f"sample_bursts.ipynb",
            kernel_name="python3",
            parameters=parameters
        )
    except Exception:
        pass

# Step 2: Collect subfolders with start/end times
folder_info = []
for folder in os.listdir(base_dir):
    if folder.startswith("OPERA_RTC_S1"):
        try:
            start = folder[27:42]
            end = folder[43:58]
            folder_info.append((folder, start, end))
        except IndexError:
            continue


# Step 3: Group overlapping folders
def time_overlap(start_str1, end_str1, start_str2, end_str2):
    fmt = "%Y%m%dT%H%M%S"
    start1 = datetime.strptime(start_str1, fmt)
    end1 = datetime.strptime(end_str1, fmt)
    start2 = datetime.strptime(start_str2, fmt)
    end2 = datetime.strptime(end_str2, fmt)

    return max(start1, start2) < min(end1, end2)

groups = []
used = set()
for i, (f1, s1, e1) in enumerate(folder_info):
    if f1 in used:
        continue
    group = [(f1, s1, e1)]
    used.add(f1)
    for j, (f2, s2, e2) in enumerate(folder_info[i+1:], start=i+1):
        if f2 not in used and time_overlap(s1, e1, s2, e2):
            group.append((f2, s2, e2))
            used.add(f2)

    # only attempt to merge cases where there are multiple frames
    if len(group) > 1:
        groups.append(group)

# Create unmerged_frames dir
unmerged_dir = os.path.join(base_dir, "unmerged_frames")
os.makedirs(unmerged_dir, exist_ok=True)

# Step 4: Process each group
for group in groups:
    ids = [f for f, _, _ in group]
    starts = [s for _, s, _ in group]
    ends = [e for _, _, e in group]
    prefix = ids[0][:26]
    merged_name = f"{prefix}_{min(starts)}_{max(ends)}"
    merged_path = os.path.join(base_dir, merged_name)
    os.makedirs(merged_path, exist_ok=True)

    for pattern in FILE_PATTERNS:
        matched_files = []
        for folder, _, _ in group:
            folder_path = os.path.join(base_dir, folder)
            for fname in os.listdir(folder_path):
                if fname.startswith(pattern) and fname.endswith(".tif"):
                    matched_files.append(os.path.join(folder_path, fname))
        if matched_files:
            output_name = f"{pattern}_30_v1.0_mosaic.tif"
            output_path = os.path.join(merged_path, output_name)
            merge_command = [
                "gdal_merge.py", "-o", output_path, *matched_files
            ]
            subprocess.run(merge_command, check=True)
            print(f"Merged to: {output_path}")

    # Step 5: Move original subfolders
    for folder, _, _ in group:
        src = os.path.join(base_dir, folder)
        dst = os.path.join(unmerged_dir, folder)
        if not os.path.exists(dst):
            shutil.move(src, dst)
            print(f"Moved {folder} to unmerged_frames/")

