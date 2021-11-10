$('#select_signal').on('change', function () {

    $.ajax({
     url: "/signal",
      type: "GET",
      contentType: 'application/json;charset=UTF-8',
      data: {
        'selected': document.getElementById('select_signal').value

      },
      dataType:"json",
      success: function (fig) {
        console.log(fig);
        Plotly.newPlot('plotly-lidar-range-correction', fig );
        //var graphs = {{ context.plot_selected_signal| safe }};
        //Plotly.plot('plotly-selected-signal', graphs, {});
      }
   });

});

var xArray = [];
var yArray = [];
var cnt = 0;
var acq_status=0;
let interval;

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
      // var graph = JSON.parse(context.plot_lidar_range_correction)
      // Plotly.newPlot('plotly-lidar-range-correction', graph);
      console.log("stop",interval);
      clearInterval(interval);
      interval=null;
      console.log("STOP OK",acq_status);
    }
 });
})

// $('#datepicker').datepicker({
//     format: 'dd/mm/yyyy',
//     startDate: '-3d'
// });


function requestData() {
  $.ajax({
    url: "/acquis",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('startbtn').value
    },
    dataType:"json",
    success: function(point) {
      xArray=point[0];
      yArray=point[1];
      // call it again after one second
      console.log(point[0])
      var data_update = [{
        x : xArray,
        y : yArray,
        mode: 'lines',
        line: {color: '#80CAF6'}
      }];

      Plotly.newPlot('plotly-lidar-range-correction', data_update, [0]);
    },
    cache: false
  });
}

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
