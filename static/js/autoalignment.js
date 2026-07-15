(function ($) {
  'use strict';

  var settingBindings = [
    ['scan_rows_apply', 'scan_rows_input'],
    ['scan_cols_apply', 'scan_cols_input'],
    ['scan_feed_apply', 'scan_feed_input'],
    ['scan_pattern_apply', 'scan_pattern_input'],
    ['scan_reverse_apply', 'scan_reverse_input'],
    ['scan_delay_apply', 'scan_delay_input'],
    ['scan_on_fail_apply', 'scan_on_fail_input']
  ];

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

  function updateConfig(data) {
    globalconfig = data;
    $('#grid_size_value').text(data.scan_rows + ' x ' + data.scan_cols);
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
      $('#pearson_best_location_value').text('C' + context.best.col + ', R' + context.best.row);
      $('#grid_current_x_value').text(Number(context.best.x).toFixed(3) + ' mm');
      $('#grid_current_y_value').text(Number(context.best.y).toFixed(3) + ' mm');
    }

    setScanProgress(context.progress || 0);
    setScanStatus(context.status || 'Idle');
    setTimeout(resizeAutoalignPlots, 50);
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
      setScanStatus('Running');
      setScanProgress(0);
      $('#pearson_max_value, #pearson_best_location_value').text('--');
      feedback('Autoalignment scan started.', 'info');

      $.ajax({
        url: '/autoalign',
        type: 'GET',
        dataType: 'json',
        data: {selected: button.val()}
      }).done(function (context) {
        renderResponse(context);
        feedback('Autoalignment scan finished.', 'success');
      }).fail(function (xhr) {
        setScanStatus('Error');
        feedback(errorMessage(xhr, 'Autoalignment scan failed.'), 'error');
      }).always(function () {
        button.prop('disabled', false);
      });
    });

    $('#autoalign_stop_btn').off('click').on('click.autoalignment', function () {
      var button = $(this);
      button.prop('disabled', true);

      $.ajax({
        url: '/autoalign',
        type: 'GET',
        dataType: 'json',
        data: {selected: button.val()}
      }).done(function (context) {
        setScanStatus(context.status || 'Stopped');
        feedback(context.message || 'Autoalignment stop requested.', 'info');
      }).fail(function (xhr) {
        feedback(errorMessage(xhr, 'Could not stop autoalignment.'), 'error');
      }).always(function () {
        button.prop('disabled', false);
      });
    });

    feedback('Scan settings ready.', 'info');
  });
})(jQuery);
