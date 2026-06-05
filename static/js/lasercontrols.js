// lasercontrols.js

function getLaserState(data) {
  if (data && data.state) {
    return data.state;
  }

  return data && data.connected ? 'ready' : 'disconnected';
}

function getLaserStatusMessage(state) {
  if (state === 'shooting') {
    return 'Laser Shooting';
  }

  if (state === 'ready') {
    return 'Laser connected/ready';
  }

  return 'Laser disconnected';
}

function setLaserStatus(data) {
  const statusText = $('#laser_status_text');
  const state = getLaserState(data);
  const connected = state !== 'disconnected';
  const message = getLaserStatusMessage(state);

  statusText
    .text(message)
    .toggleClass('text-success', state === 'ready')
    .toggleClass('text-warning', state === 'shooting')
    .toggleClass('text-danger', data && data.ok === false)
    .toggleClass('text-muted', !connected && !(data && data.ok === false));

  $('#laser_nav_message').text(message);
  $('#laser_nav_warning').toggleClass('d-none', state !== 'shooting');
  $('#laser_nav_led')
    .removeClass('disconnected ready shooting')
    .addClass(state);

  $('#laser_port_input').prop('readonly', connected);
  $('#laser_connectbtn').prop('disabled', connected);
  $('#laser_disconnectbtn').prop('disabled', !connected);
  $('#laser_startbtn').prop('disabled', !connected);
  $('#laser_stopbtn').prop('disabled', !connected);
  $('#laser_shotsbtn').prop('disabled', !connected);
}

function sendLaserAction(action) {
  const portInput = document.getElementById('laser_port_input');

  $.ajax({
    url: "/laser",
    type: "GET",
    contentType: 'application/json;charset=UTF-8',
    data: {
      'selected': action,
      'input': portInput ? portInput.value : ''
    },
    dataType:"json",
    success: function (data) {
      setLaserStatus(data);
      showLaserShots(data);
      console.log(data.message);
    },
    error: function (xhr) {
      const data = xhr.responseJSON || {
        ok: false,
        connected: false,
        message: 'Laser control error'
      };

      setLaserStatus(data);
      console.error(data.message);
    }
  });
}

function showLaserShots(data) {
  if (!data || typeof data.shots === 'undefined') {
    return;
  }

  $('#laser_shots_value').text(Number(data.shots).toLocaleString('en-US'));
  $('#laser_shots_port').text(data.port || '');
  $('#laser_shots_modal').modal('show');
}

$('#laser_connectbtn').on('click', function () {
  sendLaserAction(this.value);
});

$('#laser_disconnectbtn').on('click', function () {
  sendLaserAction(this.value);
});

$('#laser_startbtn').on('click', function () {
  sendLaserAction(this.value);
});

$('#laser_stopbtn').on('click', function () {
  sendLaserAction(this.value);
});

$('#laser_shotsbtn').on('click', function () {
  sendLaserAction(this.value);
});

$(function () {
  if (document.getElementById('laser_nav_led')) {
    sendLaserAction('laser_status');
  }
});
