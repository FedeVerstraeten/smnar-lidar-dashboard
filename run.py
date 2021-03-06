#----------- LIBRARIES -----------

import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
from werkzeug.utils import secure_filename
import json
import configparser
import datetime

#----------- CUSTOM LIBS -----------

from utils import plotly_plot
from utils import sounding
from lidarcontroller.licelcontroller import licelController
from lidarcontroller import licelsettings
from lidarcontroller.lidarsignal import lidarSignal
from lidarcontroller.lasercontroller import laserController

#----------- FLASK CONFIG -----------

app = Flask(__name__)
app.config.from_object('config.Config')

#----------- GLOBAL VARIABLES -----------

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
lidar = lidarSignal()
lc = licelController()

globalconfig = {
                  "ip" : '10.49.234.234',
                  "port" : 2055,
                  "channel" : 0,
                  "acq_time" : 10,      # 10s = 300shots/30Hz(laser)
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
                  "smooth_level" : 5,
                  "laser_port" : 'COM3',
                  "period_time" : 1 # min
                 }

#----------- INI FILES -----------

acquis_ini = configparser.ConfigParser()
globalinfo_ini = configparser.ConfigParser()
acquis_dir = os.path.join(APP_ROOT, 'inifiles','acquis.ini')
globalinfo_dir = os.path.join(APP_ROOT, 'inifiles','globalinfo.ini')

if os.path.exists(acquis_dir) and os.path.exists(globalinfo_dir):
  acquis_ini.read(acquis_dir)
  globalinfo_ini.read(globalinfo_dir)

#----------- END-POINT ROUTES -----------

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

@app.route("/acquisition")
def acquisition_mode():

  # check acquis.ini and globalinfo.ini was loaded
  if acquis_ini.sections()==[] and globalinfo_ini.sections()==[]:
    
    error_message = "INI files did not loaded."
    warning_message = "Please, you must load the INI files with the <b>Load INI Files</b> menu in the side bar."
    context = { "error_message" : error_message,
                "warning_message" : warning_message
              }
    
    return render_template('error.html',context=context)

  else:
    # empty plot
    plot_lidar_signal = plotly_plot.plotly_empty_signal("raw")
    plot_lidar_range_correction = plotly_plot.plotly_empty_signal("rangecorrected")

    # load dict context
    context = {"plot_multiple_lidar_signal": plot_lidar_signal,
               "globalconfig" : globalconfig
              }

    # run html template
    return render_template('acquisition.html', context=context)

