# Plan de almacenamiento y exportación de datos

Fecha de inicio: 2026-10-28.
Base inspeccionada: checkout local de `main`, commit `d1df03a`.
Estado: análisis inicial completo; templates INI incorporados; cambios de
funcionamiento pendientes.

## Objetivo y alcance

Permitir guardar y descargar mediciones de Acquisition, Alignment y
Autoalignment, con selección de JSON, CSV, Licel y NetCDF. Cada formato debe
validar sus datos y metadatos requeridos antes de exportar. La compatibilidad
operativa Licel se definirá con los criterios y ejemplos del SMN que aportará
el usuario. No se considera cerrado ningún esquema de Licel o NetCDF en esta
etapa.

Telecover queda fuera de la primera entrega: su implementación actual devuelve
trazas vacías. La solución compartida deberá admitir su incorporación posterior.

## Diagnóstico del código actual

Diagnóstico inicial previo a incorporar los templates. Los avances posteriores
se registran en los ítems del plan.

| Área | Hallazgo | Referencia |
| --- | --- | --- |
| Acquisition | Guarda automáticamente JSON en el servidor, en `acquisdata/`, con timestamp, bins y señal en mV por TR. No devuelve un identificador de archivo ni ofrece una descarga implementada. | `run.py`: `acquire_multiple_licel_traces`, `licel_acquis_data`; `static/js/acquiscontrols.js` |
| Alignment | Adquiere y procesa la señal para los gráficos, sin persistir la medición. | `run.py`: `acquire_single_licel_trace`, `process_lidar_trace`, `licel_record_data` |
| Autoalignment | Guarda un JSON al finalizar o detener normalmente el barrido: configuración, posiciones, timestamps, Pearson y mejor punto. No guarda las señales por punto. Un error puede evitar el guardado final de los resultados parciales. | `run.py`: `acquire_autoalignment_point`, `save_autoalignment_results`; `lidarcontroller/autoalignment.py`: `_run` |
| Datos instrumentales | `getAnalogSignalmV` combina cuentas, calcula saturación, normaliza y convierte a mV; solo devuelve mV. Las cuentas acumuladas, saturación y disparos no forman parte del archivo actual. | `lidarcontroller/licelcontroller.py`: `getAnalogSignalmV` |
| Configuración efectiva | Se leen `Range`, `Discriminator` y `WavelengthA` del INI, pero el flujo multicanal usa un rango fijo de 500 mV y no aplica esos valores en esa función. `globalinfo.ini` se carga, sin aprovecharse para exportar metadatos. | `run.py`: `get_acquis_settings`, `acquire_multiple_licel_traces` |
| INI | No hay archivos `.ini` versionados; `inifiles/` está ignorado. La carga elimina archivos anteriores antes de validar el contenido, reutiliza parsers que pueden conservar secciones viejas y muestra éxito aunque no se complete la carga. La entrada a Acquisition solo rechaza el caso en que ambos parsers están vacíos. | `.gitignore`; `run.py`: `acquisition_mode`, `load_ini_files`; `templates/inifiles.html` |
| NetCDF | El menú es provisional: su enlace apunta a `../` con nombre de descarga `LICENSE`. No hay exportador ni dependencia específica declarada para escribir NetCDF. | `templates/acquisition.html`; `requirements.txt`; `environment.yml` |
| Integridad | Nombres de archivo con precisión de segundos y escritura directa, sin protección contra colisiones o archivos incompletos. Fechas sin zona horaria explícita. | `run.py`: funciones de adquisición y guardado; `lidarcontroller/autoalignment.py` |
| Reproducibilidad | El procesamiento agrega un cero, recorta el offset y utiliza una resolución fija de 7,5 m. Autoalignment copia la configuración al iniciar, pero la adquisición y el procesamiento consultan `globalconfig`, que puede cambiar durante el barrido. | `lidarcontroller/lidarsignal.py`; `run.py`; `lidarcontroller/autoalignment.py` |

El diagnóstico corresponde a lectura de código; no constituye validación con
hardware ni certificación de formatos.

## Plan por ítems

1. **[x] Relevar los flujos y sus faltantes.**
   Resultado: diagnóstico anterior y alcance inicial documentados.

