# Simuladores de hardware

Esta guía describe cómo ejecutar y usar los simuladores incluidos en la rama
`lidar-simulator`. Permiten probar el dashboard sin conectar el controlador de
motores GRBL, el controlador Ethernet Licel ni el láser Continuum Surelite II.

## Componentes

| Componente | Archivo | Conexión simulada |
| --- | --- | --- |
| Controlador de motores GRBL | `simulator/grbl_fake_serial.py` | Puerto serie virtual PTY |
| Láser Continuum Surelite II | `simulator/lasersurelite_fake_serial.py` | Puerto serie virtual PTY |
| Telecover Final4 | `simulator/telecover_fake_serial.py` | Puerto serie virtual PTY |
| Controlador Licel | `simulator/licel_fake_tcp.py` | Servidor TCP/IP |
| Visor de mediciones | `simulator/lidar_simul_plot.py` | Gráficos Plotly raw y RC |
| Mediciones LiDAR | `simulator/data/lidar_simul_*.json` | Datos binarios Licel `LSW`/`MSW` |
| Tests automatizados | `tests/test_*.py` | Conexiones locales y lógica de protocolo |
| Banco de prueba del motor | `tests/banco_prueba_motor_controller.ipynb` | Pruebas interactivas |

Los simuladores son procesos independientes del dashboard. Deben iniciarse
antes de usar los controles correspondientes en la interfaz.

## Simulador GRBL

### Funcionamiento

`simulator/grbl_fake_serial.py` crea un pseudo-terminal y publica el enlace
`/tmp/grbl-sim`. El dashboard puede abrir ese enlace con `pyserial` como si
fuera un controlador GRBL físico.

El simulador mantiene:

- Posición de los ejes `X`, `Y` y `Z`.
- Modo de movimiento absoluto `G90` o relativo `G91`.
- Feedrate configurado.
- Estado `Idle` o `Run`.
- Límites de `-5.0` a `5.0` para cada eje.

Los movimientos que exceden esos límites quedan recortados al valor máximo o
mínimo permitido.

### Requisitos

Los módulos `pty`, `tty` y `termios` requieren un sistema compatible con
pseudo-terminales Unix:

- Linux.
- macOS.
- WSL en Windows.

El simulador no puede crear el puerto virtual ejecutándose directamente con
Python nativo de Windows.

### Ejecución

```bash
python simulator/grbl_fake_serial.py
```

Al iniciar muestra una salida similar a:

```text
Simulador GRBL iniciado.
Puerto virtual real: /dev/pts/3
Puerto recomendado para el dashboard: /tmp/grbl-sim
```

Configurar `/tmp/grbl-sim` como puerto del motor en el dashboard. Si no fue
posible crear el enlace, usar directamente el nombre `/dev/pts/...` mostrado
por el simulador.

### Comandos implementados

| Comando | Acción |
| --- | --- |
| `?` | Devuelve estado, posición y feedrate |
| `Ctrl-X` | Reinicia posición y estado |
| `$X` | Desbloquea el controlador |
| `$H` | Ejecuta homing y vuelve al origen |
| `$$` | Devuelve una configuración GRBL básica |
| `$<n>=<valor>` | Acepta cambios de configuración |
| `G90` | Selecciona coordenadas absolutas |
| `G91` | Selecciona coordenadas relativas |
| `G0` / `G1` | Ejecuta movimientos de ejes |
| `F<valor>` | Actualiza el feedrate |

También se aceptan sin acción física los comandos `G20`, `G21`, `G17`, `G94`,
`M2`, `M3` y `M5`.

## Simulador Surelite II

### Funcionamiento

`simulator/lasersurelite_fake_serial.py` crea un pseudo-terminal con el enlace
`/tmp/laser-surelite-sim`. El dashboard lo abre mediante `laserController` usando la
configuración serie del equipo: 9600 baud, 8 bits, sin paridad y 1 stop bit.

El simulador mantiene el estado de encendido, shutter, parámetros del láser,
interlocks y contador de disparos. Los comandos deben enviarse en mayúsculas,
con el formato exacto y terminados en `CR`.

### Ejecución

```bash
python simulator/lasersurelite_fake_serial.py
```

Configurar `/tmp/laser-surelite-sim` como puerto del láser en el dashboard. Al igual
que el simulador GRBL, requiere Linux, macOS o WSL.

Para simular una condición de interlock o un contador inicial:

```bash
python simulator/lasersurelite_fake_serial.py --security-code 06
python simulator/lasersurelite_fake_serial.py --shot-count 123456
```

### Comandos implementados

