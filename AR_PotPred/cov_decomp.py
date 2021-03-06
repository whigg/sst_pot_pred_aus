#######################################
# covariance decomposition
# following ZFL method
#
# testing pahse
#
# Author: Eva Cougnon
# Created: May 2017 
# Last modif: Jul 2017
########################################

# import libraries
import numpy as np
from scipy import linalg
import xarray as xr
import time as time

from matplotlib import pyplot as plt
import matplotlib
import mpl_toolkits.basemap as bm

import sys
sys.path.insert(0,'/home/ecougnon/scripts/libraries/')
import eac_useful as eac


#def CovDecomp_ZFL(ts_mtx,tau,NumChunk,str_id,end_id):

'''
    covariance decomposition and eof following ZFL...

    the time series matrix should be (time,location)

    The method used here follow the Zheng, Frederiksen, Lou 
    method after:
    Lou et al. 2016 -- doi 10.1007/s00382-016-3229-x
    Frederiksen et al. 2015 -- doi 10.1007/s00382-015-2699-6

    INPUT:
    ts_mtx: time series matrix (time, location)
    tau  -- length of the chunk
    NumChunk -- total number of chunks
    str_id, end_id -- starting and ending indexes for each chunk

'''

#return 

# useful information
tau = 12 # number of chunk for the potential pred
outfile = '/home/ecougnon/ana/PotPred/EOF/cov_decomp_1yr_ZFL_EOF_Aus_1deg_OTEp10_Modes1-8'
fname = '/home/ecougnon/ana/OTEs_NumDays_month_Aus_19822016.nc'
#SSTa_monthly_extremes_global.nc'
deg_res = 1 #5
lat_min = -55 #-80 #-20 #-55
lat_max = 10 #80 #20 #10
lat_bin = 4 * deg_res 
lon_min = 90 #1 #160 #90
lon_max = 180 #360 #270 #180
lon_bin = 4 * deg_res
lat = xr.open_dataset(fname)['lat']
lat = lat.sel(lat=slice(lat_min,lat_max,lat_bin))
lon = xr.open_dataset(fname)['lon']
lon = lon.sel(lon=slice(lon_min,lon_max,lon_bin))
time_ts = xr.open_dataset(fname)['time']
T_keys = ['Pdays_p10']
#['TMM', 'TMX', 'TMN', 'Tp90', 'Tp10']
# choose the key, work only on one file!!!
key = T_keys[0] ############################ need to change it !!###########
print(key)
## time period
MinYear = 1982
MaxYear = 2016
NumYears = MaxYear - MinYear+1
NumMonths = NumYears*12
# define the start/end indexes for each chunk
str_id = np.arange(0,NumMonths,tau,dtype=int)
end_id = np.arange(tau-1,NumMonths+1,tau,dtype=int)
NumChunk = len(str_id)

# allocate memory
#####################################
## check what will be the output of the CovDecomp function
## may not be the covariance mtx but the EOF directly?!
## or output the cov matrices then use another function
## to compute the eigenvector of each cov mtx -- EOF
#####################################
PP_keys = ['CoVar_interC','CoVar_noise','CoVar_slow']
'''
describe the keys ..
CoVar_interC -- total inter chunk covariance matrix
CoVar_noise -- covariance matrix of the noise over all chunks
CoVar_slow -- covariance matrix of the potentially predictable component
'''
X = len(lon)
Y = len(lat)
t = len(time_ts)
'''
var = len(PP_keys)
PP = xr.Dataset({'TMM':(('PP_keys','lat','lon'),np.zeros((var, Y, X))), \
                 'TMX':(('PP_keys','lat','lon'),np.zeros((var, Y, X))), \
                 'TMN':(('PP_keys','lat','lon'),np.zeros((var, Y, X))), \
                 'Tp90':(('PP_keys','lat','lon'),np.zeros((var, Y, X))), \
                 'Tp10':(('PP_keys','lat','lon'),np.zeros((var, Y, X)))}, \
                {'PP_keys': PP_keys, 'lat': lat, 'lon': lon})
'''

# the data should already be anomalies (detrended and deseasonned)
SST_ = xr.open_dataset(fname)[key]
SST_ = SST_.sel(lat =slice(lat_min,lat_max,lat_bin), \
               lon=slice(lon_min,lon_max,lon_bin)) 