@app.route("/acquisdata", methods=['GET','POST'])
def licel_acquis_data():

  action_button = request.args['selected']

  # basic settings
  LICEL_IP = globalconfig["ip"]
  LICEL_PORT = globalconfig["port"]
  SHOTS_DELAY = globalconfig["acq_time"]*1000 # milliseconds
  PERIOD_DELAY = globalconfig["period_time"]*60*1000 # milliseconds

  # define data files path
  acquisdata_path = os.path.join(APP_ROOT, 'acquisdata')

   # create dir
  if not os.path.isdir(acquisdata_path):
    os.mkdir(acquisdata_path)

  # select all transient recorder and config parameters
  tr_list=""
  acquis_settings={}

  for section in acquis_ini.sections():
    if 'TR' in section:
      # Listing TR channel
      tr_number = section.split('TR')[1]
      if tr_number.isdigit():
        tr_list += tr_number + " "

      # Save acquis configuration
      acquis_settings[tr_number]={
                                  "Discriminator" : acquis_ini[section]["Discriminator"],
                                  "Range" : acquis_ini[section]["Range"],
                                  "WavelengthA" : acquis_ini[section]["WavelengthA"],
                                  "A-binsA" : acquis_ini[section]["A-binsA"]
                                  }
  if(action_button =="start" or action_button =="oneshot"):
    # open licel connection
    if lc.sock is None:
      lc.openConnection(LICEL_IP,LICEL_PORT)


    # setting Licel for each channel
    # for tr in acquis_settings:
    #   lc.selectTR(tr)
    #   lc.setDiscriminatorLevel(acquis_settings[tr]["Discriminator"])
    #   lc.setInputRange(acquis_settings[tr]["Range"])


    # unselectTR
    lc.unselectTR()

    # select TR acording acquis list
    lc.selectTR(tr_list.strip())
    
    # start the acquisition
    lc.multipleClearMemory()
    lc.multipleStartAcquisition()
    lc.msDelay(SHOTS_DELAY)
    lc.multipleStopAcquisition()
    

    # acquisition for each active TR
    lidar_data_mv={}
    for tr in acquis_settings:

      data_mv = lc.getAnalogSignalmV(tr,int(acquis_settings[tr]["A-binsA"]),"A",licelsettings.MILLIVOLT500)
      lidar_data_mv[tr]={ 
                            "timestamp" : datetime.datetime.now().isoformat(),
                            "bins"      : acquis_settings[tr]["A-binsA"],
                            "data_mv"   : data_mv.tolist()
                          }

    # dump data to local directory in JSON format
    filename = "lidar_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
    filepath = os.path.join(acquisdata_path,filename)
    with open(filepath,'w') as file:
      file.write(json.dumps(lidar_data_mv))

    # Plotting
    plot_multiple_lidar_signal = plotly_plot.plot_multiple_lidar_signal(lidar_data_mv,globalconfig["raw_limits_init"],globalconfig["raw_limits_final"])

    context = {
                 "plot_multiple_lidar_signal": plot_multiple_lidar_signal,
                 "shots_delay": SHOTS_DELAY,
                 "period_delay": PERIOD_DELAY
              }
 
    # # run html template
    return context

  if(action_button =="stop"):
    data=[]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

@app.route("/record", methods=['GET','POST'])
def licel_record_data():
  action_button = request.args['selected']

  # basic settings
  LICEL_IP = globalconfig["ip"]
  LICEL_PORT = globalconfig["port"]
  BIN_LONG_TRANCE = globalconfig["max_bins"]
  SHOTS_DELAY = globalconfig["acq_time"]*1000 # milliseconds 
  OFFSET_BINS = globalconfig["bin_offset"]
  THRESHOLD_METERS = globalconfig["bias_init"] # meters


  if(action_button =="start" or action_button =="oneshot"):

    # initialization
    global lc
    tr=globalconfig["channel"]

    # TODO mejorar esto
    if lc.sock is None:
      lc.openConnection(LICEL_IP,LICEL_PORT)

    lc.selectTR(tr)
    lc.setInputRange(licelsettings.MILLIVOLT500)
   
    # start the acquisition
    lc.clearMemory()
    lc.startAcquisition()
    lc.msDelay(SHOTS_DELAY)
    lc.stopAcquisition() 

    # get signall in mV
    data_mv = lc.getAnalogSignalmV(tr,BIN_LONG_TRANCE,"A",licelsettings.MILLIVOLT500)

    # close socket
    # lc.closeConnection()

    # range correction
    lidar.loadSignal(data_mv)
    lidar.offsetCorrection(OFFSET_BINS)
    lidar.rangeCorrection(THRESHOLD_METERS)
    lidar.smoothSignal(level = globalconfig["smooth_level"])

    # Rayleigh-fit
    lidar.setSurfaceConditions(temperature=globalconfig["temperature"],pressure=globalconfig["pressure"])
    lidar.molecularProfile(wavelength=globalconfig["wavelength"],masl=globalconfig["masl"])
    lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"]) # meters
    lidar.overlapFitting()

    # plotting
    plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar,globalconfig["raw_limits_init"],globalconfig["raw_limits_final"])
    plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar,globalconfig["rc_limits_init"],globalconfig["rc_limits_final"],globalconfig["wavelength"])
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
    return response

