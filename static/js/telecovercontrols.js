var telecoverCurrentStatus = {
  disk_position: "UNKNOWN",
  lift: "UNKNOWN",
  darkcover: "UNKNOWN",
  motion: "IDLE",
  homed_lift: false,
  homed_disk: false,
  error: null
};

var telecoverTraceColors = {
  N: "#007bff",
  E: "#28a745",
  S: "#fd7e14",
  W: "#6f42c1",
  DC: "#343a40"
};

function telecoverRequest(url) {
  return fetch(url, {headers: {"Accept": "application/json"}}).then(function(response) {
    return response.json();
  });
}

function telecoverAction(action) {
  return telecoverRequest("/telecover_control?action=" + encodeURIComponent(action))
    .then(updateTelecoverStatus)
    .catch(function(error) {
      updateTelecoverStatus({motion: "ERROR", error: error.message});
    });
}

function telecoverSetup(selected, input) {
  return telecoverRequest(
    "/telecover_setup?selected=" + encodeURIComponent(selected) +
    "&input=" + encodeURIComponent(input)
  ).catch(function(error) {
    updateTelecoverStatus({motion: "ERROR", error: error.message});
  });
}

function telecoverStatus() {
  return telecoverRequest("/telecover_status")
    .then(updateTelecoverStatus)
    .catch(function(error) {
      updateTelecoverStatus({motion: "ERROR", error: error.message});
    });
}

function telecoverAcquireCurrent() {
  var position = telecoverCurrentStatus.disk_position || "UNKNOWN";
  return telecoverRequest(
    "/telecover_acquire_current?position=" + encodeURIComponent(position)
  ).then(function(data) {
    if (Array.isArray(data.raw_trace) && data.raw_trace.length) {
      updateTelecoverPlot(data.position, data.raw_trace);
    }
    return data;
  });
}

function telecoverRunSequence() {
  return telecoverRequest("/telecover_run_sequence").then(function(data) {
    if (Array.isArray(data.results)) {
      data.results.forEach(function(result) {
        if (Array.isArray(result.raw_trace) && result.raw_trace.length) {
          updateTelecoverPlot(result.position, result.raw_trace);
        }
      });
    }
    if (data.status === "ERROR") {
      updateTelecoverStatus({motion: "ERROR", error: data.message});
    } else {
      telecoverStatus();
    }
    return data;
  });
}

function updateTelecoverStatus(data) {
  data = data || {};
  telecoverCurrentStatus = Object.assign({}, telecoverCurrentStatus, data);

  setTelecoverText("tc-position-value", telecoverCurrentStatus.disk_position || "UNKNOWN");
  setTelecoverText("tc-lift-value", telecoverCurrentStatus.lift || "UNKNOWN");
  setTelecoverText("tc-darkcover-value", telecoverCurrentStatus.darkcover || "UNKNOWN");
  setTelecoverText("tc-motion-value", telecoverCurrentStatus.motion || "UNKNOWN");
  setTelecoverText("tc-error-value", telecoverCurrentStatus.error || "\u2014");

  updateTelecoverPlate(
    telecoverCurrentStatus.disk_position,
    telecoverCurrentStatus.motion,
    telecoverCurrentStatus.lift,
    telecoverCurrentStatus.darkcover
  );
  return data;
}

function setTelecoverText(id, value) {
  var element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function updateTelecoverPlate(position, motion, lift, darkcover) {
  var sectors = {
    N: document.getElementById("tc-sector-n"),
    E: document.getElementById("tc-sector-e"),
    S: document.getElementById("tc-sector-s"),
    W: document.getElementById("tc-sector-w")
  };
  var plate = document.getElementById("tc-plate");
  var overlay = document.getElementById("tc-plate-overlay");
  var fillClass = "tc-sector-unknown";
  var overlayText = "";

  position = String(position || "UNKNOWN").toUpperCase();
  motion = String(motion || "IDLE").toUpperCase();
  lift = String(lift || "UNKNOWN").toUpperCase();
  darkcover = String(darkcover || "UNKNOWN").toUpperCase();

  if (motion === "ERROR") {
    fillClass = "tc-sector-error";
    overlayText = "ERROR";
  } else if (motion === "MOVING") {
    fillClass = "tc-sector-moving";
    overlayText = "MOVING";
  } else if (lift === "UP") {
    fillClass = "tc-sector-closed";
    overlayText = "TELECOVER OFF";
  } else if (darkcover === "CLOSED") {
    fillClass = "tc-sector-dark";
  } else if (darkcover === "OPEN" && ["N", "E", "S", "W"].indexOf(position) !== -1) {
    fillClass = "tc-sector-closed";
  }

  Object.keys(sectors).forEach(function(key) {
    var sector = sectors[key];
    if (!sector) {
      return;
    }
    sector.setAttribute(
      "class",
      "tc-sector-border " +
      (fillClass === "tc-sector-closed" && darkcover === "OPEN" && position === key ? "tc-sector-open" : fillClass)
    );
  });

  if (plate) {
    plate.classList.toggle("tc-plate-off", lift === "UP" && motion !== "ERROR" && motion !== "MOVING");
  }
  if (overlay) {
    overlay.textContent = overlayText;
    overlay.classList.toggle("d-none", !overlayText);
  }
}

function updateTelecoverPlot(position, rawTrace) {
  var plot = document.getElementById("plotly-telecover-raw");
  if (!plot || !Array.isArray(rawTrace) || !rawTrace.length) {
    return;
  }

  position = String(position || "UNKNOWN").toUpperCase();
  Plotly.addTraces(plot, {
    x: rawTrace.map(function(_, index) { return index; }),
    y: rawTrace,
    mode: "lines",
    name: position,
    line: {color: telecoverTraceColors[position] || "#6c757d"}
  });
}

function resizeTelecoverPlot() {
  var plot = document.getElementById("plotly-telecover-raw");
  if (plot) {
    Plotly.Plots.resize(plot);
  }
}

document.addEventListener("DOMContentLoaded", function() {
  var figure = window.telecoverInitialPlot || {data: [], layout: {}};
  var layout = Object.assign({}, figure.layout || {}, {
    autosize: true,
    title: null,
    margin: {t: 32, r: 24, b: 56, l: 64},
    xaxis: Object.assign({}, (figure.layout || {}).xaxis, {title: "Bin"}),
    yaxis: Object.assign({}, (figure.layout || {}).yaxis, {title: "Raw signal"})
  });
  delete layout.width;
  delete layout.height;

  Plotly.newPlot(
    "plotly-telecover-raw",
    figure.data || [],
    layout,
    {responsive: true, displaylogo: false}
  );

  if ("ResizeObserver" in window) {
    var telecoverResizeObserver = new ResizeObserver(function() {
      window.requestAnimationFrame(resizeTelecoverPlot);
    });
    telecoverResizeObserver.observe(document.getElementById("plotly-telecover-raw"));
  }

  window.addEventListener("resize", resizeTelecoverPlot);
  document.addEventListener("click", function(event) {
    if (event.target.closest('[data-widget="pushmenu"]')) {
      setTimeout(resizeTelecoverPlot, 350);
    }
  });

  updateTelecoverStatus(telecoverCurrentStatus);
});
