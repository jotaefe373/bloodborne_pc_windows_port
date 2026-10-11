> Traducción al español de `docs/history/CURRENT_STATUS_2026-09-29.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Bloodborne en PC: estado real del port y del upscaler

Corte al **29 de septiembre de 2026**. Fuente: los archivos en `game_files`, el historial de Git
de `native_probe` hasta `ac9fe90`, los cambios actuales sin commitear, los logs guardados de
ejecuciones y las pruebas locales. En este documento «está en el código», «se ejecutó» y «se verificó
en la imagen» no se consideran lo mismo.

## Resumen breve

Es un **port nativo para Linux** experimental que funciona, no una ejecución mediante un
emulador completo: el `CUSA03173/eboot.bin` original x86-64 se ejecuta en la CPU de la PC,
las llamadas al sistema de PS4 las atiende un runtime HLE propio, y los gráficos los produce
un núcleo Vulkan basado en shadPS4. El juego llega hasta la escena con el personaje, acepta
entrada, funciona con sonido y partidas guardadas; esto lo confirman los logs de ejecución,
las capturas y los videos en la raíz de `native_probe`. Completar todo el juego, todas las zonas y la
ausencia de fallos **no están confirmados** por estos materiales.

**El temporal upscaling FSR 3.1 realmente funciona por la ruta verificada con la resolución
de escena definida al inicio**: el log `логи.md` muestra `960×540 → 1920×1080`,
la composición de la UI en 1920×1080 y la ejecución en una RX 7800 XT. La ruta actual de cambio de preset
sin reiniciar sigue siendo problemática en esta tarjeta gráfica: el último
`last_run.log` muestra el cambio de los tamaños de escena solicitados, pero el contexto de FSR
`1920×1080 → 1920×1080`. Según el código, aquí no se eligen los targets reducidos cuando
`D32S8` no admite blit. Por lo tanto, el log del cambio de presets **no
demuestra una reducción real de la resolución 3D ni una ganancia de FPS**.

## Composición del proyecto y evolución

| Ruta | Rol |
|---|---|
| `../CUSA03173/` | Archivos locales del juego, `eboot.bin`, recursos y módulos de PS4. |
| `../np_base/` | Instantánea de una base temprana del port; el desarrollo activo se hace en `native_probe`. |
| `prepare.py`, `link_libc.py`, `link_modules.py`, `probe.c`, `runtime_*.c` | Preparación de la imagen ejecutable, enlace de módulos, cargador y HLE. |
| `gpu/` | Núcleo de video Vulkan, recompilador de shaders, ajustes para el juego, FSR e ImGui. El núcleo tomado de shadPS4 se describe en `gpu/VENDOR.txt`. |
| `patches/Bloodborne.xml`, `patches.py` | Parches de FPS y resolución que se aplican al código invitado al iniciar. |
| `bbport.ini`, `run.sh`, `build.sh` | Configuración, ejecución completa y compilación. |
| `out/`, `out/dev/`, `last_run.log`, `логи.md` | Binarios compilados y rastros de las verificaciones; parte de los logs corresponde a versiones anteriores del código. |

Evolución según Git: el 25 de septiembre se agregaron el cargador, HLE, gráficos, sonido y
optimizaciones de CPU/GPU; el 26 de septiembre, análisis de frame, vectores de cámara, jitter,
FSR 3.1, presets y menú; el 27 de septiembre el último commit `ac9fe90` corrigió
el cambio de presets y la visualización de la máscara. Después de él, en el árbol de trabajo hay
mejoras sin commitear de vectores de objetos, targets de render reducidos,
separación de resoluciones de escena/UI, scripts y pruebas. Esto es el **árbol de trabajo
actual**, no un release listo. Las secciones antiguas de `README.md`, `docs/upscaler.md`
y `docs/ROADMAP.md` describen etapas distintas y en partes ya están desactualizadas.

## Qué está implementado

### Ejecución y rendimiento

- El `eboot` invitado y parte de los PRX originales se ejecutan junto con implementaciones
  de memoria, hilos, archivos, tiempo, control, audio, partidas guardadas y servicios.
  La red funciona en modo offline; PSN no está implementado.
- SDL3 atiende el gamepad y el control de respaldo con teclado. El sonido se emite
  a través del sistema de audio del host; en el código hay una corrección del ritmo de `AudioOut` y un flag
  de guardado para los sonidos que faltaban.
- El renderer Vulkan obtuvo un hilo dedicado a la grabación de comandos, preparación de draws en
  cuatro hilos, cachés de texturas y buffers, copia de memoria invitada y un pool
  de staging buffers. `docs/parallel_gpu.md` y `docs/ROADMAP.md` contienen
  mediciones en escenas específicas; no se pueden extrapolar a todas las configuraciones.
- `BB_FPS=uncap` aplica por defecto el parche con paso de simulación según el tiempo
  de frame; están disponibles `30`, `60`, `90`. La frecuencia de salida está limitada por el monitor
  y por un máximo de 120 FPS. Para diagnóstico están `BB_FRAME_STATS=1`,
  `BB_TOGGLE_FILE` y la captura de la estructura del frame mediante `BB_CAPTURE_TRIGGER`.

### Upscaler

- El juego no tiene un buffer de velocidad listo. El port calcula los vectores de cámara a partir de
  la profundidad y las matrices de dos frames; para la geometría de la escena aplica un
  jitter subpíxel de Halton. La reproyección de la geometría estática se verificó anteriormente
  (`docs/upscaler.md`).
- FSR 3.1 está integrado mediante `gpu/third_party/fsr-vulkan`. Native AA funciona
  1:1 sobre el color HDR de la escena antes del posprocesado. El modo verificado con resolución
  reducida usa el parche de resolución invitada, FSR después del tonemapping y
  una composición separada de la interfaz en 1920×1080. El parche de UI en el árbol actual
  deja sus coordenadas nativas. Un `BB_RENDER_RES=AnchoxAlto` explícito activa
  esta ruta; por ejemplo, el log `логи.md` confirma `960x540`.
- Presets en el código: Native AA `1920×1080`, Quality `1280×720`, Balanced
  `1130×636`, Performance `960×540`, Ultra Performance `640×360` para una salida de
  1920×1080. El menú ImGui se abre con `Insert` o `L3+R3`. En `bbport.ini`
  se guardan FSR, preset, nitidez, jitter, máscara de reactividad, modo
  de depuración, vectores de objetos y contador de FPS. La configuración actual contiene
  `upscaler=fsr3`, `preset=4`, `jitter=1`, `reactive=1`,
  `object_motion=1`, `debug_view=0`.
- La máscara de reactividad se forma comparando el color antes y después de las pasadas
  transparentes. Es opcional: observaciones anteriores señalan temblor de la neblina
  fina cuando está activada. La configuración por defecto en el código la deja desactivada, pero
  en el `bbport.ini` actual está activada.
- En el árbol de trabajo hay vectores experimentales de objetos animados:
  posiciones previas de vértices, un target adicional de G-buffer, correspondencia de
  dibujados entre frames y restricción a buffers de pose/huesos adecuados.
  Cambiar `object_motion` requiere reiniciar. Según
  `out/dev/motion-selective.log`, el historial en los draws seleccionados se encuentra con frecuencia,
  sin omisiones por capacidad en los intervalos mostrados. Es una métrica de draws, **no
  una evaluación de la cobertura de píxeles ni de la calidad visual**.

## Defecto actual de los presets dinámicos

En `vk_scene_resolution.cpp` la función `SceneTargets::Eligible` exige
`BlitSrc|BlitDst` en el formato de cada candidato. En `vk_rasterizer.cpp`
la pasada reducida se desactiva si la profundidad no es adecuada; de ella también depende
la elección de la entrada reducida de FSR en `vk_temporal_upscaler.cpp`. El log guardado
para la RX 7800 XT informa la ausencia de `blit` en `D32S8`. Más tarde se agregó un
fallback que **limpia la profundidad de la UI** en lugar de copiarla, pero no
elimina el requisito de `blit` para la profundidad de la **escena 3D**.

Resultado en esta máquina: en `last_run.log` del 28 de septiembre aparecen cambios a
`640×360`, `1280×720`, `960×540` y otros presets, pero el
contexto de FSR creado se mantuvo en `1920×1080 → 1920×1080 (HDR scene color)`. El mensaje
`Scene resolution: raster ...` refleja el tamaño solicitado de los targets proxy;
no mide el tamaño realmente usado por cada draw. Las afirmaciones de
`README_FIXES.md` y las indicaciones del menú sobre un escalado dinámico que funciona en todas las GPU
son más fuertes de lo que permiten el código y el último log. `логи.md`
corresponde a una ejecución anterior con selección automática del parche de inicio,
que luego se cambió en `run.sh`.

## Verificaciones y límites de certeza

| Verificación | Resultado |
|---|---|
| Logs de ejecución del juego y frames del 27–28 de septiembre | Confirmadas la carga en la escena de juego y la salida de imagen. No se hizo una prueba de recorrido de punta a punta. |
| `логи.md` en RX 7800 XT | Confirmados el parche de escena `960×540`, UI `1920×1080`, contexto de FSR `960×540 → 1920×1080`. |
| `last_run.log` | El menú cambiaba presets sin reiniciar, pero FSR era 1:1; no hay estadísticas de FPS de esta ejecución. |
| `out/dev/motion-selective.log` | Para una serie de escenas con vectores de objetos selectivos se ven intervalos de aproximadamente 72–100 FPS, sin `capacity skips` en los resúmenes mostrados; no es una comparación controlada de presets. |
| `out/gpu/motion-history-test` y `out/gpu/ui-composition-test` | Ejecutadas de nuevo el 29 de septiembre: ambas `PASS`. |
| `nix-shell shell.nix --run 'python3 -m unittest -v test_patches'` | Ejecutado de nuevo el 29 de septiembre: 5 pruebas `OK`. |
| `out/dev/scene-validation.log` | La prueba Vulkan de targets reducidos en Lavapipe **terminó con un assertion** por la discrepancia entre la versión de los headers de Vulkan y el dispatcher. El log no ofrece una verificación completa y exitosa de esta ruta. |

Los vectores de objetos en el juego y su efecto sobre las estelas del arma y la ropa no están confirmados
visualmente con una prueba A/B sistemática. Las mediciones tempranas de alrededor de 49 FPS con
todos los draws frente a 77–78 FPS sin ellos y de alrededor de 81–87 FPS en una
selección más acotada corresponden a ejecuciones distintas; son una referencia para la siguiente prueba,
no un rendimiento garantizado de la configuración actual. La captura
`image_2026-09-28_00-44-14.png` muestra una escena de juego y un overlay de alrededor de
59 FPS, pero no revela las condiciones de la medición.

## Qué falta hacer / qué verificar a continuación

1. Corregir y confirmar el render 3D realmente reducido en el modo dinámico
   en la RX 7800 XT: verificar el tamaño real de los color/depth attachments
   y la entrada de FSR en cada preset. Si la ruta sigue siendo incompatible con `D32S8`,
   elegir explícitamente el parche de resolución de inicio y mostrar en el menú que se necesita
   reiniciar.
2. Después de la corrección, recorrer la misma escena de juego con Native AA,
   Quality y Performance: registrar la entrada/salida de FSR, FPS, tiempo de frame,
   nitidez de la UI e imagen en movimiento.
3. Comparar visualmente los vectores de objetos activados/desactivados al correr, al girar
   la cámara y en combate; verificar las estelas, la cobertura del historial y el costo de GPU.
4. Resolver el assertion en `scene-resolution-test`; las demás pruebas no
   reemplazan una prueba Vulkan dentro del juego. Generación de frames, FSR 4, DLSS y XeSS
   no existen en el port actual: figuran en `docs/ROADMAP.md` como planes.

## Cómo reproducir la ruta confirmada

Desde `game_files` en esta configuración:

```bash
BB_RENDER_RES=960x540 BB_FRAME_STATS=1 bash native_probe/run.sh
```

`BB_RENDER_RES` elige el parche de resolución de escena inicial, y el
`patches.py` actual mantiene la UI en 1920×1080. Cambiar la resolución de esta forma
requiere una nueva ejecución. Sin `BB_RENDER_RES` se activa la ruta dinámica
experimental descrita arriba. La ejecución recompila el port y usa los
archivos locales de `CUSA03173`; tener el código fuente y el binario no
confirma por sí solo que sea reproducible en otra PC.

## Corrección del 29 de septiembre: cambio de preset en vivo

Las razones por las que cambiar el preset en el menú no cambiaba la imagen eran dos:

1. `SceneTargets` copiaba los targets entre el tamaño nativo y el reducido solo
   mediante `vkCmdBlitImage`, y RADV no ofrece blit para `D32S8`. Por eso la profundidad
   de la escena se consideraba no adecuada y el render reducido no se activaba. Ahora, para
   formatos depth/stencil sin blit, la copia se hace con un dibujado a pantalla completa
   (`host_shaders/depth_resample.frag`): la profundidad se escribe mediante `gl_FragDepth`,
   el stencil mediante `VK_EXT_shader_stencil_export`.
2. La máscara de reactividad (`reactive=1`) capturaba el color en 1920×1080 y recreaba el
   contexto de FSR 1920→1920, y la pasada principal lo recreaba enseguida para la
   entrada reducida. El contexto se recreaba en cada frame. Ahora la máscara
   lee el target reducido de la escena.

Verificación en RX 7800 XT (`out/dyn-res-test.log`): los cambios en el menú dan
`FSR 3 context 1280x720 / 1130x636 / 960x540 / 640x360 -> 1920x1080`,
una sola recreación por cambio de preset, sin fallos. Los FPS en esta escena rondan
54–56 en todos los presets, es decir, aquí el cuello de botella no está en la resolución 3D.

## 30 de septiembre: FSR 4 INT8 y rendimiento

### FSR 4 (v07 INT8/DOT4)

- `vk_fsr4.cpp/.h`: proveedor FSR-Vulkan `ffxFsr4V07*` con un modelo por preset (native,
  quality, balanced, performance, ultraperf), tier 1080. Las entradas son las mismas que en FSR 3.1.
  En el menú «Upscaler → FSR 4 (INT8)», en el ini `upscaler=fsr4`, env `BB_UPSCALER=fsr4`.
  Si faltan los assets o las capacidades de la GPU, se activa automáticamente FSR 3.1.
- Assets: `fetch_fsr4_assets.sh` descarga el conjunto compilado por Q2RTX a partir del código fuente MIT
  del FidelityFX SDK (`fsr4_shaders/`, en `.gitignore`, 98 SHA-256 cotejados con los manifiestos).
  `BB_FSR4_DIR` define otro directorio.
- Dispositivo: se activan `shaderIntegerDotProduct` y `VK_KHR_compute_shader_derivatives`
  (`Instance::IsFsr4Int8Supported`).
- Verificado en RX 7800 XT: los modelos quality/ultraperf se crean; al cambiar de preset hay
  un congelamiento de ~6,5 s (compilación). Usuario: la imagen es más nítida que con FSR 3.1, pero hay ghosting fuerte
  en el personaje y el arma. Los vectores se verificaron con la vista de depuración y son correctos:
  el personaje recibe vectores de objeto. En el SPIR-V de la pre-pasada la profundidad se elige
  por mínimo (igual que nosotros), y los vectores se interpretan como «anterior − actual». Para A/B
  en el menú: «FSR 4: autoexposición», «FSR 4: invertir signo del jitter».

### Rendimiento (perf, hilo de comandos de GPU)

- `SceneTargets::Eligible` consultaba al driver las propiedades del formato en cada dibujado:
  ~13–15% del tiempo del hilo de GPU. Ahora hay caché por formato.
- `ObjectMotion::Attach`, la captura de color y la máscara de reactividad llamaban a
  `Scheduler::CommandBuffer()`. Esto pasaba la grabación de todo el resto del submit (casi
  todo el G-buffer) al hilo de GPU. Ahora pasan por `Scheduler::Record`.
  Quedaron dos llamadas directas al final del frame (`TemporalUpscaler::Run`, el presentador).
- Resultado: hilo de GPU ~74% en lugar de ~94% de un núcleo. En escenas de juego, 61–98 FPS frente a
  53–87 antes de las correcciones (las escenas no coinciden exactamente; es una referencia).

### Perfil con stack DWARF (perf, hilo de comandos de GPU, 30.09)

- `Motion::IndexedRange` (escaneo y hash de índices para los vectores de objetos) ocupaba ~10% del hilo
  de GPU. Se agregó `Motion::IndexRangeCache`: el resultado se reutiliza y se
  reverifica por completo cada 32 frames. En el juego, ~98% de los rangos salen de la caché (260 entradas).
- `SceneTargets`: tabla plana de propiedades de formatos y memoria de los últimos ocho targets;
  junto con Attachment/Get/View/Eligible, ~4% en lugar de ~7%.
- Después de esto, el hilo de GPU está ocupado con trabajo sin esperas notables. El hilo de grabación de Vulkan
  ~40% de trabajo y ~57% de espera. La GPU (RX 7800 XT) en promedio ~65% de ocupación.
  Lo que limita el frame es el hilo de comandos de GPU. Las partidas principales son los costos base del núcleo de video:
  FindView ~5,6%, BindTextures ~5,6%, memmove ~4,6%, SmallGuestCopy ~3,5%,
  CachedImageDescEntry ~3,2%, BindBuffers/BindVertexBuffers ~3% cada una.
  El siguiente paso es trasladar estos cálculos a los hilos de trabajo (paso 2 de parallel_gpu.md).

### FSR 4: ghosting en el personaje y el arma (30.09, verificación repetida)

Video `video_2026-09-30_03-43-12.mp4`: FSR 4, Ultra Performance (640×360 → 1920×1080). Detrás
del disco de sierra en movimiento queda una huella oscura sobre el fondo que se descubre. Verificado:

- vista de depuración de vectores (FSR 4): el personaje y el arma reciben vectores de objeto;
- la caché de rangos de índices no queda desactualizada (0 cambios en las reverificaciones);
- la secuencia de jitter coincide con el proveedor (Halton 2/3, ceil(8·ratio²) fases);
- A/B en una misma ejecución con las optimizaciones posteriores al 29.09 desactivadas (bits 4096, 8192, 1<<30):
  las estelas son iguales en ambas fases, es decir, no es una regresión causada por ellas. De paso: estas
  optimizaciones juntas dan 84,4 frente a 70,8 FPS al correr (+19%).

El modelo v07 determina el fondo descubierto por el color (la profundidad se usa solo para expandir
los vectores), y con una entrada de 640×360 tiene poca información. FSR 3.1 descarta ese historial por
profundidad, por eso en Ultra Performance tiene menos estelas.
