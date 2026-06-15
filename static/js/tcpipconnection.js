function setLicelStatus(data, updateConnectionFields) {
  const state = data.state || (data.connected ? 'connected' : 'disconnected');
  const messages = {
    disconnected: 'Licel disconnected',
    connected: 'Licel Connected',
    acquiring: 'Licel Acquiring'
  };
  const statusMessage = messages[state] || messages.disconnected;
  const detailMessage = data.message || statusMessage;
  const navbarLed = document.getElementById('licel_nav_led');
  const navbarMessage = document.getElementById('licel_nav_message');
  const sidebarStatus = document.getElementById('licel_connection_status');
  const connectButton = document.getElementById('licel_connectbtn');
  const disconnectButton = document.getElementById('licel_disconnectbtn');
  const startButtons = [
    document.getElementById('startbtn'),
    document.getElementById('acq_startbtn')
  ].filter(Boolean);
  const stopButtons = [
    document.getElementById('stopbtn'),
    document.getElementById('acq_stopbtn')
  ].filter(Boolean);
  const singleShotButtons = [
    document.getElementById('oneshotbtn'),
    document.getElementById('acq_oneshotbtn')
  ].filter(Boolean);
  const ipInput = document.getElementById('licel_ip_input');
  const portInput = document.getElementById('licel_port_input');
  const connected = state !== 'disconnected';

  if (navbarMessage) {
    navbarMessage.textContent = statusMessage;
  }
  if (navbarLed) {
    navbarLed.classList.remove('disconnected', 'connected', 'acquiring');
    navbarLed.classList.add(state);
  }
  if (sidebarStatus) {
    sidebarStatus.textContent = detailMessage;
  }
  if (connectButton) {
    connectButton.disabled = connected;
  }
  if (disconnectButton) {
    disconnectButton.disabled = !connected || state === 'acquiring';
  }
  startButtons.forEach(function (button) {
    button.disabled = !connected || state === 'acquiring';
  });
  stopButtons.forEach(function (button) {
    button.disabled = !connected;
  });
  singleShotButtons.forEach(function (button) {
    button.disabled = !connected || state === 'acquiring';
  });
  if (ipInput) {
    ipInput.readOnly = connected;
    if (updateConnectionFields && data.ip) {
      ipInput.value = data.ip;
    }
  }
  if (portInput) {
    portInput.readOnly = connected;
    if (updateConnectionFields && data.port) {
      portInput.value = data.port;
    }
  }
}

function setLicelAcquiring() {
  setLicelStatus({
    state: 'acquiring',
    connected: true
  });
}

function updateLicelFromRequest(xhr, fallbackMessage) {
  const response = xhr.responseJSON || {
    state: 'disconnected',
    message: fallbackMessage
  };
  setLicelStatus(response);
}

function sendLicelAction(action) {
  const ipInput = document.getElementById('licel_ip_input');
  const portInput = document.getElementById('licel_port_input');

  $.ajax({
    type: 'POST',
    url: '/tcpip',
    data: {
      selected: action,
      ip: ipInput ? ipInput.value : '',
      port: portInput ? portInput.value : ''
    },
    success: function (data) {
      setLicelStatus(data, action === 'licel_connect');
    },
    error: function (xhr) {
      updateLicelFromRequest(xhr, 'Licel connection error');
    }
  });
}

$(document).ready(function () {
  $('#licel_connectbtn').on('click', function () {
    sendLicelAction('licel_connect');
  });

  $('#licel_disconnectbtn').on('click', function () {
    sendLicelAction('licel_disconnect');
  });

  sendLicelAction('licel_status');
});
