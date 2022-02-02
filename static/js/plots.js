// plots.js

$('#raw_limits_apply').on('click', function (e) {
  $.ajax({
    url: "/plots",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('raw_limits_apply').value,
      'input': JSON.stringify([
                                document.getElementById('raw_limits_init_input').value,
                                document.getElementById('raw_limits_final_input').value
                              ])
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#rc_limits_apply').on('click', function (e) {
  $.ajax({
    url: "/plots",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('rc_limits_apply').value,
      'input': JSON.stringify([
                                document.getElementById('rc_limits_init_input').value,
                                document.getElementById('rc_limits_final_input').value
                              ])
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})

$('#smooth_level_apply').on('click', function (e) {
  $.ajax({
    url: "/plots",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': document.getElementById('smooth_level_apply').value,
      'input': document.getElementById('smooth_level_input').value
    },
    dataType:"json",
    success: function (data) {
      console.log(data);
    }
  });
})