# calval-RTC

## **ALL MODULES ARE WORKS IN PROGRESS**

**Tools for validating OPERA RTC products.**

---

## CalVal Data Access

`OPERA_RTC_download_reproject_mosaic_sample_bursts.ipynb`

Run the above notebook to create RTC and static file mosaics to input to CalVal modules described below.

---

## 1) Point Target-based absolute geolocation evaluation module

1. Run `point_target-based_absolute_geolocation_evaluation/ALE_OPERA-RTC.ipynb`

---

## 2) Cross-correlation-based relative geolocation evaluation module
1. Run `cross_correlation_relative_geolocation_evaluation/1a_prepare_data_from_hyp3.ipynb`
1. Run `cross_correlation_relative_geolocation_evaluation/2b_check_cross_correlation_on_two_scenes.ipynb` 

---

## 3) Radiometric terrain flattening performance: gamma naught comparisons of foreslope, flat, and backslope areas in forested regions

1. Run data prep notebooks
    1. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_data_stage1_part1.ipynb`
    1. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_data_stage1_part2.ipynb`
    1. `compare_gamma0_on_foreslope_flat_backslope/data_prep/Prep_OPERA_RTC_CalVal_data_stage1_part3.ipynb`
 1. Run analysis notebook
     1. `compare_gamma0_on_foreslope_flat_backslope/gamma0_comparisons_on_foreslope_backslope/Backscatter_Distributions_by_Slope.ipynb`   

---

## 4) Radiometric terrain flattening performance: regression analysis of terrain flattened gamma_naught and local incidence angle

1. TBD: Waiting on updates to "gamma naught comparisons of foreslope, flat, and backslope areas in forested regions"