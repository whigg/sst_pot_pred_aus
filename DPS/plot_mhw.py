'''
    Calc and plot the mhw/cold spell time series of the specified
    member (ensemble of the 96 memners used or the 11 individual 
    members available for specific analyses

    Uses the Hobday et al. 2016 definition of a mhw

    Author: Eva Cougnon
    Date created: Apr 2018
    Modified: 

'''
# load required modules

import numpy as np
import xarray as xr
import pandas as pd
#import time as time
from datetime import date
from geopy.distance import vincenty # distance lat/lon

from scipy import io # load matlab file
from scipy import signal # detrend
import scipy.stats.mstats as st # highly similar to scipy.stats 
                                # but adapted for masked arrays

from matplotlib import pyplot as plt
import matplotlib
import mpl_toolkits.basemap as bm
import cmocean

import sys
sys.path.insert(0,'/home/ecougnon/scripts/libraries/')
import eric_oliver as eo
import marineHeatWaves as mhw
import eac_useful as eac

#figfile ='/home/ecougnon/ana/MHW_paper_SarahKirkpatrick/SSTa_mhw_west_tas.png'

##########################
# define some conditions
##########################
# define which member to plot
'''
    WHICH == '00' ensemble mean
    WHICH == ['01':'11'] individual member
    WHICH == 'all' will plot each members in grey overlaid by the
		ensemble mean in black
'''
WHICH = 'all'  #'all' # '01'
# define indexes for lat lon of one pixel
# !!! LONGITUDE in the model!!! from -280 to 80 deg E
'''
info on the regions: 
        Tasman Sea Box with extended western boundary:
                lat[-46:-26]; lon[135:174]E
        SE Aus, Oliver et al. 2017 box: 
                lat[-45:-37]; lon[147:155]E
        west Tasmania, west of the above box:
                lat[-45:-37]; lon[139:147]E
        western Australia (box used in Ming Feng studies)
		lat[-32:-28]; lon[112:115]E
'''
lat_min = -45 #-32 #-55 #-45 #-46 # deg N
lat_max = -37 #-28 #10 #-37 #-26
lon_min = 147 - 360 # 112 #90  #139 #147 #135 #150 # deg E
lon_max = 155 - 360 # 115 #180 #147 #155 #174

################################
# load the model data and 
# area-avearged them
################################
header = '/home/ecougnon/data/DPS/forecast/'
header_reana = '/home/ecougnon/data/DPS/reanalysis/ETKF/'
gname = header + 'RAW/ocean_daily_2002_01_01.nc'
area = xr.open_dataset(gname)['area_t'].sel(yt_ocean=slice(lat_min,lat_max), \
                                            xt_ocean=slice(lon_min,lon_max))

if WHICH == '00' or 'all':
    fname = header + 'sst_daily_Aus_ensemble.nc'
    fname_reana = header_reana + 'sst_reana_ETKF_mem001_20032017_daily_Aus.nc'
else:
    fname = header + 'sst_daily_Aus_mem0' + WHICH + '.nc'

if WHICH == 'all':
# load reanalysis
    sst_reana = xr.open_dataset(fname_reana)['temp'].sel(yt_ocean=slice(lat_min, \
                                                                        lat_max), \
                                                  xt_ocean=slice(lon_min,lon_max), \
                                                  time=slice('2007-01-01','2010-12-31'))
##########
# load the forecast runs (ensemble mean)
##########
    sst_ens = xr.open_dataset(fname)['sst'].sel(yt_ocean=slice(lat_min,lat_max), \
                                                xt_ocean=slice(lon_min,lon_max), \
                                                time=slice('2007-01-01','2010-12-31'))
# create the  mask and the weight matrix
    mask_land = np.ones((len(sst_ens.yt_ocean),len(sst_ens.xt_ocean)))
    mask_land = np.ma.masked_where((np.squeeze(sst_ens[100,:,:]))<-1e15, mask_land)
    area = area * mask_land
    weight = area/np.nansum(area)

    sst_ens = ((sst_ens*weight).sum(dim=('yt_ocean','xt_ocean')))
