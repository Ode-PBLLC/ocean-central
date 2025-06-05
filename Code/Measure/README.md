The following details data methodology for the Measure section of the Ocean Central platform.

There are few existing ecosystems described by global, historical datasets. These analyses are intended to illustrate the overall trends of each ecosystem over time, rather than to provide precise values at any single point in time. 

For each dataset, a spline interpolation was created using the UnivariateSpline function from the SciPy library and graphed to help users visualize changes over time. The spline degree was chosen based on visual fit to the data, given that we do not project values nor expect the polynomial degree assigned to match the complexity of ocean ecosystem dynamics. 

See the accompanying files for code implementation of each methodology. [measure.ipynb](https://github.com/Ode-PBLLC/ocean-central/blob/8d439da363d6ef0be860ac35347025d43fd52390/Code/Measure/measure.ipynb) details each ecosystem, using scripts from https://github.com/jdunic/2021_Global-seagrass-trends/ and seagrass_processing.r as an input.

**Mangroves:**
A spline interpolation was created using 1) a 1970 extent value from Spalding et. al (1997) and FAO decadal mangrove extent datasets, using 2) a 1980 extent value from a dataset covering 1980-2005 (2007), and 3) data onwards from a dataset covering 1990-2020 (2020). 

**Tidal flats:**
A spline interpolation was created from a global dataset of tidal flat extent from 1985-2015, produced by Murray et. al. (2022).

**Kelp:**
A theoretical trend is plotted following a 1.8% annual global rate of decline in kelp abundances from 1952-2015, documented by Krumhansal et. al. (2016).

**Salt marshes:**
Given a 50% historical decline in salt marsh coverage, documented by Crooks et. al. (2011), and a 0.28% annual rate of decline in the years 2000-2019, the percent remaining in 2000 was estimated to be 52.9%. From this point, a step-wise linear function was created and a spline interpolation was created based on initial 100% coverage estimated to be present in 1900.

**Oyster reefs:**
A spline interpolation was created based on visually inspected values produced by Mcafee (2020) on oyster reef extent. Note that the increasing trend is almost driven by non-native Pacific oyster species, while native oyster populations continue to decline.

**Coral:**
Historical coral data was pulled from Figure 1 of Eddy et al. (2021). A spline was then fit over the period 1900 to 2020.

**Seagrass:**
Seagrass historical time series for seven bioregions were aggregated by Dunic et al. (2017). We then took the average of these time series and fit a spline to the data. All values were then rescaled so that the year 1900 represented the ecosystem at 100% health.
