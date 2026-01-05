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

## Directorios relevantes
- `inifiles/`: aquí se guardan los INI cargados desde la UI (`acquis.ini`, `globalinfo.ini`).
- `acquisdata/`: mediciones adquiridas en JSON (se crea automáticamente si no existe).
- `sounding/`: descargas de radiosondeo solicitadas desde la interfaz.
- `utils/`: utilidades de ploteo (`utils/plotly_plot.py`) y manejo de radiosondeos (`utils/sounding.py`).
- `lidarcontroller/`: lógica de señal (corrección de rango, Rayleigh-fit) y controladores Licel/láser.

## Notas adicionales
- Los valores por defecto (IP, puerto, rangos, parámetros de ajuste) se cargan desde `globalconfig` en `run.py` y pueden modificarse en la UI.
- No se incluyen tests automatizados; se recomienda validar conectividad con el hardware y revisar la salida en consola al ajustar parámetros o descargar radiosondeos.
- El modo de autoalineación está en desarrollo

## Referencias

- Verstraeten Portomeñe, F. *Sistema de adquisición y alineación de equipos LiDAR del Servicio Meteorológico Nacional*. [Tesis de grado, FIUBA](https://bibliotecadigital.fi.uba.ar/items/show/19341).
- Redes: SAVERNet, LALINET.
