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
globalconfig = {
                  "channel" : 0,
                  "adq_time" : 10,      # 10s = 300shots/30Hz(laser)
                  "max_bins" : 4000,
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
             "plot_lidar_rms": plot_lidar_rms
            }

  # run html template
  return render_template('lidar.html', context=context)

@app.route("/lidar")
def plot_lidar_signal():

  # basic settings
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["adq_time"]*1000 # milliseconds
  OFFSET_BINS = 10
  THRESHOLD_METERS = 2000 # meters


  #----------- LICEL ADQUISITION ---------------

  # initialization
  tr=globalconfig["channel"] 
  lc = licelcontroller()
  lc.openConnection('10.49.234.234',2055)
  lc.selectTR(tr)
  lc.setInputRange(licelsettings.MILLIVOLT500)
  # lc.setThresholdMode(licelsettings.THRESHOLD_LOW)
  # lc.setDiscriminatorLevel(8) # can be set between 0 and 63
  
 
  # start the acquisition
  lc.clearMemory()
  lc.startAcquisition()
  lc.msDelay(SHOTS_DELAY)
  lc.stopAcquisition() 
  #lc.waitForReady(100) # wait till it returns to the idle state

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
  plot_lidar_rms = plotly_plot.plot_lidar_rms(lidar.raw_signal)

  # load dict context
  context = {"number_bins": lidar.bin_long_trace,
             "plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction,
             "plot_lidar_rms": plot_lidar_rms
            }

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
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["adq_time"]*1000 # milliseconds 
  OFFSET_BINS = 10
  THRESHOLD_METERS = 2000 # meters


  if(action_button =="start"):
      
    # initialization
    tr=globalconfig["channel"] 
    lc = licelcontroller()
    lc.openConnection('10.49.234.234',2055)
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
    plot_lidar_rms = plotly_plot.plot_lidar_rms(lidar.raw_signal)

    # load dict context
    context = {"number_bins": lidar.bin_long_trace,
               "plot_lidar_signal": plot_lidar_signal,
               "plot_lidar_range_correction": plot_lidar_range_correction,
               "plot_lidar_rms": plot_lidar_rms
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
  
  # Max bins
  if(field_selected == "max_bins" and data_input.isdigit()):
    MAX_BINS = 4000
    
    if(0 < int(data_input) < MAX_BINS):
      globalconfig[field_selected] = int(data_input)
    else:
      globalconfig[field_selected] = MAX_BINS
  
  

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