2. **[ ] Definir el contrato de datos y la matriz de metadatos (prioridad alta).**
   Separar sesión/barrido, medición, canal y productos procesados. Identificar
   cada registro y versionar su esquema. Conservar inicio/fin con zona horaria,
   modo, configuración efectiva, unidades, bins, resolución, offset y estado de
   la captura. En Autoalignment vincular señal, posición, intento, Pearson y
   mejor punto. Diferenciar cuentas instrumentales, señal en mV sin correcciones
   y productos corregidos. Evitar duplicar grandes señales en las respuestas
   periódicas de estado.
   Cierre: esquema documentado y requisitos por formato acordados; campos SMN
   pendientes identificados explícitamente.

3. **[ ] Recuperar templates INI y corregir su carga (prioridad alta).**
   Avance 2026-10-28: templates recibidos incorporados en `config-templates/`
   como `acquis.ini` y `globalinfo.ini`, con nombre genérico `LidarSMN`,
   directorio `acquidata` y el resto de la metadata original preservada, más
   guía de carga hacia `inifiles/`. Verificada la opción **Load INI files** de
   Alignment y Acquisition por lectura de sus formularios y endpoint. No se
   modificó la condición de acceso a Acquisition ni la lógica de carga.
   Queda pendiente la validación y corrección de carga descrita a continuación.
   Agregar ejemplos versionados en un directorio independiente de los archivos
   operativos ignorados, con instrucciones y valores de ejemplo identificados.
   Validar secciones, claves, tipos, rangos y canales con parsers nuevos antes
   de reemplazar la configuración vigente. Mantener los archivos anteriores si
   la carga falla y dar mensajes concretos de error. Separar configuración
   necesaria para adquirir de metadatos necesarios para cada exportación.
   Cierre: una instalación nueva puede configurarse con ejemplos; una carga
   inválida no destruye ni mezcla la configuración anterior.

4. **[ ] Conservar datos instrumentales y verificar configuración (prioridad alta).**
   Ampliar la captura para retener cuentas acumuladas, disparos efectivos,
   saturación y parámetros aplicados junto a los mV. Revisar la normalización
   `shots_number - 2`, incluidos cero y un disparo; hoy `cycles` puede quedar sin
   definir. Contrastar parámetros INI con comandos realmente enviados. Verificar
   longitud de trazas, cero insertado, offset y resolución. Congelar la
   configuración efectiva usada por cada adquisición y barrido.
   Cierre: señales y metadatos describen la misma captura; no hace falta
   reconstruir cuentas a partir de mV para implementar Licel.

5. **[ ] Crear persistencia común y recuperar resultados parciales (prioridad alta).**
   Extraer el guardado de `run.py` a un servicio compartido. Incorporar nombres
   únicos, escrituras atómicas, organización por sesión/modo y errores visibles
   de almacenamiento. Guardar cada medición de Alignment y cada punto de
   Autoalignment antes de continuar; registrar finalización, detención, fallos
   e intentos. Conservar la relación con el resumen del barrido. Mantener
   compatibilidad de lectura con los JSON existentes y con el simulador.
   Cierre: un fallo posterior no elimina las mediciones ya confirmadas; no hay
   sobrescrituras silenciosas. No se presupone que sea necesaria una base de datos.

6. **[ ] Implementar JSON y CSV desde el registro común.**
   JSON incluirá señales y metadatos con versión de esquema. Para CSV, definir
   columnas/unidades y un archivo de metadatos o paquete asociado cuando una
   tabla no alcance. Separar resumen de barrido y perfiles completos. Rechazar
   registros inconsistentes y definir cómo representar valores no finitos.
   Cierre: exportaciones reabribles, valores y cantidades de muestras
   verificables, y lectura de los JSON históricos preservada.

7. **[ ] Implementar Licel según los criterios del SMN.**
   Definir variante, encabezados, nombres, estructura binaria, escalas y canales
   a partir de archivos reales y documentación aplicable. Mapear cada campo a su
   fuente y exigir la metadata correspondiente. Acordar cómo acompañar el
   archivo con posiciones y resultados del barrido cuando no tengan lugar en
   el formato. No presentar un cambio de extensión o una reconstrucción con
   pérdida como exportación compatible.
   Dependencias: ítems 2 a 5 y especificaciones SMN.
   Cierre: archivos aceptados por el lector o flujo operativo usado por el SMN,
   comparados con referencias conocidas.

