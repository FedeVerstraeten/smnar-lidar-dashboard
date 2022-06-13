// acquiscontrols.js

let acqinterval;

function requestAcquisData() {
  $.ajax({
    url: "/acquisdata",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('acq_startbtn').value
    },
    dataType:"json",
    success: function (context) {
      
      // Raw signal plot
      var graph_raw = JSON.parse(context.plot_multiple_lidar_signal);
      Plotly.newPlot('plotly-lidar-signal', graph_raw);
      
    },
    cache: false
  });
}

$('#period_time_apply').on('click', function (e) {
  $.ajax({
    url: "/licelcontrols",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('period_time_apply').value,
      'input': document.getElementById('period_time_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})


$('#acq_startbtn').on('click', function (e) {

    $.ajax({
     url: "/acquisdata",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('acq_startbtn').value

      },
      dataType:"json",
      success: function (context) {
        
        // var DELTA_TIME_MS = 2000
        console.log("Period delay ms",context.period_delay)
        
        if (!acqinterval) {
          acqinterval = setInterval(requestAcquisData,context.period_delay);
          console.log("ACQ START success",acqinterval);
        }
      }
   });
})

$('#acq_stopbtn').on('click', function (e) {
  $.ajax({
    url: "/acquisdata",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('acq_stopbtn').value
    },
    dataType:"json",
    success: function (context) {
      clearInterval(acqinterval);
      acqinterval=null;
      console.log("ACQ STOP success",acqinterval);
    }
  });
})

$('#acq_oneshotbtn').on('click', function (e) {

    $.ajax({
     url: "/acquisdata",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('acq_oneshotbtn').value

      },
      dataType:"json",
      success: function (context) {
        
        // Raw signal plot
        var graph_raw = JSON.parse(context.plot_multiple_lidar_signal);
        Plotly.newPlot('plotly-lidar-signal', graph_raw);
        
      }
   });
})
