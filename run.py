import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import json
import configparser

from utils import plotly_plot
from utils import sounding
from lidarcontroller.licelcontroller import licelcontroller
from lidarcontroller import licelsettings
from lidarcontroller.lidarsignal import lidarsignal
from lidarcontroller.lasercontroller import laserController

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')

# global
lidar = lidarsignal()
lc = None
#lc = licelcontroller()
#lc.openConnection('10.49.234.234',2055)
acquis_ini = configparser.ConfigParser()
globalinfo_ini = configparser.ConfigParser()

globalconfig = {
                  "channel" : 0,
                  "adq_time" : 10,      # 10s = 300shots/30Hz(laser)
                  "max_bins" : 4000,    #bin
                  "bias_init" : 22500,  # m (3000 bins)
                  "bias_final" : 30000, # m (4000 bins)
                  "temperature" : 300,  # K
                  "pressure" : 1023,    # hPa
                  "masl" : 0,           # m
                  "wavelength" : 532,   # nm
                  "fit_init" : 5000,    # m
                  "fit_final" : 10000,  # m
                  "rc_limits_init" : 0,       # m 
                  "rc_limits_final" : 30000,  # m
                  "raw_limits_init" : 0,      # m 
                  "raw_limits_final" : 30000  # m
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

  lidar.setSurfaceConditions(temperature=globalconfig["temperature"],pressure=globalconfig["pressure"]) # optional?
  lidar.molecularProfile(wavelength=globalconfig["wavelength"],masl=globalconfig["masl"]) # optional?
  lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
 
  print("Adj factor a(r,dr)=",np.format_float_scientific(lidar.adj_factor))
  print("Err RMS =",np.format_float_scientific(lidar.rms_err))
 
  #-------------- PLOTING --------------------

  #ploting
  plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar,globalconfig["raw_limits_init"],globalconfig["raw_limits_final"])
  plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar,globalconfig["rc_limits_init"],globalconfig["rc_limits_final"])
  plot_lidar_rms =  plotly_plot.plotly_empty_signal("rms")

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

    # TODO mejorar esto
    if lc is None:
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
    # lc.closeConnection()

    # rayleigh fit 
    lidar.loadSignal(data_mv)
    lidar.offsetCorrection(OFFSET_BINS)
    lidar.rangeCorrection(THRESHOLD_METERS)
    lidar.smoothSignal(level = 3)
    lidar.setSurfaceConditions(temperature=globalconfig["temperature"],pressure=globalconfig["pressure"]) # optional?
    lidar.molecularProfile(wavelength=globalconfig["wavelength"],masl=globalconfig["masl"]) # optional?
    lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
  
    # ploting
    plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar,globalconfig["raw_limits_init"],globalconfig["raw_limits_final"])
    plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar,globalconfig["rc_limits_init"],globalconfig["rc_limits_final"])
    plot_lidar_rms = plot_lidar_rms =  plotly_plot.plotly_empty_signal("rms")

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
      globalconfig["max_bins"] = round(int(bias_range[1])/BIN_METERS)
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

@app.route("/plots",methods=['GET','POST'])
def plots_limits():
  field_selected = request.args['selected']
  data_input = request.args['input']

  MAX_HEIGHT_LIMIT = globalconfig["bias_final"]
  
  # Plot limits Range Corrected signal
  rc_limits=json.loads(data_input)
  if(field_selected == "rc_limits" and rc_limits[0].isdigit() and rc_limits[1].isdigit()):
    if(int(rc_limits[0]) < int(rc_limits[1]) <= MAX_HEIGHT_LIMIT):
      globalconfig["rc_limits_init"] = int(rc_limits[0])
      globalconfig["rc_limits_final"] = int(rc_limits[1])
  
  # Plot limits Raw signal
  raw_limits=json.loads(data_input)
  if(field_selected == "raw_limits" and raw_limits[0].isdigit() and raw_limits[1].isdigit()):
    if(int(raw_limits[0]) < int(raw_limits[1]) <= MAX_HEIGHT_LIMIT):
      globalconfig["raw_limits_init"] = int(raw_limits[0])
      globalconfig["raw_limits_final"] = int(raw_limits[1])
  
  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

@app.route("/laser")
def laser_controls():
  
  action_button = request.args['selected']
  serial_port = request.args['input']

  if(action_button =="laser_start"):
    laser = laserController(port = serial_port, baudrate = 9600, timeout = 5)
    laser.connect()
    laser.startLaser()
    laser.disconnect()
    data ="Laser START"
  
  if(action_button =="laser_stop"):
    laser = laserController(port = serial_port, baudrate = 9600, timeout = 5)
    laser.connect()
    laser.stopLaser()
    laser.disconnect()
    data="Laser STOP"
  
  response = make_response(json.dumps(data))
  response.content_type = 'application/json'
  print(response)
  
  return response

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt','TXT', 'ini', 'INI'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/inifiles', methods=['POST'])
def load_ini_files():

  # create dir
  APP_ROOT = os.path.dirname(os.path.abspath(__file__))
  target = os.path.join(APP_ROOT, 'inifiles')

  if not os.path.isdir(target):
    os.mkdir(target)

  # load ini files
  file=request.files.get("acquisini")
  if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    destination = "/".join([target, file.filename])
    file.save(destination)
    acquis_ini.read(destination)

  file=request.files.get("globalinfoini")
  if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    destination = "/".join([target, file.filename])
    file.save(destination)
    globalinfo_ini.read(destination)

  return render_template('inifiles.html')

@app.route('/sounding', methods=['POST'])
def sounding_data():

  station = request.form["station_number"]
  region = request.form["region_sounding"]
  date = request.form["date_sounding"]

  sounding.download_sounding(station,region,date)

  return render_template('inifiles.html')

if __name__ == '__main__':
  app.run(debug=True)