# Create an EOF solver to do the EOF analysis. 
# Do a spatially weighted anomaly covariance matrix of a field
# The SSTs are already anomalies, then weight before the computation of EOFs: 
# Square-root of cosine of latitude
coslat = np.cos(np.deg2rad(SST_.coords['lat'].values))
wgts = np.sqrt(coslat)[..., np.newaxis]

SST_ = SST_/wgts
SST = np.array(SST_)
# reshape to have all the locations in the same dimension, time in the other
SST_flat = SST.reshape((t,X*Y))

### below -- should dbe part of a function
# remove land points
ts_mtx = SST_flat[:,~np.isnan(SST_flat).all(0)]

# chunck time series -- dim (time, location)
ts_mtx_chunk = np.empty((tau*NumChunk,len(ts_mtx[0,:])))
ts_mtx_chunk.fill(np.nan)
ts_mtx_chunkmean_all = np.empty((len(ts_mtx[0,:])))
ts_mtx_chunkmean_all.fill(np.nan)
# chunk mean allocation
ts_mtx_chunkmean = np.empty((NumChunk,len(ts_mtx[0,:])))
ts_mtx_chunkmean.fill(np.nan)
kk=0
for c in range(0,NumChunk): # run through each chunk
    ts_mtx_chunk[kk:kk+tau,:] = ts_mtx[str_id[c]:end_id[c]+1,:]
    ts_mtx_chunkmean[c,:] = np.nanmean(ts_mtx[str_id[c]:end_id[c]+1,:],axis=0)    
    kk = kk + tau

# covariance matrix (every degree)
cov_mtx_chunk = np.cov(ts_mtx_chunkmean, rowvar=0)

'''
## estimating the co-variance matrix of the unpredictible component
# low pass filter: remove the chunk length running mean filter of 
# the combined chunk time series 
ts_box = np.apply_along_axis(eac.moving_average,0,ts_mtx_chunk[:,:],tau)
# remove low pass filter -- keep the noise part  
ts_noise = ts_mtx_chunk[int(tau/2):-int(tau/2)+1,:] - ts_box[:,:]

# auto correlation coef with lag-1 -- vector for each location
#alpha = np.apply_along_axis(eac.get_autocorr_coef,0,ts_noise[1:,:],ts_noise[:-1,:])
# np.apply_along_axis not working....
alpha=np.empty(len(ts_noise[0,:]))
alpha.fill(np.nan)
for i in range(0,len(ts_noise[0,:])):
    alpha[i] = eac.get_autocorr_coef(ts_noise[1:,i],ts_noise[:-1,i])

# covariance matrix from Frederiksen et al 2015 for the unpredictable component
cov_noise = np.empty((len(alpha), len(alpha)))
cov_noise.fill(np.nan)
fact_a = 1/((tau-1)*NumChunk) # factor for a calc (or gamma depends if a is defined!)
tt_b=np.arange(1,tau)
tmp_a = np.empty(NumChunk)
tmp_a.fill(np.nan)
for i in range(0,len(alpha)):
    for j in range(i,len(alpha)):
#        t_key = time.time()

###############################################       
# part in (wide curly braket)/tau^2 in their paper eq (2)
#        for tt in range(1,tau):
#            tmp_b[tt-1] = (tau - tt)*(alpha[i]**tt + alpha[j]**tt)
#        beta = (np.nansum(tmp_b) + tau) / tau**2
        beta = (np.nansum( (tau - tt_b)*(alpha[i]**tt_b+alpha[j]**tt_b) ) \
                + tau) / tau**2
# as in their eq (3) combine with eq (4) -- a        
        for tt in range(0,NumChunk):
            tmp_a[tt] = np.nansum((ts_mtx[str_id[tt]+1:end_id[tt]+1,i] - \
                                   ts_mtx[str_id[tt]:end_id[tt],i]) * \
                                   (ts_mtx[str_id[tt]+1:end_id[tt]+1,j] - \
                                   ts_mtx[str_id[tt]:end_id[tt],j])) 
        gamma = (fact_a * np.nansum(tmp_a)) / (2 - alpha[i] - alpha[j])

        cov_noise[i,j] = beta * gamma
        cov_noise[j,i] = beta * gamma

####################################       
        cov_noise[i,j] = eac.cov_unpred_testing(ts_mtx[:,i],ts_mtx[:,j], \
                                                alpha[i],alpha[j],tau,NumChunk, \
                                                str_id, end_id)

        cov_noise[j,i] = cov_noise[i,j].copy()

#        elapsed_key = time.time() - t_key
#        print('elapsed time for each key:', elapsed_key)
'''

