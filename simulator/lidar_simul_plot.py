"""Visualiza mediciones guardadas en ``simulator/data``.

Muestra la senal raw y la senal corregida en rango para todos los canales.
La correccion elimina bins de offset, calcula el bias sobre la cola y aplica
``(senal - bias) * rango**2``.

Uso:
    python simulator/lidar_simul_plot.py
    python simulator/lidar_simul_plot.py simulator/data/lidar_simul_5.json
    python simulator/lidar_simul_plot.py --channel 0

Los argumentos ``--bin-offset`` y ``--bias-start`` permiten modificar los
valores usados por defecto. Cada grafico tiene zoom y autoescala independientes.
"""

import argparse
import json
from pathlib import Path
from statistics import fmean

import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots


BIN_SIZE_M = 7.5
DEFAULT_FILE = Path(__file__).resolve().parent / "data" / "lidar_simul_0.json"
DEFAULT_BIN_OFFSET = 10
DEFAULT_BIAS_START_M = 22500.0

# Ajusta el eje Y a los puntos visibles despues de cada zoom horizontal.
AUTOSCALE_Y_SCRIPT = """
const graph = document.getElementById('{plot_id}');
let updatingY = false;

graph.on('plotly_relayout', (changes) => {
    if (updatingY) return;

    const axes = [
        {xLayout: 'xaxis', yLayout: 'yaxis', xTrace: 'x', yTrace: 'y'},
        {xLayout: 'xaxis2', yLayout: 'yaxis2', xTrace: 'x2', yTrace: 'y2'}
    ];
    const update = {};

    axes.forEach((axis) => {
        const rangeStart = changes[`${axis.xLayout}.range[0]`];
        const rangeEnd = changes[`${axis.xLayout}.range[1]`];
        const reset = changes[`${axis.xLayout}.autorange`];

        if (reset === true) {
            update[`${axis.yLayout}.autorange`] = true;
            return;
        }
        if (rangeStart === undefined || rangeEnd === undefined) return;

        const visibleY = [];
        graph.data.forEach((trace) => {
            const traceX = trace.xaxis || 'x';
            const traceY = trace.yaxis || 'y';
            if (traceX !== axis.xTrace || traceY !== axis.yTrace) return;

            trace.x.forEach((x, index) => {
                const y = trace.y[index];
                if (x >= rangeStart && x <= rangeEnd && Number.isFinite(y)) {
                    visibleY.push(y);
                }
            });
        });
        if (!visibleY.length) return;

        let minimum = Math.min(...visibleY);
        let maximum = Math.max(...visibleY);
        const padding = Math.max((maximum - minimum) * 0.05, 1e-12);
        update[`${axis.yLayout}.range`] = [minimum - padding, maximum + padding];
        update[`${axis.yLayout}.autorange`] = false;
    });

    if (Object.keys(update).length) {
        updatingY = true;
        Plotly.relayout(graph, update).finally(() => {
            updatingY = false;
        });
    }
});
"""


def load_recording(path):
    # Carga una medicion completa desde JSON.
    with path.open("r", encoding="utf-8") as recording_file:
        recording = json.load(recording_file)

    # Verifica que el archivo contenga canales.
    if not isinstance(recording, dict) or not recording:
        raise ValueError(f"{path} no contiene canales")

    return recording


def select_channels(recording, channel):
    # Sin seleccion explicita se muestran todos los canales.
    if channel is None:
        return sorted(recording, key=lambda value: int(value))

    # Rechaza canales inexistentes.
    if channel not in recording:
        available = ", ".join(sorted(recording, key=lambda value: int(value)))
        raise ValueError(
            f"El canal {channel} no existe. Canales disponibles: {available}"
        )

    return [channel]


def range_correction(raw, bin_offset, bias_start_m):
    # Valida el desplazamiento inicial.
    if bin_offset < 0:
        raise ValueError("El offset de bins no puede ser negativo")

    # Reproduce el bin cero agregado por lidarSignal.
    signal = [0.0, *raw]
    if bin_offset >= len(signal):
        raise ValueError(
            f"El offset de {bin_offset} bins elimina toda la senal"
        )

    # Elimina los bins afectados por el offset temporal.
    signal = signal[bin_offset:]

    # Convierte el indice de cada bin a metros.
    range_m = [index * BIN_SIZE_M for index in range(len(signal))]

    # Calcula el bias usando la cola de la senal.
    bias_start_bin = int(bias_start_m / BIN_SIZE_M)
    bias_start_bin = min(max(0, bias_start_bin), len(signal) - 1)
    bias = fmean(signal[bias_start_bin:])

    # Quita el bias y aplica la correccion cuadratica.
    corrected = [
        (value - bias) * distance**2
        for value, distance in zip(signal, range_m)
    ]

    return range_m, corrected, bias


