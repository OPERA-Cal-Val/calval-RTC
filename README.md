# calval-RTC

## **ALL MODULES ARE WORKS IN PROGRESS**

**Tools for validating OPERA RTC products.**

---

## CalVal Data Access

`OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb`

Run the above notebook to create RTC and static file mosaics as input to CalVal modules described below.

---

## 1) Point Target-based absolute geolocation evaluation module

1. Download and mosaic OPERA RTC sample burst data for a given Seninel-1 scene using the notebook `OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb`
1. Run `point_target-based_absolute_geolocation_evaluation/ALE_OPERA-RTC.ipynb`

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