> Traducción al español de `docs/DEVELOPMENT_LOG.ru.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Bloodborne: primer experimento de ejecución nativa

## Tasa de frames, sonido, diagnóstico (2026-09-25)

- **FPS**: `BB_FPS=uncap` (por defecto) aplica el parche «Uncap FPS++»
  (Lance McDonald, Kyo) de `patches/Bloodborne.xml`: intervalo de flip 1 y
  pasos de simulación según el deltatime real del frame. El vblank sigue en ese caso
  la frecuencia del monitor (`BB_VBLANK_HZ=0`). `BB_FPS=60`/`90` son parches con
  paso fijo, `BB_FPS=30` es sin parches. Parches adicionales del XML:
  `BB_PATCHES="Skip Intro;Disable Motion Blur (perf increase)"`.
  `patches.py` los compila en `out/patches.bin`; las direcciones del XML son
  direcciones virtuales de PS4 (base del eboot 0x400000); el cargador las escribe en el
  offset `dirección-0x400000` después de las relocalizaciones (`--patches`).
- **Sonido**: `sceAudioOutOutput` ahora devuelve el control estrictamente una vez por
  periodo de buffer (como el hardware). Antes, las llamadas llegaban en ráfagas una vez por quantum de PipeWire
  (21 ms), el hilo de salida de FMOD se adelantaba al mezclador y reproducía mitades no escritas
  de bloques de 512 frames: un chasquido cada 10.7 ms.
- **Rendimiento del hilo de GPU** (`shadPS4:GpuCommandProcessor` es el cuello
  de botella: ~97% de un núcleo). Medición en una escena: 26.5 → 47 FPS.
  - `runtime_memory.c`: tabla de regiones bajo rwlock en lugar de un mutex
    recursivo (el hilo de GPU pasaba el 18% del tiempo esperándolo), más una caché de regiones por hilo,
    verificada con el contador de generaciones de la tabla: las consultas del núcleo de video en cada
    draw se hacen sin bloqueo.
  - `vk_scheduler.cpp`: `PopPendingOperations` en cada draw hacía un ioctl
    de sondeo del timeline semaphore; ahora solo si la cola no está vacía y no más de
    una vez cada 250 µs.
  - `fetch_shader.cpp`: el análisis del fetch shader se cachea por dirección de código con
    verificación de una copia del código.
  - `region_manager.h`: sin páginas modificadas en el rango, la protección no
    se recalcula.
  - Grabación de comandos Vulkan en un hilo aparte `bb:VkRecorder`
    (`Scheduler::Record`, los comandos y sus datos en bloques de 128 KiB; draw,
    dispatch, descriptores, barreras, copias, dynamic state, detiling).
    `CommandBuffer()` para el código no migrado se sincroniza y activa la
    grabación directa hasta el final del draw. `BB_VK_RECORD_THREAD=0`: comportamiento anterior.
  - Caché de descripciones de texturas (`ImageDesc`) por T# y flags del recurso, caché de
    `FindImage`, verificación de páginas modificadas sin bloqueo para vinculaciones
    de solo lectura, carga de datos guest de los buffers en el hilo de grabación.
  - Medición en una escena: con todas las optimizaciones 64 FPS, sin ellas 40 FPS (×1.6).
  - `BB_TOGGLE_FILE=<archivo>`: máscara de optimizaciones desactivadas, se cambia durante el
    juego (1 caché de regiones, 2 caché de fetch shaders, 4 salida temprana del seguimiento de
    páginas, 8 límite de sondeo del driver, 16 hilo de grabación, 32 caché de texturas,
    64 verificación de páginas sin bloqueo, 128 caché de FindImage, 256 carga
    de buffers en el hilo de grabación, 512 memo del tracker de barreras), para buscar
    regresiones sin reiniciar.
- **Sonido**: al arrancar Bloodborne se establece el flag `0x204E` en
  `SPRJ0005/userdata0010` (hack de rainvmaker del fork de Diegolix29): con el
  flag en cero, parte de los sonidos, por ejemplo el arma del jugador, no se reproduce.
  `BB_SOUND_HACK=0` lo desactiva.
  Profiling sin perf: con SIGUSR2 el cargador imprime RIP, `rdi` (dirección del
  mutex al esperar en futex) y la cadena de frames de pila del hilo; la biblioteca de GPU
  se compila con `-fno-omit-frame-pointer`.
- **Diagnóstico**: `BB_FRAME_STATS=1`: FPS, peor frame y tiempo de compilación
  de shaders/pipelines cada 5 s; `BB_AUDIO_STATS=1`: ritmo y llenado de la
  cola de sonido; `BB_AUDIO_DUMP=ruta`: PCM crudo de cada puerto.

## Estado actual (2026-09-25)

El código x86-64 original de `eboot.bin` se ejecuta directamente en Linux y pasa
los constructores globales, la inicialización de memoria y el arranque del propio sistema
de hilos del juego: se crearon 13 hilos guest (`FD4JobWorker:0`, `EzWorkPool_*` ×9,
`MOMainThread`, logger). El juego asigna ~4.8 GiB de memoria direct y ~337 MiB
de memoria flexible. La detención actual es `sceAjmInitialize` (códec de audio ATRAC9),
caller `0xd18a6a`.

Cambios de esta etapa:

- `runtime_memory.c` reescrito: un único memfd sparse para todo el pool direct
  (5056 MiB, como `sceKernelGetDirectMemorySize` en PS4), tabla de regiones
  con división, flexible memory (448 MiB), `ReserveVirtualRange`, `Mprotect`,
  `QueryMemoryProtection`, `VirtualQuery`, `GetDirectMemoryType`, `BatchMap(2)`,
  unmap/release parciales, `MAP_FIXED`/`NO_OVERWRITE`, bits de protección de GPU.
- **Todas las direcciones visibles para el guest se ubican por debajo de 1 TiB**: la imagen, las pilas de hilos,
  la pila principal, los trampolines (`runtime_low_map`), la memoria guest
  (`0x10_0000_0000..0xfc_0000_0000`), los heaps de objetos host (non-PIE + `mallopt`).
  El juego empaqueta punteros en 40 bits: por ejemplo, el lock en la dirección `0x20368c0`
  guarda al dueño como `scePthreadSelf() & 0xffffffffff` y lo compara con el valor
  completo. Con handles `0x7f…` esto producía un interbloqueo eterno.
- El watchdog (`--timeout`) imprime RIP y la cadena de frames de pila de todos los hilos
  (offsets relativos a la imagen y a `bb-probe` para `addr2line`).
  `BB_TRACE_SEMA=1` imprime las esperas bloqueantes en semáforos.
  `got_import.py <dirección GOT>` nombra el import detrás de un stub de PLT.
- Red en modo «cable desconectado»: las plantillas/conexiones/solicitudes HTTP se crean,
  el envío devuelve un error de red; NpWebApi/Matching2/Signaling/Score:
  «no está en PSN»; chat de voz: puertos sin sonido.

Los siguientes subsistemas, en orden de aparición: Ajm (ATRAC9 mediante ffmpeg),
Fios2, SaveData, Rtc, Pad, AudioOut, AvPlayer, VideoOut y GnmDriver.

## Descripción anterior


**El código x86-64 original de `eboot.bin` se ejecuta directamente en el procesador
con Linux y pasa el tramo inicial de constructores.** Ahora regresa de
`_init_env`, registra tres manejadores `atexit` y 279 destructores de C++,
pasa 1416 guards de inicialización, crea 1422 mutex, un rwlock y 17 semáforos,
asigna/mapea 116 MiB para el asignador del juego.
La `libc.prx` original se carga junto con el eboot, su inicializador devuelve 0,
el constructor `std::ios_base::Init` se completó. La siguiente detención controlada es
`sceSysmoduleLoadModule(0xb4)` (`g8cM39EUZ6o#M#N`, caller `0x2026149`).
Una prueba aparte de Vulkan ejecuta un comando de llenado de buffer y verifica
los 4096 bytes devueltos. shadPS4 no se ejecuta en este experimento.

