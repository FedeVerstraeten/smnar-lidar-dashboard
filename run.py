import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
import pandas as pd
import numpy as np
import json
from utils import plotly_plot


from lidarcontroller.licelcontroller import licelcontroller
from lidarcontroller import licelsettings
from lidarcontroller.lidarsignal import lidarsignal

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')



# global
lidar = lidarsignal()
#lc = licelcontroller()
#lc.openConnection('10.49.234.234',2055)

globalconfig = {
                  "channel" : 0,
                  "adq_time" : 10,      # 10s = 300shots/30Hz(laser)
                  "max_bins" : 4000,
                  "bias_init" : 22500,   # m
                  "bias_final" : 30000,   # m
                  "temperature" : 300,  # K
                  "pressure" : 1023,    # hPa
                  "masl" : 0,           # m
                  "wavelength" : 532,   # nm
                  "fit_init" : 1000,    # m
                  "fit_final" : 2000    # m
                 }


# Defining routes

@app.route("/")
def homepage():

  # empty plot
  plot_lidar_signal = plotly_plot.plotly_empty_signal("raw")
  plot_lidar_range_correction = plotly_plot.plotly_empty_signal("rangecorrected")
  plot_lidar_rms = plotly_plot.plotly_empty_signal("rms")

  # load dict context
  context = {"plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction,
             "plot_lidar_rms": plot_lidar_rms,
             "globalconfig" : globalconfig
            }

  # run html template
  return render_template('lidar.html', context=context)

@app.route("/lidar")
def plot_lidar_signal():

  # basic settings
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["adq_time"]*1000 # milliseconds
  OFFSET_BINS = 10
  THRESHOLD_METERS = globalconfig["bias_init"] # meters


  #----------- LICEL ADQUISITION ---------------

  # initialization
  tr=globalconfig["channel"] 
  lc_local = licelcontroller()
  print("por aca")
  lc_local.openConnection('10.49.234.234',2055)
  lc_local.selectTR(tr)
  lc_local.setInputRange(licelsettings.MILLIVOLT500)
  # lc.setThresholdMode(licelsettings.THRESHOLD_LOW)
  # lc.setDiscriminatorLevel(8) # can be set between 0 and 63
  
 
  # start the acquisition
  lc_local.clearMemory()
  lc_local.startAcquisition()
  lc_local.msDelay(SHOTS_DELAY)
  lc_local.stopAcquisition() 
  #lc.waitForReady(100) # wait till it returns to the idle state

  # get the shotnumber 
  if lc_local.getStatus() == 0:
    if (lc_local.shots_number > 1):
      cycles = lc_local.shots_number - 2 # WHY??!

  # read from the TR triggered mem A
  data_lsw = lc_local.getDatasets(tr,"LSW",BIN_LONG_TRANCE+1,"A")
  data_msw = lc_local.getDatasets(tr,"MSW",BIN_LONG_TRANCE+1,"A")
  
  # combine, normalize an scale data to mV
  data_accu,data_clip = lc_local.combineAnalogDatasets(data_lsw, data_msw)
  data_phys = lc_local.normalizeData(data_accu,cycles)
  data_mv = lc_local.scaleAnalogData(data_phys,licelsettings.MILLIVOLT500) 
  
  # close socket
  lc_local.closeConnection()
  # # DUMP THE DATA INTO A FILE
  # with open('analog.txt', 'w') as file: # or analog.dat 'wb'
  #   np.savetxt(file,data_mv,delimiter=',')

  #----------- RANGE CORRECTION ---------------

  lidar_data = np.array(data_mv)

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
  lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
 
  print("Adj factor a(r,dr)=",np.format_float_scientific(lidar.adj_factor))
  print("Err RMS =",np.format_float_scientific(lidar.rms_err))
 
  #-------------- PLOTING --------------------

  #ploting
  plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar.raw_signal)
  plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar)
  plot_lidar_rms = plotly_plot.plotly_lidar_rms(lidar.raw_signal)

  # load dict context
  context = {"number_bins": lidar.bin_long_trace,
             "plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction,
             "plot_lidar_rms": plot_lidar_rms
            }

  # run html template
  return render_template('lidar.html', context=context)

