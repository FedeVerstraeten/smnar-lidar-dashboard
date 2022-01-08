// licelcontrols.js

let interval;

function requestPlots() {
  $.ajax({
    url: "/record",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('startbtn').value
    },
    dataType:"json",
    success: function (context) {
      
      // Raw signal plot
      var graph_raw = JSON.parse(context.plot_lidar_signal);
      Plotly.newPlot('plotly-lidar-signal', graph_raw);
      
      // Range corrected plot
      var graph_rc = JSON.parse(context.plot_lidar_range_correction);
      Plotly.newPlot('plotly-lidar-range-correction', graph_rc);
      
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
            range: [olderTime,futureTime]
          }
        };

      Plotly.relayout('plotly-lidar-rms', minuteView);
      Plotly.extendTraces('plotly-lidar-rms', update, [0])
    },
    cache: false
  });
}

$('#startbtn').on('click', function (e) {

    $.ajax({
     url: "/record",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('startbtn').value

      },
      dataType:"json",
      success: function (context) {
        
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

        Plotly.newPlot('plotly-lidar-rms',initial_data);
        var delay_ms = context.shots_delay + DELTA_TIME_MS;

        if (!interval) {
          interval = setInterval(requestPlots,delay_ms);
          console.log("START success",interval);
        }
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
      clearInterval(interval);
      interval=null;
      console.log("STOP success",interval);
    }
  });
})

$('#oneshotbtn').on('click', function (e) {

    $.ajax({
     url: "/record",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('oneshotbtn').value

      },
      dataType:"json",
      success: function (context) {
        
        // Raw signal plot
        var graph_raw = JSON.parse(context.plot_lidar_signal);
        Plotly.newPlot('plotly-lidar-signal', graph_raw);
        
        // Range corrected plot
        var graph_rc = JSON.parse(context.plot_lidar_range_correction);
        Plotly.newPlot('plotly-lidar-range-correction', graph_rc);
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

$('#adq_time_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('adq_time_apply').value,
      'input': document.getElementById('adq_time_input').value
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