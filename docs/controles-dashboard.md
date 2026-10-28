# Controles y estados del dashboard

Esta guia resume la navegacion, las conexiones de hardware y los graficos
interactivos del dashboard.

## Barra superior

La barra superior permanece fija mientras se desplaza el contenido central.
El modo activo se muestra con un boton solido:

- `Alignment Mode`
- `Acquisition Mode`
- `Autoalignment Mode`
- `Telecover Mode`

La barra muestra indicadores de Licel, laser y la conexion compartida de
motores/Telecover:

| Estado | Color | Significado |
| --- | --- | --- |
| `Licel disconnected` | Rojo | No existe una conexion TCP activa |
| `Licel Connected` | Verde | La conexion esta lista |
| `Licel Acquiring` | Naranja | Hay una adquisicion en curso |
| `Motors / Telecover disconnected` | Rojo | El puerto serie compartido esta cerrado |
| `Motors / Telecover connected` | Verde | El puerto serie compartido esta abierto |
| `Motors / Telecover busy` | Naranja | Una operacion esta utilizando la conexion |

## Conexion Licel

La seccion `TCP/IP connection` se encuentra debajo de `Licel controls` y antes
de `Plots controls` en los tres modos.

1. Ingresar la IP y el puerto del equipo o simulador.
2. Presionar `CONNECT`.
3. Confirmar que el indicador superior cambie a verde.
4. Usar los controles de adquisicion.
5. Presionar `DISCONNECT` antes de cambiar IP o puerto.

Los campos IP y puerto permanecen editables mientras Licel esta desconectado.
El dashboard no los sobrescribe mientras el operador escribe.

Los botones `START`, `STOP` y `SINGLE SHOT` estan deshabilitados hasta establecer
la conexion. Durante una adquisicion, `START` y `SINGLE SHOT` se bloquean para
evitar solicitudes simultaneas.

Para el simulador local:

```text
IP: 127.0.0.1
Port: 2055
```

## Laser: orden y espera entre comandos

El encendido envia `ST 1`, espera **2 segundos** y envia `SH 1` para abrir el
shutter. El apagado invierte la secuencia: `SH 0`, espera **2 segundos** y
`ST 0`. Cada escritura se completa en el puerto (`flush`) antes de continuar.
La espera es configurable mediante `command_delay` del controlador y no depende
de la velocidad de respuesta del navegador. Ya existia una espera de un segundo;
se amplio para dar mas tiempo al equipo entre comandos.

## Conexion compartida de motores y Telecover

Alignment, Autoalignment y Telecover muestran el mismo bloque **Motors /
Telecover serial port**. Desde cualquiera de esos modos:

1. Ingresar el puerto de la conexion fisica compartida (por defecto `COM4`).
2. Presionar **CONNECT**. Se abre una sola conexion a 115200 baud y se esperan
   dos segundos para permitir el arranque del controlador al abrir el puerto.
3. Usar movimientos manuales, barridos o acciones de Telecover.
4. Presionar **DISCONNECT** cuando termine la operacion, antes de cambiar el
   puerto.

La conexion permanece abierta al cambiar de modo y al finalizar un movimiento,
barrido o desplazamiento a la mejor posicion. El dashboard envia los comandos
por ese mismo transporte; la redireccion interna del hardware es transparente.
Los nombres de configuracion existentes `motor_port` y `telecover_port` se
mantienen sincronizados para compatibilidad.

Sin conexion se bloquean los movimientos y el inicio de Autoalignment, tanto
en la interfaz como en el servidor. Durante una operacion se rechazan comandos
incompatibles y la desconexion; no se encolan para ejecutarlos despues. El
indicador se actualiza cada dos segundos sin consultar el hardware ni consumir
las respuestas de otra operacion. Refleja el estado del puerto abierto; no es
una verificacion de posicion o de homing.

**STOP** sigue disponible con el puerto conectado. Para Telecover envia
`TCVDetener` y evita enviar los siguientes comandos de la operacion detenida.
En un barrido de Autoalignment solicita la detencion entre puntos mediante el
servicio existente. Fuera de un barrido, el STOP del motor envia la cancelacion
de jog de GRBL.

Los fallos del puerto y las esperas de respuesta agotadas se informan como
errores y cierran la conexion para permitir reconectar. Los comandos GRBL
estandar tienen una espera maxima de dos segundos para recibir `ok` o `error`,
en lugar de esperar indefinidamente. El laser utiliza una conexion independiente
y se rechaza intentar abrir para ambos dispositivos el mismo puerto.

