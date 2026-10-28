# Templates INI de Licel

Estos archivos se basan en los INI proporcionados para `LidarAEP`. Usan
`Location=LidarSMN` y `working_directory=acquidata` como valores genericos.
Conservan las demas secciones, claves, valores y comas decimales originales.
Los comentarios agregados identifican su uso como templates; las coordenadas y
los parametros instrumentales no se consideran una configuracion universal.

- `acquis.ini`: configuracion de TR0 a TR3 y seccion `[Acquis]`.
- `globalinfo.ini`: sitio, directorio de ejemplo, prefijo y parametros del laser.

## Carga desde el dashboard

1. Abrir **Alignment** y desplegar **Load INI files** en el menu lateral.
   El mismo formulario existe en Acquisition, si se puede acceder a ese modo.
2. Seleccionar `acquis.ini` en **Acquis file** y `globalinfo.ini` en
   **Global Info file**. Para otra instalacion, editar previamente copias de
   los templates con los datos del sitio y equipo correspondientes.
3. Pulsar **Load config** y volver al dashboard.

El servidor guarda los archivos con nombres fijos, independientemente de sus
nombres de origen:

```text
inifiles/acquis.ini
inifiles/globalinfo.ini
```

Tambien pueden copiarse manualmente con esos nombres a `inifiles/` antes de
iniciar la aplicacion. Al arrancar, el codigo intenta leerlos si ambos existen.
No hay copia automatica desde esta carpeta de templates. Se mantiene la
condicion actual de acceso a Acquisition; su revision queda pendiente.

`config-templates/` conserva los ejemplos en Git. `inifiles/` sigue siendo el
directorio operativo ignorado por Git: la carga actual desde la interfaz
elimina su contenido antes de guardar los nuevos archivos. Por eso no se
almacenan los templates alli.

## Sitio y parametros del template

| Seccion / clave | Valor del template | Interpretacion |
| --- | --- | --- |
| `global_info.Location` | `LidarSMN` | Identificador generico del sitio. |
| `global_info.Longitude` | `-58,417126` | Longitud: -58.417126 grados. |
| `global_info.Latitude` | `-34,564120` | Latitud: -34.564120 grados. |
| `global_info.Height_asl` | `10,000000` | Altitud declarada sobre el nivel del mar: 10 m. |
| `global_info.working_directory` | `acquidata` | Directorio generico solicitado para el template. |
| `global_info.first_letter` | `a` | Prefijo del ejemplo original; convencion SMN pendiente de confirmar. |
| `global_info.frequency1` | `30,000000` | Frecuencia declarada del laser 1: 30 Hz. |
| `global_info.frequency2` | `0,000000` | Frecuencia declarada del laser 2: 0 Hz. |
| `global_info_Laser1.Laser1_Wavelength0` | `532,000000` | Longitud de onda declarada para el laser 1: 532 nm. |

Salvo el nombre y el directorio, los valores se mantienen tal como llegaron,
sin verificarlos contra el sitio fisico. Antes de usarlos para exportaciones,
confirmar coordenadas, referencia de altitud, parametros del laser y
convenciones del formato.

La configuracion de adquisicion contiene cuatro canales analogicos A de 4092
bins: TR0 a 355 nm, TR1 y TR2 a 532 nm (polarizacion codificada como 0 y 1), y
TR3 a 1064 nm. Declara `Range=0`, `Discriminator=8`, `SamplingRate=20,000000`
y `Records=300`. No se modifica su significado ni se supone que todos estos
campos sean aplicados por el dashboard actual.

## Adaptacion de la metadata a una instalacion

- `Location`: el template usa `LidarSMN`; al configurar una instalacion real,
  usar el identificador oficial y estable del sitio/equipo.
- `Longitude`, `Latitude`, `Height_asl`: usar la ubicacion y altitud reales del
  instrumento, confirmando la referencia geodesica. No reemplazarlas por la
  ubicacion del operador o del servidor.
- `working_directory`: el template usa `acquidata`, tal como fue solicitado.
  Hoy esta clave no controla el guardado del dashboard, que sigue usando
  `APP_ROOT/acquisdata/` directamente. Unificar los directorios requiere un
  cambio posterior en el servicio de almacenamiento.
- `first_letter`: acordar el prefijo con la convencion de nombres Licel del SMN.
- Frecuencias, longitudes de onda y parametros de los TR: confirmar contra el
  equipo y sus canales; conservar estos valores solo cuando correspondan.

Los templates no se activan automaticamente ni modifican los parametros
instrumentales recibidos.
`globalinfo.ini` se carga en memoria, pero actualmente el dashboard no utiliza
sus campos para completar los JSON ni para configurar los parametros del
Rayleigh-fit.
