#----------- LIBRARIES -----------

import os
import sys
from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
from werkzeug.utils import secure_filename
import json
import configparser
import datetime
import serial 
import threading
import time
from contextlib import contextmanager
from functools import wraps

#----------- CUSTOM LIBS -----------

from utils import plotly_plot
from utils import sounding
from lidarcontroller.licelcontroller import licelController
from lidarcontroller import licelsettings
from lidarcontroller.lidarsignal import lidarSignal
from lidarcontroller.lasercontroller import laserController
from lidarcontroller.motorcontroller import MotorController
from lidarcontroller.telecovercontroller import TelecoverController
from lidarcontroller.motionconnection import (
  MotionConnection, MotionConnectionBusy, MotionConnectionError
)
from lidarcontroller.autoalignment import (
  AutoalignmentAlreadyRunning,
  AutoalignmentMoveUnavailable,
  AutoalignmentService
)

#----------- FLASK CONFIG -----------

app = Flask(__name__)
app.config.from_object('config.Config')

#----------- GLOBAL VARIABLES -----------

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
lidar = lidarSignal()
lc = licelController()
licel_lock = threading.Lock()
licel_state = "disconnected"
laser = laserController(port = 'COM3', baudrate = 9600, timeout = 5)
laser_lock = threading.Lock()
laser_state = "disconnected"

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
                  "period_time" : 1, # min
                  "motor_port" : 'COM4',
                  "motor_resolution" : 0.1,
                  "motor_steps" : 10,
                  "motor_feed_rate" : 50,
                  "corr_range_init" : 5000,
                  "corr_range_final" : 10000,
                  "grid_min_resolution" : 0.1,
                  "scan_rows" : 8,
                  "scan_cols" : 8,
                  "scan_step_x" : 1.000,
                  "scan_step_y" : 1.000,
                  "scan_feed" : 50,
                  "scan_pattern" : "raster",
                  "scan_centered" : True,
                  "scan_reverse" : False,
                  "scan_delay" : 0.0,
                  "scan_on_fail" : "retry",
                  "telecover_port" : "COM4",  # Same physical connection as motor_port.
                  "telecover_baudrate" : 115200,
                  "telecover_timeout" : 2.0,
                  "telecover_download_dir" : "telecover",
                  "telecover_acq_time" : 10,
                  "telecover_settle_time" : 2.0,
                  "telecover_sequence" : ["N", "E", "S", "W"],
                  "telecover_include_darkcurrent" : True,
                  "telecover_return_to_north_before_darkcurrent" : True,
                  "telecover_darkcurrent_requires_north" : True,
                  "telecover_reverse" : False,
                  "telecover_auto_save" : True,
                  "telecover_channel" : 0,
                  "telecover_raw_limits_init" : 0,
                  "telecover_raw_limits_final" : 30000,
                  "telecover_require_homing" : True,
                  "telecover_lift_required_for_rotation" : "UP",
                  "telecover_lift_required_for_measurement" : "DOWN"
                 }

motion_connection = MotionConnection(port=globalconfig["motor_port"])

#----------- INI FILES -----------

acquis_ini = configparser.ConfigParser()
globalinfo_ini = configparser.ConfigParser()
acquis_dir = os.path.join(APP_ROOT, 'inifiles','acquis.ini')
globalinfo_dir = os.path.join(APP_ROOT, 'inifiles','globalinfo.ini')

if os.path.exists(acquis_dir) and os.path.exists(globalinfo_dir):
  acquis_ini.read(acquis_dir)
  globalinfo_ini.read(globalinfo_dir)

def licel_status_payload(ok=True,message=""):
  current_state = licel_state if lc.isConnected() else "disconnected"
  return {
    "ok": ok,
    "message": message,
    "connected": lc.isConnected(),
    "ip": globalconfig["ip"],
    "port": globalconfig["port"],
    "state": current_state
  }