# detrend the forecast (remove model drift)
    tmp_mean = np.mean(sst_ens)
    sst_ens = signal.detrend(sst_ens, axis=0, type='linear') + np.array(tmp_mean)

    sst_reana = ((sst_reana*weight).sum(dim=('yt_ocean','xt_ocean')))
#    sst_reana = sst_reana.mean(dim=('yt_ocean','xt_ocean'))
##########
# load each member
########## 
    tim_mem_tmp = pd.date_range('2007-01-01','2010-11-22',name='time',freq='D')
    sst_mem = np.NaN*np.zeros((11,len(tim_mem_tmp))) 
    for ii in range(1,12):
        if ii < 10:
            tmp = xr.open_dataset(header + 'sst_daily_Aus_mem00' + str(ii) +'.nc')['sst']. \
                      sel(yt_ocean=slice(lat_min,lat_max), \
                          xt_ocean=slice(lon_min,lon_max), \
                          time=slice('2007-01-01','2010-12-31'))
        elif ii >= 10:
            tmp = xr.open_dataset(header + 'sst_daily_Aus_mem0' + str(ii) +'.nc')['sst']. \
                         sel(yt_ocean=slice(lat_min,lat_max), \
                             xt_ocean=slice(lon_min,lon_max), \
                             time=slice('2007-01-01','2010-12-31'))
# area-averaged sst
        sst_mem[ii-1,:] = ((tmp*weight).sum(dim=('yt_ocean','xt_ocean')))
#        sst_mem[ii-1,:] = tmp.mean(dim=('yt_ocean','xt_ocean'))
# detrend the forecast for each member(remove model drift)
    tmp_mean = np.mean(sst_mem, axis=1)
    sst_mem = signal.detrend(sst_mem, axis=1, type='linear') 
    for ii in range(0,11):
        sst_mem[ii,:] = sst_mem[ii,:] + np.array(tmp_mean[ii])
##########
# load spread
##########
    fname_sp = header + 'temp_spread_enkf13.nc' #'SST_ensemble_spread_2002-2017.nc'
#find the index of lat/lon in the gname file
    xt_lon = xr.open_dataset(gname)['xt_ocean']
    yt_lat = xr.open_dataset(gname)['yt_ocean']
    id_lon_min, _ = eac.find_nearest(np.array(xt_lon),lon_min)
    id_lon_max, _ = eac.find_nearest(np.array(xt_lon),lon_max)
    id_lat_min, _ = eac.find_nearest(np.array(yt_lat),lat_min)
    id_lat_max, _ = eac.find_nearest(np.array(yt_lat),lat_max)
    yaxis_1 = xr.open_dataset(fname_sp)['yaxis_1'].sel(yaxis_1=slice(id_lat_min, \
                                                                     id_lat_max)) #-1))
    xaxis_1 = xr.open_dataset(fname_sp)['xaxis_1'].sel(xaxis_1=slice(id_lon_min, \
                                                                     id_lon_max))
# adjust time
    ID = 66
# ID=13 with the spread from enkf-9 and starting in 2003
# ID = 14 with the spread from enkf-13 starting in 2003
# ID = 66 with the spread from enkf-13 starting in 2007
    T = len(xr.open_dataset(fname_sp)['Time'])
    tim_vec_sp = pd.date_range('2002-01-01','2010-10-31',name='time',freq='28D')
    sst_spread = xr.open_dataset(fname_sp)['temp_an'].sel(Time=slice(ID,T), \
                                                          xaxis_1=xaxis_1, \
                                                          yaxis_1=yaxis_1, \
                                                          zaxis_1=0).squeeze()

    sst_spread = ((sst_spread*np.array(weight)).sum(dim=('yaxis_1','xaxis_1'))) 

