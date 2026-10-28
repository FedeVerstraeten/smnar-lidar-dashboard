// A single serial connection is shared by alignment motors and Telecover.
window.motorConnectionStatus = {connected: false, busy: false, state: 'disconnected'};
window.autoalignmentState = null;
var motorConnectionRequestPending = false;

function updateMotorActionButtons() {
  var data = window.motorConnectionStatus;
  var scan = window.autoalignmentState || {};
  var scanActive = scan.running || scan.moving;
  var available = data.connected && !data.busy && !scanActive;
  $('#motor_left_btn, #motor_right_btn, #motor_up_btn, #motor_down_btn, #motor_gethome_btn, #motor_sethome_btn').prop('disabled', !available);
  $('#motor_stop_btn').prop('disabled', !data.connected);
  $('[data-motion-action]').prop('disabled', !available);
  $('[data-motion-stop]').prop('disabled', !data.connected);
  $('#autoalign_start_btn').prop('disabled', !available);
  $('#autoalign_move_best_btn').prop('disabled', !available || scan.status !== 'Complete' || !scan.best);
}

function setMotorConnectionStatus(response) {
  var data = response.motor_connection || response;
  if (typeof data.connected !== 'boolean') { return; }
  window.motorConnectionStatus = data;
  var busy = !!data.busy;
  var message = !data.connected ? 'Motors / Telecover disconnected' :
    (busy ? 'Motors / Telecover busy' : 'Motors / Telecover connected');
  $('#motor_nav_message').text(message);
  $('#motor_nav_led').removeClass('disconnected connected acquiring').addClass(
    busy ? 'acquiring' : (data.connected ? 'connected' : 'disconnected')
  );
  $('#motor_connection_status').text(data.ok === false ? data.message : message)
    .toggleClass('text-danger', data.ok === false)
    .toggleClass('text-success', data.ok !== false && data.connected && !busy)
    .toggleClass('text-warning', data.ok !== false && busy);
  $('#motor_port_input').prop('readonly', data.connected || busy || motorConnectionRequestPending);
  if (data.port && (data.connected || !$('#motor_port_input').val())) {
    $('#motor_port_input').val(data.port);
  }
  $('#motor_connectbtn').prop('disabled', data.connected || busy || motorConnectionRequestPending);
  $('#motor_disconnectbtn').prop('disabled', !data.connected || busy || motorConnectionRequestPending);
  updateMotorActionButtons();
}

function motorRequestFailure(xhr) {
  var data = xhr.responseJSON || Object.assign({}, window.motorConnectionStatus, {
    ok: false, message: 'Could not communicate with the dashboard.'
  });
  setMotorConnectionStatus(data);
}

function sendMotorConnectionAction(action) {
  if (motorConnectionRequestPending) { return; }
  motorConnectionRequestPending = true;
  setMotorConnectionStatus(window.motorConnectionStatus);
  $.ajax({
    url: '/motor_connection', type: 'POST', dataType: 'json',
    data: {selected: action, input: $('#motor_port_input').val() || ''}
  }).done(setMotorConnectionStatus).fail(motorRequestFailure).always(function () {
    motorConnectionRequestPending = false;
    setMotorConnectionStatus(window.motorConnectionStatus);
  });
}

function sendMotorAction(action, input) {
  $.ajax({
    url: '/motor', type: 'POST', dataType: 'json',
    data: {selected: action, input: input || ''}
  }).done(setMotorConnectionStatus).fail(motorRequestFailure);
}

function pollMotorConnection() {
  if (motorConnectionRequestPending || document.hidden) {
    setTimeout(pollMotorConnection, 2000);
    return;
  }
  $.ajax({url: '/motor_connection', data: {selected: 'motor_status'}, dataType: 'json', cache: false})
    .done(function (data) {
      // Preserve a control error until the next successful operator action.
      if (window.motorConnectionStatus.ok === false) {
        data.ok = false;
        data.message = window.motorConnectionStatus.message;
      }
      setMotorConnectionStatus(data);
    })
    .always(function () { setTimeout(pollMotorConnection, 2000); });
}

$(function () {
  // The third status row can increase the height of the fixed navbar.
  var navbar = document.querySelector('.main-header');
  var content = document.querySelector('.content-wrapper');
  if (navbar && content) {
    var fitNavbar = function () {
      content.style.marginTop = navbar.getBoundingClientRect().height + 'px';
    };
    fitNavbar();
    if ('ResizeObserver' in window) {
      new ResizeObserver(fitNavbar).observe(navbar);
    } else {
      window.addEventListener('resize', fitNavbar);
    }
  }
  $('#motor_connectbtn').on('click', function () { sendMotorConnectionAction('motor_connect'); });
  $('#motor_disconnectbtn').on('click', function () { sendMotorConnectionAction('motor_disconnect'); });
  ['resolution', 'steps', 'feed_rate'].forEach(function (setting) {
    $('#motor_' + setting + '_apply').on('click', function () {
      sendMotorAction('motor_' + setting, $('#motor_' + setting + '_input').val());
    });
  });
  ['left', 'right', 'up', 'down', 'stop', 'gethome', 'sethome'].forEach(function (action) {
    $('#motor_' + action + '_btn').on('click', function () { sendMotorAction('motor_' + action); });
  });
  updateMotorActionButtons();
  pollMotorConnection();
});
