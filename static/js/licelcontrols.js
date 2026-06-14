// licelcontrols.js

let interval;

function installVisibleYAutoscale(targetId) {
  var graph = document.getElementById(targetId);
  if (!graph || typeof graph.on !== 'function') {
    return;
  }

  if (graph._visibleYAutoscaleHandler) {
    graph.removeListener('plotly_relayout', graph._visibleYAutoscaleHandler);
  }

  var updatingY = false;
  graph._visibleYAutoscaleHandler = function (changes) {
    if (updatingY) {
      return;
    }

    if (changes['xaxis.autorange'] === true) {
      updatingY = true;
      Plotly.relayout(graph, {'yaxis.autorange': true}).finally(function () {
        updatingY = false;
      });
      return;
    }

    var changedRange = changes['xaxis.range'];
    var rangeStart = changedRange
      ? changedRange[0]
      : changes['xaxis.range[0]'];
    var rangeEnd = changedRange
      ? changedRange[1]
      : changes['xaxis.range[1]'];
    if (rangeStart === undefined || rangeEnd === undefined) {
      return;
    }

    var fullXAxis = graph._fullLayout && graph._fullLayout.xaxis;
    var dateRange = fullXAxis && fullXAxis.type === 'date';
    var start = dateRange
      ? new Date(rangeStart).getTime()
      : Number(rangeStart);
    var end = dateRange
      ? new Date(rangeEnd).getTime()
      : Number(rangeEnd);
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
      return;
    }

    var visibleY = [];
    graph.data.forEach(function (trace) {
      if (
        trace.visible === false
        || trace.visible === 'legendonly'
        || !trace.x
        || !trace.y
      ) {
        return;
      }

      trace.x.forEach(function (xValue, index) {
        var x = dateRange ? new Date(xValue).getTime() : Number(xValue);
        var y = Number(trace.y[index]);
        if (x >= start && x <= end && Number.isFinite(y)) {
          visibleY.push(y);
        }
      });
    });

    if (!visibleY.length) {
      return;
    }

    var minimum = Math.min.apply(null, visibleY);
    var maximum = Math.max.apply(null, visibleY);
    var padding = Math.max(
      (maximum - minimum) * 0.05,
      Math.abs(maximum || minimum) * 0.01,
      1e-12
    );

    updatingY = true;
    Plotly.relayout(graph, {
      'yaxis.range': [minimum - padding, maximum + padding],
      'yaxis.autorange': false
    }).finally(function () {
      updatingY = false;
    });
  };

  graph.on('plotly_relayout', graph._visibleYAutoscaleHandler);
}

function updateLidarPlot(targetId, figureJson, layoutOverrides) {
  var figure;
  try {
    figure = typeof figureJson === 'string'
      ? JSON.parse(figureJson)
      : figureJson;
  } catch (error) {
    console.error('Invalid Plotly figure for ' + targetId, error, figureJson);
    return;
  }

  if (!figure || !Array.isArray(figure.data)) {
    console.error('Plotly figure has no data for ' + targetId, figure);
    return;
  }

  console.debug(
    'Updating ' + targetId,
    figure.data.map(function (trace) {
      return {
        name: trace.name,
        xPoints: Array.isArray(trace.x) ? trace.x.length : 0,
        yPoints: Array.isArray(trace.y) ? trace.y.length : 0
      };
    })
  );

  var layout = Object.assign({}, figure.layout || {}, layoutOverrides || {});
  delete layout.width;
  delete layout.height;
  layout.autosize = true;

  Plotly.react(
    targetId,
    figure.data || [],
    layout,
    {responsive: true, displaylogo: false}
  ).then(function () {
    installVisibleYAutoscale(targetId);
  });
}

function updateLidarSignalPlots(context) {
  updateLidarPlot(
    'plotly-lidar-signal',
    context.plot_lidar_signal,
    {title: null, margin: {t: 32, r: 24, b: 56, l: 64}}
  );
  updateLidarPlot(
    'plotly-lidar-range-correction',
    context.plot_lidar_range_correction,
    {margin: {t: 104, r: 24, b: 64, l: 64}}
  );
}