**Esto todavía no es una recompilación de todo el juego ni un port jugable.** No hay ventana del juego,
menú, renderizado de recursos del juego ni un bucle de juego funcional. Vulkan todavía
no está conectado con los comandos gráficos del juego. La detención controlada en el siguiente
import no soportado es un límite medible del prototipo; el arranque del juego no está completo.

## Ejecución en el entorno actual

Desde `game_files`:

```bash
bash native_probe/run.sh --software
```

El script encuentra Python, GCC y el Vulkan SDK locales, prepara la imagen,
compila el cargador y lo ejecuta. En esta máquina las herramientas se encontraron
en `/nix/store`; no hizo falta descargar ni instalar nada.
`--software` selecciona Lavapipe y desactiva las Vulkan layers implícitas para la prueba.
En el entorno verificado no existe `/dev/dri`, así que no se probó una GPU real.

Resultado esperado:

```text
Vulkan: llvmpipe (LLVM 21.1.8, 256 bits); command submission + 4096-byte readback PASS
Mapped 91973152 bytes, 4 segments; applied 237083 relocations
Starting native libc.prx at image offset 0x56e0000; fallback exports=202
Runtime: application heap API registered
Native libc module initializer returned 0
Entering original x86-64 code at guest offset 0xa0
Runtime: _init_env returned (verified libc implementation: RET)
Runtime: direct allocation offset=0x0, size=121634816 bytes
Runtime: mapped direct memory, size=121634816, alignment=0x200000
Runtime: semaphore id=1, attr=2, initial=0, max=1
Runtime: semaphore id=2, attr=2, initial=0, max=1
Runtime: semaphore id=3, attr=2, initial=0, max=1
Runtime: semaphore id=4, attr=2, initial=0, max=1
Runtime: semaphore id=5, attr=2, initial=0, max=1
Runtime: semaphore id=6, attr=2, initial=0, max=1
Runtime: semaphore id=7, attr=2, initial=0, max=1
Runtime: semaphore id=8, attr=2, initial=0, max=1
Runtime: semaphore id=9, attr=2, initial=0, max=1
Runtime: semaphore id=10, attr=2, initial=0, max=1
Runtime: semaphore id=11, attr=2, initial=0, max=1
Runtime: semaphore id=12, attr=2, initial=0, max=1
Runtime: semaphore id=13, attr=2, initial=0, max=1
Runtime: semaphore id=14, attr=2, initial=0, max=1
Runtime: semaphore id=15, attr=2, initial=0, max=1
Runtime: semaphore id=16, attr=2, initial=0, max=1
Runtime: semaphore id=17, attr=2, initial=0, max=1
STOP: first unsupported PS4 import: g8cM39EUZ6o#M#N (index 249)
API: sceSysmoduleLoadModule
Caller return offset: 0x2026149; first argument: 0xb4
Runtime: _init_env=1, atexit=3, __cxa_atexit=279, registered handlers=282
Runtime: static guards acquired=1416, released=1416
Runtime: mutexes created=1422, locks=3208, unlocks=3208
Runtime: rwlocks created=1, reads=21, writes=1, unlocks=22
Runtime: semaphores created=17, deleted=0, acquired=0, signals=0, timeouts=0
Runtime: direct memory allocations=1, maps=1, live=121634816, budget=536870912
Runtime: memory operations=9884
Original guest entry instructions executed; game initialization is incomplete.
```

