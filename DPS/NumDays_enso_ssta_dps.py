# load SSTs daily time series and estimate a percentage of the data
# above/below p90/p10 values during El Nino and La Nina yeats



# load required modules

import numpy as np
from scipy import stats
import pandas as pd
import xarray as xr

from datetime import date
from calendar import monthrange
import time as time

import sys
sys.path.insert(0,'/home/ecougnon/scripts/libraries/')
import eac_ClimateIndex as eac

# indicate whether we want +ve, +ve or ignore the NINO3.4 phases
#ENSO = 'pos' # consider only the positive phases
ENSO = 'neg' # consider only the negative phases

header = '/home/ecougnon/data/DPS/reanalysis/ETKF/'
if ENSO == 'neg':
    outfile = header + '/NumDays_LaN_p90p10_Aus_dps.nc'
elif ENSO == 'pos':
    outfile = header + '/NumDays_ElN_p90p10_Aus_dps.nc'

################################
# define the region
################################
lat_min = -55
lat_max = 10
# !!! LONGITUDE in the model!!! from -280 to 80 deg E
lon_min = 90 - 360
lon_max = 180 - 360
# grid info
gname = header + 'ocean_daily_SST_enkf9_mem001_2002.nc'
yt_ocean = xr.open_dataset(gname)['yt_ocean']
yt_ocean = yt_ocean.sel(yt_ocean=slice(lat_min,lat_max))
xt_ocean = xr.open_dataset(gname)['xt_ocean'] #!!! from -280 to 80 deg E
xt_ocean = xt_ocean.sel(xt_ocean=slice(lon_min,lon_max))
# usefull numbers
MinYear = 2003
MaxYear = 2017
NumYear = MaxYear - MinYear+1
# warning finishes in Nov 2017 not Dec
dtime = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,11,30).toordinal()+1)
NumDays = len(dtime)
# number of days for 10% of the total number of days
tim_10th = len(dtime)/10
# Load data
# Daily SSTa
SSTa_d = xr.open_dataset(header + 'ssta_reana_ETKF_mem001_20032017_daily_Aus.nc') \
                        ['dsst_mdl'].sel(time=slice('2003-01-01','2017-11-30'), \
                                         yt_ocean=slice(lat_min,lat_max), \
                                         xt_ocean=slice(lon_min,lon_max))
# threshold values (from the daily SSTa time series)
fname2 = header + 'SSTa_stats_map_Aus.nc' 
#SST_X = xr.open_dataset(fname2)
sst_p10 = np.array(xr.open_dataset(fname2)['Tp10'])
sst_p90 = np.array(xr.open_dataset(fname2)['Tp90'])

#################################
# allocate memory
#################################
Y = len(xt_ocean)
X = len(yt_ocean)
'''
n_p90_LaN -- number of days above p90 corresponding to La Nina year
n_p10_LaN -- number of days below p10 corresponding to La Nina year
p_p90_LaN -- percentage of number of days above p90 corresponding to La Nina year
p_p10_LaN -- percentage of number of days below p10 corresponding to La Nina year
'''
if ENSO == 'neg':
    Pdays = xr.Dataset({'n_p90_LaN':(('lon','lat'),np.zeros((X, Y))), \
                        'n_p10_LaN':(('lon','lat'),np.zeros((X, Y))), \
                        'p_p90_LaN':(('lon','lat'),np.zeros((X, Y))), \
                        'p_p10_LaN':(('lon','lat'),np.zeros((X, Y)))}, \
                       {'lat': yt_ocean, 'lon': xt_ocean})
elif ENSO == 'pos':
    Pdays = xr.Dataset({'n_p90_ElN':(('lon','lat'),np.zeros((X, Y))), \
                        'n_p10_ElN':(('lon','lat'),np.zeros((X, Y))), \
                        'p_p90_ElN':(('lon','lat'),np.zeros((X, Y))), \
                        'p_p10_ElN':(('lon','lat'),np.zeros((X, Y)))}, \
                       {'lat': yt_ocean, 'lon': xt_ocean})
########################################
## CLIMATE MODE
########################################
# calc NINO3.4 index from DPS
###################################################
nino34 = eac.nino34_index_dps()
mtime = pd.date_range('2003-01-01','2017-12-01',name='time',freq='M')
# make the index daily to be applied on the daily output
nino34_d= np.nan*np.zeros(len(dtime))
m=0
y=0
d=0
for yy in np.arange(0,NumYear):
    if (yy==NumYear-1):
        for mm in np.arange(1,11+1):
            nino34_d[d:d+monthrange(MinYear+y,mm)[1]] = nino34[m]
            m = m + 1
            d = d + monthrange(MinYear+y,mm)[1]
    else:
        for mm in np.arange(1,12+1):
            nino34_d[d:d+monthrange(MinYear+y,mm)[1]] = nino34[m]
            m = m + 1
            d = d + monthrange(MinYear+y,mm)[1]
    y = y + 1
# save indexes where enso is +ve (p) and -ve (n)
nino34_p_id = np.nonzero(nino34_d>=0.4)
nino34_n_id = np.nonzero(nino34_d<=-0.4)
nino34_neu_id = np.nonzero((nino34_d>-0.4) & (nino34_d<0.4))

if ENSO == 'pos':
# SSTa for positive ENSO
    sst_ElN = np.array(SSTa_d)
    sst_ElN[nino34_n_id,:,:] = np.nan
    sst_ElN[nino34_neu_id,:,:] = np.nan
elif ENSO == 'neg':
# SSTa for negative ENSO
    sst_LaN = np.array(SSTa_d)
    sst_LaN[nino34_p_id,:,:] = np.nan
    sst_LaN[nino34_neu_id,:,:] = np.nan


for ln in range(0,Y):
    for lt in range(0,X):
        if ENSO == 'neg':
            Pdays['n_p90_LaN'][lt,ln] = np.count_nonzero(sst_LaN[:,lt,ln] \
                                                         > sst_p90[lt,ln], \
                                                         axis=0)
            Pdays['n_p10_LaN'][lt,ln] = np.count_nonzero(sst_LaN[:,lt,ln] \
                                                         < sst_p10[lt,ln], \
                                                         axis=0)
            Pdays['p_p90_LaN'][lt,ln] = Pdays['n_p90_LaN'][lt,ln]/tim_10th
            Pdays['p_p10_LaN'][lt,ln] = Pdays['n_p10_LaN'][lt,ln]/tim_10th 
        
        elif ENSO == 'pos':
            Pdays['n_p90_ElN'][lt,ln] = np.count_nonzero(sst_ElN[:,lt,ln] \
                                                         > sst_p90[lt,ln], \
                                                         axis=0)
            Pdays['n_p10_ElN'][lt,ln] = np.count_nonzero(sst_ElN[:,lt,ln] \
                                                         < sst_p10[lt,ln], \
                                                         axis=0)
            Pdays['p_p90_ElN'][lt,ln] = Pdays['n_p90_ElN'][lt,ln]/tim_10th
            Pdays['p_p10_ElN'][lt,ln] = Pdays['n_p10_ElN'][lt,ln]/tim_10th
        

## save files
Pdays.to_netcdf(outfile)



