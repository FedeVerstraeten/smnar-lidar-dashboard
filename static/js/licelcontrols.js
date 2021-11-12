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
      // console.log(context);
      var graph_rc = JSON.parse(context.plot_lidar_range_correction)
      var graph_raw = JSON.parse(context.plot_lidar_signal)
      Plotly.newPlot('plotly-lidar-range-correction', graph_rc);
      Plotly.newPlot('plotly-lidar-signal', graph_raw);
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
        console.log("START OK");
        if (!interval) {
          interval = setInterval(requestPlots,2000);
          console.log("start",interval);
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
      console.log("stop",interval);
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