**El código de salida 20 significa la detención esperada por falta de implementación
de una API de PS4.** Es distinto de 0 a propósito. Los errores de carga devuelven 1;
los modos de runtime explícitamente no soportados, 21; la activación del stack protector, 22.
Las señales de Linux, 128 + número de señal. Para la ejecución del código guest en Linux
hay un temporizador de 10 segundos.

En un sistema con GPU disponible puedes probar `bash native_probe/run.sh`.
Esto usa la selección normal de dispositivo Vulkan; el resultado en hardware aquí
no está verificado. Para volver a ejecutar los archivos ya compilados:

```bash
native_probe/out/bb-probe native_probe/out/boot-libc.bin --cpu-only
native_probe/out/bb-probe --vulkan-only
```

La imagen base sin la libc nativa se guarda en `out/boot.bin` para comparar
con la detención anterior en `std::ios_base::Init`.

Desde el directorio `native_probe` el comando sigue siendo el mismo: `bash run.sh --software`.
Para reproducir la detención más temprana en `_init_env`, usa
`out/bb-probe out/boot.bin --cpu-only --strict-imports` desde ese directorio.

El último comando usa la configuración normal de Vulkan. Para el driver
por software, define `VK_DRIVER_FILES` apuntando a su JSON y
`VK_LOADER_LAYERS_DISABLE='~implicit~'`, como hace `run.sh --software`.

## Qué se encontró en los archivos

