library(tidyverse)

# Load trends data
trends <- readRDS("data_outputs/GAM_bioregion_fits_1900_2020.rds")

# Step 1: Get the closest value to 1900 per bioregion
baseline <- trends %>% 
  group_by(bioregion) %>% 
  mutate(dist_to_1900 = abs(year - 1900)) %>%     
  slice_min(order_by = dist_to_1900, n = 1, with_ties = FALSE) %>%  
  ungroup() %>% 
  transmute(bioregion, baseline_fit = fit)

# Step 2: Filter out bioregions where the baseline (1980) fit is negative
valid_bioregions <- baseline %>%
  filter(baseline_fit >= 0)

# Step 3: Join only valid bioregions back into full trend set
trends_pct <- trends %>% 
  semi_join(valid_bioregions, by = "bioregion") %>%
  left_join(valid_bioregions, by = "bioregion") %>%
  mutate(fit_pct = 100 * fit / baseline_fit) %>%
  select(-baseline_fit)

# Step 4: Calculate mean across valid bioregions for each year
annual_mean <- trends_pct %>% 
  group_by(year) %>% 
  summarise(
    mean_pct = mean(fit_pct, na.rm = TRUE),
    n_bioregions = n(),
    .groups = "drop"
  )

# Step 5: Save to CSV
readr::write_csv(annual_mean %>% select(year, mean_pct), "data_outputs/seagrass_timeseries.csv")