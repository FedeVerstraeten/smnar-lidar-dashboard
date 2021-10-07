import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
import pandas as pd
import numpy as np
import json
from utils import plotly_plot

from scipy import constants
from scipy import integrate
from scipy.interpolate import interp1d

from lidarcontroller.licelcontroller import licelcontroller
from lidarcontroller import licelsettings

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')


# Defining routes

@app.route("/")
@app.route("/lidar")
def plot_lidar_signal():

  # basic settings
  BIN_LONG_TRANCE = 4000
  SHOTS_DELAY = 1000 # wait 10s = 300shots/30Hz
  OFFSET_BINS = 10


  # initialization
  lc = licelcontroller()
  lc.openConnection('10.49.234.234',2055)
  tr=0 #first TR
  lc.selectTR(tr)
  lc.setInputRange(licelsettings.MILLIVOLT500)
  lc.setThresholdMode(licelsettings.THRESHOLD_LOW)
  # lc.setDiscriminatorLevel(8) # can be set between 0 and 63
  
 
  # start the acquisition
  lc.clearMemory()
  lc.startAcquisition()
  lc.msDelay(SHOTS_DELAY)
  lc.stopAcquisition() 
  #lc.waitForReady(100) # wait till it returns to the idle state

  ## get the shotnumber 
  if lc.getStatus() == 0:
    if (lc.shots_number > 1):
      cycles = lc.shots_number - 2 # WHY??!

  # read from the TR triggered mem A
  data_lsw = lc.getDatasets(tr,"LSW",BIN_LONG_TRANCE+1,"A")
  data_msw = lc.getDatasets(tr,"MSW",BIN_LONG_TRANCE+1,"A")
  
  # combine, normalize an scale data to mV
  data_accu,data_clip = lc.combineAnalogDatasets(data_lsw, data_msw)
  data_phys = lc.normalizeData(data_accu,cycles)
  data_mv = lc.scaleAnalogData(data_phys,licelsettings.MILLIVOLT500) 
  
  # DUMP THE DATA INTO A FILE
  with open('analog.txt', 'w') as file: # or analog.dat 'wb'
    np.savetxt(file,data_mv,delimiter=',')

  #----------- RANGE CORRECTION ---------------

  lidar_signal = np.array(data_mv)
  
  # load data
  # LIDAR_FILE='./analog_532par_500mV_CON_THRESHOLD.txt'
  # data_csv = pd.read_csv(LIDAR_FILE,sep='\n',header=None)
  # lidar_signal = np.array(data_csv[0])
  
   # number_bins = len(data_csv[0])

  # offset correction
  lidar_signal=lidar_signal[OFFSET_BINS:]
  number_bins = len(lidar_signal)

  # LiDAR signal range correction since bin number 1000
  # BIN_RC_THRESHOLD=1000
  BIN_RC_THRESHOLD=int(BIN_LONG_TRANCE/4)
  height = np.arange(0, number_bins, 1)
  lidar_bias = np.mean(lidar_signal[BIN_RC_THRESHOLD:])
  lidar_rc = (lidar_signal - lidar_bias)*(height**2)

  # smooth with box
  box_pts=5
  box = np.ones(box_pts)/box_pts
  lidar_rc = np.convolve(lidar_rc, box, mode='same')

  #----------- RAYLEIGH-FIT ------------------

  #-------------
  #  Parameters
  #-------------

  # LiDAR 
  BIN_RC_THRESHOLD=1000
  wave_length = 532 #nm

  # Current surface atmospheric conditions (Av.Dorrego SMN)
  SURFACE_TEMP = 300 # [K] 27C
  SURFACE_PRESS = 1024 # [hPa]
  MASL = 10.0 # meters above sea level (AMSL)

  # rayleigh-fit meters 
  RF_INIT=3000
  RF_FINAL=8000

  #----------
  #  MODEL
  #----------

  # load data
  MODEL_FILE='./US-StdA_DB_CEILAP.csv'
  data_csv = pd.read_csv(MODEL_FILE,sep=',',header=None)

  height_lowres=np.array(data_csv[0])
  temp_lowres=np.array(data_csv[1])
  press_lowres=np.array(data_csv[2])

  print("number bins ",number_bins)
  # Height high resolution
  #height_highres = np.linspace(height_lowres[0], number_bins*7.5, num=number_bins, endpoint=True)
  
  height_highres = np.arange(height_lowres[0], (number_bins+1)*7.5, 7.5,) # ESTE ES EL CORRECTO PERO HAY QUE AGREGAR UN CERO AL PRINCIPIO
  #height_lowres[-1] = height_highres[-1]

  index_MASL = (np.abs(height_highres - MASL)).argmin() # Height above mean sea level (AMSL)

  # Interpolation Spline 1D
  temp_spline = interp1d(height_lowres, temp_lowres, kind='cubic')
  temp_highres = temp_spline(height_highres)

  press_spline = interp1d(height_lowres, press_lowres, kind='cubic')
  press_highres = press_spline(height_highres)

  # Scaling the temperature and pressure profiles in the model
  # with current surface conditions
  temp_highres = SURFACE_TEMP * (temp_highres/temp_highres[index_MASL])
  press_highres = SURFACE_PRESS * (press_highres/press_highres[index_MASL])

  # atm molecular concentration 
  kboltz=constants.k
  nmol = (100*press_highres[index_MASL:])/(temp_highres[index_MASL:]*kboltz) 

  # alpha y beta
  beta_mol = nmol * (550/wave_length)**4.09 * 5.45 * (10**-32)
  alpha_mol = beta_mol * (8*np.pi/3)

  range_lidar = height_highres[:-index_MASL]
  cumtrapz = integrate.cumtrapz(alpha_mol, range_lidar, initial=0)
  tm2r_mol = np.exp(-2*cumtrapz)
  pr2_mol = beta_mol*tm2r_mol


  #----------
  #  Min ECM
  #----------
  bin_init = int(RF_INIT/7.5)
  bin_fin = int(RF_FINAL/7.5)


  # sig == lidar_rc
  # sigmol == pr2_mol
  mNum = np.dot(lidar_rc[bin_init:bin_fin+1],pr2_mol[bin_init:bin_fin+1])
  mDen = np.dot(pr2_mol[bin_init:bin_fin+1],pr2_mol[bin_init:bin_fin+1])
  factor_adj = mNum/mDen

  print("Min ECM:",np.format_float_scientific(factor_adj))

 
  #-------------- PLOTING --------------------

  #ploting
  plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar_signal)
  plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(range_lidar,lidar_rc,pr2_mol*factor_adj)

  # load dict context
  context = {"number_bins": number_bins,
             "plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction}

  # run html template
  return render_template('lidar.html', context=context)

@app.route("/signal", methods=['GET','POST'])
def plot_selected_signal():

  lidar_type_plot = request.args['selected']

  #lidar_type_plot = request.form['lidar_type_plot']
  
  # load data
  LIDAR_FILE='./analog.txt'
  data_csv = pd.read_csv(LIDAR_FILE,sep='\n',header=None)
  lidar_signal = np.array(data_csv[0])
  number_bins = len(data_csv[0])

  if(lidar_type_plot == "raw"):
    # plot_selected_signal  = plotly_plot.plotly_lidar_signal(lidar_signal)
    plot_selected_signal_JSON  = plotly_plot.plotly_lidar_signal(lidar_signal)


  elif(lidar_type_plot == "range"):
    # LiDAR signal range correction since bin number 1000
    BIN_RC_THRESHOLD=1000
    height = np.arange(0, number_bins, 1)
    lidar_bias = np.mean(lidar_signal[BIN_RC_THRESHOLD:])
    lidar_rc = (lidar_signal - lidar_bias)*(height**2)
    # plot_selected_signal  = plotly_plot.plotly_lidar_range_correction(lidar_rc)
    plot_selected_signal_JSON  = plotly_plot.plotly_lidar_range_correction(lidar_rc)

  # load dict context
  # context = {"number_bins": number_bins,
  #            "plot_selected_signal": plot_selected_signal }

  # return render_template('signal.html', context=context)
  print(plot_selected_signal_JSON)
  return plot_selected_signal_JSON

@app.route("/acquis", methods=['GET','POST'])
def plot_acquis():
  action_button = request.args['selected']

  # basic settings
  BIN_LONG_TRANCE = 4000

  SHOTS_DELAY = 1000 # wait 10s = 300shots/30Hz

  lc = licelcontroller()
  lc.openConnection('10.49.234.234',2055)
  tr=0 #first TR

  if(action_button =="start"):
    # start the acquisition
    lc.clearMemory()
    lc.startAcquisition()
    lc.msDelay(SHOTS_DELAY)
    lc.stopAcquisition() 
    #lc.waitForReady(100) # wait till it returns to the idle state

    ## get the shotnumber 
    if lc.getStatus() == 0:
      if (lc.shots_number > 1):
        cycles = lc.shots_number - 2 # WHY??!

    # read from the TR triggered mem A
    data_lsw = lc.getDatasets(tr,"LSW",BIN_LONG_TRANCE+1,"A")
    data_msw = lc.getDatasets(tr,"MSW",BIN_LONG_TRANCE+1,"A")
    
    # combine, normalize an scale data to mV
    data_accu,data_clip = lc.combineAnalogDatasets(data_lsw, data_msw)
    data_phys = lc.normalizeData(data_accu,cycles)
    data_mv = lc.scaleAnalogData(data_phys,licelsettings.MILLIVOLT500) 
    
    # DUMP THE DATA INTO A FILE
    with open('analog.txt', 'w') as file: # or analog.dat 'wb'
      np.savetxt(file,data_mv,delimiter=',')

    lidar_signal = np.array(data_mv)
    number_bins = len(data_mv)
 
    BIN_RC_THRESHOLD=int(BIN_LONG_TRANCE/4)
    height = np.arange(0, number_bins, 1)
    lidar_bias = np.mean(lidar_signal[BIN_RC_THRESHOLD:])
    lidar_rc = (lidar_signal - lidar_bias)*(height**2)

    #ploting
    plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar_signal)
    plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar_rc)

    # load dict context
    context = {"number_bins": number_bins,
               "plot_lidar_signal": plot_lidar_signal,
               "plot_lidar_range_correction": plot_lidar_range_correction}

    # run html template
    return context


if __name__ == '__main__':
  app.run(debug=True)