## JSON de Autoalignment

Se mantiene el archivo `acquisdata/autoalign_<timestamp>.json` y sus claves
`globalconfig`, `results` y `best`. Al completar el barrido o detenerlo
normalmente, `results` incluye la señal de cada punto medido, ademas de sus
posiciones e indices existentes.

| Campo por punto | Contenido |
| --- | --- |
| `data_mv` | Vector original de la captura en mV, antes del cero agregado por el procesamiento, el recorte de offset y las correcciones. |
| `channel`, `bins`, `bin_size_m` | Canal evaluado, cantidad real de muestras guardadas y resolucion de 7,5 m/bin. |
| `timestamp`, `timestamp_end` | Inicio y fin de la captura, en ISO 8601 con zona UTC explicita. |
| `pearson` | Correlacion calculada para esa señal y configuracion. |
| `signal_units`, `signal_stage` | Unidades y etapa de la señal almacenada. |
| `shots`, `input_range_mv` | Disparos informados por Licel y rango analogico utilizado (500 mV en el flujo actual). |
| `bias_mv`, `rayleigh_fit_factor`, `rms_error` | Resultados del procesamiento del punto. |
| `atmospheric_model`, `sounding_data` | Fuente atmosferica y perfil de radiosondeo utilizado, si corresponde. Las alturas del perfil estan en m, temperaturas en K y presiones en hPa. |

`globalconfig` guarda exclusivamente estas 25 claves, con los valores efectivos
del barrido:

- `channel`, `acq_time`, `bin_offset`, `max_bins`, `bias_init`, `bias_final`.
- `temperature`, `pressure`, `masl`, `wavelength`, `fit_init`, `fit_final`.
- `motor_resolution`, `motor_feed_rate`, `corr_range_init`, `corr_range_final`,
  `grid_min_resolution`.
- `scan_rows`, `scan_cols`, `scan_step_x`, `scan_step_y`, `scan_feed`,
  `scan_pattern`, `scan_centered`, `scan_reverse`.

`acq_time` esta en segundos, `temperature` en grados Celsius, `pressure` en hPa,
`wavelength` en nm y `masl`, bias y rangos de ajuste/correlacion en m. Las
velocidades `scan_feed` y `motor_feed_rate` estan en mm/min; los pasos y la
resolucion del motor, en mm. IP, puertos, opciones de Telecover y parametros
ajenos a esta lista quedan fuera del archivo de configuracion exportado.

La adquisicion y el procesamiento usan la copia de configuracion tomada al
iniciar el barrido. Las ediciones posteriores de esos parametros se aplican al
proximo barrido. El perfil atmosferico se copia al comenzar cada punto y se
almacena con esa señal.

Para reproducir el analisis, cargar `data_mv` con `lidarSignal.loadSignal`,
aplicar el offset y los parametros de `globalconfig`, y restaurar
`sounding_data` cuando se haya utilizado. No volver a recortar el offset antes
de cargar la señal. `smooth_level` queda fuera del JSON porque el suavizado se
aplica a la señal corregida que se grafica y a su factor de ajuste Rayleigh.
No modifica `data_mv` ni interviene en el calculo de Pearson, que compara la
señal raw con bias sustraido contra el perfil molecular ajustado. Puede elegirse
otro suavizado para visualizar el caso sin cambiar la señal raw ni Pearson.

`best.index` identifica su registro completo en `results`; no se duplica la
señal dentro de `best`. Las respuestas periodicas de estado mantienen los
resumenes y graficos existentes, sin retransmitir todas las capturas. Esta
ampliacion no agrega todavia una opcion de carga de casos en la interfaz ni
guardado incremental en disco ante un fallo del barrido.

## Graficos de Alignment Mode

Los tres graficos ajustan automaticamente el eje vertical cuando cambia el zoom
horizontal:

- Senal raw.
- Senal corregida en rango.
- Coeficiente de correlacion de Pearson.

El rango vertical se calcula con los puntos visibles y agrega un margen pequeno.
Al restablecer el zoom horizontal, Plotly recupera la autoescala completa.

## Proteccion del backend

Las rutas de adquisicion rechazan `START` y `SINGLE SHOT` cuando no existe una
conexion Licel. La conexion se mantiene abierta hasta que el operador presiona
`DISCONNECT`.

Los intentos fallidos de conexion cierran y descartan el socket, permitiendo
corregir IP o puerto y volver a intentar.
