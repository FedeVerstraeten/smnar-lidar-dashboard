# SMNAR LiDAR Dashboard

**Sistema de adquisición y alineación de equipos LiDAR del Servicio Meteorológico Nacional (SMN)**

Este software asiste al operador en el procedimiento de alineación láser–telescopio de sistemas LiDAR atmosféricos, utilizando análisis en tiempo real mediante el método **Rayleigh-Fit** y cuantificación con el **coeficiente de correlación de Pearson**.

Se desarrolló como parte de la tesis de grado en Ingeniería Electrónica en la **Facultad de Ingeniería de la UBA** y fue implementado en el marco de la red **SAVERNet/LALINET**.

## Características principales

- **Adquisición en vivo** de señales LiDAR desde sistemas Licel.
- Procesamiento de señal y corrección en rango.
- Visualización interactiva (modos *Alignment* y *Acquisition*).
- Cálculo de Rayleigh-Fit y coeficiente de Pearson.
- Control remoto del láser y periféricos.
- Guardado de datos en **JSON** y **NetCDF (CF compliant)** (PENDIENTE).
- Compatible con operación manual, semiautomática y automática (EN DESARROLLO).
- Integración con sistemas de alineación motorizados (motores paso a paso) (EN DESARROLLO).
- Integración opcional con datos de radiosondeos.


## Funcionalidades

- Modos `Alignment` y `Acquisition` accesibles desde la barra superior.
- Control de TR Licel (canal, tiempo de adquisición, bin offset y rango de bias) y disparo `START/STOP/ONESHOT`.
- Visualización interactiva con Plotly: señal cruda, señal corregida por rango y coeficiente de correlación (RMS).
- Ajuste Rayleigh (temperatura, presión, MASL, longitud de onda, rango de ajuste) y suavizado del ruido.
- Configuración TCP/IP para la controladora Licel y control del láser por puerto serie.
- Carga de archivos `acquis.ini` y `globalinfo.ini` desde la UI; guardado de adquisiciones en `acquisdata/` en formato JSON.
- Descarga de radiosondeos (Universidad de Wyoming) o uso del modelo atmosférico estándar de EE.UU. para perfilar la atmósfera.

## Requisitos

- Python 3.8+ (probado con 3.8.10).
- Dependencias en `requirements.txt` (Flask, Plotly, SciPy, NumPy, pandas, pyserial, python-dotenv).
- Acceso al hardware correspondiente: Licel TR en la IP/puerto configurados (por defecto `10.49.234.234:2055`) y, si se usa, láser conectado al puerto serie definido (`COM3` por defecto).
- Opcional: conexión a internet para descargar radiosondeos.

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/FedeVerstraeten/smnar-lidar-dashboard.git
cd smnar-lidar-dashboard
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python3 -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuración
- Crear un archivo `.env` a partir de `.env.example`.
- Ajustar parámetros de adquisición y alineación desde archivos INI compatibles con Licel.

### 4. Ejecutar
```bash
flask run
# o
python run.py
```

## Uso de la interfaz
- **Alignment Mode (`/`):** ajusta parámetros del TR (canal, tiempo de adquisición, offset y rango de bias), lanza adquisiciones (`START/STOP/ONESHOT`), define límites de gráficos, nivel de suavizado y parámetros del Rayleigh-fit. Muestra la señal cruda, la señal corregida por rango y la correlación.
- **Acquisition Mode (`/acquisition`):** requiere cargar `acquis.ini` y `globalinfo.ini` desde el menú lateral (`Load INI Files`). Permite disparos periódicos según `acq_time` y `period_time`, generando archivos `acquisdata/lidar_<timestamp>.json` con las trazas de los TR definidos en el INI.
- **TCP/IP:** actualiza IP y puerto de la controladora Licel desde la barra lateral.
- **Láser:** inicia/detiene el láser en el puerto serie configurado.
- **Sounding:** descarga radiosondeos por estación/región/fecha o usa el modelo atmosférico estándar; los archivos se guardan en `sounding/`.

## Simuladores de hardware

Documentación relacionada:

- [`docs/simuladores.md`](docs/simuladores.md): ejecución, conexiones fake y tests.
- [`docs/controles-dashboard.md`](docs/controles-dashboard.md): estados Licel,
  controles de conexión y autoescala de gráficos.

La rama `lidar-simulator` incluye simuladores independientes para probar el
dashboard sin conectar el hardware:

```bash
# Controlador de motores GRBL (Linux/WSL)
python simulator/grbl_fake_serial.py

# Controlador Ethernet Licel
python simulator/licel_fake_tcp.py

# Láser Continuum Surelite II (Linux/WSL)
python simulator/lasersurelite_fake_serial.py
```

El simulador Licel escucha por defecto en `127.0.0.1:2055`. Lee
automáticamente las adquisiciones reales
`simulator/data/lidar_simul_*.json`, elige una
captura aleatoria con cada comando `START`/`MSTART` y la entrega como datos binarios
`LSW`/`MSW`. Para canales que no aparecen en la captura genera una señal
sintética.

Para usarlo, iniciar `simulator/licel_fake_tcp.py` y configurar la conexión
TCP/IP del dashboard con IP `127.0.0.1` y puerto `2055`.

El simulador Surelite crea el puerto serie virtual `/tmp/laser-surelite-sim`.
Configurar ese path como puerto del láser en el dashboard. Emula los comandos
RS232 del equipo a 9600 baud y formato 8N1.

Las pruebas automatizadas de los simuladores y el notebook del banco de
pruebas del motor están centralizados en `tests/`:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Directorios relevantes
- `inifiles/`: aquí se guardan los INI cargados desde la UI (`acquis.ini`, `globalinfo.ini`).
- `acquisdata/`: mediciones adquiridas en JSON (se crea automáticamente si no existe).
- `simulator/`: scripts de simulación y visor de mediciones LiDAR.
- `simulator/data/`: adquisiciones reales usadas por el simulador TCP Licel.
- `sounding/`: descargas de radiosondeo solicitadas desde la interfaz.
- `utils/`: utilidades de ploteo (`utils/plotly_plot.py`) y manejo de radiosondeos (`utils/sounding.py`).
- `lidarcontroller/`: lógica de señal (corrección de rango, Rayleigh-fit) y controladores Licel/láser.

## Notas adicionales
- Los valores por defecto (IP, puerto, rangos, parámetros de ajuste) se cargan desde `globalconfig` en `run.py` y pueden modificarse en la UI.
- Los tests automatizados están en `tests/` y se ejecutan con `unittest discover`.
- El modo de autoalineación está en desarrollo

## Referencias

- Verstraeten Portomeñe, F. *Sistema de adquisición y alineación de equipos LiDAR del Servicio Meteorológico Nacional*. [Tesis de grado, FIUBA](https://bibliotecadigital.fi.uba.ar/items/show/19341).
- Redes: SAVERNet, LALINET.