function requestPlots() {
  setLicelAcquiring();
  $.ajax({
    url: "/record",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('startbtn').value
    },
    dataType:"json",
    success: function (context) {
      setLicelStatus({state: context.licel_state || 'connected', connected: true});
      updateLidarSignalPlots(context);
      
      // Continuous RMS error plot
      var time = new Date();
      var update = {
        x: [[time]],
        y: [[context.rms_error]]
      }
      console.log(update);
      var olderTime = time.setMinutes(time.getMinutes() - 1);
      var futureTime = time.setMinutes(time.getMinutes() + 1);
  
      var minuteView = {
        xaxis: {
            type: 'date',
            range: [olderTime,futureTime],
            title:{
              text: "Datetime [hh:mm:ss]"
            }
          }
        };

      Plotly.relayout('plotly-lidar-rms', minuteView);
      Plotly.extendTraces('plotly-lidar-rms', update, [0])
    },
    error: function (xhr) {
      updateLicelFromRequest(xhr, 'Licel acquisition failed');
    },
    cache: false
  });
}

$('#startbtn').on('click', function (e) {
    setLicelAcquiring();
    $.ajax({
     url: "/record",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('startbtn').value

      },
      dataType:"json",
      success: function (context) {
        setLicelStatus({state: context.licel_state || 'connected', connected: true});
        updateLidarSignalPlots(context);
        console.log("error es ",context.rms_error);
        var DELTA_TIME_MS = 1000

        // Adding RMS first point
        var time = new Date();
        var initial_data = [{
          x: [time],
          y: [0],
          mode: 'lines',
          line: {color: '#b23434'}
        }]

        var layout = {
          title: "Pearson correlation coefficient",
          xaxis: {
            title:{
              text: "Datetime [hh:mm:ss]"
            }
          },
          yaxis: {
            title:{
              text: "Correlation [\u03C1]"
            }
          },
          showlegend: false
        };

        Plotly.newPlot(
          'plotly-lidar-rms',
          initial_data,
          layout,
          {responsive: true, displaylogo: false}
        ).then(function () {
          installVisibleYAutoscale('plotly-lidar-rms');
        });
        var delay_ms = context.shots_delay + DELTA_TIME_MS;

        if (!interval) {
          interval = setInterval(requestPlots,delay_ms);
          console.log("START success",interval);
        }
      },
      error: function (xhr, status, error) {
        updateLicelFromRequest(xhr, 'Licel acquisition failed');
        console.error('START acquisition failed', status, error, xhr.responseText);
      }
   });
})

$('#stopbtn').on('click', function (e) {
  $.ajax({
    url: "/record",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('stopbtn').value
    },
    dataType:"json",
    success: function (context) {
      setLicelStatus({state: context.licel_state || 'connected', connected: true});
      clearInterval(interval);
      interval=null;
      console.log("STOP success",interval);
    }
  });
})

$('#oneshotbtn').on('click', function (e) {
    setLicelAcquiring();
    $.ajax({
     url: "/record",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('oneshotbtn').value

      },
      dataType:"json",
      success: function (context) {
        setLicelStatus({state: context.licel_state || 'connected', connected: true});
        updateLidarSignalPlots(context);

        var time = new Date();
        Plotly.extendTraces(
          'plotly-lidar-rms',
          {x: [[time]], y: [[context.rms_error]]},
          [0]
        );
      },
      error: function (xhr, status, error) {
        updateLicelFromRequest(xhr, 'Licel acquisition failed');
        console.error(
          'SINGLE SHOT acquisition failed',
          status,
          error,
          xhr.responseText
        );
      }
   });
})

$('#channel_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('channel_apply').value,
      'input': document.getElementById('channel_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#acq_time_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('acq_time_apply').value,
      'input': document.getElementById('acq_time_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#bin_offset_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('bin_offset_apply').value,
      'input': document.getElementById('bin_offset_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#bias_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('bias_apply').value,
      'input': JSON.stringify([
                                document.getElementById('bias_init_input').value,
                                document.getElementById('bias_final_input').value
                              ])
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$(document).ready(function () {
  [
    'plotly-lidar-signal',
    'plotly-lidar-range-correction',
    'plotly-lidar-rms'
  ].forEach(installVisibleYAutoscale);
});
