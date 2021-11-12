// controls.js

var xArray = [];
var yArray = [];

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

// $('#datepicker').datepicker({
//     format: 'dd/mm/yyyy',
//     startDate: '-3d'
// });

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