| Comando | Acción |
| --- | --- |
| `SS` | Ejecuta un disparo si el láser está iniciado y `PD` es `000` |
| `SE` | Devuelve el código de interlock con 2 dígitos |
| `SH 0/1` | Cierra o abre el shutter |
| `ST 0/1` | Detiene o inicia el láser |
| `QS XXX` | Configura el retardo del Q-switch |
| `RR XX.X` | Configura la tasa de repetición |
| `VA X.XX` | Configura el voltaje de la fuente |
| `PD XXX` | Configura la división de pulsos |
| `SC` | Devuelve el contador con 9 dígitos |

Sólo `SE` y `SC` generan una respuesta. Ambas son ASCII y terminan en `CR`.

Los códigos configurables para la respuesta `SE` son:

| Código | Estado |
| --- | --- |
| `00` | Operación normal |
| `01` | Surelite fuera de modo serie |
| `02` | Flujo de refrigerante interrumpido |
| `03` | Temperatura de refrigerante alta |
| `04` | Sin uso |
| `05` | Problema en el cabezal |
| `06` | Interlock externo |
| `07` | Fin de carga no detectado |
| `08` | Simmer no detectado |
| `09` | Flow switch trabado |

## Simulador Telecover

### Funcionamiento

`simulator/telecover_fake_serial.py` crea un pseudo-terminal con el enlace
`/tmp/telecover-sim`. El dashboard lo abre con `pyserial` como si fuera el
firmware `TelecoverFinal4.ino`.

El simulador mantiene:

- Home, posicion y movimiento del eje de elevacion.
- Home, posicion y movimiento del plato rotativo.
- Estado de total cover para corriente oscura.
- Contador de encoder y sensor superior simulado.

Los comandos Telecover empiezan con `TCV`. Los comandos desconocidos que no
empiezan con `TCV` se tratan como G-code reenviado a GRBL y responden `ok`.

### Ejecucion

```bash
python simulator/telecover_fake_serial.py
```

Configurar `/tmp/telecover-sim` como puerto Telecover en el dashboard. Al igual
que los otros simuladores serie, requiere Linux, macOS o WSL.

Opciones disponibles:

```bash
python simulator/telecover_fake_serial.py --help
python simulator/telecover_fake_serial.py --link /tmp/telecover-sim
python simulator/telecover_fake_serial.py --delay 0.2
python simulator/telecover_fake_serial.py --initial-lift UP
python simulator/telecover_fake_serial.py --initial-disk N
python simulator/telecover_fake_serial.py --verbose
```

Al iniciar muestra el puerto real `/dev/pts/...` y el puerto recomendado:

```text
/tmp/telecover-sim
```

### Comandos implementados

| Comando | Accion |
| --- | --- |
| `TCVHomeE` | Home del eje vertical y deja el telecover arriba |
| `TCVArriba` | Sube el telecover |
| `TCVAbajo` | Baja el telecover si se hizo home |
| `TCVDetener` | Detiene solo el eje de elevacion |
| `TCVEstado` | Devuelve el bloque textual de elevacion |
| `TCVNorte` | Inicializa o mueve el plato a Norte |
| `TCVHomeP` | Home/retorno antihorario del plato desde Norte |
| `TCVEste` | Mueve de Norte a Este |
| `TCVSur` | Mueve de Este a Sur |
| `TCVOeste` | Mueve de Sur a Oeste |
| `TCVCOI` | Cierra total cover desde Norte para corriente oscura |
| `TCVCOO` | Abre total cover y vuelve a Norte |
| `TCVEstadoPlato` | Devuelve el bloque textual del plato |

## Simulador Licel

### Funcionamiento

`simulator/licel_fake_tcp.py` crea un servidor TCP compatible con
`lidarcontroller/licelcontroller.py`. Por defecto escucha en:

```text
127.0.0.1:2055
```

El dashboard usa la misma secuencia que utilizaría con el equipo:

1. Abre la conexión TCP.
2. Selecciona uno o varios transient recorders.
3. Limpia las memorias.
4. Inicia y detiene la adquisición.
5. Consulta el estado y el número de disparos.
6. Solicita datasets binarios `LSW`, `MSW` o `PC`.

No hay una ruta especial de simulación dentro de `run.py`. El dashboard se
comunica con el servidor fake usando el protocolo normal de Licel.

### Mediciones reales

El directorio `simulator/data/` contiene 33 adquisiciones reales exportadas por el
módulo Acquisition:

```text
simulator/data/lidar_simul_0.json
...
simulator/data/lidar_simul_32.json
```

Con cada comando `START` o `MSTART`, el simulador selecciona una captura
aleatoria y asigna sus canales a los transient recorders correspondientes.

Los valores `data_mv` se convierten de nuevo a cuentas ADC y después se
codifican como palabras de 16 bits `LSW` y `MSW`. De esta forma
`licelController.getAnalogSignalmV()` reconstruye la señal pasando por el mismo
flujo de combinación, normalización y escalado usado con el hardware.

Si una captura no contiene el canal solicitado, el simulador genera una señal
sintética con fondo, decaimiento y un pico LiDAR.