def licel_acquisition_required(route_function):
  @wraps(route_function)
  def guarded_route(*args,**kwargs):
    global licel_state

    action = request.values.get("selected","")
    if action not in {"start","oneshot","autoalign_start"}:
      return route_function(*args,**kwargs)

    with licel_lock:
      if not lc.isConnected():
        return jsonify(licel_status_payload(
          False,
          "Connect Licel before starting an acquisition."
        )),409

      licel_state = "acquiring"
      try:
        result = route_function(*args,**kwargs)
      except Exception as ex:
        return jsonify(licel_status_payload(False,str(ex))),500
      finally:
        licel_state = "connected" if lc.isConnected() else "disconnected"

      if isinstance(result,dict):
        result["licel_state"] = licel_state
      return result

  return guarded_route

#----------- ACQUISITION HELPERS -----------

def get_acquis_settings():
  tr_list = ""
  acquis_settings = {}

  for section in acquis_ini.sections():
    if 'TR' in section:
      tr_number = section.split('TR')[1]
      if tr_number.isdigit():
        tr_list += tr_number + " "

      acquis_settings[tr_number]={
                                  "Discriminator" : acquis_ini[section]["Discriminator"],
                                  "Range" : acquis_ini[section]["Range"],
                                  "WavelengthA" : acquis_ini[section]["WavelengthA"],
                                  "A-binsA" : acquis_ini[section]["A-binsA"]
                                  }

  return tr_list.strip(), acquis_settings


def acquire_single_licel_trace():
  tr = globalconfig["channel"]
  shots_delay = globalconfig["acq_time"]*1000

  lc.selectTR(tr)
  lc.setInputRange(licelsettings.MILLIVOLT500)

  lc.clearMemory()
  lc.startAcquisition()
  lc.msDelay(shots_delay)
  lc.stopAcquisition()

  requested_bins = globalconfig["max_bins"] + max(0,globalconfig["bin_offset"])
  return lc.getAnalogSignalmV(tr,requested_bins,"A",licelsettings.MILLIVOLT500)


def process_lidar_trace(data_mv):
  lidar.loadSignal(data_mv)
  lidar.offsetCorrection(globalconfig["bin_offset"])
  lidar.rangeCorrection(globalconfig["bias_init"])
  lidar.smoothSignal(level = globalconfig["smooth_level"])

  lidar.setSurfaceConditions(temperature=globalconfig["temperature"],pressure=globalconfig["pressure"])
  lidar.molecularProfile(wavelength=globalconfig["wavelength"],masl=globalconfig["masl"])
  lidar.rayleighFit(globalconfig["fit_init"] ,globalconfig["fit_final"])
  lidar.overlapFitting()

  return lidar


def acquire_processed_lidar_trace():
  data_mv = acquire_single_licel_trace()
  return process_lidar_trace(data_mv)


def build_alignment_context():
  plot_lidar_signal = plotly_plot.plotly_lidar_signal(lidar,globalconfig["raw_limits_init"],globalconfig["raw_limits_final"])
  plot_lidar_range_correction = plotly_plot.plotly_lidar_range_correction(lidar,globalconfig["rc_limits_init"],globalconfig["rc_limits_final"],globalconfig["wavelength"])
  plot_lidar_rms = plotly_plot.plotly_empty_signal("rms")

  return {"number_bins": lidar.bin_long_trace,
          "plot_lidar_signal": plot_lidar_signal,
          "plot_lidar_range_correction": plot_lidar_range_correction,
          "plot_lidar_rms": plot_lidar_rms,
          "shots_delay": globalconfig["acq_time"]*1000,
          "rms_error" : lidar.rms_err
         }


def acquire_multiple_licel_traces(acquis_settings, tr_list):
  lc.unselectTR()
  lc.selectTR(tr_list)

  lc.multipleClearMemory()
  lc.multipleStartAcquisition()
  lc.msDelay(globalconfig["acq_time"]*1000)
  lc.multipleStopAcquisition()

  lidar_data_mv={}
  for tr in acquis_settings:
    data_mv = lc.getAnalogSignalmV(tr,int(acquis_settings[tr]["A-binsA"]),"A",licelsettings.MILLIVOLT500)
    lidar_data_mv[tr]={
                          "timestamp" : datetime.datetime.now().isoformat(),
                          "bins"      : acquis_settings[tr]["A-binsA"],
                          "data_mv"   : data_mv.tolist()
                        }

  return lidar_data_mv