# using the updated cov_unpred_testing function (20 Jul 2017)
cov_noise = eac.cov_unpred_testing(ts_mtx, tau, NumChunk, str_id, end_id)


EIGVAL = {}
keys_eigval = ['eigvalP_tot', 'eigvalP_unp', 'eigvalP_pred', \
              'delta_eigval_tot', 'delta_eigval_pred', 'delta_eigval_unp']
for key in keys_eigval:
    EIGVAL[key] = np.zeros(len(cov_noise))

## calc eigenvalues and vectors
eigval_tot, eigvec_tot = linalg.eigh(cov_mtx_chunk)
eigval_unp, eigvec_unp = linalg.eigh(cov_noise)
eigval_pred, eigvec_pred = linalg.eigh(cov_mtx_chunk-cov_noise)
# percentage of explained variance
EIGVAL['eigvalP_tot'] = eigval_tot/np.sum(eigval_tot) * 100
EIGVAL['eigvalP_unp'] = eigval_unp/np.sum(eigval_unp) * 100
EIGVAL['eigvalP_pred'] = eigval_pred/np.sum(eigval_pred) * 100

# Uses North et al equation 24 to see if eigenvalues (lambda) are 
# significantly separated
EIGVAL['delta_eigval_tot'] = EIGVAL['eigvalP_tot'] \
                             * np.sqrt(2/len(EIGVAL['eigvalP_tot']))
EIGVAL['delta_eigval_pred'] = EIGVAL['eigvalP_pred'] \
                              * np.sqrt(2/len(EIGVAL['eigvalP_pred']))
EIGVAL['delta_eigval_unp'] = EIGVAL['eigvalP_unp'] \
                             * np.sqrt(2/len(EIGVAL['eigvalP_unp']))

# PC1 and PC2 projected on the monthly time series 
PC = {}
keys_PC = ['PC1_tot', 'PC1_unp', 'PC1_pred', 'PC2_tot', 'PC2_unp', 'PC2_pred', \
           'PC3_tot', 'PC3_unp', 'PC3_pred', 'PC4_tot', 'PC4_unp', 'PC4_pred', \
           'PC5_tot', 'PC5_unp', 'PC5_pred', 'PC6_tot', 'PC6_unp', 'PC6_pred', \
           'PC7_tot', 'PC7_unp', 'PC7_pred', 'PC8_tot', 'PC8_unp', 'PC8_pred',]
for key in keys_PC:
    PC[key] = np.zeros(len(ts_mtx_chunk))