#    sst_spread = sst_spread.mean(dim=('yaxis_1','xaxis_1'))
###########
# load HadISST
###########
#    ds_hadisst = xr.open_dataset('/home/data/sst/HadISST_sst.nc')['sst']. \
#                    sel(latitude=slice(lat_max,lat_min), \
#                        longitude=slice(lon_min+360,lon_max+360), \
#                        time=slice('2007-01-01','2010-12-01'))
#    ds_hadisst = ds_hadisst.mean(dim=('latitude','longitude'))
###########
# load AVHRR OISST smoothed
###########
    ds_oisst = xr.open_dataset('/home/ecougnon/ana/SST_smooth_1deg.nc')['__xarray_dataarray_variable__']. \
                  sel(lat=slice(lat_min,lat_max,4), \
                      lon=slice(lon_min+360,lon_max+360,4), \
                      time=slice('2007-01-01','2010-12-31'))
    ds_oisst = ds_oisst.mean(dim=('lat','lon'))

else:
    sst = xr.open_dataset(fname)['sst'].sel(yt_ocean=slice(lat_min,lat_max), \
                                            xt_ocean=slice(lon_min,lon_max), \
                                            time=slice('2003-01-01','2010-12-31'))
    mask_land = np.ones((len(sst.yt_ocean),len(sst.xt_ocean)))
    mask_land = np.ma.masked_where((np.squeeze(sst[100,:,:]))<-1e10, mask_land)
    area = area * mask_land
    area_tot_ocean = np.nansum(area)
    weight = area/area_tot_ocean
# area-averaged sst
    sst_aa = ((sst*weight).sum(dim=('yt_ocean','xt_ocean')))


####################################
## apply the MHW code
####################################
#time vector for the mhw function!!!
# needs to be generated wth datetime format!
MinYear = 2007
MaxYear = 2010 # warninng, so far finishes in Jan!!
NumYears = MaxYear-MinYear+1
MaxNumLeapYear = NumYears//4 + 1 # use only the integer (+1 is used in 
                                     # case the first year is a leap year
NumDays = 365*NumYears + MaxNumLeapYear
# WARNING different finish time
if WHICH == '00':
    dtime = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,10,25). \
                                        toordinal()+1)
# time vector for plotting with mhw
    tim_vec_plot = pd.date_range('2003-01-01','2010-10-25',name='time',freq='D')
elif WHICH == 'all':
    dtime_reana = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,12,31). \
                                              toordinal()+1)
    tim_vec_plot_reana = pd.date_range('2007-01-01','2010-12-31',name='time',freq='D')

    dtime_ens = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,10,25). \
                                            toordinal()+1)
    tim_ens_plot = pd.date_range('2007-01-01','2010-10-25',name='time',freq='D')
    dtime_mem = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,11,22). \
                                            toordinal()+1)
    tim_mem_plot = pd.date_range('2007-01-01','2010-11-22',name='time',freq='D')
else:
    dtime = np.arange(date(MinYear,1,1).toordinal(),date(MaxYear,11,22). \
                                        toordinal()+1)
# time vector for plotting with mhw
    tim_vec_plot = pd.date_range('2003-01-01','2010-11-22',name='time',freq='D')
    sst_mean_d = np.array(sst_aa)
if WHICH != 'all':
    sst_mean_d = np.array(sst_aa)
    mhws, clim = mhw.detect(dtime, sst_mean_d, climatologyPeriod=[2003,2006])

####################################
# Plotting
####################################
plt.figure(figsize=(13,12)) 

if WHICH != 'all':
    ax = plt.subplot(211)
    plt.plot(tim_vec_plot, clim['seas'], '0.5')
    plt.plot(tim_vec_plot, sst_mean_d, 'k')
    plt.plot(tim_vec_plot, clim['thresh'],'b')
    plt.legend(['climatology','SST daily','threshold'])
    ax.set_xlim(['2003-01-01','2010-12-31'])
    ax.set_ylim([10, 22])