def autoalign_results_to_plots(results):
  pearson_trace = [{
                    "x": [item["index"] + 1 for item in results],
                    "y": [item["pearson"] for item in results],
                    "mode": "lines+markers",
                    "name": "Pearson r",
                    "line": {"color": "#17a2b8"}
                  }]
  pearson_layout = {
                    "autosize": True,
                    "margin": {"t": 18, "r": 16, "b": 42, "l": 52},
                    "yaxis": {"title": "r", "range": [-1, 1]},
                    "xaxis": {"title": "Iteration"}
                   }

  xs = sorted(list({item["col"] for item in results}))
  ys = sorted(list({item["row"] for item in results}))
  values = []
  for y in ys:
    row_values = []
    for x in xs:
      point = next((item for item in results if item["col"] == x and item["row"] == y), None)
      row_values.append(point["pearson"] if point else None)
    values.append(row_values)

  grid_trace = [{
                 "type": "heatmap",
                 "x": xs,
                 "y": ys,
                 "z": values,
                 "colorscale": "Viridis",
                 "zmin": -1,
                 "zmax": 1,
                 "hovertemplate": "Column %{x}<br>Row %{y}<br>Pearson r %{z:.3f}<extra></extra>",
                 "colorbar": {"title": "Pearson r", "len": 0.8}
                }]
  grid_layout = {
                 "margin": {"t": 18, "r": 24, "b": 42, "l": 52},
                 "xaxis": {"title": "Column", "dtick": 1, "constrain": "domain", "scaleanchor": "y", "scaleratio": 1},
                 "yaxis": {"title": "Row", "dtick": 1, "autorange": "reversed"},
                 "autosize": True
                }

  return {
          "plot_pearson": json.dumps({"data": pearson_trace, "layout": pearson_layout}),
          "plot_measurement_grid": json.dumps({"data": grid_trace, "layout": grid_layout})
         }


@contextmanager
def autoalignment_acquisition_context():
  global licel_state

  with licel_lock:
    if not lc.isConnected():
      raise RuntimeError("Connect Licel before starting autoalignment.")

    licel_state = "acquiring"
    try:
      yield
    finally:
      licel_state = "connected" if lc.isConnected() else "disconnected"


def acquire_autoalignment_point():
  acquire_processed_lidar_trace()
  context = build_alignment_context()
  return {
          "pearson": float(lidar.alignment_factor),
          "plots": {
                    "plot_lidar_signal": context["plot_lidar_signal"],
                    "plot_lidar_range_correction": context["plot_lidar_range_correction"]
                   }
         }


def save_autoalignment_results(config, results, best):
  acquisdata_path = os.path.join(APP_ROOT, 'acquisdata')
  os.makedirs(acquisdata_path, exist_ok=True)
  filename = "autoalign_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"
  filepath = os.path.join(acquisdata_path,filename)
  with open(filepath,'w') as file:
    file.write(json.dumps({
                           "globalconfig": config,
                           "results": results,
                           "best": best
                          }))
  return filename


@contextmanager
def autoalignment_motor_connection(config):
  with motion_connection.operation("autoalignment") as connection:
    yield connection


autoalignment_service = AutoalignmentService(
  serial_factory=lambda config: serial.Serial(
    port=config["motor_port"], baudrate=115200, timeout=2.0
  ),
  motor_factory=lambda serial_connection: MotorController(ser=serial_connection),
  acquire_point=acquire_autoalignment_point,
  plots_builder=autoalign_results_to_plots,
  results_saver=save_autoalignment_results,
  run_context=autoalignment_acquisition_context,
  connection_context=autoalignment_motor_connection,
)

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


@app.route("/autoalignment")
def autoalignment_mode():

  # empty plots
  plot_lidar_signal = plotly_plot.plotly_empty_signal("raw")
  plot_lidar_range_correction = plotly_plot.plotly_empty_signal("rangecorrected")

  context = {"plot_lidar_signal": plot_lidar_signal,
             "plot_lidar_range_correction": plot_lidar_range_correction,
             "globalconfig": globalconfig
            }

  return render_template('autoalignment.html', context=context)