8. **[ ] Implementar NetCDF con un esquema explícito.**
   Definir dimensiones y coordenadas para tiempo, canal, rango y puntos de
   barrido; contemplar canales con distinta cantidad de bins. Definir variables,
   unidades, atributos, valores ausentes y compresión. Acordar las convenciones
   aplicables y verificar la compatibilidad antes de declarar cumplimiento CF.
   Incorporar la dependencia elegida en los entornos soportados.
   Cierre: lectura independiente y comparación de señales, coordenadas y
   atributos con el registro fuente.

9. **[ ] Integrar selección de formato y descarga en los tres modos.**
   Compartir controles de guardado/exportación y mostrar qué formatos están
   disponibles, qué metadatos faltan y dónde se guarda cada medición. Distinguir
   guardado en el equipo servidor de descarga al navegador. Ofrecer última
   medición y selección de sesión/barrido, con descarga por punto o en paquete
   cuando corresponda. La descarga debe utilizar la captura existente sin
   disparar una nueva adquisición. Reemplazar el menú NetCDF provisional.
   Cierre: Acquisition, Alignment y Autoalignment permiten recuperar los datos
   seleccionados en los formatos implementados y válidos para esa captura.

10. **[ ] Validar el conjunto y actualizar documentación.**
    Cubrir INI inválidos y recargas, captura multicanal, pocos disparos, datos
    faltantes, cambios de configuración durante un barrido, detenciones,
    fallos parciales, colisiones y errores de escritura. Verificar lectura de
    cada formato y preservación de muestras, unidades y metadatos; usar los
    simuladores y pruebas existentes. Para Licel, agregar ejemplos SMN y
    validación externa del lector. Actualizar README y guía de operación.
    Cierre: pruebas relevantes aprobadas y limitaciones documentadas.

## Metadata: propuesta inicial a validar

Esta tabla organiza el diseño; no reemplaza la especificación de cada formato.

| Grupo | Contenido propuesto |
| --- | --- |
| Común | Identificadores, versión de esquema/software, modo, fecha/hora con zona, estado y procedencia real/simulada. |
| Instrumento y canal | Estación/equipo, TR y memoria, tipo de detección, longitud de onda, resolución, bins, offset, rango ADC y discriminador efectivos, disparos, tiempos y unidades. |
| Señal | Cuentas originales, saturación y mV sin correcciones; productos procesados opcionales y parámetros que permiten reproducirlos. |
| Alineación | Posición y referencia de coordenadas cuando estén disponibles, Pearson, intervalo Rayleigh, bias, suavizado y fuente atmosférica. |
| Barrido | Grilla, patrón, orden, punto/intento, estado, fallos y mejor posición. |
| Específico de formato | Datos de estación, geometría y encabezados que exijan Licel/SMN; dimensiones, coordenadas y atributos que se acuerden para NetCDF. |

La ausencia de un campo debe representarse explícitamente. No se completarán
metadatos instrumentales desconocidos con valores ficticios para habilitar un
formato.

## Definiciones pendientes del SMN y del flujo operativo

- Ejemplos y criterios de `acquis.ini`, `globalinfo.ini` y archivos Licel válidos;
  variante del formato y programa que debe leerlos.
- Reglas de nombres, directorios, fechas/zona horaria y separación de canales.
- Metadata obligatoria, unidades, canales analógicos/fotoconteo y geometría del
  instrumento. El flujo actual inspeccionado adquiere señales analógicas.
- Guardado manual/automático por modo, retención y alcance de la exportación:
  perfil, sesión o barrido completo. Propuesta inicial: conservar cada punto y
  ofrecer un resumen adicional de Autoalignment.
- Productos esperados en NetCDF y eventual convención o lector de destino.

Estos pendientes condicionan el cierre de los formatos específicos; el trabajo
sobre integridad, captura, INI y persistencia puede avanzar mientras se definen.

## Tareas relacionadas y seguimiento

- [x] Laser: verificar `ST 1 -> SH 1` y cierre inverso, completar cada escritura
  serie y ampliar a dos segundos la pausa entre comandos. Verificado con prueba
  de secuencia y tiempos del controlador.
- [x] Motores/Telecover: incorporar una sola conexion serie persistente,
  controles y estado compartidos, validaciones y uso de la conexion desde
  Autoalignment. Verificado con simuladores y pruebas de interfaz, concurrencia,
  desconexion y errores. La comprobacion con el hardware fisico queda pendiente.

Las mejoras independientes que solicite el usuario se registrarán como ítems
adicionales con su alcance, dependencias y validación. Se conservará este plan
como referencia del trabajo de almacenamiento y se actualizarán sus estados al
completar cada entrega.
