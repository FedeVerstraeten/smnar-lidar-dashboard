// lasercontrols.js

$('#laser_startbtn').on('click', function (e) {
  $.ajax({
    url: "/laser",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('laser_startbtn').value,
      'input': document.getElementById('laser_port_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("LASER START");
    }
  });
})

$('#laser_stopbtn').on('click', function (e) {
  $.ajax({
    url: "/laser",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('laser_stopbtn').value,
      'input': document.getElementById('laser_port_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("LASER STOP");
    }
  });
})
