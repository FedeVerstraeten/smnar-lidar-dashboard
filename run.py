import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
import pandas as pd
import numpy as np
import json
from utils import plotly_plot

# from scipy import constants
# from scipy import integrate
# from scipy.interpolate import interp1d

from lidarcontroller.licelcontroller import licelcontroller
from lidarcontroller import licelsettings
from lidarcontroller.lidarsignal import lidarsignal

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')

# global
lidar = lidarsignal()

# Defining routes

@app.route("/")
@app.route("/lidar")
def plot_lidar_signal():

  # basic settings
  BIN_LONG_TRANCE = 4000
  SHOTS_DELAY = 1000 # wait 10s = 300shots/30Hz
  OFFSET_BINS = 10
  THRESHOLD_METERS = 2000 # meters


  # initialization
  # lc = licelcontroller()
  # lc.openConnection('10.49.234.234',2055)
  # tr=0 #first TR
  # lc.selectTR(tr)
  # lc.setInputRange(licelsettings.MILLIVOLT500)
  # lc.setThresholdMode(licelsettings.THRESHOLD_LOW)
  # # lc.setDiscriminatorLevel(8) # can be set between 0 and 63
  
 
  # # start the acquisition
  # lc.clearMemory()
  # lc.startAcquisition()
  # lc.msDelay(SHOTS_DELAY)
  # lc.stopAcquisition() 
  # #lc.waitForReady(100) # wait till it returns to the idle state

  # ## get the shotnumber 
  # if lc.getStatus() == 0:
  #   if (lc.shots_number > 1):
  #     cycles = lc.shots_number - 2 # WHY??!

  # # read from the TR triggered mem A
  # data_lsw = lc.getDatasets(tr,"LSW",BIN_LONG_TRANCE+1,"A")
  # data_msw = lc.getDatasets(tr,"MSW",BIN_LONG_TRANCE+1,"A")
  
  # # combine, normalize an scale data to mV
  # data_accu,data_clip = lc.combineAnalogDatasets(data_lsw, data_msw)
  # data_phys = lc.normalizeData(data_accu,cycles)
  # data_mv = lc.scaleAnalogData(data_phys,licelsettings.MILLIVOLT500) 
  
  # # DUMP THE DATA INTO A FILE
  # with open('analog.txt', 'w') as file: # or analog.dat 'wb'
  #   np.savetxt(file,data_mv,delimiter=',')

  #----------- RANGE CORRECTION ---------------

  # lidar_signal = np.array(data_mv)
  
  # load data
  # LIDAR_FILE='./analog_532par_500mV_CON_THRESHOLD.txt'
  # LIDAR_FILE='./analog_dia_nubes_20mV.txt'
  # LIDAR_FILE='./dashboard_532par_500mV_analog_SIN_THRESHOLD.txt'
  # LIDAR_FILE='./tr1_532par_100mV_20211001_1757_analog.txt'
  LIDAR_FILE='./tr1_532par_500mV_20211001_1740_analog.txt'
  data_csv = pd.read_csv(LIDAR_FILE,sep='\n',header=None)
  lidar_data = np.array(data_csv[0])

  # lidarsignal class
  # lidar = lidarsignal()
  global lidar
  lidar.loadSignal(lidar_data)
  lidar.offsetCorrection(OFFSET_BINS)
  lidar.rangeCorrection(THRESHOLD_METERS)
  lidar.smoothSignal(level = 3)

  #----------- RAYLEIGH-FIT ------------------

  lidar.setSurfaceConditions(temperature=298,pressure=1023)
  lidar.molecularProfile(wavelength=533,masl=10)
  lidar.rayleighFit(3000,5000) # meters
 
  print("Adj factor a(r,dr)=",np.format_float_scientific(lidar.adj_factor))
  print("Err RMS =",np.format_float_scientific(lidar.rms_err))
 
  #-------------- PLOTING --------------------

  #ploting
  plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar.raw_signal)
  plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar.range,lidar.rc_signal,lidar.pr2_mol*lidar.adj_factor)
  # plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar_signal)
  # plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(range_lidar,lidar_rc,pr2_mol*factor_adj)

  # load dict context
  context = {"number_bins": lidar.bin_long_trace,
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

  # lc = licelcontroller()
  # lc.openConnection('10.49.234.234',2055)
  # tr=0 #first TR

  if(action_button =="start"):
    while(True):
      # height = [7.5*i for i in range(0,1000)]
      # mv = [np.random.randint(0, 500) for iter in range(1000)]
      height = lidar.range
      mv = lidar.rc_signal + np.array([np.random.randint(-1e6,1e6) for iter in range(len(lidar.rc_signal))])
      data = [height.tolist(), mv.tolist()]
      response = make_response(json.dumps(data))
      response.content_type = 'application/json'
      print(response)
      return response
    # COPY CODE!!
    # start the acquisition
  
    ## get the shotnumber 
  
    # read from the TR triggered mem A
    
    # combine, normalize an scale data to mV
    
    # DUMP THE DATA INTO A FILE
    # with open('analog.txt', 'w') as file: # or analog.dat 'wb'
    #   np.savetxt(file,data_mv,delimiter=',')

    # lidar_signal = np.array(data_mv)
    # number_bins = len(data_mv)
 
    # BIN_RC_THRESHOLD=int(BIN_LONG_TRANCE/4)
    # height = np.arange(0, number_bins, 1)
    # lidar_bias = np.mean(lidar_signal[BIN_RC_THRESHOLD:])
    # lidar_rc = (lidar_signal - lidar_bias)*(height**2)

    # #ploting
    # plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar_signal)
    # plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar_rc)

    # # load dict context
    # context = {"number_bins": number_bins,
    #            "plot_lidar_signal": plot_lidar_signal,
    #            "plot_lidar_range_correction": plot_lidar_range_correction}

    # run html template
    # return context
  if(action_button =="stop"):
    data=[[],[]]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    print(response)
    return response

if __name__ == '__main__':
  app.run(debug=True)
