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