@app.route("/telecover")
def telecover_mode():
  context = {
    "plot_telecover_raw": plotly_plot.plotly_empty_signal("raw"),
    "globalconfig": globalconfig
  }
  return render_template("telecover.html", context=context)

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
@licel_acquisition_required
def licel_acquis_data():

  action_button = request.args['selected']

  # basic settings
  SHOTS_DELAY = globalconfig["acq_time"]*1000 # milliseconds
  PERIOD_DELAY = globalconfig["period_time"]*60*1000 # milliseconds

  # define data files path
  acquisdata_path = os.path.join(APP_ROOT, 'acquisdata')

   # create dir
  if not os.path.isdir(acquisdata_path):
    os.mkdir(acquisdata_path)

  # select all transient recorder and config parameters
  tr_list, acquis_settings = get_acquis_settings()

  if(action_button =="start" or action_button =="oneshot"):
    lidar_data_mv = acquire_multiple_licel_traces(acquis_settings, tr_list)

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
@licel_acquisition_required
def licel_record_data():
  action_button = request.args['selected']

  # basic settings
  SHOTS_DELAY = globalconfig["acq_time"]*1000 # milliseconds 


  if(action_button =="start" or action_button =="oneshot"):
    acquire_processed_lidar_trace()
    context = build_alignment_context()
    context["shots_delay"] = SHOTS_DELAY
 
    # run html template

    return context
  
  if(action_button =="stop"):
    data=[]
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

def start_autoalignment():
  if not motion_connection.is_connected() or motion_connection.snapshot()["busy"]:
    return jsonify({
      "ok": False, "status": "Error",
      "message": "Connect motors/Telecover and wait until the shared connection is free.",
      "motor_connection": motion_connection.snapshot()
    }), 409
  if not lc.isConnected():
    return jsonify({
                    "ok": False,
                    "status": "Error",
                    "message": "Connect Licel before starting autoalignment."
                  }), 409

  try:
    state = autoalignment_service.start(globalconfig)
    return jsonify(state), 202
  except AutoalignmentAlreadyRunning as ex:
    return jsonify({
                    "ok": False,
                    "status": "Running",
                    "message": str(ex)
                  }), 409


@app.route("/autoalign/start", methods=['POST'])
def autoalignment_start():
  return start_autoalignment()


@app.route("/autoalign/status", methods=['GET'])
def autoalignment_status():
  return jsonify(autoalignment_service.snapshot())


@app.route("/autoalign/stop", methods=['POST'])
def autoalignment_stop():
  return jsonify(autoalignment_service.stop())


@app.route("/autoalign/move-best", methods=['POST'])
def autoalignment_move_best():
  if not motion_connection.is_connected() or motion_connection.snapshot()["busy"]:
    return jsonify({
      "ok": False, "message": "Connect motors/Telecover and wait until the shared connection is free.",
      "motor_connection": motion_connection.snapshot()
    }), 409
  try:
    return jsonify(autoalignment_service.move_to_best())
  except AutoalignmentMoveUnavailable as ex:
    return jsonify({
                    "ok": False,
                    "status": autoalignment_service.snapshot()["status"],
                    "message": str(ex)
                  }), 409
  except Exception:
    return jsonify(autoalignment_service.snapshot()), 500


@app.route("/autoalign", methods=['GET','POST'])
def autoalignment_data():
  """Compatibility endpoint for clients using the original action API."""
  action_button = request.values.get('selected','')

  if action_button == "autoalign_start":
    return start_autoalignment()
  if action_button == "autoalign_stop":
    return jsonify(autoalignment_service.stop())
  if action_button == "autoalign_status":
    return jsonify(autoalignment_service.snapshot())

  return jsonify({
                  "ok": False,
                  "status": "Error",
                  "message": "Invalid autoalignment action."
                }), 400

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

def telecover_error_payload(error):
  return {
    "device": "telecover",
    "status": "ERROR",
    "command": None,
    "event": "error",
    "subsystem": "unknown",
    "disk_position": "UNKNOWN",
    "target_position": "NONE",
    "lift": "UNKNOWN",
    "darkcover": "UNKNOWN",
    "motion": "ERROR",
    "homed_lift": False,
    "homed_disk": False,
    "sensors": {},
    "message": str(error),
    "error": str(error),
    "last_response": ""
  }

