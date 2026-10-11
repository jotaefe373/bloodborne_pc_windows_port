> Traducción al español de `docs/ROADMAP.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Port nativo de Bloodborne: qué está hecho y qué sigue

El texto principal refleja el estado al 2026-09-26; abajo, como primera sección, está lo que cambió hasta el 30.09.
La vista más detallada: [CURRENT_STATUS_2026-09-29.md](history/CURRENT_STATUS_2026-09-29.md).
Informe del trabajo del 30.09 al 01.10 (pipeline de GPU, upscaler, crash, launcher, AppImage):
[SESSION_2026-09-30.md](history/SESSION_2026-09-30.md).
Detalles por tema:
[parallel_gpu.md](../parallel_gpu.md) (multihilo de GPU, tirones durante la carga),
[upscaler.md](upscaler.md) (análisis del frame del juego, constantes de escena).

## Actualización 30.09

- Hecho después del 26.09: FSR 4 INT8 (v07), vectores de movimiento de objetos, cambio de preset sin
  reiniciar (render targets de escena reducidos; la profundidad D32S8 se copia con un shader), LTO y PGO,
  escalado de la preparación de draws según el número de hilos (también Steam Deck).
- Problemas de la sección «Problemas conocidos» de abajo: el punto 3 (reinicio al cambiar de preset)
  está resuelto; el punto 1 (vectores de objetos) está implementado, pero FSR 4 sigue mostrando ghosting en el personaje en
  Ultra Performance; punto 2 (interfaz borrosa): la UI se dibuja en 1920×1080.
- Limitación: el render reducido de la escena (`SceneTargets::Eligible`) requiere un target de 1920×1080,
  es decir, solo funciona con salida a 1080p.
- Paralelización del hilo de comandos de GPU (paso 2 de [parallel_gpu.md](../parallel_gpu.md)): las texturas en
  un hilo aparte, en paralelo con los buffers, funcionan correctamente, pero no dan ganancia:
  los datos de cada draw se mueven entre núcleos. El cuello de botella es el hilo de comandos de GPU: 91 % en CPU,
  ~9 % esperando pequeñas copias de memoria del guest antes del fence. Lo siguiente: un pipeline de dos etapas
  (el segundo hilo es dueño de la caché de texturas y de la grabación de draws, con copia de registros a partir de los deltas del escáner)
  o memoización de los bindings de texturas entre frames; ver «What would scale» en parallel_gpu.md.
- **Pipeline de draws de dos etapas** (`vk_draw_pipe.h`): el hilo de comandos de GPU decodifica PM4 y
  elige el pipeline; un segundo hilo (`bb:DrawRec`), con su propia copia de los registros, vincula los recursos
  y graba el draw. +19 % de FPS con 16 hilos, +18 % con 8 (como el Steam Deck). Activado por defecto
  con 8 o más hilos (`BB_DRAW_PIPE=0/1`). El cuello de botella ahora es la segunda etapa; detalles y plan
  en parallel_gpu.md.
- Presets y carga de GPU: la escena en la RX 7800 XT cuesta poco, así que el preset cambia el tiempo de GPU
  apenas ~0.5 ms, mientras que FSR 4 en sí, con salida a 1080p, cuesta ~1.4 ms (FSR 4 Ultra Performance es más caro que
  el render nativo sin upscaler). Corregido: los pases de iluminación se quedaban en 1920×1080 con
  cualquier preset (la verificación miraba slots de targets ajenos); los targets reducidos ahora se muestrean
  directamente, sin remuestreo a nativo (la caché de shaders se reconstruye una vez). Lo siguiente para
  Steam Deck: la copia en memoria del guest de los render targets `3d5ebf4e` (ver parallel_gpu.md).
- **Corregido el crash con el pipeline** (corrupción del heap del guest, guest offset `0x263b8e7`, tras
  13–17 minutos): la interrupción «la GPU está inactiva» salía antes que las marcas EOP diferidas al hilo de grabación
  de Vulkan, y el juego liberaba los objetos con esas marcas. Ahora, antes de ella, se espera al pipeline y a las marcas
  diferidas; 2 corridas de 30 minutos sin crashes (antes de la corrección, 7 crashes de 7).
- **Resolución de salida 1440p/2160p** (menú «Resolución de salida», bbport.ini `output_res`, después de
  reiniciar): la escena se dibuja a la resolución del preset relativa a la salida, el upscaler (FSR 3 o FSR 4)
  completa el frame y la interfaz se rasteriza a la resolución de salida. Los efectos del juego (aberración,
  DoF, desenfoque, SSAO, antialiasing del juego, sombras dinámicas, SSR, cinemáticas, LOD) también.
- **Launcher** (`launcher/bb-launcher.sh`, GTK4/libadwaita) y **AppImage** para Steam Deck
  (`bash packaging/appimage.sh` → `dist/`; datos en `~/.local/share/bbport`, `--play`:
  inicio sin la ventana del launcher).
- Herramientas: `BB_PAD_FILE` (entrada de gamepad por script), `ab.sh` (A/B de bits de
  `BB_TOGGLE_FILE` en el juego en ejecución); en `Frame stats`, tiempo inactivo y bloqueos del hilo de GPU.

## Cómo está construido el port

- El eboot original (CUSA03173 v01.09) se ejecuta directamente en x86-64. Las bibliotecas del sistema
  de PS4 se reemplazan por un runtime HLE propio en C (`runtime_*.c`, `probe.c`).
- Gráficos: el núcleo de video y el recompilador de shaders de shadPS4 (GPL), compilados en `libbbgpu.so`
  (`gpu/`), con mejoras propias. El emulador shadPS4 completo no se usa.
- Los parches del juego (FPS, resolución, etc.) son XML de la comunidad (`patches/Bloodborne.xml`),
  compilados por `patches.py` y aplicados por el cargador al iniciar.

## Hecho

### Rendimiento y fluidez

| Qué | Resultado |
|---|---|
| Grabación de comandos de Vulkan en un hilo aparte, cachés de texturas/buffers, rwlock en lugar de mutex | 26 → 64 FPS en una misma escena |
| Preparación de draw calls en 4 hilos (`bb:DrawPrep`), verificación en el hilo de GPU | +11.5 % |
| Ventana de desprotección de 256 KiB cuando el juego escribe en memoria (menos page faults) | +22 % |
| Caché de descriptores de texturas, ruta rápida para los mismos render targets | hasta ~94 FPS en exteriores |
| Copias de memoria del guest en un pool de hilos, pool de staging buffers | congelamientos al cargar de 60–170 ms → 40–50 ms |
| Espera de las copias antes de los fences visibles para el juego | eliminado el parpadeo de la interfaz |
| Modo «Readbacks Relaxed» | sin «explosiones de vértices» (FaceGen) |
| Vblank de 480 Hz + límite de frames hasta min(monitor, 120), salida inmediata en el flip | entrega de frames pareja; correr no se ralentiza por encima de 120 FPS |

Todo se alterna durante el juego mediante `BB_TOGGLE_FILE` (máscara de bits) para comparaciones A/B.
Estadísticas: `BB_FRAME_STATS=1`.

### Sonido, entrada

- Salida de audio con el ritmo correcto (antes había chasquidos cada 10.7 ms).
- Gamepad mediante SDL3, distribución de teclado de respaldo.

### Análisis del frame

- `BB_CAPTURE_TRIGGER=<archivo>` graba un frame: pases, targets, shaders, texturas,
  constantes, modos de mezcla.
- Desglosada la estructura del frame de Bloodborne (G-buffer, iluminación, color de escena RGBA16F, niebla,
  posprocesado, tonemapping, antialiasing del juego, interfaz) y las constantes de escena de 864 bytes
  (matrices de vista y proyección).

### Upscaler temporal (FSR 3.1)

- **Vectores de movimiento de cámara**: a partir de la profundidad de la escena y de las matrices del frame actual y del anterior
  (`vk_camera_motion.cpp`, `camera_motion.comp`). Verificados reproyectando el frame anterior:
  la geometría estática coincide.
- **Jitter**: desplazamiento subpíxel de la geometría de la escena mediante el viewport, secuencia
  Halton(2,3); número de fases 8·(salida/render)². La interfaz y el posprocesado no se desplazan.
- **FSR 3.1** (FireBurn/FSR-Vulkan, Vulkan nativo, submódulo `gpu/third_party/fsr-vulkan`):
  - *Native AA*: sobre el color HDR de la escena antes del posprocesado, 1:1.
  - *Presets Quality/Balanced/Performance/Ultra Performance* (x1.5/1.7/2/3): el juego renderiza a
    resolución reducida (parche de resolución que `patches.py` deriva del parche de 720p
    de la comunidad), y FSR escala el frame terminado a 1920x1080 antes del primer pase de interfaz.
    La interfaz y el pase de salida se redirigen a imágenes de tamaño completo, y el presentador
    las muestra en lugar del buffer del juego.
- **Máscara de reactividad** (captura de la escena antes de los draws transparentes, comparación antes de aplicar
  la niebla): funciona, pero con la neblina de Bloodborne produce temblor; desactivada por defecto.
- **Menú dentro del juego** (Dear ImGui, Insert o L3+R3): upscaler, preset, nitidez,
  jitter, máscara, contador de FPS. Los ajustes se guardan en `bbport.ini`. El cambio de preset se hace con el botón
  «Aplicar y reiniciar el juego».

## Problemas conocidos

Estado del último commit. En el árbol de trabajo está preparado el paso de los presets a render targets
reducidos, conservando los buffers del guest, el posprocesado y la UI en 1920×1080. Las transiciones
entre presets y la copia de color/profundidad/stencil pasaron la prueba de Vulkan en Lavapipe.
La RX 7800 XT no soporta blit de D32S8, por lo que la nueva ruta dejaba la entrada de FSR en 1920×1080
y bajaba los FPS. Para esas GPU, el inicio ahora elige automáticamente la ruta probada con el parche
de resolución del juego y la UI en 1920×1080; el cambio de preset vuelve a requerir reinicio. En las GPU con el soporte
necesario se mantiene el cambio sin reinicio. Los puntos 2–3 de abajo se refieren al último
commit, anterior a estos cambios del árbol de trabajo.

El pase general de vectores de movimiento de objetos era demasiado caro: Performance daba unos
49 FPS con él y 77–78 FPS sin él. Ahora el target adicional y los shaders se activan solo
para los draws al G-buffer que tienen buffer de pose/huesos; los demás usan los vectores de cámara.
En una corrida de prueba, la ruta selectiva se mantuvo en unos 81–87 FPS, sin omisiones por falta de capacidad
del historial. Los vectores de objetos están activados por defecto; `BB_OBJECT_MOTION=0` los desactiva y
`BB_OBJECT_MOTION_ALL=1` restaura la antigua ruta general para comparar. La selección por tamaño
de buffer todavía es heurística: la calidad de armas y ropa en movimiento requiere verificación en el juego.

1. **Los objetos en movimiento «se desmoronan»** (arma en la espalda, personaje, tela, enemigos): solo hay
   vectores de movimiento de cámara. La cámara en tercera persona sigue al personaje, por lo que
   los vectores de cámara son incorrectos para él, y el upscaler toma el historial del lugar equivocado. Esto afecta
   a cualquier upscaler temporal (FSR 3/4, DLSS, XeSS).
2. **La interfaz en los presets se ve borrosa**: con el parche de resolución, el juego se cree un juego a 540p y,
   al parecer, prepara las fuentes y los elementos de la interfaz para esa resolución. Los menús
   (título, pausa) ni siquiera pasan por el upscaler.
3. **El cambio de preset requiere reinicio**: la resolución se fija con un parche de código al iniciar, y
   el juego asigna los buffers una sola vez.

## Plan

### 1. Vectores de movimiento de objetos

Los necesitan todos los upscalers y la generación de frames. El juego no los calcula, así que los calculamos nosotros.

Cómo:
- Para cada draw al G-buffer (pases con 5 o más targets), el recompilador crea una segunda variante
  del vertex shader que emite la posición dos veces: con las constantes actuales y con las constantes
  del frame anterior. La diferencia de las proyecciones es el vector de movimiento, que se escribe en un target auxiliar
  RG16F como salida adicional del pixel shader.
- Constantes del frame anterior: para cada draw guardamos el contenido de los constant buffers
  (matriz del objeto, huesos del esqueleto) con la clave «shader + número de draw en el pase» o por la dirección
  de los datos. Hay que averiguar cómo guarda el juego las matrices del esqueleto: en buffers que se sobrescriben
  cada frame (entonces copiamos la versión anterior) o en un ring buffer (entonces basta con la
  dirección del frame anterior).
- Donde no se encuentra el objeto (primer frame, objeto nuevo): vectores de cámara, como ahora.
- Verificación: vista de depuración de los vectores (`BB_DEBUG_MOTION`), reproyección del frame anterior
  con los vectores completos y, visualmente, la sierra en la espalda al correr.

### 2. Escalado a nivel del renderizador (en lugar del parche de resolución)

El juego funciona a 1920x1080 (o a la resolución del monitor), y a resolución reducida se dibujan
solo los pases de la escena 3D. La interfaz y los menús se mantienen nítidos, y el preset se cambia al vuelo.

Cómo:
- La caché de texturas asigna para los targets de la escena (G-buffer, profundidad, iluminación, color de escena, efectos) una copia
  de tamaño reducido; la memoria del guest y los descriptores del juego no cambian.
- El viewport y el scissor de los pases hacia esos targets se escalan (como ya se hace para la interfaz,
  incluidos los pases con el recorte desactivado).
- Los shaders que calculan con coordenadas de píxel (`gl_FragCoord`, `texelFetch`,
  compute shaders por píxel) reciben el factor de escala mediante push constants
  del recompilador. Los muestreos con coordenadas normalizadas funcionan sin cambios.
- FSR se coloca en el mismo lugar que Native AA: el color de la escena antes del posprocesado (HDR, mejor
  calidad); el posprocesado y la interfaz van a resolución completa.
- Riesgos: pases que leen los targets de la escena por coordenadas de píxel en el posprocesado, y
  lecturas desde la memoria del guest de esos targets (hay que prohibirlas o escalarlas de vuelta).

### 3. Otros upscalers

Todos usan las mismas entradas (color, profundidad, vectores de movimiento, jitter, máscaras).

- **FSR 4 (INT8)**: FSR-Vulkan tiene un proveedor experimental de FSR 4 v07 INT8; agregarlo
  como opción en el menú y compararlo con FSR 3.1 después del paso 1.
- **DLSS**: SDK nativo de Vulkan para Linux (NGX). No funciona en la RX 7800 XT, pero hace falta para
  los usuarios de NVIDIA.
- **XeSS / XeFG y OptiScaler**: Intel los distribuye solo como DLL de Windows. Opciones:
  un cargador de DLL de Windows (PE) dentro del proceso, o ejecutar toda la build bajo Proton con
  OptiScaler, al que le pasamos las entradas mediante la interfaz de DLSS.
  Verificado el 29.09: libxess.dll (la misma en DOOM: The Dark Ages, PRAGMATA, etc.) tiene
  una ruta de Vulkan (`xessVKCreateContext`, `xessVKExecute`), pero importa ~300 funciones:
  MSVCP140 (iostream), VCRUNTIME140 (excepciones de C++), UCRT, kernel32, setupapi, dxgi.
  Se decidió posponerlo; la ruta más realista es un helper bajo Wine con memoria compartida de Vulkan.

### 4. Generación de frames

- FSR 3.1 Frame Generation (incluido en FSR-Vulkan): un frame intermedio entre dos frames terminados,
  con los mismos vectores de movimiento; la interfaz debe dibujarse encima por separado (existe la redirección
  de la interfaz, que se puede renderizar en una capa aparte).
- XeFG: después de resolver lo de las DLL de Windows (ver arriba).
- Requisito: entrega de frames a través del presentador (la cola y VRR ya funcionan).

### 5. Otros

- Steam Deck: build portátil (patchelf, sin Nix), verificación de los presets a 1280x800.
- Seguir descargando el hilo de GPU (paso 2 de [parallel_gpu.md](../parallel_gpu.md)).
