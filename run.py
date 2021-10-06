from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
import pandas as pd
import numpy as np
import json
from utils import plotly_plot

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')


# Defining routes

@app.route("/")
@app.route("/lidar")
def plot_lidar_signal():

  # load data
  LIDAR_FILE='./analog.txt'
  data_csv = pd.read_csv(LIDAR_FILE,sep='\n',header=None)

  lidar_signal = np.array(data_csv[0])
  number_bins = len(data_csv[0])

  # LiDAR signal range correction since bin number 1000
  BIN_RC_THRESHOLD=1000
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


if __name__ == '__main__':
  app.run(debug=True)