def motion_error_response(exc, telecover=False):
  code = 409 if isinstance(exc, MotionConnectionError) else 400 if isinstance(exc, ValueError) else 503 if isinstance(exc, (serial.SerialException, OSError)) else 500
  status = motion_connection.snapshot(ok=False, message=str(exc))
  payload = telecover_error_payload(exc) if telecover else dict(status)
  payload["motor_connection"] = status
  if hasattr(exc, "partial_results"):
    payload["partial_results"] = exc.partial_results
  return jsonify(payload), code


def motion_operation(owner):
  def decorate(view):
    @wraps(view)
    def guarded(*args, **kwargs):
      try:
        scan = autoalignment_service.snapshot()
        stopping_motor = owner == "alignment" and request.values.get("selected") == "motor_stop"
        stopping_telecover = owner == "telecover" and request.values.get("action") == "stop"
        if stopping_motor and scan["running"]:
          autoalignment_service.stop()
          return jsonify(motion_connection.snapshot(message="Autoalignment stop requested."))
        if stopping_motor or stopping_telecover:
          command = b"\x85" if stopping_motor else b"TCVDetener\n"
          if motion_connection.interrupt(owner, command):
            return jsonify({"status": "OK", "message": "Stop requested.", "motor_connection": motion_connection.snapshot()})
        if scan["running"] or scan["moving"]:
          raise MotionConnectionBusy("Autoalignment is using the shared motor/Telecover connection.")
        with motion_connection.operation(owner) as connection:
          result = view(connection, *args, **kwargs)
        response = make_response(result)
        if response.is_json:
          status_code = response.status_code
          payload = response.get_json()
          payload["motor_connection"] = motion_connection.snapshot()
          response = jsonify(payload)
          response.status_code = status_code
        return response
      except Exception as exc:
        return motion_error_response(exc, telecover=owner == "telecover")
    return guarded
  return decorate


@app.route("/motor_connection", methods=["GET", "POST"])
def motor_connection_controls():
  action = request.values.get("selected", "motor_status")
  try:
    scan = autoalignment_service.snapshot()
    if action != "motor_status" and (scan["running"] or scan["moving"]):
      raise MotionConnectionBusy("Stop autoalignment before changing the shared connection.")
    if action == "motor_connect":
      port = motion_connection.validate_port(request.values.get("input", motion_connection.port))
      if laser.isConnected() and port.casefold() == globalconfig["laser_port"].casefold():
        raise MotionConnectionBusy("This serial port is already used by the laser.")
      result = motion_connection.connect(port)
    elif action == "motor_disconnect":
      result = motion_connection.disconnect()
    elif action == "motor_status":
      result = motion_connection.snapshot()
    else:
      raise ValueError("Invalid motor connection action.")
    return jsonify(result)
  except Exception as exc:
    return motion_error_response(exc)
  finally:
    globalconfig["motor_port"] = motion_connection.port
    globalconfig["telecover_port"] = motion_connection.port


@app.route("/telecover_status")
@motion_operation("telecover")
def telecover_status(connection):
  telecover = TelecoverController(connection)
  telecover.status_lift()
  return jsonify(telecover.status_disk())


@app.route("/telecover_control")
@motion_operation("telecover")
def telecover_control(connection):
  action = request.args.get("action", "")
  telecover = TelecoverController(connection)
  actions = {
    "home": telecover.full_home,
    "home_lift": telecover.home_lift,
    "home_disk": telecover.home_disk,
    "lift_up": telecover.lift_up,
    "lift_down": telecover.lift_down,
    "move_n": lambda: telecover.move_to("N"),
    "move_e": lambda: telecover.move_to("E"),
    "move_s": lambda: telecover.move_to("S"),
    "move_w": lambda: telecover.move_to("W"),
    "dark_close": telecover.dark_close,
    "dark_open": telecover.dark_open,
    "move_dc": telecover.dark_close,
    "stop": telecover.stop_lift,
  }
  if action not in actions:
    raise ValueError("Unsupported telecover action: {}".format(action))
  state = actions[action]()
  if state["status"] in {"ERROR", "TIMEOUT"}:
    raise RuntimeError(state.get("error") or state.get("message"))
  return jsonify(state)

def parse_boolean(value):
  normalized = str(value).strip().lower()
  if normalized not in {"true", "false"}:
    raise ValueError("Expected boolean value.")
  return normalized == "true"

