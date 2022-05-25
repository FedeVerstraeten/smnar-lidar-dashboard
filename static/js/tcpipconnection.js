// tcpipconnection.js

$('#licel_ip_apply').on('click', function (e) {
  $.ajax({
    url: "/tcpip",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('licel_ip_apply').value,
      'input': document.getElementById('licel_ip_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("TCP IP address updated");
    }
  });
})

$('#licel_port_apply').on('click', function (e) {
  $.ajax({
    url: "/tcpip",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('licel_port_apply').value,
      'input': document.getElementById('licel_port_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("TCP Port updated");
    }
  });
})
