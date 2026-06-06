# Simuladores de hardware

Esta guía describe cómo ejecutar y usar los simuladores incluidos en la rama
`lidar-simulator`. Permiten probar el dashboard sin conectar el controlador de
motores GRBL ni el controlador Ethernet Licel.

## Componentes

| Componente | Archivo | Conexión simulada |
| --- | --- | --- |
| Controlador de motores GRBL | `grbl_fake_serial.py` | Puerto serie virtual PTY |
| Controlador Licel | `licel_fake_tcp.py` | Servidor TCP/IP |
| Mediciones LiDAR | `simul/lidar_simul_*.json` | Datos binarios Licel `LSW`/`MSW` |
| Tests automatizados | `tests/test_*.py` | Conexiones locales y lógica de protocolo |
| Banco de prueba del motor | `tests/banco_prueba_motor_controller.ipynb` | Pruebas interactivas |

Los simuladores son procesos independientes del dashboard. Deben iniciarse
antes de usar los controles correspondientes en la interfaz.

## Simulador GRBL

### Funcionamiento

`grbl_fake_serial.py` crea un pseudo-terminal y publica el enlace
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
python grbl_fake_serial.py
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

## Simulador Licel

### Funcionamiento

`licel_fake_tcp.py` crea un servidor TCP compatible con
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

El directorio `simul/` contiene 33 adquisiciones reales exportadas por el
módulo Acquisition:

```text
simul/lidar_simul_0.json
...
simul/lidar_simul_32.json
```

Con cada comando `START` o `MSTART`, el simulador selecciona la siguiente
captura y asigna sus canales a los transient recorders correspondientes. Al
llegar al último archivo vuelve al primero.

Los valores `data_mv` se convierten de nuevo a cuentas ADC y después se
codifican como palabras de 16 bits `LSW` y `MSW`. De esta forma
`licelController.getAnalogSignalmV()` reconstruye la señal pasando por el mismo
flujo de combinación, normalización y escalado usado con el hardware.

Si una captura no contiene el canal solicitado, el simulador genera una señal
sintética con fondo, decaimiento y un pico LiDAR.

### Ejecución

```bash
python licel_fake_tcp.py
```

Configurar en la sección TCP/IP del dashboard:

```text
IP: 127.0.0.1
Puerto: 2055
```

Opciones disponibles:

```bash
python licel_fake_tcp.py --help
python licel_fake_tcp.py --host 127.0.0.1 --port 2055
python licel_fake_tcp.py --devices 0-3
python licel_fake_tcp.py --shot-rate 30
python licel_fake_tcp.py --data-dir simul
```

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

En Linux o WSL se pueden abrir tres terminales:

Terminal 1:

```bash
python grbl_fake_serial.py
```

Terminal 2:

```bash
python licel_fake_tcp.py
```

Terminal 3:

```bash
python run.py
```

En el dashboard configurar:

- Motor: `/tmp/grbl-sim`.
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

Comprobar que `licel_fake_tcp.py` esté ejecutándose y que el dashboard use
`127.0.0.1:2055`. Verificar también que el puerto no esté ocupado por otro
proceso.

### El dashboard no abre `/tmp/grbl-sim`

Comprobar que el simulador GRBL siga activo. El enlace se elimina al cerrar el
proceso. Si el enlace no pudo crearse, usar el `/dev/pts/...` informado al
inicio.

### No aparecen las mediciones reales

Comprobar que `--data-dir` apunte al directorio `simul/`. Al comenzar una
adquisición debe aparecer en consola:

```text
Using recorded acquisition: lidar_simul_N.json
```

### El puerto 2055 está ocupado

Iniciar el simulador en otro puerto:

```bash
python licel_fake_tcp.py --port 12055
```

Configurar el mismo puerto en el dashboard.