@app.route("/telecover_setup")
def telecover_setup():
  selected = request.args.get("selected", "")
  input_value = request.args.get("input", "")
  try:
    if selected == "telecover_port":
      scan = autoalignment_service.snapshot()
      if scan["running"] or scan["moving"]:
        raise MotionConnectionBusy("Stop autoalignment before changing the shared connection.")
      motion_connection.configure(input_value)
      globalconfig["motor_port"] = motion_connection.port
      globalconfig["telecover_port"] = motion_connection.port
    elif selected == "telecover_download_dir":
      value = str(input_value).strip()
      if not value:
        raise ValueError("Telecover download folder is required.")
      globalconfig[selected] = value
    elif selected == "telecover_acq_time":
      value = int(input_value)
      if value < 0:
        raise ValueError("Acquisition time must be >= 0.")
      globalconfig[selected] = value
    elif selected == "telecover_settle_time":
      value = float(input_value)
      if value < 0:
        raise ValueError("Settle time must be >= 0.")
      globalconfig[selected] = value
    elif selected == "telecover_reverse":
      globalconfig[selected] = False
    elif selected == "telecover_auto_save":
      globalconfig[selected] = parse_boolean(input_value)
    elif selected == "telecover_channel":
      value = int(input_value)
      if value < 0:
        raise ValueError("Channel must be >= 0.")
      globalconfig[selected] = value
    elif selected == "telecover_sequence":
      sequence = json.loads(input_value)
      if (
        not isinstance(sequence, list)
        or not sequence
        or any(position not in {"N", "E", "S", "W"} for position in sequence)
      ):
        raise ValueError("Invalid telecover sequence.")
      globalconfig[selected] = sequence
    else:
      raise ValueError("Unsupported telecover setting: {}".format(selected))
    return jsonify(globalconfig)
  except (TypeError, ValueError, MotionConnectionError) as exc:
    return motion_error_response(exc, telecover=True)

@app.route("/telecover_acquire_current")
def telecover_acquire_current():
  position = request.args.get("position", "UNKNOWN").upper()
  return jsonify({
    "status": "OK",
    "position": position,
    "raw_trace": [],
    "metadata": {
      "acq_time": globalconfig["telecover_acq_time"],
      "channel": globalconfig["telecover_channel"]
    }
  })

@app.route("/telecover_run_sequence")
@motion_operation("telecover")
def telecover_run_sequence(connection):
  globalconfig["telecover_sequence"] = ["N", "E", "S", "W"]
  globalconfig["telecover_reverse"] = False
  sequence = list(globalconfig["telecover_sequence"])
  results = []
  telecover = TelecoverController(connection)
  try:
    telecover.home_lift()
    telecover.move_to("N")
    telecover.lift_down()
    for position in sequence:
      if position != "N":
        telecover.move_to(position)
      time.sleep(globalconfig["telecover_settle_time"])
      results.append({"position": position, "status": "OK", "raw_trace": []})
    if globalconfig["telecover_return_to_north_before_darkcurrent"]:
      telecover.move_to("N")
    if globalconfig["telecover_include_darkcurrent"]:
      telecover.dark_close()
      time.sleep(globalconfig["telecover_settle_time"])
      results.append({"position": "DC", "status": "OK", "raw_trace": []})
      telecover.dark_open()
    return jsonify({
      "status": "OK",
      "sequence": sequence + (["DC"] if globalconfig["telecover_include_darkcurrent"] else []),
      "results": results
    })
  except Exception as exc:
    exc.partial_results = results
    raise


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
  global licel_state

  action = request.values.get("selected","licel_status")
  ip_input = request.values.get("ip","").strip()
  port_input = request.values.get("port","").strip()

  if action == "licel_status":
    return jsonify(licel_status_payload(
      True,
      "Licel connected" if lc.isConnected() else "Licel disconnected"
    ))

  with licel_lock:
    try:
      if action in {"ip","port"}:
        if lc.isConnected():
          return jsonify(licel_status_payload(
            False,
            "Disconnect Licel before changing IP or port."
          )),409

        legacy_input = request.values.get("input","").strip()
        if action == "ip":
          ip_input = legacy_input
        else:
          port_input = legacy_input

      if action in {"licel_connect","ip"} and ip_input:
        octets = ip_input.split(".")
        if (
          len(octets) != 4
          or not all(
            octet.isdigit() and 0 <= int(octet) <= 255
            for octet in octets
          )
        ):
          return jsonify(licel_status_payload(
            False,
            "Invalid Licel IP address."
          )),400
        globalconfig["ip"] = ip_input

      if action in {"licel_connect","port"} and port_input:
        if not port_input.isdigit() or not 1 <= int(port_input) <= 65535:
          return jsonify(licel_status_payload(
            False,
            "Invalid Licel TCP port."
          )),400
        globalconfig["port"] = int(port_input)

      if action == "licel_connect":
        if not lc.isConnected():
          lc.openConnection(globalconfig["ip"],globalconfig["port"])
        licel_state = "connected"
        message = "Licel connection established"

      elif action == "licel_disconnect":
        lc.closeConnection()
        licel_state = "disconnected"
        message = "Licel connection closed"

      elif action in {"ip","port"}:
        message = "Licel connection settings updated"

      else:
        return jsonify(licel_status_payload(
          False,
          "Invalid Licel connection action."
        )),400

      return jsonify(licel_status_payload(True,message))

    except ValueError as ex:
      licel_state = "disconnected"
      return jsonify(licel_status_payload(False,str(ex))),500

