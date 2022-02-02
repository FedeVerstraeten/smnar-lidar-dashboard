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
from lidarcontroller.lidarsignal import lidarSignal
from lidarcontroller.lasercontroller import laserController

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')

# global
lidar = lidarSignal()
lc = None
#lc = licelcontroller()
#lc.openConnection('10.49.234.234',2055)
acquis_ini = configparser.ConfigParser()
globalinfo_ini = configparser.ConfigParser()

globalconfig = {
                  "channel" : 0,
                  "adq_time" : 10,      # 10s = 300shots/30Hz(laser)
                  "bin_offset" : 10,    # bin (default)
                  "max_bins" : 4000,    # bin
                  "bias_init" : 22500,  # m (3000 bins)
                  "bias_final" : 30000, # m (4000 bins)
                  "temperature" : 25,   # C deg
                  "pressure" : 1023,    # hPa
                  "masl" : 5.0,         # m
                  "wavelength" : 532,   # nm
                  "fit_init" : 5000,    # m
                  "fit_final" : 10000,  # m
                  "rc_limits_init" : 0,       # m 
                  "rc_limits_final" : 30000,  # m
                  "raw_limits_init" : 0,      # m 
                  "raw_limits_final" : 30000, # m
                  "laser_port" : 'COM3',
                 }

# Defining routes

@app.route("/")
@app.route("/alignment")
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
  return render_template('alignment.html', context=context)

@app.route("/adquisition")
def adquisition_mode():

  # crear licelcontroller
  # verificar acquis.ini y globalinfo.ini
  # leer cantidad de tr y params correspondientes
  # configurar
  # unselectTR
  # selectTR segun acquis.ini
  # mtart
  # delay
  # mstop
  # adquirir por cada TR activo
  # corregir en rango
  # almacenar temporalmente o netCDF?
  # graficar solo las señales corregidas en rango para cada TR
  # no fiteo, no rms, no raw

  # empty plot
  plot_lidar_signal = plotly_plot.plotly_empty_signal("raw")
  plot_lidar_range_correction = plotly_plot.plotly_empty_signal("rangecorrected")

  # load dict context
  context = {"plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction,
             "globalconfig" : globalconfig
            }

  # run html template
  return render_template('adquisition.html', context=context)

@app.route("/record", methods=['GET','POST'])
def licel_record_data():
  action_button = request.args['selected']

  # basic settings
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["adq_time"]*1000 # milliseconds 
  OFFSET_BINS = globalconfig["bin_offset"]
  THRESHOLD_METERS = globalconfig["bias_init"] # meters


  if(action_button =="start" or action_button =="oneshot"):
  #----------- LICEL ADQUISITION ---------------

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

    #----------- RANGE CORRECTION ---------------
    lidar.loadSignal(data_mv)
    lidar.offsetCorrection(OFFSET_BINS)
    lidar.rangeCorrection(THRESHOLD_METERS)
    lidar.smoothSignal(level = 3)

    #----------- RAYLEIGH-FIT ------------------
    lidar.setSurfaceConditions(temperature=globalconfig["temperature"],pressure=globalconfig["pressure"]) # optional?
    lidar.molecularProfile(wavelength=globalconfig["wavelength"],masl=globalconfig["masl"]) # optional?
    lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
    
    #-------------- PLOTING --------------------
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

      if(int(bias_range[1]) < MAX_BINS*BIN_METERS):
        globalconfig["bias_final"] = int(bias_range[1])
      else:
        globalconfig["bias_final"] = MAX_BINS*BIN_METERS

    # Max bins
    if(0 < int(bias_range[1]) < MAX_BINS*BIN_METERS):
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
  ZERO_KELVIN = 273.15

  # Temperature
  if(field_selected == "temperature" and (data_input.replace('.','',1).isdigit() or data_input.replace('-','',1).isdigit())):
    if float(data_input) + ZERO_KELVIN > 0:
      globalconfig[field_selected] = float(data_input)
  
  # Pressure
  if(field_selected == "pressure" and data_input.replace('.','',1).isdigit()):
    if float(data_input) > 0:
      globalconfig[field_selected] = float(data_input)

  # MASL
  if(field_selected == "masl" and data_input.replace('.','',1).isdigit()):
    if float(data_input) >= 0:
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

@app.route("/laser",methods=['GET','POST'])
def laser_controls():
  
  action_button = request.args['selected']
  serial_port = request.args['input']
  data = ""

  if serial_port:
    if serial_port != globalconfig["laser_port"]:
      globalconfig["laser_port"] = serial_port

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

  # define ini files path
  APP_ROOT = os.path.dirname(os.path.abspath(__file__))
  target = os.path.join(APP_ROOT, 'inifiles')

  # create dir
  if not os.path.isdir(target):
    os.mkdir(target)

  # remove old files
  if os.path.exists(target):
    for file in os.listdir(target):
      os.remove(os.path.join(target,file))
      print(file)
  else:
    print("Can not delete the file as it doesn't exists")

  # load ini files
  file=request.files.get("acquisini")
  if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    destination = os.path.join(target, file.filename)
    file.save(destination)
    acquis_ini.read(destination)

  file=request.files.get("globalinfoini")
  if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    destination = os.path.join(target, file.filename)
    file.save(destination)
    globalinfo_ini.read(destination)

  return render_template('inifiles.html')

@app.route('/sounding', methods=['POST'])
def sounding_data():

  if request.form.get('ussdt_checkbox') == 'on':
    lidar.clearSoundingData()
    resp="U.S. Standard Atmosphere model, enabled." 
    filename=""
    header_info=""
    sounding_data=""

  else:
    station = request.form["station_number"]
    region = request.form["region_sounding"]
    date = request.form["date_sounding"]

    # create sounding dir
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(APP_ROOT, 'sounding')
    if not os.path.isdir(target):
      os.mkdir(target)

    header_info,sounding_data = sounding.download_sounding(station,region,date)

    if sounding_data == "":
      resp = "No data available for ST" + station + " on " + date
      filename=""

    else:
      resp = "Radiosonde download successful!"

      # Load sounding
      height,temperature,pressure = sounding.get_htp(sounding_data)
      lidar.loadSoundingData(height,temperature,pressure)

      # print to file
      filename='UWyoming_'+date+'_'+station+'.txt'
      destination = os.path.join(target,filename)
      with open(destination,'w') as file:
        file.write(sounding_data)

  context = {
              "response": resp,
              "filename": filename,
              "station_info":header_info,
              "sounding_data": sounding_data
            }

  return render_template('sounding.html',context=context)

if __name__ == '__main__':
  app.run(debug=True)
