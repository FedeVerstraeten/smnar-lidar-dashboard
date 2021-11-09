import dateutil
import datetime
import plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from vega_datasets import data
import pandas as pd
import json

#-----------
#   LiDAR
#-----------

def plotly_lidar_signal(lidar_signal):
  # Plotly plot 1:
  df = pd.DataFrame(lidar_signal)
  df.reset_index(inplace=True)
  df.columns=["bin","TR0_500mV"]
  
  fig = px.line(df, 
                x='bin', 
                y=['TR0_500mV'], 
                title='LiDAR raw signal')
  
  fig.update_xaxes(rangeslider_visible=True)
  fig.update_layout(width=1200, height=500)

  plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json

# def plotly_lidar_range_correction(lidar_rc):
#   # Plotly plot 2:
#   df = pd.DataFrame(lidar_rc)
#   df.reset_index(inplace=True)
#   df.columns=["bin","TR0_500mV"]
  
#   fig = px.line(df, 
#                 x='bin', 
#                 y=['TR0_500mV'], 
#                 title='LiDAR range-corrected signal')
  
#   fig.update_xaxes(rangeslider_visible=True)
#   fig.update_layout(width=1500, height=500)
#   fig.add_vrect(x0=250, x1=1500, line_width=0, fillcolor="red", opacity=0.2)
#   plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
#   return plot_json    

def plotly_lidar_range_correction(range_lidar,lidar_rc,lidar_RF):
  # Plotly plot 1:
  print("lengs",len(range_lidar),len(lidar_rc),len(lidar_RF))
  df=pd.DataFrame({'meters':range_lidar,'TR0_500mV':lidar_rc,'TR0_500mV_RF':lidar_RF})
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
      # width=1200, height=700
      width=800, height=600
  )
  # display rayleigh-fit range
  fig.add_vrect(x0=5000, x1=15000, line_width=0, fillcolor="red", opacity=0.2)

   # Set x-axis title
  #fig.update_xaxes(tickangle=45,rangeslider_visible=True)
  fig.update_xaxes(tickangle=45,title_text="Height [m]")
  
  # Set y-axes titles
  fig.update_yaxes(title_text="TR0 500mV",
                   secondary_y=False, showgrid=False)
  fig.update_yaxes(title_text="TR0 500mV RF", tickangle=45,
                   secondary_y=True, showgrid=False)
  
  plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
  
  return plot_json
