(function ($) {
  'use strict';

  var settingBindings = [
    ['scan_rows_apply', 'scan_rows_input'],
    ['scan_cols_apply', 'scan_cols_input'],
    ['scan_feed_apply', 'scan_feed_input'],
    ['scan_pattern_apply', 'scan_pattern_input'],
    ['scan_centered_apply', 'scan_centered_input'],
    ['scan_reverse_apply', 'scan_reverse_input'],
    ['scan_delay_apply', 'scan_delay_input'],
    ['scan_on_fail_apply', 'scan_on_fail_input']
  ];
  var statusTimer = null;
  var lastRevision = -1;
  var statusPollDelayMs = 500;

  function feedback(message, level) {
    var element = $('#scan_setup_feedback');
    var className = level === 'error' ? 'text-danger' :
      (level === 'success' ? 'text-success' : 'text-light');

    element.removeClass('text-light text-success text-danger').addClass(className);
    element.text(message);
  }

  function errorMessage(xhr, fallback) {
    if (xhr.responseJSON && xhr.responseJSON.message) {
      return xhr.responseJSON.message;
    }
    return fallback;
  }

  function formatPosition(point) {
    var gridX = typeof point.col === 'number' ? point.col : 0;
    var gridY = typeof point.row === 'number' ? point.row : 0;
    var formatGridCoordinate = function (value) {
      return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);
    };
    return '(' + formatGridCoordinate(gridX) + ',' +
      formatGridCoordinate(gridY) + ') = (' +
      Number(point.x).toFixed(2) + ', ' +
      Number(point.y).toFixed(2) + ') mm';
  }

  function updateConfig(data) {
    globalconfig = data;
    $('#grid_size_value').text(data.scan_rows + ' x ' + data.scan_cols);
    var homeX = data.scan_centered ? (Number(data.scan_cols) + 1) / 2 : 0;
    var homeY = data.scan_centered ? (Number(data.scan_rows) + 1) / 2 : 0;
    $('#grid_current_position_value').text(
      '(' + homeX + ',' + homeY + ') = (0.00, 0.00) mm'
    );
  }

  function validateInput(inputId) {
    var input = document.getElementById(inputId);
    if (!input || typeof input.checkValidity !== 'function' || input.checkValidity()) {
      return true;
    }

    input.reportValidity();
    feedback('Check the highlighted scan setting.', 'error');
    return false;
  }

  function applySetting(buttonId, inputId) {
    var button = $('#' + buttonId);
    var input = $('#' + inputId);

    if (!validateInput(inputId)) {
      return;
    }

    button.prop('disabled', true);
    feedback('Saving scan setting...', 'info');

    $.ajax({
      url: '/scan_setup',
      type: 'GET',
      dataType: 'json',
      data: {
        selected: button.val(),
        input: input.val()
      }
    }).done(function (data) {
      updateConfig(data);
      feedback('Scan setting updated.', 'success');
    }).fail(function (xhr) {
      feedback(errorMessage(xhr, 'Could not update the scan setting.'), 'error');
    }).always(function () {
      button.prop('disabled', false);
    });
  }

  function applySteps() {
    var button = $('#scan_steps_apply');
    if (!validateInput('scan_step_x_input') || !validateInput('scan_step_y_input')) {
      return;
    }

    button.prop('disabled', true);
    feedback('Saving scan steps...', 'info');

    $.ajax({
      url: '/scan_setup',
      type: 'GET',
      dataType: 'json',
      data: {
        selected: button.val(),
        input: JSON.stringify([
          $('#scan_step_x_input').val(),
          $('#scan_step_y_input').val()
        ])
      }
    }).done(function (data) {
      updateConfig(data);
      $('#scan_step_x_input').val(Number(data.scan_step_x).toFixed(3));
      $('#scan_step_y_input').val(Number(data.scan_step_y).toFixed(3));
      feedback('Scan steps updated.', 'success');
    }).fail(function (xhr) {
      feedback(errorMessage(xhr, 'Could not update the scan steps.'), 'error');
    }).always(function () {
      button.prop('disabled', false);
    });
  }

  function renderResponse(context) {
    if (context.plot_lidar_range_correction) {
      drawResponsivePlot('plotly-lidar-range-correction', parsePlotFigure(context.plot_lidar_range_correction), {
        margin: rangeCorrectedMargins
      });
    }
    if (context.plot_lidar_signal) {
      drawResponsivePlot('plotly-lidar-signal', parsePlotFigure(context.plot_lidar_signal), {
        title: null,
        margin: rawSignalMargins
      });
    }
    if (context.plot_pearson) {
      drawResponsivePlot('plotly-pearson', parsePlotFigure(context.plot_pearson), {
        margin: {t: 18, r: 16, b: 42, l: 52}
      });
    }
    if (context.plot_measurement_grid) {
      drawResponsivePlot('plotly-measurement-grid', parsePlotFigure(context.plot_measurement_grid), {
        margin: {t: 18, r: 24, b: 42, l: 52}
      });
    }
    if (context.best) {
      $('#pearson_max_value').text(Number(context.best.pearson).toFixed(4));
      $('#pearson_best_location_value').text(formatPosition(context.best));
    }
    if (context.current) {
      $('#grid_current_position_value').text(formatPosition(context.current));
    }

    setScanProgress(context.progress || 0);
    setScanStatus(context.status || 'Idle');
    setTimeout(resizeAutoalignPlots, 50);
  }

  function scanIsActive(context) {
    return context.running || ['Starting', 'Running', 'Stopping'].indexOf(context.status) >= 0;
  }

  function operationIsActive(context) {
    return scanIsActive(context) || context.moving || context.status === 'Moving';
  }

  function canMoveToBest(context) {
    return context.status === 'Complete' && context.best && !operationIsActive(context);
  }

  function stopStatusPolling() {
    if (statusTimer) {
      clearTimeout(statusTimer);
      statusTimer = null;
    }
  }

  function scheduleStatusPoll() {
    stopStatusPolling();
    statusTimer = setTimeout(pollStatus, statusPollDelayMs);
  }

  function handleStatus(context) {
    if (typeof context.revision === 'number' && context.revision < lastRevision) {
      return;
    }

    if (context.revision !== lastRevision) {
      lastRevision = context.revision;
      renderResponse(context);
      if (context.message) {
        feedback(context.message, context.status === 'Error' ? 'error' : 'info');
      }
    }

    $('#autoalign_start_btn').prop('disabled', operationIsActive(context));
    $('#autoalign_stop_btn').prop('disabled', !scanIsActive(context));
    $('#autoalign_move_best_btn').prop('disabled', !canMoveToBest(context));

    if (operationIsActive(context)) {
      scheduleStatusPoll();
      return;
    }

    stopStatusPolling();
    if (context.status === 'Complete') {
      feedback('Autoalignment scan finished.', 'success');
    } else if (context.status === 'Stopped') {
      feedback('Autoalignment stopped.', 'info');
    }
  }

  function pollStatus() {
    $.ajax({
      url: '/autoalign/status',
      type: 'GET',
      dataType: 'json',
      cache: false
    }).done(handleStatus).fail(function (xhr) {
      feedback(errorMessage(xhr, 'Could not read autoalignment status.'), 'error');
      scheduleStatusPoll();
    });
  }

  $(function () {
    settingBindings.forEach(function (binding) {
      var button = $('#' + binding[0]);
      button.off('click').on('click.autoalignment', function (event) {
        event.preventDefault();
        applySetting(binding[0], binding[1]);
      });
    });

    $('#scan_steps_apply').off('click').on('click.autoalignment', function (event) {
      event.preventDefault();
      applySteps();
    });

    $('#autoalign_start_btn').off('click').on('click.autoalignment', function () {
      var button = $(this);
      button.prop('disabled', true);
      $('#autoalign_stop_btn').prop('disabled', false);
      $('#autoalign_move_best_btn').prop('disabled', true);
      setScanStatus('Starting');
      setScanProgress(0);
      $('#pearson_max_value, #pearson_best_location_value').text('--');
      feedback('Autoalignment scan started.', 'info');

      $.ajax({
        url: '/autoalign/start',
        type: 'POST',
        dataType: 'json',
      }).done(function (context) {
        lastRevision = -1;
        handleStatus(context);
      }).fail(function (xhr) {
        setScanStatus('Error');
        button.prop('disabled', false);
        $('#autoalign_stop_btn').prop('disabled', true);
        feedback(errorMessage(xhr, 'Autoalignment scan failed.'), 'error');
      });
    });

    $('#autoalign_stop_btn').off('click').on('click.autoalignment', function () {
      var button = $(this);
      button.prop('disabled', true);
      setScanStatus('Stopping');

      $.ajax({
        url: '/autoalign/stop',
        type: 'POST',
        dataType: 'json',
      }).done(function (context) {
        handleStatus(context);
      }).fail(function (xhr) {
        button.prop('disabled', false);
        feedback(errorMessage(xhr, 'Could not stop autoalignment.'), 'error');
      });
    });

    $('#autoalign_move_best_btn').off('click').on('click.autoalignment', function () {
      var button = $(this);
      button.prop('disabled', true);
      $('#autoalign_start_btn').prop('disabled', true);
      setScanStatus('Moving');
      feedback('Moving to the best autoalignment position...', 'info');

      $.ajax({
        url: '/autoalign/move-best',
        type: 'POST',
        dataType: 'json',
      }).done(function (context) {
        handleStatus(context);
        feedback('Motor moved to the best autoalignment position.', 'success');
      }).fail(function (xhr) {
        feedback(errorMessage(xhr, 'Could not move to the best position.'), 'error');
        pollStatus();
      });
    });

    $('#autoalign_stop_btn').prop('disabled', true);
    $('#autoalign_move_best_btn').prop('disabled', true);
    feedback('Scan settings ready.', 'info');
    pollStatus();
  });
})(jQuery);