| Parámetro | Resultado |
|---|---|
| Juego | Bloodborne, CUSA03173 |
| Versión según `param.sfo` | APP_VER 01.09, VERSION 01.00 |
| Contenedor | SELF, 8 entradas de segmentos |
| CPU | x86-64, ELF64 little-endian, ABI PS4/FreeBSD |
| Tipo de ELF | ET_SCE_DYNEXEC (`0xfe10`) |
| Punto de entrada | `0xa0` relativo a la base de carga |
| Segmentos cargables | 2: código/datos de solo lectura y datos modificables/BSS |
| Imagen en memoria | 91 042 036 bytes |
| Imports | 686 símbolos importados únicos |
| Dependencias DT_NEEDED | 42 módulos |
| Relocalizaciones de direcciones | 231 478 RELATIVE, 2 838 ABS64, 23 GLOB_DAT, 661 JUMP_SLOT |
| Recursos de `dvdroot_ps4` | 31 322 968 005 bytes |

Entre las dependencias: libc, libkernel, GnmDriver, VideoOut, Pad, Fios2,
AudioOut, SaveData, Sysmodule, APIs de red y de diálogos. En `sce_module`
hay solo siete archivos; tener los archivos de los módulos no sustituye el soporte de su ABI.

Los segmentos SELF usados están disponibles en texto plano. La extracción no realiza
descifrado. Los segmentos comprimidos/cifrados no soportados se rechazan.
Un segmento de metadatos no cargable (`program header 9`, tipo `0x6fffff01`)
no está presente en los segmentos SELF disponibles. En el `eboot.elf` de diagnóstico su
rango está lleno de ceros: **esta no es una reconstrucción del ELF completa byte a byte**.
Se verificó la presencia de todos los segmentos que necesita este experimento.

Los detalles, el SHA-256 del eboot original, la lista de dependencias, NID, segmentos
y la cantidad de recursos por directorio están en `out/analysis.json`.
Los nombres de varios imports se verificaron calculando el NID a partir de los nombres supuestos;
los resultados se registran en `import_name_hints`. Para la primera llamada a `_init_env`
se obtuvo el NID `bzQExy189ZI`; la llamada siguiente corresponde a `atexit`.

## Cómo está construido el prototipo

`prepare.py` lee el SELF y el SFO, verifica los límites, reconstruye los segmentos
disponibles, analiza las tablas dynamic/symbol/RELA de PS4 y genera `out/boot.bin`.
Los archivos originales se abren solo en modo lectura. Todos los resultados van a `out/`.

Además se verifica el export real de `_init_env` en `sce_module/libc.prx`:
NID `bzQExy189ZI`, dirección `0x5fef0`, tamaño 1, byte `c3` (RET).
El SHA-256 de la libc y la evidencia se escriben en `analysis.json/libc_evidence`.
La suposición inicial de una inicialización compleja dentro de `_init_env`
no se confirmó para este dump. El retorno corresponde al código real de la función.
El formato `BBPROBE2` contiene un flag de esta verificación; sin el flag, el runtime está desactivado.
Las imágenes antiguas `BBPROBE1` se leen con el runtime desactivado.

`link_libc.py` crea un `out/boot-libc.bin` aparte con formato `BBPROBE3`:
agrega dos segmentos de la libc original, sus relocalizaciones de direcciones y 202
vinculaciones de exports de respaldo. Empareja los NID junto con los nombres y versiones
de la biblioteca/módulo: los sufijos locales de libc `#C#A` y del eboot `#q#q` son distintos.
Los contratos host implementados tienen prioridad. El resto de los imports que coinciden
apuntan al código/datos reales de libc, incluidos objetos y tablas de C++.
Los archivos originales del juego no se modifican; la información sobre las vinculaciones y el SHA-256 de libc
se escribe en `out/libc-link.json`.

Antes de entrar al eboot se ejecuta el `DT_INIT` de libc. Se soporta el TLS de esta biblioteca:
módulo 2, plantilla de 544 bytes, bloque de 1184 bytes por hilo host, resto puesto en cero;
14 relocalizaciones `DTPMOD64` escriben el número de módulo, no un puntero a la imagen.
`__tls_get_addr` verifica el módulo y los límites. El TLS completo de todos los módulos de PS4,
su liberación al terminar los hilos guest y el acceso directo mediante FS
no están implementados. Para el único hilo guest actual, el bloque vive hasta la salida.
`sceKernelGetProcParam` devuelve el procparam original relocalizado del eboot;
`_sceKernelRtldSetApplicationHeapAPI` guarda la tabla de callbacks del asignador.

