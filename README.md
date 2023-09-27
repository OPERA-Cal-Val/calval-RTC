# calval-RTC

## **ALL MODULES ARE WORKS IN PROGRESS**

**Tools for validating OPERA RTC products.**

---
## Create the `opera_calval_rtc` Conda Environment

- create the `opera_calval_rtc` conda environment using `environment/environment.yaml`

---

## CalVal Data Access

#### Run The Notebook

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

#### Run as a Script with Papermill

Run the `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` notebook on a list of Sentinel-1 scenes using the `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py` Python script.

- Update the `scenes` list in the script to contain the desired scene IDs
- Update `opera_dir` to the directory in which you would like to store your RTC directories
- Update `keep_date_index` to target a given batch of samples
  - 0: oldest sample, -1: most recent sample, -2: 2nd to most recent sample, etc...
- In a terminal, run the following commands:
  1. `conda activate opera_calval_rtc`
  2. `python papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py`


---

## 1) Point Target-based absolute geolocation evaluation module

1. Download and mosaic OPERA RTC sample burst data for a given Seninel-1 scene using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb` or the Python script `papermill_OPERA_RTC_download_reproject_mosaic_sample_bursts.py`
1. Run the notebook to evaluate absolute geolocation on a single scene or the Python script to evaluate multiple scenes

#### Run the Notebook:

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

#### Run as a Script with Papermill:

Run the `point_target-based_absolute_geolocation_evaluation/ALE_OPERA-RTC.ipynb` notebook on a list of paths to OPERA RTC mosaics using the `calval-RTC/point_target-based_absolute_geolocation_evaluation/papermill_ALE_OPERA-RTC_v2.py` Python script.

- Update the `data_dirs` list in the script with paths to directories containing OPERA RTC mosacis
- In a terminal, run the following commands:
  1. `conda activate opera_calval_rtc`
  1. `python path/to/point_target-based_absolute_geolocation_evaluation/papermill_ALE_OPERA-RTC_v2.py`

---

## 2) Cross-correlation-based relative geolocation evaluation module

1. Run `cross_correlation_relative_geolocation_evaluation/1a_prepare_data_from_hyp3.ipynb`
2. Run `cross_correlation_relative_geolocation_evaluation/2b_check_cross_correlation_on_two_scenes.ipynb` 

---

## 3) Radiometric terrain flattening performance: gamma naught comparisons of foreslope, flat, and backslope pixels in forested regions

1. Download and mosaic OPERA RTC sample burst data for a given Seninel-1 scene using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb`
1. Prepare the data for the analysis notebook by running the following 3 data prep notebooks
    1. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_1.ipynb`
      - Downloads [Copernicus Global Land Cover (100m)](https://lcviewer.vito.be/download) tiles, projects them to OPERA RTC's UTM, mosaics them, and subsets mosaic to OPERA RTC extents
    3. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_2.ipynb`
      - Creates geotiffs for each polarization and slope. All non-forested pixels are masked and sets of tiffs are produced for each polarization containing only foreslope pixels, backslope pixels, or flat pixels.
    4. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_Slope_Compare_Part_3.ipynb`
      -  Create MGRS tiles for each prepared geotiff
 2. Run analysis notebook
     1. `compare_gamma0_on_foreslope_flat_backslope/gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb`   

---

## 4) Radiometric terrain flattening performance: regression analysis of terrain flattened gamma_naught and local incidence angle

1. TBD: Waiting on updates to "gamma naught comparisons of foreslope, flat, and backslope areas in forested regions"