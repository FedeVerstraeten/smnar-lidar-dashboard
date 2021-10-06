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
        var graph = JSON.parse(context.plot_lidar_range_correction)
        Plotly.newPlot('plotly-lidar-range-correction', graph);
      }
   });
})