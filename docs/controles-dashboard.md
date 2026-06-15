# Controles y estados del dashboard

Esta guia resume el comportamiento de navegacion, conexion Licel y graficos
interactivos del dashboard.

## Barra superior

La barra superior permanece fija mientras se desplaza el contenido central.
El modo activo se muestra con un boton solido:

- `Alignment Mode`
- `Acquisition Mode`
- `Autoalignment Mode`

El estado Licel aparece encima del estado del laser:

| Estado | Color | Significado |
| --- | --- | --- |
| `Licel disconnected` | Rojo | No existe una conexion TCP activa |
| `Licel Connected` | Verde | La conexion esta lista |
| `Licel Acquiring` | Naranja | Hay una adquisicion en curso |

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
