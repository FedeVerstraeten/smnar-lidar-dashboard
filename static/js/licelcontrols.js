// licelcontrols.js

let interval;

function requestPlots() {
  $.ajax({
    url: "/acquis",
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
      // var graph_rms = JSON.parse(context.plot_lidar_rms);
      // Plotly.newPlot('plotly-lidar-rms', graph_rms);
    },
    cache: false
  });
}

$('#startbtn').on('click', function (e) {

    $.ajax({
     url: "/acquis",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('startbtn').value

      },
      dataType:"json",
      success: function (context) {
        
        var delay_ms = context.shots_delay + 1000

        if (!interval) {
          interval = setInterval(requestPlots,delay_ms);
          console.log("START success",interval);
        }
      }
   });
})

$('#stopbtn').on('click', function (e) {
  $.ajax({
    url: "/acquis",
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

$('#max_bins_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('max_bins_apply').value,
      'input': document.getElementById('max_bins_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})