`runtime_thread.c` implementa self y las consultas init/get/getaffinity/destroy
de atributos del hilo guest actual. Para este prototipo existe una sola
CPU virtual (máscara 1); no es la máscara de CPU del host ni una configuración de su affinity.
La creación de hilos guest y el cambio de atributos siguen sin soporte.

`probe.c` asigna memoria, copia los segmentos y aplica las relocalizaciones de direcciones.
Las funciones desconocidas se dirigen a interceptores ejecutables que imprimen el NID
y terminan el proceso. Los datos importados no soportados se dirigen a páginas inaccesibles:
usarlos provoca un error en lugar de devolver datos ficticios.
Después de la carga se aplican los permisos de página según el ELF; el código recibe permisos RX.
Luego se hace una llamada directa al punto de entrada original según la SysV ABI.
La preparación de argumentos alcanza para el tramo observado; la pila completa
de arranque del kernel de PS4, las excepciones y el mecanismo general de carga de módulos dependientes
no están implementados; por ahora solo se conecta específicamente libc.

`runtime.c` implementa el retorno verificado de `_init_env`, el registro de `atexit`/
`__cxa_atexit` con orden inverso y filtrado por DSO, `__cxa_finalize`,
`exit`, guard acquire/release/abort, un stack canary aleatorio local al proceso,
un manejador de emergencia para la corrupción de pila, cuatro funciones de manejo de memoria y `strlen`.
El emparejamiento se hace por el NID completo con el sufijo de library/module de este
eboot en particular, sin un «devolver 0» automático para imports desconocidos.
El registro de finalización y los guards están pensados para el único hilo guest actual;
una inicialización de guard recursiva/concurrente detiene la ejecución con el código 21.

`runtime_mutex.c` vincula los mutex/atributos de PS4 con pthread de Linux, convierte
tipos y códigos de error, soporta mutex recursivos y creados estáticamente.
Los protocolos de prioridad, el planificador de PS4 y los hilos guest no están implementados.
Los opaque handles están pensados para las APIs implementadas; el layout binario
de los mutex internos de PS4 no se reproduce. El tramo observado de libc funciona
mediante estas APIs; el acceso directo a los internos de los mutex requerirá una implementación aparte.

Los imports POSIX de mutex de `libScePosix` usan el mismo backend mediante
wrappers separados: devuelven errno de PS4 positivos, no los códigos negativos
de `scePthread`. El `pthread_mutex_init` de dos argumentos no lee el tercer
argumento inexistente. El errno de Linux no se pasa directamente al guest.

`runtime_sema.c` implementa create/delete del kernel, wait/poll, signal/cancel.
Los handles son IDs únicos de 32 bits; los IDs eliminados no se reutilizan.
Se verificaron los contadores y el desbordamiento, el timeout en microsegundos con reloj
monotónico, la reserva de tokens antes del despertar, la cancelación y la eliminación con
hilos host en espera. El objeto se libera después de que regresan todas las llamadas en espera.
En modo FIFO se atienden las solicitudes adecuadas en orden de cola; una solicitud
de menor tamaño puede adelantarse a una solicitud en espera para la que todavía no hay tokens.
Esto corresponde al modelo de referencia de shadPS4 utilizado; la comparación
con una PS4 real todavía no se ha hecho.
Los atributos 0/2 permiten la creación y las operaciones no bloqueantes, pero la espera
bloqueante detiene explícitamente el prototipo (21): todavía falta el planificador de PS4
con prioridades. Tampoco están implementados los option parameters distintos de cero. En la ejecución
actual el juego creó 17 semáforos con attr=2, initial=0, max=1, pero todavía no
ejecutó wait/signal; estas operaciones se verificaron con pruebas en C separadas.

`runtime_time.c` soporta el `gettimeofday` de POSIX: el tiempo se toma del host,
los campos se copian a timeval/timezone de PS4 explícitos. Se verificaron los límites de los campos y
el rango de microsegundos. Un error inesperado de la API del host detiene el prototipo:
el puente completo de errno/TLS de POSIX todavía no está implementado.