@app.route("/laser",methods=['GET','POST'])
def laser_controls():
  global laser_state

  action_button = request.values.get('selected', '')
  serial_port = request.values.get('input', '').strip()

  with laser_lock:
    try:
      connected = laser.isConnected()
      if not connected:
        laser_state = "disconnected"
      elif laser_state == "disconnected":
        laser_state = "ready"

      if serial_port and serial_port != globalconfig["laser_port"]:
        if connected:
          return jsonify({
            "ok": False,
            "message": "Disconnect the laser before changing the serial port.",
            "connected": connected,
            "port": globalconfig["laser_port"],
            "state": laser_state
          }), 409

        globalconfig["laser_port"] = serial_port

      if(action_button == "laser_connect"):
        if motion_connection.is_connected() and globalconfig["laser_port"].casefold() == motion_connection.port.casefold():
          raise ValueError("This serial port is already used by motors/Telecover.")
        if not globalconfig["laser_port"]:
          return jsonify({
            "ok": False,
            "message": "Serial port is required.",
            "connected": False,
            "port": globalconfig["laser_port"],
            "state": laser_state
          }), 400

        laser.connect(port = globalconfig["laser_port"], baudrate = 9600, timeout = 5)
        laser_state = "ready"
        data = "Laser serial connection established"

      elif(action_button == "laser_disconnect"):
        laser.disconnect()
        laser_state = "disconnected"
        data = "Laser serial connection closed"

      elif(action_button == "laser_start"):
        laser.startLaser()
        laser_state = "shooting"
        data = "Laser START"

      elif(action_button == "laser_stop"):
        laser.stopLaser()
        laser_state = "ready"
        data = "Laser STOP"

      elif(action_button == "laser_shots"):
        shots = laser.shotsCounter()
        return jsonify({
          "ok": True,
          "message": "Laser shot counter: {:,}".format(shots),
          "connected": laser.isConnected(),
          "port": globalconfig["laser_port"],
          "state": laser_state,
          "shots": shots
        })

      elif(action_button == "laser_status"):
        data = "Laser connected" if laser.isConnected() else "Laser disconnected"

      else:
        return jsonify({
          "ok": False,
          "message": "Invalid laser action.",
          "connected": laser.isConnected(),
          "port": globalconfig["laser_port"],
          "state": laser_state
        }), 400

      return jsonify({
        "ok": True,
        "message": data,
        "connected": laser.isConnected(),
        "port": globalconfig["laser_port"],
        "state": laser_state
      })

    except ValueError as ex:
      return jsonify({
        "ok": False,
        "message": str(ex),
        "connected": laser.isConnected(),
        "port": globalconfig["laser_port"],
        "state": laser_state
      }), 500

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

