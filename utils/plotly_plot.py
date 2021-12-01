import dateutil
import datetime
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd
import json

#-----------
#   LiDAR
#-----------

def plotly_lidar_signal(lidar_signal,limit_init,limit_final):
  
  df=pd.DataFrame({
                  'meters':lidar_signal.range[limit_init:limit_final],
                  'TR0_500mV':lidar_signal.raw_signal[],
                  })
  df.index=df['meters']

  fig = px.line(df, 
                x=df.index, 
                y=df['TR0_500mV'], 
                title='LiDAR raw signal')
  
  # Set axes titles
  fig.update_xaxes(rangeslider_visible=True,title_text="Height [m]")
  fig.update_yaxes(title_text="TR0 Raw [mV]",)

  fig.update_layout(width=1200, height=500)

  plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json


def plotly_lidar_range_correction(lidar_signal):

  df=pd.DataFrame({
                  'meters':lidar_signal.range,
                  'TR0_500mV':lidar_signal.rc_signal,
                  'TR0_500mV_RF':lidar_signal.pr2_mol*lidar_signal.adj_factor
                  })
  df.index=df['meters']
  fig = go.Figure()
  fig = make_subplots() # rayleigh-fit secondary curve?
  #fig = make_subplots(specs=[[{"secondary_y": True}]]) # rayleigh-fit secondary curve?

  # Adding traces
  fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["TR0_500mV"],
        mode="lines",
        name="TR0 500mV",
        marker_color='#39ac39',
        opacity=1
    ),
    secondary_y=False
  )

  fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["TR0_500mV_RF"],
        mode="lines",
        name="TR0 500mV RF",
        marker_color='#b23434',
        opacity=0.7
    ),
    secondary_y=False
  )

  # Add figure title
  fig.update_layout(legend=dict(
      orientation="h",
      yanchor="bottom",
      y=1.02,
      xanchor="right",
      x=0.93),
      title={
      'text': '<span style="font-size: 20px;">Range corrected LiDAR signal </span><br><span style="font-size: 10px;">(click and drag)</span>',
      'y': 0.97,
      'x': 0.45,
      'xanchor': 'center',
      'yanchor': 'top'},
      paper_bgcolor="#ffffff",
      plot_bgcolor="#ffffff",
      width=640, height=480
      # width=800, height=600
  )
  # display rayleigh-fit range
  fig.add_vrect(x0=lidar_signal.fit_init, x1=lidar_signal.fit_final, line_width=0, fillcolor="red", opacity=0.2)

  # Set x-axis title
  #fig.update_xaxes(tickangle=45,rangeslider_visible=True)
  fig.update_xaxes(tickangle=45,title_text="Height [m]")
  
  # Set y-axes titles
  fig.update_yaxes(title_text="TR0 RC [mV x m^2] ",
                   secondary_y=False, showgrid=False)
  fig.update_yaxes(title_text="TR0 RC 500mV RF", tickangle=45,
                   secondary_y=True, showgrid=False)
  
  plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json

def plotly_empty_signal(signal_type):
  
  BIN_LONG_TRANCE = 4000
  empty_signal = [0] * BIN_LONG_TRANCE
  plot_json = {}
  
  if signal_type == "raw":
    df = pd.DataFrame(empty_signal)
    df.reset_index(inplace=True)
    df.columns=["bin","TR0_500mV"]
    fig = px.line(df, 
                  x='bin', 
                  y=['TR0_500mV'], 
                  title='LiDAR raw signal')
    
    fig.update_xaxes(rangeslider_visible=True)
    fig.update_layout(width=1200, height=500)
    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

  elif signal_type =="rms":
    df = pd.DataFrame(empty_signal)
    df.reset_index(inplace=True)
    df.columns=["sample","rms_error"]
 
    fig = go.Figure(data=go.Scatter(
          x=df['sample'],
          y=df["rms_error"],
          mode="lines",
          name="RMS error",
          # title="RMS TMS",
          marker_color='#b23434',
          opacity=1
    ))

    fig.update_layout(
      width=640,
      height=480,
      title={
        'text': '<span style="font-size: 20px;">RMS Error</span>',
        'y': 0.97,
        'x': 0.45,
        'xanchor': 'center',
        'yanchor': 'top'}
      )
      
    # Set x-axes titles
    fig.update_xaxes(title_text="Sample",rangeslider_visible=False)

    # Set y-axes titles
    fig.update_yaxes(title_text="Error",showgrid=True)
    
    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

  elif signal_type == "rangecorrected":
    df = pd.DataFrame(empty_signal)
    df.reset_index(inplace=True)
    df.columns=["bin","TR0_500mV"]
    df.index=df['bin']
    fig = go.Figure()
    fig = make_subplots() # rayleigh-fit secondary curve?


    # Adding traces
    fig.add_trace(
      go.Scatter(
          x=df.index,
          y=df["TR0_500mV"],
          mode="lines",
          name="TR0 500mV",
          marker_color='#39ac39',
          opacity=1
      ),
      secondary_y=False
    )

    # Add figure title
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=0.93),
        title={
        'text': '<span style="font-size: 20px;">Range corrected LiDAR signal </span><br><span style="font-size: 10px;">(click and drag)</span>',
        'y': 0.97,
        'x': 0.45,
        'xanchor': 'center',
        'yanchor': 'top'},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        width=640, height=480
        # width=800, height=600
    )

    # Set x-axis title
    fig.update_xaxes(tickangle=45,title_text="Height [m]")
  
    # Set y-axes titles
    fig.update_yaxes(title_text="TR0 500mV",
                     secondary_y=False, showgrid=False)
    
    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json

def plotly_lidar_rms(lidar_rms):

  df = pd.DataFrame(lidar_rms)
  df.reset_index(inplace=True)
  df.columns=["sample","rms_error"]

  fig = go.Figure(data=go.Scatter(
        x=df['sample'],
        y=df["rms_error"],
        mode="lines",
        name="RMS error",
        # title="RMS TMS",
        marker_color='#b23434',
        opacity=1
  ))

  fig.update_layout(
    width=640,
    height=480,
    title={
      'text': '<span style="font-size: 20px;">RMS Error</span>',
      'y': 0.97,
      'x': 0.45,
      'xanchor': 'center',
      'yanchor': 'top'}
    )
    
  # Set x-axes titles
  fig.update_xaxes(title_text="Sample",rangeslider_visible=False)

  # Set y-axes titles
  fig.update_yaxes(title_text="Error",showgrid=True)
  
  plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json