PC['PC1_tot'] = np.dot(eigvec_tot[:,-1],np.transpose(ts_mtx_chunk))
PC['PC1_unp'] = np.dot(eigvec_unp[:,-1],np.transpose(ts_mtx_chunk))
PC['PC1_pred'] = np.dot(eigvec_pred[:,-1],np.transpose(ts_mtx_chunk))
PC['PC2_tot'] = np.dot(eigvec_tot[:,-2],np.transpose(ts_mtx_chunk))
PC['PC2_unp'] = np.dot(eigvec_unp[:,-2],np.transpose(ts_mtx_chunk))
PC['PC2_pred'] = np.dot(eigvec_pred[:,-2],np.transpose(ts_mtx_chunk))
PC['PC3_tot'] = np.dot(eigvec_tot[:,-3],np.transpose(ts_mtx_chunk))
PC['PC3_unp'] = np.dot(eigvec_unp[:,-3],np.transpose(ts_mtx_chunk))
PC['PC3_pred'] = np.dot(eigvec_pred[:,-3],np.transpose(ts_mtx_chunk))
PC['PC4_tot'] = np.dot(eigvec_tot[:,-4],np.transpose(ts_mtx_chunk))
PC['PC4_unp'] = np.dot(eigvec_unp[:,-4],np.transpose(ts_mtx_chunk))
PC['PC4_pred'] = np.dot(eigvec_pred[:,-4],np.transpose(ts_mtx_chunk))
PC['PC5_tot'] = np.dot(eigvec_tot[:,-5],np.transpose(ts_mtx_chunk))
PC['PC5_unp'] = np.dot(eigvec_unp[:,-5],np.transpose(ts_mtx_chunk))
PC['PC5_pred'] = np.dot(eigvec_pred[:,-5],np.transpose(ts_mtx_chunk))
PC['PC6_tot'] = np.dot(eigvec_tot[:,-6],np.transpose(ts_mtx_chunk))
PC['PC6_unp'] = np.dot(eigvec_unp[:,-6],np.transpose(ts_mtx_chunk))
PC['PC6_pred'] = np.dot(eigvec_pred[:,-6],np.transpose(ts_mtx_chunk))
PC['PC7_tot'] = np.dot(eigvec_tot[:,-7],np.transpose(ts_mtx_chunk))
PC['PC7_unp'] = np.dot(eigvec_unp[:,-7],np.transpose(ts_mtx_chunk))
PC['PC7_pred'] = np.dot(eigvec_pred[:,-7],np.transpose(ts_mtx_chunk))
PC['PC8_tot'] = np.dot(eigvec_tot[:,-8],np.transpose(ts_mtx_chunk))
PC['PC8_unp'] = np.dot(eigvec_unp[:,-8],np.transpose(ts_mtx_chunk))
PC['PC8_pred'] = np.dot(eigvec_pred[:,-8],np.transpose(ts_mtx_chunk))

# normalised the eigenvector by its max for the 8 upper modes: 
#  include the for loop
tot_modes = eigvec_tot[:,-8:].copy()
unp_modes = eigvec_unp[:,-8:].copy()
pred_modes = eigvec_pred[:,-8:].copy()
'''
for ii in range(0,6):
    tot_modes[:,ii] = tot_modes[:,ii]/np.max(np.abs(tot_modes[:,ii]))
    unp_modes[:,ii] = unp_modes[:,ii]/np.max(np.abs(unp_modes[:,ii]))
    pred_modes[:,ii] = pred_modes[:,ii]/np.max(np.abs(pred_modes[:,ii]))
'''
# reshape!
MODES_MAP = {}
keys_modes = ['tot_modes_map', 'unp_modes_map', 'pred_modes_map']
for key in keys_modes:
    MODES_MAP[key] = np.zeros((len(tot_modes[0,:]),len(SST_flat[0,:])))
#tot_modes_map = np.empty((len(tot_modes[0,:]),len(SST_flat[0,:])))
#unp_modes_map = np.empty((len(unp_modes[0,:]),len(SST_flat[0,:])))
#pred_modes_map = np.empty((len(pred_modes[0,:]),len(SST_flat[0,:])))
k=0
for ii in range(0,len(SST_flat[0,:])):
    if (np.isnan(SST_flat[0,ii]).all(0) == False):
         MODES_MAP['tot_modes_map'][:,ii] = tot_modes[k,:]
         MODES_MAP['unp_modes_map'][:,ii] = unp_modes[k,:]
         MODES_MAP['pred_modes_map'][:,ii] = pred_modes[k,:]
         k += 1
    elif (np.isnan(SST_flat[0,ii]).all(0) == True):
        MODES_MAP['tot_modes_map'][:,ii] = np.nan
        MODES_MAP['unp_modes_map'][:,ii] = np.nan
        MODES_MAP['pred_modes_map'][:,ii] = np.nan
MODES_MAP['tot_modes_map'] = \
MODES_MAP['tot_modes_map'].reshape(len(MODES_MAP['tot_modes_map'][:,0]),Y,X)
MODES_MAP['unp_modes_map'] = \
MODES_MAP['unp_modes_map'].reshape(len(MODES_MAP['unp_modes_map'][:,0]),Y,X)
MODES_MAP['pred_modes_map'] = \
MODES_MAP['pred_modes_map'].reshape(len(MODES_MAP['pred_modes_map'][:,0]),Y,X)

