> Traducción al español de `docs/upscaler.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Upscaling temporal y generación de frames — análisis del frame y plan

## TAA nativo y assets de FSR 4 faltantes (2026-10-01)

`upscaler=taa` / `BB_UPSCALER=taa` es un modo independiente de AA temporal a resolución
nativa, disponible en vivo en el launcher y en el overlay. Usa el jitter existente y los
motion vectors de cámara/objetos, reproyección, rechazo por profundidad y clipping de
vecindad 3×3 en un solo pase de compute con dos historiales RGBA16F en ping-pong. El historial guarda
la profundidad en alfa; el alfa original de la escena se conserva gracias a la fusión HDR. El HUD se
compone después y nunca entra en el historial. Los cambios de salida y los cambios de AA/proveedor
reinician el historial. TAA usa las dimensiones de Native AA y conserva el preset de FSR guardado,
y no reserva un contexto de FSR ni ejecuta un modelo de FSR/RCAS.
Aun así añade trabajo de GPU en comparación con desactivar el AA temporal; el costo de
rasterización a 4K nativo también se mantiene. La ruta de compatibilidad explícita `BB_RENDER_RES` debe estar sin definir.

FSR Native AA no es un pass-through rápido: renderiza a la resolución de salida y
además ejecuta la reconstrucción temporal (incluido el modelo en el caso de FSR 4) y el
sharpening opcional. Por eso puede ser más lento que no usar AA con la misma salida.

Los assets de FSR 4.1.1 tienen niveles separados de 1080p/2160p y modelos estándar/Ultra:
`t1080_m0`, `t1080_m1`, `t2160_m0`, `t2160_m1`. Las salidas por encima de 1080p necesitan el nivel 2160,
independientemente del preset. Que falte `t2160_m0/spd.spv` significa que faltan
assets, no un fallo de funcionalidades de la GPU. Estos assets no se incluyen: genera el conjunto
completo con `tools/fsr4cap/build_assets.sh` y colócalo en `BB_FSR411_DIR` o en `fsr4_411`
del directorio de datos del paquete. Los fallos fatales de assets ahora seleccionan FSR 3.1 en
la configuración en vivo, de modo que el menú muestra el proveedor activo, conserva el error y
permite reintentar FSR 4 después de cambiar la salida o instalar los assets.

`taa-shader-test` comprueba la salida SPIR-V real para acumulación, clipping, desoclusión
por profundidad, historial inválido y movimiento fuera del frame en Vulkan (Lavapipe funciona).
`out/taa-appimage-build.log` registra estas comprobaciones, los round trips de configuración y 64
pruebas de Python. `out/taa-live-validation.log` y `out/taa-appimage-validation.log`
comprueban TAA a 1080p/720p/1440p/4K, TAA ↔ FSR 3 y un modelo de FSR 4.1.1 del nivel 2160 faltante
en un solo proceso de juego, incluidas capturas de la salida y movimiento de cámara.
`out/taa-launcher-validation.log` comprueba los controles GTK reales y la configuración guardada.
TAA todavía no se ha probado en la GTX 1060 del tester.

## El parche al inicio vuelve a ser el predeterminado para salidas distintas de 1080p (2026-10-02)

La ruta en vivo descrita abajo hizo que el Steam Deck y una GTX 1060 + Haswell de 4 núcleos cayeran a 7–8 FPS
(AppImage de la versión 0.1: 40–50 FPS en el Deck). Con las asignaciones del guest a 1920×1080, el
post-procesado del juego se queda en 1080p incluso con salida 720p, los pases de compute del guest resuelven los proxies de escena
de vuelta a 1080p en cada frame (RX 7800 XT, 720p FSR 3 Performance en 4 núcleos: 826 vs 576
draws/frame, 185 vs 210 FPS), y en GPUs sin exportación de stencil desde shader cada copia de
profundidad/stencil requería nueve draws.

- `run.sh` vuelve a parchear el tamaño de render del juego para salidas distintas de 1080p (como en 0.1) y
  lo marca con `BB_AUTO_RENDER_RES=1`, para que un reinicio dentro del juego lo recalcule. Los cambios de preset y de salida
  requieren entonces un reinicio (el menú lo ofrece). `BB_LIVE_RES=1` selecciona la ruta en vivo.
  La salida 1080p y TAA mantienen la ruta en vivo.
- Los proxies de escena de profundidad/stencil vuelven a necesitar `VK_EXT_shader_stencil_export`; sin él, estos
  targets se quedan en resolución nativa (como en 0.1). `BB_SCENE_STENCIL_BITS=1` sigue forzando el
  resampler portable para las pruebas.

## Cambios de resolución en vivo (2026-10-01)

El selector de salida dentro del juego ahora redimensiona los targets del host de 720p/1080p/1440p/2160p en un
límite de pase de presentación. Los presets usan `output / scale`, incluidos tamaños de rasterización por encima de
1080p (4K Quality: 2560×1440; Native AA: 3840×2160). Las asignaciones del guest se quedan en
1920×1080; `run.sh` ya no inserta un parche de resolución para las opciones de salida normales.
Se conserva el override de compatibilidad explícito `BB_RENDER_RES`.

`SceneTargets` resuelve y retira los proxies antiguos antes de cambiar de tamaño. Los recursos de FSR
y el historial se reconstruyen para la nueva entrada/salida, con esperas de finalización tanto para
FSR 3 como para FSR 4. La ruta de 1080p mantiene la reconstrucción HDR antes del post del juego;
las demás salidas reconstruyen los proxies de escena ya con tonemapping en el primer pase de Scaleform
y luego dibujan la geometría del HUD/menú en el target de tamaño de salida. El display buffer también
se redimensiona. La identificación de shaders de video evita que un pase de post a pantalla completa
de tamaño nativo se confunda con la UI.

Los pases de compute del guest conservan sus tamaños de dispatch nativos y pueden resolver los proxies
de vuelta a 1080p. Este cambio no escala todos los pases de post-procesado; el rendimiento
y el detalle intermedio pueden diferir de los antiguos tamaños de render parcheados al inicio.

Verificación: `out/dev/live-resolution-summary.log` cambia la salida, el preset y FSR
apagado/encendido en un mismo PID. `BB_PRESENT_DUMP_TRIGGER` captura el display buffer completo del host
(incluido el HUD) en `BB_DUMP_DIR`. Las capturas confirman buffers reales de 720p/1440p/2160p.
`scene-resolution-test` cubre round trips de color/profundidad/stencil a través de
proxies tanto más pequeños como más grandes que la asignación del guest. `BB_PRESET_FILE` acepta
`preset [output-index [upscaler-index]]` para cambios por script equivalentes a los del menú.

Analizador de frames: `BB_CAPTURE_TRIGGER=<file> BB_CAPTURE_DIR=<dir>`; al crear el archivo se registra
el siguiente frame (límite: el pase que escribe un display buffer): pases, targets, shaders,
texturas muestreadas y el primer 1 KiB de las constantes enlazadas para pases pequeños y primeros draws.

## El frame de Bloodborne (1920x1080, Sueño del Cazador / Pesadilla)

| Pases | Qué |
|---|---|
| primer pase de un frame | copia del target de UI anterior al display buffer (sRGB) |
| sombras | profundidad D32 de 4096x4096 |
| G-buffer | 6 targets de 1920x1080 (RGBA8 x3, albedo sRGB, B10G11R11, RGBA16F) + profundidad D32S8 |
| iluminación | volúmenes de luz en dos targets B10G11R11 |
| color de escena | RGBA16F de 1920x1080, también draws forward/transparentes y efectos |
| niebla volumétrica | compute, lee la profundidad lineal (R32F de 1920x1080) y la compone en el color de escena |
| efectos a media resolución | RGBA8 de 960x540 con profundidad a media resolución |
| post | combine/pirámide de bloom en RGBA16F / B10G11R11 |
| tonemap | a RGBA8 de 1920x1080 (el target de UI) |
| AA del juego | ping-pong RGBA8 de 1920x1080 después del tonemap (a omitir al hacer upscaling) |
| UI | draws con máscara de stencil sobre el mismo target RGBA8 |

No hay velocity buffer, tampoco con la cámara en movimiento: los motion vectors se calculan.

## Constantes de escena (864 bytes, enlazadas por la mayoría de los pases)

Firma: `[0]=3000 (far) [1]=1/3000 [4]=1920 [5]=1080 [6]=1/1920 [7]=1/1080`.

| Floats | Significado |
|---|---|
| 8–19 | matriz de vista, filas 3x4 (rotación + traslación); el único bloque que cambia con la cámara |
| 36–51 | proyección inversa (0.700285 = 1/1.42799, 0.39391 = 1/2.53865) |
| 52, 57, 62, 63 | proyección (filas 52–67), profundidad D3D 0..1: x 1.42799, y 2.53865, z 1.00002 / -0.0500679 (near 0.05, far 3000) |
| 112–175 | matrices de las cascadas de sombras |
| 180–191 | vista inversa (cámara a mundo), 3x4 (176–179: 2, 8, 15, 0) |

Las matrices del frame anterior no están ahí; el port las guarda por su cuenta.

## Plan

1. Encontrar las constantes de escena en cada frame (firma), guardar la vista/proyección anteriores.
2. Motion vectors de cámara: pase de compute a partir de la profundidad y las matrices actuales/anteriores hacia un
   target RG16F; vista de depuración para comprobarlos. Movimiento de objetos más adelante (reproducción del vertex shader con las
   constantes del frame anterior a través del recompilador).
3. Jitter: desplazamiento subpíxel de las posiciones en clip space en los pases de escena (recompilador).
4. Upscaler en la etapa de color de escena (antes del post y de la UI): primero FSR 3.1 (abierto, Vulkan nativo,
   también generación de frames), luego DLSS (nativo en Linux), XeSS/XeFG y OptiScaler mediante un
   loader para sus DLL de Windows.

## Estado

- Motion vectors de cámara: verificados reproyectando el frame anterior (`BB_DEBUG_MOTION=1`,
  toggles 1<<22 frame reproyectado, 1<<23 mapa de error): la geometría estática coincide.
- FSR 3.1 (`BB_UPSCALER=fsr3`, submódulo FireBurn/FSR-Vulkan): color de escena antes del
  combine de post-procesado (compute shader 9a9cf8a9), 1:1, RGB reescrito (el juego guarda datos
  en el alfa). El toggle 1<<24 lo desactiva en tiempo de ejecución.
- Jitter: desplazamiento del viewport de la geometría de escena (dibujada con la profundidad de escena, no quads
  a pantalla completa), Halton(2,3) de 8 fases; signo comprobado por nitidez (correcto 255, invertido 208, desactivado 271:
  el jitter 1:1 cambia aliasing de alta frecuencia por una imagen ligeramente más suave). El toggle 1<<25 lo desactiva.
- Diferencia de frame a frame estando quieto: ~33% menor con FSR.
- Falta: movimiento de objetos animados (personajes, tela, follaje), máscaras de reactividad/transparencia
  para partículas y niebla, escalado de la resolución de render, generación de frames.

## 2026-10-01: FSR 4 con salida 1440p/2160p no funcionaba (parpadeo y temblor)

Video `video_2026-10-01_03-58-59.mp4` (salida 3840x2160, FSR 4 Performance): parpadeo y temblor
de todos los objetos. Causa: en este modo el upscaler no se ejecutaba en absoluto, pero el jitter seguía
activado: a la pantalla llegaba el frame de escena estirado, cada frame desplazado según su fase de Halton.

1. El pase de UI se identificaba por el tamaño exacto del target `BB_RENDER_RES` (1916x1078), pero el juego reserva
   targets con la altura alineada (1916x1080; en las constantes de escena también 1916x1080). `RunScaled` no
   se llamaba ni una sola vez (en el log no aparecía `UI: native composition`). Ahora se admite una alineación
   de hasta 8 píxeles (`RenderTarget`), y el tamaño de escena para FSR se toma de las constantes de escena
   (`CameraMotion::RenderSize`, `SceneSize`).
2. Después de eso, FSR 4 fallaba con `external image registration failed (-1000069000)`: `RunScaled`
   creaba image views nuevas en cada frame, y el registro de FSR 4 admite ocho. Ahora se usan los mismos
   `CachedView` que en la ruta de Native AA.

Verificación con dump (`BB_DUMP_TRIGGER=<archivo> BB_DUMP_DIR=<carpeta>`, `BB_DUMP_FRAMES`, por defecto 8:
entrada de FSR, motion vectors y salida, raw): con la cámara quieta, el PSNR entre frames consecutivos de la salida es de
~45 dB frente a ~28 dB en la entrada con jitter; al girar la cámara y al caminar no hay estelas. Los FPS en este
modo son ~107 en lugar de ~220: antes FSR 4 simplemente no se ejecutaba.

Pendiente: los sprites (de 4 índices) que van al color de escena con la profundidad de escena (resplandores, lucecitas)
siguen sin desplazarse con el jitter (regla «≤ 6 índices = pase a pantalla completa»).

## 2026-10-01: FSR 4 más rápido — el pase post (2.9 → 0.8 ms en 4K)

Mediciones: `BB_FSR4_PROFILE=1` (tiempo de cada pase de FSR 4, parche del proveedor en el submódulo,
ver `gpu/patches/fsr-vulkan`), benchmark fuera del juego `out/gpu/fsr4-bench` (`ninja -C out/gpu
fsr4-bench`; `--stats`: registros e instrucciones según RADV). 4K Balanced (2260x1272 → 3840x2160),
RX 7800 XT: todo FSR 4 tarda 5.8 ms, de los cuales **post 2.5–2.9 ms** (no es la red neuronal: las últimas capas,
el pixel shuffle 2x2 y la mezcla con el historial), los 12 pases del modelo 2.4 ms, pre 0.55.

Causa: cada hilo calcula un bloque de 2x2 píxeles de salida y los escribe uno por uno en tres imágenes
(estado recurrente, historial, salida): cada instrucción de escritura de la wave escribe píxeles salteados
(uno sí, uno no). Quitando cualquiera de las tres escrituras, el pase se aceleraba entre 1.3 y 4 veces con el mismo código.

Solución: `tools/fsr4_optimize.sh` descompila el post (spirv-cross), `tools/fsr4_post_lds.pl`
reúne el bloque de 16x16 del workgroup en shared memory y escribe en filas continuas, glslang
lo vuelve a compilar en `fsr4_shaders/opt/`; `vk_fsr4.cpp` lo toma de ahí (`BB_FSR4_OPT=0`:
el original). Dos sutilezas, encontradas comparando las salidas:
- spirv-cross traduce el desempaquetado int8 con signo (`OpBitcast` a `i8vec4`) como `unpack8(uint)`
  (sin signo): sin la corrección el resultado es totalmente distinto (PSNR 17 dB);
- los valores en shared memory deben seguir siendo float: el compilador convierte un half leído de shared memory
  en una escritura de 16 bits, y esta redondea a unorm8 de otra manera.

`tools/fsr4_verify.sh` compara el post original y el optimizado para todos los presets con salida
1080p/1440p/4K sobre entradas pseudoaleatorias: 1440p y 4K, idénticos bit a bit; post 4K 2.1–3.5 →
0.81–0.87 ms, 1440p 1.2–1.5 → 0.36–0.38 ms, 1080p 0.37–0.69 → 0.20–0.22 ms. En el juego (4K
Balanced): FSR 4 5.8 → 4.0 ms, frame de GPU 13.1 → ~11.6 ms; a partir de ahí los FPS quedan limitados por la CPU (el hilo
de comandos de GPU espera las copias de la memoria del guest, «host copies» ~20%).

Hallado de paso: **el FSR 4 original en el nivel 1080 (salida 1920x1080) no es determinista**: de
una ejecución a otra, con las mismas entradas, cambia una franja junto al borde izquierdo (columnas 0–132), es decir,
hay en algún lugar una condición de carrera o una lectura de memoria no inicializada en el modelo/proveedor. Con salida 1080p esto
puede producir parpadeo junto al borde izquierdo del frame. No investigado.

La máscara de reactividad ya no se calcula con FSR 4 (FSR 4 no la acepta).

### Qué más se comprobó (en el mismo lugar, 4K Balanced)

- **A/B en un mismo proceso** (`ab.sh`, bit 24: FSR desactivado, copia de UI sin upscaling): 86.5 FPS con
  FSR 4 frente a 87.7 sin él. Tras optimizar el post, el frame queda limitado por la CPU (hilo de comandos de GPU,
  espera de copias de la memoria del guest), no por la GPU. Async compute para FSR (solaparlo con el inicio del
  frame siguiente) no daría más que ese ~1%; se pospone hasta acelerar la parte de CPU; además,
  requiere reordenar los comandos de UI y de presentación del frame N después del trabajo del frame N+1.
- **WMMA (`VK_KHR_cooperative_matrix`, RADV en RDNA3 lo soporta)**: prototipo del pase 1
  del modelo (bloque residual de 16 canales: 3x3 16→16, 1x1 16→32 ReLU, 1x1 32→16): 0.85 ms en la primera
  versión, 0.49 ms con disposición por palabras en shared memory, frente a 0.30 ms del dot4 original.
  La aritmética en WMMA ocuparía ~0.1 ms, pero con 16 canales la colocación de los tiles, los epílogos a través de shared
  memory y la ocupación (6 waves/SIMD, límite por LDS) se comen la ganancia. El techo es de alrededor de 1 ms para
  los 12 pases con una reescritura manual minuciosa de cada uno; no se ha empezado.
- `RADV_PERFTEST=cswave32` (wave32 para compute): FSR 4 más lento, 4.2 → 5.4 ms.
- El pase pre (0.54 ms) no está limitado por la escritura (0.50 ms sin escritura).

## 2026-10-01: parpadeo de FSR 4 junto al borde izquierdo con salida 1080p — condición de carrera en el pase 11 del modelo

El no determinismo del nivel 1080 (ver arriba) es un error en el shader del modelo v07, pase 11 (decodificador,
de 1/4 → 1/2 de resolución). Cada hilo corresponde a un píxel de la entrada a 1/4 de resolución y escribe un bloque de 2x2 de la salida
a 1/2 de resolución. El dispatch redondea el ancho a 64 hilos, y los hilos que quedan más allá del ancho de la entrada no
se detienen: en el nivel 1080 (entrada de 480 de ancho), los hilos 480..511 escriben los píxeles de salida
960..1023, es decir, los primeros píxeles de la fila siguiente (una fila de cualquier tensor ocupa 15360 bytes), y
compiten con sus verdaderos autores. Con salida 4K el ancho de 960 es divisible entre 64 y no hay error.

`tools/fsr4_pass11_guard.pl` añade una salida anticipada para los hilos fuera del límite (el tamaño se toma de la
comprobación de vecinos del propio pase); `tools/fsr4_optimize.sh` lo compila en `fsr4_shaders/opt`
para todos los presets junto con el post; `vk_fsr4.cpp` y el benchmark toman de `opt/` cualquier pase.
`tools/fsr4_verify.sh`: 1440p/4K, bit a bit como el original (ahí la protección no se activa); 1080p,
mismo resultado de una ejecución a otra, y las diferencias con el original tras el primer frame están solo en la
antigua franja junto al borde izquierdo.

Hallado en el proceso: spirv-cross traduce todos los desempaquetados int8 con signo (`OpBitcast` a `v4char`)
como `unpack8(uint)` sin signo; en el pass 11 hay nueve formas distintas. La corrección es común a los
scripts: `tools/Fsr4SpirvCrossFixes.pm` (todos los `unpack8` a través de un helper con signo).

## 2026-10-01: FSR 4.1.1 — qué tiene por dentro y cómo ejecutarlo en Vulkan (exploración)

Fuente: `amd_fidelityfx_upscaler_dx12.dll` 4.1.1.2740 de OptiScaler (`FSR4_LATEST`).
- En la DLL está el proveedor `ffxProvider_FSR4_Int8` / `Fsr4Int8UpscalerModel` (versión «FSR4-i8 4.1.1»).
  1028 contenedores DXIL (25.7 MB): pases del modelo `fsr4_model_v07_fp8_no_scale_pass1..12` (+ `_post`),
  270 variantes de `prepass`, 144 de `postpass`, `fsr_rcas_pass` y un FSR 3.1/2 de respaldo. No hay datos comprimidos.
- A pesar del «fp8» en el nombre, los pases del modelo son DXIL normal con `dot4AddPacked` (dot4 int8), sin
  extensiones de AMD (WMMA). La arquitectura es la misma v07 (12 pases), pero los pesos y sesgos no están incrustados en el
  shader, sino que se leen de `InitializerBuffer` (t18, typed buffer), los tamaños de los tensores del cbuffer
  `CsTensorSizes`, y el scratch es `u11`. Cada pase tiene 9 variantes: la cuadrícula está incrustada (niveles 1080 / 4K /
  8K: 480x270, 960x540, 1920x1080 para el pase 5) y, al parecer, los presets.
- `amdxcffx64.dll` (loader 2.3.0.2913, lo carga Proton) tiene los mismos pases FP8 de FSR 4 y generación de frames
  por ML (`mlfi_*`); no hay un modelo INT8 aparte. `FSR4_INT8` 4.0.2 es `v07_i8`, es decir,
  lo que el port ya usa.
- dxil-spirv (HansKristian-Work/dxil-spirv, se compila desde el código fuente) traduce los pases a
  SPIR-V correcto: `dxil-spirv <pass> --enable-shader-i8-dot --ssbo-uav --use-reflection-names`.

Lo que falta para un proveedor propio de 4.1.1: la correspondencia de los contenedores (preset, nivel, pase),
el contenido de `InitializerBuffer`, los valores de `CsTensorSizes`, las permutaciones de prepass/postpass, las constantes y
los tamaños de los dispatches. El camino más fiable no es desensamblar el código x86 del proveedor, sino grabar un frame:
un pequeño programa de prueba sobre la FFX API (DX12, MinGW) bajo Wine/Proton con vkd3d-proton, selección explícita
del proveedor «FSR4-i8» mediante un override de versión, y una capa de Vulkan que escriba los pipelines (SPIR-V de
dxil-spirv), el contenido de los buffers y los tamaños de los dispatches. Luego, reproducirlo con un proveedor propio
mediante el mismo benchmark (`fsr4-bench`), verificando contra la salida grabada.

## 2026-10-01: FSR 4.1.1 en el port (upscaler=fsr411)

El modelo de AMD 4.1.1 (INT8) funciona de forma nativa en Vulkan y coincide con la DLL bit a bit.

**Cómo se obtuvo.** `tools/fsr4cap/fsr4cap.exe` (C, MinGW) llama a la FidelityFX API 2.3 de
`amd_fidelityfx_loader_dx12.dll` con la versión 4.1.1 explícita y, sustituyendo las tablas de métodos de D3D12,
graba todo lo que hace la DLL bajo vkd3d-proton: pipelines (DXIL), root signatures,
descriptores, cargas, constantes, dispatches. Un frame son 29 dispatches: SPD de autoexposición, prepass,
pass0_post, pases del modelo 1..12 (cada uno seguido de su `_post`, que pone a cero el borde del tensor), postpass, RCAS.
- Hay dos modelos: m0 (Native..Performance) y m1 (Ultra Performance, relación 3.0); los pesos ocupan 128 KB
  (`InitializerBuffer`). Niveles: t1080 (salida hasta 1920x1080), t2160 (mayor, incl. 2560x1080).
- Los tensores se calculan a partir de la salida alineada a 8; la tabla `CsTensorSizes` (17 tamaños), el número de
  grupos y las constantes (MLSR como en v07, pero width/height sin alinear e `inv_scale = 1 / scale`;
  SPD; RCAS) se verifican con `extract.py` sobre 20 grabaciones.
- dxil-spirv traduce el DXIL igual que vkd3d-proton: `--mixed-float-dot-product`
  (`VK_VALVE_shader_mixed_float_dot_product`, dot2 en half con acumulación en float); sin él,
  PSNR de 40 dB en lugar de coincidencia exacta. `--class-bindings` (parche) distribuye los registros SRV/UAV/
  CBV/samplers en los bindings +0/+32/+64/+96; el runtime enlaza los recursos por nombre.
- `fsr411/fsr411.cpp` es un núcleo independiente sobre Vulkan (el juego y `fsr4-bench --fsr411`).
- `verify.sh`: DLL y reproducción con las mismas entradas, 8 frames: idénticos bit a bit en
  1080p (ambos modelos), 1440p, 2560x1080, 4K (ambos modelos). 1600x900 diverge solo junto al borde
  derecho, donde la propia DLL no es determinista (condición de carrera en sus shaders cuando el ancho del tensor no es múltiplo de 64).

**Aceleración.** El postpass se reescribió usando workgroup memory al nivel del ensamblador SPIR-V
(`postpass_lds.py`; la traducción a través de GLSL es imprecisa: se pierden `DenormPreserve` y la colocación exacta de
`RelaxedPrecision`, y algo más cambia el resultado): 2.18 → 0.95 ms en 4K, bit a bit como la DLL.
Todo FSR 4.1.1: 1.09 ms en 1080p (1280x720), 4.2 ms en 4K Balanced. En el juego (4K Balanced),
el upscaler tarda 4.12 ms frente a 4.32 ms del v07 acelerado.

**Generación de los assets** (por el usuario, a partir de sus propias DLL; en el repositorio no hay nada de AMD):

    bash tools/fsr4cap/build_assets.sh <amd_fidelityfx_upscaler_dx12.dll 4.1.x> <amd_fidelityfx_loader_dx12.dll 2.3.x>

Se necesita nix-shell (o MinGW, cmake, ninja, python3, SPIRV-Tools, umu-run), red para dxil-spirv y
los headers del FidelityFX SDK, y Proton (GE-Proton). Las DLL las tiene, por ejemplo, OptiScaler
(`FSR4_LATEST/`) y los juegos con FSR 3.1/4. Una compilación desde cero produce los mismos archivos; `VERIFY=1` al final
compara con la DLL.

**Corrección al A/B de arriba («el frame queda limitado por la CPU»).** Esas mediciones se hicieron mientras 12 procesos
colgados de shadPS4 ocupaban un núcleo cada uno. En un sistema libre: «host copies» 1.6%, espera de la GPU ~41%: el frame
queda limitado por la GPU, así que async compute para FSR vuelve a tener sentido.