### Ejecución

```bash
python simulator/licel_fake_tcp.py
```

Configurar en la sección TCP/IP del dashboard:

```text
IP: 127.0.0.1
Puerto: 2055
```

Opciones disponibles:

```bash
python simulator/licel_fake_tcp.py --help
python simulator/licel_fake_tcp.py --host 127.0.0.1 --port 2055
python simulator/licel_fake_tcp.py --devices 0-3
python simulator/licel_fake_tcp.py --shot-rate 30
python simulator/licel_fake_tcp.py --data-dir simulator/data
```

En el dashboard se debe presionar `CONNECT` antes de usar `START` o
`SINGLE SHOT`. El indicador Licel cambia de rojo a verde al conectar y a
naranja durante la adquisición. Los campos IP y puerto pueden editarse mientras
la conexión está cerrada.

Para trabajar únicamente con señales sintéticas, indicar un directorio vacío
en `--data-dir`.

### Comandos implementados

El conjunto corresponde a los comandos usados por `licelcontroller.py`:

| Comando | Acción |
| --- | --- |
| `SELECT` | Selecciona uno o varios TR |
| `RANGE` | Configura el rango de entrada |
| `THRESHOLD` | Configura el modo de threshold |
| `DISC` | Configura el discriminador |
| `CLEAR` / `MCLEAR` | Limpia uno o varios TR |
| `START` / `MSTART` | Inicia adquisición |
| `STOP` / `MSTOP` | Detiene adquisición |
| `STAT?` | Devuelve disparos y estado |
| `DATA?` | Devuelve datos binarios de 16 bits |

Las respuestas de texto terminan con `CRLF`. `DATA?` devuelve exactamente dos
bytes por bin, sin agregar texto ni `CRLF` al bloque binario.

## Uso conjunto

En Linux o WSL se pueden abrir cuatro terminales:

Terminal 1:

```bash
python simulator/grbl_fake_serial.py
```

Terminal 2:

```bash
python simulator/lasersurelite_fake_serial.py
```

Terminal 3:

```bash
python simulator/licel_fake_tcp.py
```

Terminal 4:

```bash
python run.py
```

En el dashboard configurar:

- Motor: `/tmp/grbl-sim`.
- Láser: `/tmp/laser-surelite-sim`.
- Licel: `127.0.0.1`, puerto `2055`.

Los logs de los simuladores muestran cada comando recibido con `>>` y cada
respuesta con `<<`, lo que permite seguir el intercambio durante las pruebas.

## Tests

Todos los artefactos de prueba están en `tests/`.

Ejecutar la suite completa:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

Ejecutar únicamente GRBL:

```bash
python -m unittest discover -s tests -p "test_grbl_fake_serial.py" -v
```

Ejecutar únicamente Licel:

```bash
python -m unittest discover -s tests -p "test_licel_fake_tcp.py" -v
```

Ejecutar únicamente Surelite:

```bash
python -m unittest discover -s tests -p "test_lasersurelite_fake_serial.py" -v
```

### Cobertura GRBL

Las pruebas verifican:

- Reporte de estado.
- Movimientos absolutos y relativos.
- Feedrate.
- Límites de ejes.
- Homing y soft reset.
- Unlock y configuración básica.

La lógica de comandos GRBL puede probarse en Windows. Solo la creación del PTY
requiere Linux, macOS o WSL.

### Cobertura Licel

Las pruebas verifican:

- Flujo de configuración de un TR.
- Selección y control de varios TR.
- Formato de respuestas de texto.
- Tamaño exacto de los bloques binarios.
- Lectura completa mediante `licelController`.
- Combinación `LSW`/`MSW`.
- Reconstrucción de señales grabadas en milivoltios.
- Respuesta ante comandos desconocidos.

El notebook `tests/banco_prueba_motor_controller.ipynb` permite realizar
pruebas manuales e interactivas del controlador de motores.

## Resolución de problemas

### El dashboard no conecta con Licel

Comprobar que `simulator/licel_fake_tcp.py` esté ejecutándose y que el dashboard use
`127.0.0.1:2055`. Verificar también que el puerto no esté ocupado por otro
proceso.

### El dashboard no abre `/tmp/grbl-sim`

Comprobar que el simulador GRBL siga activo. El enlace se elimina al cerrar el
proceso. Si el enlace no pudo crearse, usar el `/dev/pts/...` informado al
inicio.

### No aparecen las mediciones reales

Comprobar que `--data-dir` apunte al directorio `simulator/data/`. Al comenzar una
adquisición debe aparecer en consola:

```text
Using recorded acquisition: lidar_simul_N.json
```

### El puerto 2055 está ocupado

Iniciar el simulador en otro puerto:

```bash
python simulator/licel_fake_tcp.py --port 12055
```

Configurar el mismo puerto en el dashboard.