# saving
np.savez(outfile, MODES_MAP=MODES_MAP, EIGVAL=EIGVAL, PC=PC, lat=lat, lon=lon, \
	 time_ts=time_ts)
## should save the data here and have another script for plotting!!

'''
## plotting -- testing!!!
domain = [lat_min, lon_min, lat_max, lon_max] 
domain_draw = [lat_min, lon_min, lat_max, lon_max] 
dlat = 30 #10
dlon = 90 #30
llon, llat = np.meshgrid(lon, lat)
bg_col = '0.6'
cont_col = '1.0'
lev = np.hstack((np.arange(-0.15,-0.01+0.01,0.02), np.arange(0.01,0.15+0.01,0.02)))

# what to plot
var=MODES_MAP['unp_modes_map'].copy()

plt.figure(figsize=(12,11)) #7,11)) #(12,6)) # (10,8)
plt.clf()
ax1 = plt.subplot(2,1,1)
proj = bm.Basemap(projection='cyl', llcrnrlat=domain[0], llcrnrlon=domain[1], \
                  urcrnrlat=domain[2], urcrnrlon=domain[3], resolution='i')
#proj = bm.Basemap(projection='merc', llcrnrlat=domain[0], llcrnrlon=domain[1], \
#                  urcrnrlat=domain[2], urcrnrlon=domain[3], resolution='i')
proj.fillcontinents(color=(0,0,0), lake_color=(0,0,0), ax=None, \
                    zorder=None, alpha=None)
proj.drawparallels(range(domain_draw[0],domain_draw[2]+1,dlat), \
                   labels=[True,False,False,False], fontsize=14)
proj.drawmeridians(range(domain_draw[1],domain_draw[3]+1,dlon), \
                   labels=[False,False,False,True], fontsize=14)
lonproj, latproj = proj(llon, llat)
plt.contourf(lonproj, latproj, var[-1,:,:], \
             levels= lev, \
             cmap=plt.cm.seismic) 
cb=plt.colorbar(ticks=lev,shrink=0.9)
#cb.ax1.tick_params(labelsize=14)
plt.title('testing -- mode 1, 2.7% -- unpred', \
          fontsize=16, y=1.08)

ax2 = plt.subplot(2,1,2)
proj = bm.Basemap(projection='cyl', llcrnrlat=domain[0], llcrnrlon=domain[1], \
                  urcrnrlat=domain[2], urcrnrlon=domain[3], resolution='i')
#proj = bm.Basemap(projection='merc', llcrnrlat=domain[0], llcrnrlon=domain[1], \
#                  urcrnrlat=domain[2], urcrnrlon=domain[3], resolution='i')
proj.fillcontinents(color=(0,0,0), lake_color=(0,0,0), ax=None, \
                    zorder=None, alpha=None)
proj.drawparallels(range(domain_draw[0],domain_draw[2]+1,dlat), \
                   labels=[True,False,False,False], fontsize=14)
proj.drawmeridians(range(domain_draw[1],domain_draw[3]+1,dlon), \
                   labels=[False,False,False,True], fontsize=14)
lonproj, latproj = proj(llon, llat)
plt.contourf(lonproj, latproj, var[-2,:,:], levels=lev,  cmap=plt.cm.seismic) 
cb=plt.colorbar(ticks=lev, shrink=0.9)
#cb.ax2.tick_params(labelsize=14)
plt.title('testing -- mode 2, 2.3% -- unpred', \
          fontsize=16, y=1.08)
#plt.savefig(figfile,bbox_inches='tight')
plt.show()

# plotting eigenvalue spectrum -- North et al 1982
plt.figure()
plt.errorbar(np.arange(6,0,-1),eigvalP_tot[-6:],yerr=d_eigval_tot[-6:])
plt.errorbar(np.arange(6,0,-1),eigvalP_pred[-6:],yerr=d_eigval_pred[-6:])
plt.errorbar(np.arange(6,0,-1),eigvalP_unp[-6:],yerr=d_eigval_unp[-6:])
plt.legend(['tot','pred','unp'])
plt.title('Eigenvalues spectrum -- North et al. 1982')
plt.xlabel('EOF modes')
plt.ylabel('Eigenvalue (%)')
plt.show()

'''