`runtime_rwlock.c` soporta init/destroy, read/write, try-read/try-write,
timed-read/timed-write y unlock sobre pthread de Linux. El registro sincroniza
la inicialización de handles estáticos, rastrea dueños, lectores y
llamadas en espera: destruir un lock ocupado devuelve EBUSY,
un unlock ajeno, EPERM; el timeout, ETIMEDOUT de Orbis. La espera no retiene el
mutex del registro. Se verificó el funcionamiento simultáneo de varios hilos host,
pero la creación de hilos guest todavía no existe. Solo se soportan los atributos
por defecto; los atributos no estándar detienen el prototipo con el código 21.

`runtime_memory.c` ofrece un **pool de CPU limitado de 512 MiB para investigación**.
Es el presupuesto elegido para el prototipo, no la cantidad de RAM de la PS4. La asignación devuelve
un offset físico virtual; memfd de Linux proporciona un almacenamiento compartido real
para varios mapeos y alineación de 16 KiB/2 MiB.
Están implementados allocate/map, unmap completo y release completo. Se soportan los tipos
de memoria 0/3 para CPU, permissions read/write, flags=0, dirección automática;
cualquier otro modo se detiene con diagnóstico. Los release/unmap parciales por ahora
devuelven EINVAL. Faltan la coherencia de GPU, la reserva de direcciones fijas,
el espacio de direcciones completo de PS4 y la conexión de este pool con Vulkan.

`vulkan_smoke.c` crea instance/device/queue, envía `vkCmdFillBuffer`,
pone una barrera para la lectura desde CPU, espera a que termine y compara todas las palabras del buffer.
Es una prueba del futuro backend gráfico, no un traductor de GNM.

## Compilación en otros sistemas

Linux x86-64: Python 3, GCC/Clang, headers y loader de Vulkan. Normalmente basta con:

```bash
python3 native_probe/prepare.py CUSA03173
python3 native_probe/link_libc.py CUSA03173
bash native_probe/build.sh
```

El script soporta `CC`, `VULKAN_INCLUDE`, `VULKAN_LIB`;
si existe `pkg-config vulkan`, usa su configuración.

Para Windows, en el código fuente hay una rama con `VirtualAlloc`/`VirtualProtect` y una
SysV ABI explícita. Se asume **MinGW-w64 GCC/Clang x86-64**, no MSVC.
Esta rama **no se compiló ni se probó** en el entorno Linux actual.
Ejemplo de compilación manual en un entorno MinGW con el Vulkan SDK instalado:

```text
python native_probe/prepare.py CUSA03173
gcc -std=c11 -O2 -Wall -Wextra native_probe/probe.c native_probe/runtime.c native_probe/runtime_mutex.c native_probe/runtime_thread.c native_probe/runtime_rwlock.c native_probe/runtime_sema.c native_probe/runtime_time.c native_probe/runtime_memory.c native_probe/vulkan_smoke.c -I<SDK>/Include -L<SDK>/Lib -lvulkan-1 -o native_probe/out/bb-probe.exe
native_probe/out/bb-probe.exe native_probe/out/boot.bin
```

Las rutas del SDK se reemplazan por las reales; el binario de Linux no es portable a Windows.
El diagnóstico de señales y el temporizador en el código fuente actual están implementados solo para Linux.
Los nuevos backends de mutex/rwlock/semaphore/time/direct-memory también están implementados solo para Linux;
Windows llegará a un import no soportado más temprano.

## Pruebas

```bash
bash native_probe/build.sh --test
python3 -m unittest discover -s native_probe -v
```