@app.route("/acquis", methods=['GET','POST'])
def plot_acquis():
  action_button = request.args['selected']

  # basic settings
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["adq_time"]*1000 # milliseconds 
  OFFSET_BINS = 10
  THRESHOLD_METERS = globalconfig["bias_init"] # meters


  if(action_button =="start"):
      
    # initialization
    global lc
    tr=globalconfig["channel"] 
    lc = licelcontroller()
    lc.openConnection('10.49.234.234',2055)
    print(lc.sock)
    lc.selectTR(tr)
    lc.setInputRange(licelsettings.MILLIVOLT500)
   
    # start the acquisition
    lc.clearMemory()
    lc.startAcquisition()
    lc.msDelay(SHOTS_DELAY)
    lc.stopAcquisition() 

    # get the shotnumber 
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
    
    # close socket
    lc.closeConnection()

    # rayleigh fit 
    lidar.loadSignal(data_mv)
    lidar.offsetCorrection(OFFSET_BINS)
    lidar.rangeCorrection(THRESHOLD_METERS)
    lidar.smoothSignal(level = 3)
    lidar.setSurfaceConditions(temperature=298,pressure=1023) # optional?
    lidar.molecularProfile(wavelength=533,masl=10) # optional?
    lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
  
    # ploting
    plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar.raw_signal)
    plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar)
    plot_lidar_rms = plotly_plot.plotly_lidar_rms(lidar.raw_signal)

    # load dict context
    context = {"number_bins": lidar.bin_long_trace,
               "plot_lidar_signal": plot_lidar_signal,
               "plot_lidar_range_correction": plot_lidar_range_correction,
               "plot_lidar_rms": plot_lidar_rms,
               "shots_delay": SHOTS_DELAY,
               "rms_error" : lidar.rms_err
              }
 
    # run html template
    return context
  
  if(action_button =="stop"):
    data=[]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    print(response)
    return response

@app.route("/licelcontrols", methods=['GET','POST'])
def licel_controls():

  field_selected = request.args['selected']
  data_input = request.args['input']

  # Channel
  if(field_selected == "channel" and data_input.isdigit()):
    globalconfig[field_selected] = int(data_input)
  
  # Adquisition time
  if(field_selected == "adq_time" and data_input.isdigit()):
    MAX_ADQ_TIME = 600 # 600s = 10min
    MIN_ADQ_TIME = 1 
   
    if(MIN_ADQ_TIME <= int(data_input) < MAX_ADQ_TIME):
      globalconfig[field_selected] = int(data_input)
    else:
      globalconfig[field_selected] = MAX_ADQ_TIME
  
  # Bias range and max bins
  bias_range=json.loads(data_input)
  MAX_BINS = 16000
  BIN_METERS = 7.5

  if(field_selected == "bias_range" and bias_range[0].isdigit() and bias_range[1].isdigit()):

    # Bias range
    if(int(bias_range[0]) < int(bias_range[1])):
      
      if(int(bias_range[0]) > 0):
        globalconfig["bias_init"] = int(bias_range[0])
      else:
        globalconfig["bias_init"] = 0

      if(int(bias_range[1]) < MAX_BINS):
        globalconfig["bias_final"] = int(bias_range[1])
      else:
        globalconfig["bias_final"] = MAX_BINS*BIN_METERS

    # Max bins
    if(0 < int(bias_range[0]) < MAX_BINS):
      globalconfig["max_bins"] = round(int(bias_range[1])/7.5)
    else:
      globalconfig["max_bins"] = MAX_BINS

  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

@app.route("/rayleighfit", methods=['GET','POST'])
def rayleighfit_controls():

  field_selected = request.args['selected']
  data_input = request.args['input']

  # Temperature
  if(field_selected == "temperature" and (data_input.replace('.','',1).isdigit() or data_input.replace('-','',1).isdigit())):
    if float(data_input) + 273 > 0:
      globalconfig[field_selected] = float(data_input) + 273
  
  # Pressure
  if(field_selected == "pressure" and data_input.replace('.','',1).isdigit()):
    if float(data_input) > 0:
      globalconfig[field_selected] = float(data_input)

  # MASL
  if(field_selected == "masl" and data_input.replace('.','',1).isdigit()):
    if float(data_input) > 0:
      globalconfig[field_selected] = float(data_input)
  
  # Fitting range
  fitting=json.loads(data_input)
  if(field_selected == "fitting" and fitting[0].isdigit() and fitting[1].isdigit()):
    if(int(fitting[0]) < int(fitting[1])):
      globalconfig["fit_init"] = int(fitting[0])
      globalconfig["fit_final"] = int(fitting[1])
  

  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

if __name__ == '__main__':
  app.run(debug=True)
