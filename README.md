# SMNAR LiDAR Dashboard

**Sistema de adquisición y alineación de equipos LiDAR del Servicio Meteorológico Nacional (SMN)**

Este software asiste al operador en el procedimiento de alineación láser–telescopio de sistemas LiDAR atmosféricos, utilizando análisis en tiempo real mediante el método **Rayleigh-Fit** y cuantificación con el **coeficiente de correlación de Pearson**.

Se desarrolló como parte de la tesis de grado en Ingeniería Electrónica en la **Facultad de Ingeniería de la UBA** y fue implementado en el marco de la red **SAVERNet/LALINET**.

## Características principales

- **Adquisición en vivo** de señales LiDAR desde sistemas Licel.
- Procesamiento de señal y corrección en rango.
- Visualización interactiva en modos *Alignment*, *Acquisition* y
  *Autoalignment*.
- Cálculo de Rayleigh-Fit y coeficiente de Pearson.
- Control remoto de Licel, láser Continuum Surelite II y motores GRBL.
- Simuladores de hardware para pruebas sin conectar los equipos físicos.
- Guardado de datos en **JSON** y **NetCDF (CF compliant)** (PENDIENTE).
- Compatible con operación manual, semiautomática y automática (EN DESARROLLO).
- Integración con sistemas de alineación motorizados (motores paso a paso) (EN DESARROLLO).
- Integración opcional con datos de radiosondeos.

## Estructura del repositorio

```text
smnar-lidar-dashboard/
├── docs/                       # Guías de uso, simuladores y operación
├── lidarcontroller/            # Controladores Licel, láser, motor y señal LiDAR
├── simulator/
│   ├── data/                   # Mediciones reales usadas por el simulador Licel
│   ├── grbl_fake_serial.py     # Simulador serie del controlador GRBL
│   ├── lasersurelite_fake_serial.py
│   ├── licel_fake_tcp.py       # Simulador TCP/IP del controlador Licel
│   └── lidar_simul_plot.py     # Visor de mediciones raw y corregidas en rango
├── static/js/                  # Lógica de controles y gráficos del frontend
├── templates/                  # Vistas Alignment, Acquisition y Autoalignment
├── tests/                      # Tests automatizados y banco de prueba del motor
├── utils/                      # Gráficos Plotly y utilidades de radiosondeo
├── config.py                   # Configuración de Flask
├── run.py                      # Aplicación y endpoints del dashboard
├── requirements.txt            # Dependencias Python
└── environment.yml             # Entorno Conda
```

## Directorios relevantes

- `lidarcontroller/`: adquisición, procesamiento de señal y control de Licel,
  Surelite II y motores.
- `simulator/`: simuladores independientes de Licel, GRBL y Surelite, además
  del visor de mediciones.
- `simulator/data/`: 33 adquisiciones reales `lidar_simul_*.json` usadas por
  el simulador TCP Licel.
- `templates/` y `static/js/`: interfaz, controles de hardware y gráficos.
- `tests/`: tests automatizados de señal y simuladores, más el notebook del
  banco de prueba del motor.
- `docs/`: documentación de simuladores, conexiones fake y controles del
  dashboard.
- `utils/`: generación de gráficos Plotly y descarga de radiosondeos.
- `inifiles/`: archivos `acquis.ini` y `globalinfo.ini` cargados desde la UI;
  puede crearse durante la operación.
- `acquisdata/`: mediciones JSON generadas por Acquisition Mode; se crea al
  realizar adquisiciones.
- `sounding/`: radiosondeos descargados desde la interfaz; se crea cuando se
  solicitan datos.

## Funcionalidades

- Modos `Alignment`, `Acquisition` y `Autoalignment` accesibles desde una barra
  superior fija, con identificación visual del modo activo.
- Conexión y desconexión TCP/IP persistente con Licel, validación de IP/puerto
  e indicadores de estado desconectado, conectado y adquiriendo.
- Bloqueo de `START`, `STOP` y `SINGLE SHOT` cuando Licel está desconectado,
  con protección equivalente en el backend.
- Control de TR Licel: canal, tiempo de adquisición, bin offset, rango de bias
  y adquisiciones simples o periódicas.
- Visualización Plotly de señal cruda, señal corregida en rango y coeficiente
  de Pearson, con autoescala vertical según el rango visible al hacer zoom.
- Ajuste Rayleigh (temperatura, presión, MASL, longitud de onda, rango de ajuste) y suavizado del ruido.
- Conexión persistente y control serie del láser Continuum Surelite II, con
  estado, encendido, apagado y consulta del contador de disparos.
- Control de motores GRBL y flujo de Autoalignment con configuración de grilla,
  pasos, patrón, velocidad y gestión del escaneo.
- Carga de archivos `acquis.ini` y `globalinfo.ini` desde la UI; guardado de adquisiciones en `acquisdata/` en formato JSON.
- Descarga de radiosondeos (Universidad de Wyoming) o uso del modelo atmosférico estándar de EE.UU. para perfilar la atmósfera.
- Simuladores locales para Licel, GRBL y Surelite II, alimentados con mediciones
  reales o señales sintéticas.
- Tests automatizados para procesamiento de señal y protocolos simulados.

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
- Crear un archivo `.env` con `FLASK_APP`, `FLASK_ENV`, `SECRET_KEY` y,
  opcionalmente, `COMPRESSOR_DEBUG`.
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
- **Autoalignment Mode (`/autoalignment`):** configura y ejecuta recorridos de
  alineación motorizada, mostrando el progreso y las señales adquiridas.
- **TCP/IP:** configura IP y puerto, conecta o desconecta Licel y habilita las
  adquisiciones únicamente cuando la conexión está establecida.
- **Láser:** conecta el puerto serie, inicia o detiene el Surelite II y consulta
  su contador de disparos.
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

## Notas adicionales
- Los valores por defecto (IP, puerto, rangos, parámetros de ajuste) se cargan desde `globalconfig` en `run.py` y pueden modificarse en la UI.
- Los tests automatizados están en `tests/` y se ejecutan con `unittest discover`.
- El modo de autoalineación está en desarrollo

## Referencias

- Verstraeten Portomeñe, F. *Sistema de adquisición y alineación de equipos LiDAR del Servicio Meteorológico Nacional*. [Tesis de grado, FIUBA](https://bibliotecadigital.fi.uba.ar/items/show/19341).
- Redes: SAVERNet, LALINET.