def build_figure(
    recording,
    channels,
    source,
    bin_offset=DEFAULT_BIN_OFFSET,
    bias_start_m=DEFAULT_BIAS_START_M,
):
    # Crea visualizadores con zoom independiente.
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.08,
        subplot_titles=("Senal raw", "Senal corregida en rango"),
    )

    for channel in channels:
        # Lee y valida la senal medida.
        channel_data = recording[channel]
        raw = channel_data["data_mv"]
        declared_bins = int(channel_data.get("bins", len(raw)))

        if declared_bins != len(raw):
            raise ValueError(
                f"Canal {channel}: declara {declared_bins} bins "
                f"pero contiene {len(raw)} muestras"
            )

        # Procesa cada canal de forma independiente.
        raw_range_m = [index * BIN_SIZE_M for index in range(len(raw))]
        range_m, range_corrected, bias = range_correction(
            raw,
            bin_offset,
            bias_start_m,
        )
        trace_name = f"Canal {channel}"

        # Agrega la senal original.
        figure.add_trace(
            go.Scattergl(
                x=raw_range_m,
                y=raw,
                mode="lines",
                name=trace_name,
                legendgroup=channel,
                customdata=[bias] * len(raw),
                hovertemplate=(
                    "Rango: %{x:.1f} m<br>"
                    "Raw: %{y:.6g} mV<br>"
                    f"Bias: {bias:.6g} mV<extra>{trace_name}</extra>"
                ),
            ),
            row=1,
            col=1,
        )

        # Agrega la senal corregida en rango.
        figure.add_trace(
            go.Scattergl(
                x=range_m,
                y=range_corrected,
                mode="lines",
                name=trace_name,
                legendgroup=channel,
                showlegend=False,
            ),
            row=2,
            col=1,
        )

    figure.update_yaxes(title_text="Senal [mV]", row=1, col=1)
    figure.update_yaxes(title_text="Senal x rango^2 [mV m^2]", row=2, col=1)
    figure.update_xaxes(title_text="Rango [m]", row=1, col=1)
    figure.update_xaxes(title_text="Rango [m]", row=2, col=1)
    figure.update_layout(
        title=f"Medicion LiDAR: {source.name}",
        height=850,
        hovermode="x unified",
        template="plotly_white",
        meta={
            "bin_offset": bin_offset,
            "bias_start_m": bias_start_m,
        },
    )

    return figure


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Grafica las senales raw y su correccion basica por rango "
            "(senal x rango^2)."
        )
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        default=DEFAULT_FILE,
        help=f"archivo lidar_simul_*.json (default: {DEFAULT_FILE})",
    )
    parser.add_argument(
        "--channel",
        help="canal a mostrar; si se omite se muestran todos",
    )
    parser.add_argument(
        "--bin-offset",
        type=int,
        default=DEFAULT_BIN_OFFSET,
        help=f"bins iniciales a descartar (default: {DEFAULT_BIN_OFFSET})",
    )
    parser.add_argument(
        "--bias-start",
        type=float,
        default=DEFAULT_BIAS_START_M,
        metavar="METROS",
        help=(
            "rango desde el cual se promedia el bias hasta el final "
            f"(default: {DEFAULT_BIAS_START_M:g})"
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    recording = load_recording(args.file)
    channels = select_channels(recording, args.channel)
    figure = build_figure(
        recording,
        channels,
        args.file,
        args.bin_offset,
        args.bias_start,
    )

    print(
        f"{args.file}: {len(channels)} canal(es), "
        f"{len(recording[channels[0]]['data_mv'])} bins, "
        f"offset {args.bin_offset} bins, bias desde {args.bias_start:g} m"
    )

    # Agrega el autoajuste al renderer activo de Plotly.
    renderer_names = pio.renderers.default.split("+")
    for renderer_name in renderer_names:
        renderer = pio.renderers[renderer_name]
        if hasattr(renderer, "post_script"):
            renderer.post_script = AUTOSCALE_Y_SCRIPT

    # Muestra la figura sin generar archivos.
    figure.show()


if __name__ == "__main__":
    main()
