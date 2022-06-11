// rayleighfit.js

$('#temperature_apply').on('click', function (e) {
  $.ajax({
    url: "/rayleighfit",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('temperature_apply').value,
      'input': document.getElementById('temperature_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#pressure_apply').on('click', function (e) {
  $.ajax({
    url: "/rayleighfit",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('pressure_apply').value,
      'input': document.getElementById('pressure_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#masl_apply').on('click', function (e) {
  $.ajax({
    url: "/rayleighfit",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('masl_apply').value,
      'input': document.getElementById('masl_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#wavelength_apply').on('click', function (e) {
  $.ajax({
    url: "/rayleighfit",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('wavelength_apply').value,
      'input': document.getElementById('wavelength_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#fit_apply').on('click', function (e) {
  $.ajax({
    url: "/rayleighfit",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('fit_apply').value,
      'input': JSON.stringify([
                                document.getElementById('fit_init_input').value,
                                document.getElementById('fit_final_input').value
                              ])
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})
