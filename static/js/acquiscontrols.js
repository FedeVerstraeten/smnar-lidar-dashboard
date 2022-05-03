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
      
      // // Raw signal plot
      // var graph_raw = JSON.parse(context.plot_lidar_signal);
      // Plotly.newPlot('plotly-lidar-signal', graph_raw);
      
      // // Range corrected plot
      // var graph_rc = JSON.parse(context.plot_lidar_range_correction);
      // Plotly.newPlot('plotly-lidar-range-correction', graph_rc);
      
      console.log(context);
    },
    cache: false
  });
}

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
        
        var DELTA_TIME_MS = 1000
        var delay_ms = context.shots_delay + DELTA_TIME_MS;
        console.log("Delay ms",delay_ms)
        
        if (!acqinterval) {
          acqinterval = setInterval(requestAcquisData,delay_ms);
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
