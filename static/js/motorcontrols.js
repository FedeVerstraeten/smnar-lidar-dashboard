// motorcontrols.js

// Apply motor settings
$('#motor_port_apply').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_port_apply').value,
      'input': document.getElementById('motor_port_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR PORT APPLY");
    }
  });
})

$('#motor_resolution_apply').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_resolution_apply').value,
      'input': document.getElementById('motor_resolution_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR RESOLUTION APPLY");
    }
  });
})

$('#motor_steps_apply').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_steps_apply').value,
      'input': document.getElementById('motor_steps_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR STEP APPLY");
    }
  });
})

// Motors movements
// Left
$('#motor_left_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_resolution_apply').value,
      'input': 'left'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR LEFT BUTTON");
    }
  });
})
// Right
$('#motor_right_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_right_btn').value,
      'input': 'right'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR RIGHT BUTTON");
    }
  });
})
// Up
$('#motor_up_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_up_btn').value,
      'input': 'up'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR UP BUTTON");
    }
  });
})
// Down
$('#motor_down_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_down_btn').value,
      'input': 'down'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR DOWN BUTTON");
    }
  });
})

// Stop
$('#motor_stop_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_stop_btn').value,
      'input': 'stop'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR STOP BUTTON");
    }
  });
})

// Home (Get to origin)
$('#motor_gethome_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_gethome_btn').value,
      'input': 'gethome'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR GET HOME BUTTON");
    }
  });
})

// Reset (Set current position as origin)
$('#motor_sethome_btn').on('click', function (e) {
  $.ajax({
    url: "/motor",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('motor_sethome_btn').value,
      'input': 'sethome'
    },
    dataType:"json",
    success: function (data) {
      console.log("MOTOR SET HOME BUTTON");
    }
  });
})
