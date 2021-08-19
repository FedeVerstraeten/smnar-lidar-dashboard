from flask import Flask, render_template, url_for, flash, redirect, request, make_response, jsonify, abort
import pandas as pd
import numpy as np
import json
from utils import utils, plotly_plot

#configuration
app = Flask(__name__)
app.config.from_object('config.Config')


# Loading raw data and clean it

#loading data
total_confirmed, total_death, total_recovered, df_pop = utils.load_data()

(grouped_total_confirmed, grouped_total_recovered,
 grouped_total_death, timeseries_final, country_names) = utils.preprocessed_data(total_confirmed, total_death, total_recovered)

final_df = utils.merge_data(grouped_total_confirmed,
                            grouped_total_recovered, grouped_total_death, df_pop)

#for chart_js map

@app.route("/")
@app.route("/plotly")
def plot_plotly_global():
  # total confirmed cases globally
  total_all_confirmed = total_confirmed[total_confirmed.columns[-1]].sum()
  total_all_recovered = total_recovered[total_recovered.columns[-1]].sum()
  total_all_deaths = total_death[total_death.columns[-1]].sum()
  #ploting
  plot_global_cases_per_country = plotly_plot.plotly_global_cases_per_country(final_df)
  plot_global_time_series = plotly_plot.plotly_global_timeseries(timeseries_final)
  plot_geo_analysis = plotly_plot.plotly_geo_analysis(final_df)
  context = {"total_all_confirmed": total_all_confirmed,
             "total_all_recovered": total_all_recovered, "total_all_deaths": total_all_deaths,
          'plot_global_cases_per_country': plot_global_cases_per_country,
          'plot_global_time_series': plot_global_time_series,'plot_geo_analysis': plot_geo_analysis}
  return render_template('plotly.html', context=context)

@app.route("/country", methods=['POST'])
def plot_country():
    # total confirmed cases globally
    # take country input from user
    country_name = request.form['country_name']
    total_confirmed_per_country, total_death_per_country, total_recovered_per_country=utils.get_per_country_data(
            total_confirmed, total_death, total_recovered, country_name)
    #ploting
    #plotly
    plotly_country_plot = plotly_plot.plotly_per_country_time_series(total_confirmed, 
                                                            total_death, total_recovered, country_name)
    
    timeseries_country = utils.get_by_country_merged(total_confirmed, total_death, total_recovered, country_name)
    timeseries_dates = timeseries_country["date"].values.tolist()
    
    context = {"total_confirmed_per_country": total_confirmed_per_country,
            "total_death_per_country": total_death_per_country, "total_recovered_per_country": total_recovered_per_country,
            'plotly_country_plot': plotly_country_plot, "timeseries_dates": timeseries_dates}

    return render_template('country.html', context=context)


if __name__ == '__main__':
  app.run(debug=True)