@app.route('/motor', methods=['GET', 'POST'])
def motor_controls():
  action = request.values.get("selected", "")
  value = request.values.get("input", "").strip()
  try:
    if action == "motor_port":
      scan = autoalignment_service.snapshot()
      if scan["running"] or scan["moving"]:
        raise MotionConnectionBusy("Stop autoalignment before changing the shared connection.")
      motion_connection.configure(value)
      globalconfig["motor_port"] = motion_connection.port
      globalconfig["telecover_port"] = motion_connection.port
    elif action == "motor_resolution":
      if value not in {"1", "0.1", "0.01"}:
        raise ValueError("Motor resolution must be 1, 0.1 or 0.01 mm.")
      globalconfig[action] = float(value)
    elif action == "motor_steps":
      if not value.isdigit() or int(value) <= 0:
        raise ValueError("Motor steps must be a positive integer.")
      globalconfig[action] = int(value)
    elif action == "motor_feed_rate":
      feed = float(value)
      if not 0 < feed < float("inf"):
        raise ValueError("Motor feed rate must be positive and finite.")
      globalconfig[action] = feed
    else:
      return motor_movement()
    return jsonify(dict(motion_connection.snapshot(), globalconfig=globalconfig))
  except Exception as exc:
    return motion_error_response(exc)


@motion_operation("alignment")
def motor_movement(connection):
  action = request.values.get("selected", "")
  directions = {"motor_left": (-1, 0), "motor_right": (1, 0), "motor_up": (0, 1), "motor_down": (0, -1)}
  if action not in set(directions) | {"motor_stop", "motor_gethome", "motor_sethome"}:
    raise ValueError("Invalid motor action.")
  motor = MotorController(ser=connection)
  if action == "motor_stop":
    motor.jog_cancel()
  else:
    feed = globalconfig["motor_feed_rate"]
    motor.initialize(feed=feed)
    if action in directions:
      motor.disable_limits()
      distance = globalconfig["motor_steps"] * globalconfig["motor_resolution"]
      dx, dy = directions[action]
      motor.jog(dx=dx * distance, dy=dy * distance, dz=0.0, feed=feed)
    elif action == "motor_gethome":
      motor.go_home(feed=feed)
    else:
      motor.set_home()
  return jsonify(dict(motion_connection.snapshot(), globalconfig=globalconfig))

@app.route('/scan_setup', methods=['GET','POST'])
def scan_setup_controls():
  field_selected = request.args['selected']
  data_input = request.args['input']

  print("Scan setup action: " + field_selected + ", input: " + data_input)

  integer_fields = ["scan_rows", "scan_cols", "scan_feed"]
  float_fields = ["scan_step_x", "scan_step_y", "scan_delay"]
  pattern_options = ["raster", "zigzag", "spiral"]
  on_fail_options = ["retry", "skip", "abort"]

  if field_selected in integer_fields and data_input.isdigit():
    value = int(data_input)
    if field_selected in ["scan_rows", "scan_cols"] and value > 2:
      globalconfig[field_selected] = value
    if field_selected == "scan_feed" and value > 0:
      globalconfig[field_selected] = value

  if field_selected in float_fields and data_input.replace('.','',1).isdigit():
    value = float(data_input)
    if field_selected in ["scan_step_x", "scan_step_y"] and value > 0:
      globalconfig[field_selected] = round(value, 3)
    if field_selected == "scan_delay" and value >= 0:
      globalconfig[field_selected] = value

  if field_selected == "scan_steps":
    scan_steps = json.loads(data_input)
    if len(scan_steps) == 2:
      step_x = scan_steps[0]
      step_y = scan_steps[1]
      if str(step_x).replace('.','',1).isdigit() and str(step_y).replace('.','',1).isdigit():
        step_x = float(step_x)
        step_y = float(step_y)
        if step_x > 0 and step_y > 0:
          globalconfig["scan_step_x"] = round(step_x, 3)
          globalconfig["scan_step_y"] = round(step_y, 3)

  if field_selected == "scan_pattern" and data_input in pattern_options:
    globalconfig[field_selected] = data_input

  if field_selected in ["scan_reverse", "scan_centered"] and data_input in ["true", "false", "True", "False"]:
    globalconfig[field_selected] = data_input.lower() == "true"

  if field_selected == "scan_on_fail" and data_input in on_fail_options:
    globalconfig[field_selected] = data_input

  response = make_response(json.dumps(globalconfig))
  response.content_type = 'application/json'
  return response

#----------- MAIN RUN -----------

if __name__ == '__main__':
  app.run(debug=True)