@app.route("/licelcontrols", methods=['GET','POST'])
def licel_controls():

  field_selected = request.args['selected']
  data_input = request.args['input']

  # Channel
  if(field_selected == "channel" and data_input.isdigit()):
    globalconfig[field_selected] = int(data_input)
  
  # Acquisition time
  if(field_selected == "acq_time" and data_input.isdigit()):
    MAX_ACQ_TIME = 600 # 600s = 10min
    MIN_ACQ_TIME = 0
   
    if(int(data_input) > MAX_ACQ_TIME):
      globalconfig[field_selected] = MAX_ACQ_TIME
    elif(int(data_input) <= MIN_ACQ_TIME):
      globalconfig[field_selected] = MIN_ACQ_TIME
    else:
      globalconfig[field_selected] = int(data_input)

  # Bias offset
  if(field_selected == "bin_offset" and data_input.isdigit()):
    globalconfig[field_selected] = int(data_input)
  
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

   # Period time on Acquisition Mode
  if(field_selected == "period_time" and data_input.isdigit()):
    MAX_PERIOD_TIME = 60 # 1 hour
    MIN_PERIOD_TIME = 1 # 1 min
   

    if(int(data_input)*60 <= globalconfig["acq_time"]):
      globalconfig["period_time"] = round(globalconfig["acq_time"]/60 + MIN_PERIOD_TIME)
    elif(int(data_input) > MAX_PERIOD_TIME):
      globalconfig["period_time"] = MAX_PERIOD_TIME
    elif(int(data_input) <= MIN_PERIOD_TIME):
      globalconfig["period_time"] = MIN_PERIOD_TIME
    else:
      globalconfig["period_time"] = int(data_input)

  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

@app.route("/rayleighfit", methods=['GET','POST'])
def rayleighfit_controls():

  field_selected = request.args['selected']
  data_input = request.args['input']
  ZERO_KELVIN = 273.15

  # Temperature
  if(field_selected == "temperature" and data_input.replace('.','',1).replace('-','',1).isdigit()):
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
  
  # Wavelength source
  if(field_selected == "wavelength" and data_input.replace('.','',1).isdigit()):
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
  
  #noise smoothing level  
  if(field_selected == "smooth_level" and data_input.isdigit()):
    MAX_SMOOTH_LEVEL = 50
    MIN_SMOOTH_LEVEL = 0 
   
    if(MIN_SMOOTH_LEVEL <= int(data_input) <= MAX_SMOOTH_LEVEL):
      globalconfig[field_selected] = int(data_input)
    else:
      globalconfig[field_selected] = MAX_SMOOTH_LEVEL

  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

@app.route("/tcpip",methods=['GET','POST'])
def tcpip_connection():
  field_selected = request.args['selected']
  data_input = request.args['input']

  # IP
  if(field_selected == "ip" and len(data_input.split('.'))==4):
    ip_list = list(map(str,data_input.split('.')))
    ip_digits = [i for i in ip_list if i.isdigit() and int(i)<256]

    if len(ip_digits)==4:
      globalconfig[field_selected] = str(data_input)
  
  # Port
  if(field_selected == "port" and data_input.isdigit()):
    globalconfig[field_selected] = int(data_input)

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
  
  return response

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt','TXT', 'ini', 'INI'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/inifiles', methods=['POST'])
def load_ini_files():

  # define ini files path
  target = os.path.join(APP_ROOT, 'inifiles')

  # create dir
  if not os.path.isdir(target):
    os.mkdir(target)

  # request from frontend
  acquis_file=request.files.get("acquisini")
  globalinfo_file=request.files.get("globalinfoini")

  if acquis_file and globalinfo_file:
    
    # remove old files
    if os.path.exists(target):
      for file in os.listdir(target):
        os.remove(os.path.join(target,file))
    else:
      print("Can not delete the file as it doesn't exists")

    # load ini files
    if acquis_file and allowed_file(acquis_file.filename):
      filename = secure_filename('acquis.ini')
      destination = os.path.join(target,'acquis.ini')
      acquis_file.save(destination)
      acquis_ini.read(destination)

    if globalinfo_file and allowed_file(globalinfo_file.filename):
      filename = secure_filename('globalinfo.ini')
      destination = os.path.join(target,'globalinfo.ini')
      globalinfo_file.save(destination)
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

#----------- MAIN RUN -----------

if __name__ == '__main__':
  app.run(debug=True)