Pasaron 35 pruebas de Python, incluida la ejecución del conjunto de verificaciones en C del runtime:
límites del SELF/imagen, verificación de la instrucción de `_init_env`, ejecución directa de
x86-64, relocalizaciones de direcciones, modo strict, desactivación del runtime no confirmado,
diagnóstico de fallos. Las verificaciones en C cubren el orden inverso de los destructores,
DSO y la finalización repetida, el registro durante la finalización y el crecimiento del registro,
guard acquire/abort/release, errores y recursividad de mutex, alineación,
no superposición de las asignaciones físicas, shared aliasing y la reasignación
de memoria liberada. El stack protector y el guard recursivo se verificaron en un subprocess.
Además se verificaron el ciclo de vida del rwlock, las capturas read repetidas,
el unlock ajeno, la destrucción estando ocupado, varios lectores simultáneos,
un writer en espera, la conversión de timeouts y `strlen` con NUL dentro de la cadena.
Se agregaron verificaciones del inicializador/export nativo, la prioridad de la API del host,
la desactivación de libc en modo strict, los permisos de ejecución y los límites de la nueva metadata,
la coincidencia de identidad con distintos IDs locales, el rechazo ante otra versión de
la biblioteca y el manejo de relocalizaciones TLS. La prueba en C verifica bloques TLS separados
en hilos host, la plantilla/BSS, las consultas de atributos y el registro de la heap API.
Un `sema-test` aparte verifica la escritura de 32 bits del handle sin dañar el campo
vecino, IDs obsoletos, desbordamiento, timeout, cola de varios hilos host,
reserva de tokens, cancelación/eliminación con hilos en espera y el rechazo explícito de la
espera bloqueante con prioridades. Se verificaron los errores positivos de los mutex
POSIX, la captura recursiva y las estructuras de salida de `gettimeofday`.
La compilación en Linux se hizo con `-Wall -Wextra -Werror`.
La ejecución de integración actual del eboot real está registrada en `out/run.log`;
el resultado del modo antiguo, en `out/strict-run.log`.

## Próximas etapas del port real

1. Implementar la carga/registro de módulos del sistema y los contratos necesarios
   de AppContent. El juego llamó a `sceSysmoduleLoadModule(0xb4)` desde `0x2026149`;
   según la tabla de referencia, este ID corresponde a `libSceAppContent`. Ese archivo no está
   entre los siete `sce_module/*.prx` locales. Hará falta implementar
   las APIs usadas y el estado del módulo; no se agregó un simple retorno de éxito.
2. Continuar con los constructores, completar la memoria/sincronización y luego implementar
   el TLS de los demás módulos, el arranque de hilos y la carga de los módulos necesarios.
3. Llegar a `main`, agregar el sistema de archivos (`/app0` → directorio de recursos)
   y registrar cada contrato no soportado siguiente.
4. Traducir los comandos GNM/PM4, los formatos de recursos y los shaders de AMD GCN a Vulkan/SPIR-V;
   luego vincular VideoOut con la ventana y el swapchain. Tener Vulkan por sí solo
   no hace compatible el código gráfico de PS4.
5. Para la recompilación estática, reconstruir las funciones y el flujo de control,
   las tablas de llamadas virtuales, las excepciones y la ABI; verificar el comportamiento comparándolo
   con el código máquina original. En x86-64, la ejecución directa con un runtime compatible
   ya permite investigar el arranque sin traducir antes todo el código de CPU.

La prioridad del siguiente cambio es Sysmodule/AppContent y los constructores siguientes.

## Fuentes de referencia

El formato SELF y las reglas de correspondencia de segmentos se cotejaron con los
[headers del cargador de shadPS4](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/loader/elf.h)
y la [carga de segmentos](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/loader/elf.cpp).
Las tablas dynamic de PS4 y el cálculo de NID se cotejaron con
[module.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/module.cpp),
el contexto de arranque, con [linker.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/linker.cpp).
Las firmas de mutex y los valores de tipos se cotejaron con
[mutex.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/threads/mutex.cpp)
y [pthread.h](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/threads/pthread.h),
rwlock, con [rwlock.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/threads/rwlock.cpp),
las firmas de direct memory, con
[memory.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/memory.cpp).
Los semáforos se cotejaron con
[semaphore.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/threads/semaphore.cpp),
las estructuras de tiempo, con
[time.h](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/time.h).
El identificador de AppContent, con
[sysmodule_table.h](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/sysmodule/sysmodule_table.h).
Los nuevos contratos de registro de la heap API y procparam se cotejaron con
[linker.h](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/linker.h)
y [process.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/process.cpp),
los atributos de hilos, con
[pthread_attr.cpp](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/libraries/kernel/threads/pthread_attr.cpp).
El cuerpo de `_init_env` y la estructura de los guards se verificaron desensamblando la libc local.
La implementación del prototipo se escribió por separado; no hay dependencia del ejecutable de shadPS4.

El directorio `out/` contiene datos derivados del juego, tiene `.gitignore` y no es necesario
para distribuir el código fuente de la herramienta.