#ax.fill_between(tim_vec_plot, sst_mean_d, \
#                where=sst_mean_d>= clim['thresh'], \
#                facecolor='red', alpha=0.5, \
#               interpoate=True)
    plt.title('SST Tasman Sea Box area', fontsize=16)
    plt.grid()

    ax = plt.subplot(212)
    plt.plot(tim_vec_plot, sst_mean_d-clim['seas'], 'k')
    ax.set_xlim(['2003-01-01','2010-12-31'])
    ax.set_ylim([-3, 3])
    plt.title('SSTa Tasman Sea Box area', fontsize=16)
    plt.grid()

elif WHICH == 'all':
    ax = plt.subplot(211)
    for ii in range(0,11):
        ax.plot(tim_mem_plot, sst_mem[ii,:], '0.5', label='F mem')
#    ax.plot(tim_ens_plot, sst_ens, 'k', label= 'F ens mean')
    ax.plot(tim_vec_plot_reana, sst_reana, 'r', label= 'R ens mean')
    ax.plot(tim_ens_plot, sst_ens, 'k', label= 'F ens mean')
    ax.plot(ds_oisst.time, ds_oisst,'g', label= 'oisst')
    ax.plot(tim_vec_sp[ID:-1], sst_ens[np.arange(22,len(sst_ens),28)] + \
                               sst_spread[:-1], '--*b', label= 'spread')
    ax.plot(tim_vec_sp[ID:-1], sst_ens[np.arange(22,len(sst_ens),28)] - \
                               sst_spread[:-1], '--*b', label= 'spread')
    ax.set_xlim(['2007-01-01','2010-12-31'])
    ax.set_ylim([11, 21])
    handles, labels = ax.get_legend_handles_labels()
    handles = [handles[-6], handles[-5], handles[-4], handles[-3], handles[-2]]
    labels = [labels[-6], labels[-5], labels[-4], labels[-3], labels[-2]]
    ax.legend(handles,labels)
    plt.title('SST for a specified region (TAS)')
    plt.grid()
   
    ax = plt.subplot(212)
    '''
    for ii in range(0,11):
        mhws, clim = mhw.detect(dtime_mem, sst_mem[ii,:], \
                                climatologyPeriod=[2007,2010])
        plt.plot(tim_mem_plot, sst_mem[ii,:]-clim['seas'], '0.5')

    tmp_sst_reana = np.array(sst_reana)
    mhws, clim = mhw.detect(dtime_reana, tmp_sst_reana, \
                            climatologyPeriod=[2007,2010])
    plt.plot(tim_vec_plot_reana, tmp_sst_reana-clim['seas'], 'r')
    tmp_sst = np.array(sst_ens)
    mhws, clim = mhw.detect(dtime_ens, tmp_sst, climatologyPeriod=[2007,2010])
    plt.plot(tim_ens_plot, tmp_sst-clim['seas'], 'k')
#    tmp_sst_reana = np.array(sst_reana)
#    mhws, clim = mhw.detect(dtime_reana, tmp_sst_reana, climatologyPeriod=[2003,2006])
#    plt.plot(tim_vec_plot_reana, tmp_sst_reana-clim['seas'], 'r')
    ax.set_xlim(['2007-01-01','2010-12-31'])
    ax.set_ylim([-3, 3])
    plt.title('SSTa for a specified region -- climatology based on 2003-2006', \
              fontsize=16)
    '''
    ax.plot(tim_vec_sp[ID:-1], sst_spread[:-1], '--*b', label= 'spread')
    plt.title('spread area-averaged for the region')
    ax.set_xlim(['2007-01-01','2010-12-31'])
    plt.grid()
    
    figfile = header + 'plots/SST_TAS_forecast_dedrifted_oisst_temp_an.png'
plt.savefig(figfile, bbox_inches='tight', format='png', dpi=300)

plt.show()

