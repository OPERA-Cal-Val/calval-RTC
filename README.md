# calval-RTC

**Tools for validating OPERA RTC products.**

---
---
## Create the `opera_calval_rtc` Conda Environment

- create the `opera_calval_rtc` conda environment using `environment/environment.yaml`

---
---

## CalVal Data Access

#### **Option 1: Run The Notebook**

Run the `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` notebook to create RTC and static file mosaics as inputs to CalVal modules.

The notebook:
- Inputs a Sentinel-1 scene ID
- Identifies potential bursts associated with the scene
- Searches `s3://opera-pst-rs-pop1/products/RTC_S1` for bursts
- Filters discovered bursts for the most recent, 2nd to most recent, etc... batch of samples
- Downloads VV, VH, incidence angle map, local incidence angle map, and layover/shadow mask
- Reprojects all bursts in scene to prodominant UTM (if necessary)
- Merges all bursts and saves mosaics
- Deletes bursts

#### **Option 2: Run as a Script with Papermill**
Run the `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` notebook on a list of Sentinel-1 scenes using the `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py` Python script.

- Update the `scenes` list in the script to contain the desired scene IDs
- Update `opera_dir` to the directory in which you would like to store your RTC directories
- Update `keep_date_index` to target a given batch of samples
  - 0: oldest sample, -1: most recent sample, -2: 2nd to most recent sample, etc...
- In a terminal, run the following commands:
  1. `conda activate opera_calval_rtc`
  2. `python path/to/papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py`


---
---

## Point Target-Based Absolute Geolocation Evaluation Module

1. Download and mosaic OPERA RTC sample burst data for a given Seninel-1 scene using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` or the Python script `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py` (see above instructions)
1. Run the notebook to evaluate absolute geolocation on a single scene or the Python script to evaluate multiple scenes (instructions follow)

#### **Option 1: Run the Absolute Geolocation Validation Notebook:**

Run `point_target-based_absolute_geolocation_evaluation/ALE_OPERA-RTC.ipynb` notebook

The notebook:
- Inputs a path to the directory holding an RTC mosaic
- Creates an output directory named `absolute_geolocation_{S1 scene ID}`
- Deletes all mosaics except VV polarization, which is moved to the output directory
- Identifies corner reflector site intersecting data
- Downloads corner reflector data
- Filters corner reflectors, removing those facing away from the sensor
- Calculates the geolocation error in Northing and Easting
- Removes corner refectors that fall on the edge of a pixel
- Plots the error
-  Appends results to a CSV file

#### **Option 2: Run as a Script with Papermill:**

Run the `point_target-based_absolute_geolocation_evaluation/ALE_OPERA-RTC.ipynb` notebook on a list of paths to OPERA RTC mosaics using the `calval-RTC/point_target-based_absolute_geolocation_evaluation/papermill_ALE_OPERA-RTC_v2.py` Python script

- Update the `data_dirs` list in the script with paths to directories containing OPERA RTC mosacis
- In a terminal, run the following commands:
  1. `conda activate opera_calval_rtc`
  1. `python path/to/point_target-based_absolute_geolocation_evaluation/papermill_ALE_OPERA-RTC_v2.py`

---
---

## Cross-Correlation-Based Relative Geolocation Evaluation Module

1. Download and mosaic a OPERA RTC sample burst data for a stack of Seninel-1 scenes using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` or the Python script `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py` (see above instructions)
1. Run the notebook to evaluate relative geolocation between scenes with a cross-correlation approach (instructions follow)

#### **Option 1: Run the Cross-Correlation-Based Relative Geolocation Evaluation Notebook:**

Run the `cross_correlation_relative_geolocation_evaluation/OPERA_RTC_Cross_Correlation.ipynb` notebook

The notebook:
- Buffers all scenes in the stack so they have the same extents
- Remove the top and bottom 1% Gamma0 values
- Divide each scene into 64 tiles
- Perform phase cross correlation on:
  - nearest neighbors
    - scene1 scene2, scene2 scene3, scene3 scene4, etc...
  - first and last scene in stack
  - nearest 4th neighbor scenes
    - scene1 scene4, scene4 scene8, scene8 scene12, etc...
- Plot results
- Write results to CSV

#### **Option 2: Run as a Script With Papermill

Run the `cross_correlation_relative_geolocation_evaluation/papermill_OPERA_RTC_Cross_Correlation.py` script on multiple RTC stacks

1. Update `stack_dirs`, adding paths to the directories holding RTC stacks
1. Update `delete_mosaics`
  - `True`: deletes input data
  - `False`: saves input data
1. Update `cleanup_list` to save or delete intermediate data
  - uncomment data products to delete
1. Save changes to script
1. Run script in `opera_calval_rtc` conda environment
   1. Open a terminal and run the following commands
   2. `conda activate opera_calval_rtc`
   3. `Python path/to/cross_correlation_relative_geolocation_evaluation/papermill_OPERA_RTC_Cross_Correlation.py`

---
---

## 3) Radiometric Terrain Flattening Performance Evaluation Module: Gamma Naught Comparisons of Foreslope, Flat, and Backslope Pixels in Forested Regions

1. Download and mosaic OPERA RTC sample burst data for a given Seninel-1 scene using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` or the Python script `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py` (see above instructions)

#### **Option 1: Run the 3 Data Prep Notebooks and the Slope Comparison Notebook**

1. Prepare the data for the analysis notebook by running the following 3 data prep notebooks
    1. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb`
      - Downloads [Copernicus Global Land Cover (100m)](https://lcviewer.vito.be/download) tiles, projects them to OPERA RTC's UTM, mosaics them, and subsets mosaic to OPERA RTC extents
    3. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb`
      - Creates geotiffs for each polarization and slope. All non-forested pixels are masked and sets of tiffs are produced for each polarization containing only foreslope pixels, backslope pixels, or flat pixels.
    4. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_3.ipynb`
      -  Create MGRS tiles for each prepared geotiff
 2. Run analysis notebook
     1. `compare_gamma0_on_foreslope_flat_backslope/gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb`   

#### **Option 2: Run All Four Notebooks with a Script Using Papermill**

Run `compare_gamma0_on_foreslope_flat_backslope/papermill_gamma0_slope_comparison.py` to run all four notebooks on multiple RTCs

- Update `data_dirs`, adding paths to directories holding RTCs
- Update `log` to set log or power scale
- Update `save` to save output plots as PNGs, or not
1. Save changes to script
1. Run script in `opera_calval_rtc` conda environment
   1. Open a terminal and run the following commands
   2. `conda activate opera_calval_rtc`
   3. `Python path/to/compare_gamma0_on_foreslope_flat_backslope/papermill_gamma0_slope_comparison.py`


---
---

## 4) Radiometric Terrain Flattening Performance: Regression Analysis of Terrain Flattened Gamma Naught and Local Incidence Angle

Work in progess