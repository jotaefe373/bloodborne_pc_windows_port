> Traducción al español de `docs/TEMPORAL_REVIEW_2026-10-01.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Revisión del TAA y de las entradas de los upscalers temporales — 2026-10-01

## Estado del proyecto

bbport es un runtime de Linux especializado para el código x86-64 original de Bloodborne
CUSA03173 1.09, con traducción de los comandos de GPU a Vulkan basada en shadPS4. Es un
port experimental: el cargador, el HLE de llamadas al sistema, el sonido, la entrada, las partidas guardadas, la interfaz de ajustes
dentro del juego y el temporal upscaling ya están implementados. En esta copia de trabajo están disponibles el código fuente, la
biblioteca compilada, el dump del juego y una partida guardada. No hay metadatos de Git del proyecto, por lo que el historial
de cambios y la limpieza del árbol de trabajo no se pueden verificar.

Esta revisión no confirma la partida completa ni la portabilidad a otros drivers y a la Steam Deck.
En la documentación siguen las limitaciones: occlusion queries artificiales,
predication incompleta, efectos transparentes sin vectores de movimiento propios y condiciones de carrera
en el modelo de FSR 4.1.1 para algunos tamaños de salida no estándar.

## Video y causas

Grabación original `video_2026-10-01_21-21-02.mp4`: 94.89 s, 2560×1080, 60 FPS.
En ella se alternan TAA, FSR 4.1.1, FSR 4 y FSR 3.1. En la arquitectura, los contornos delgados
y el arma en movimiento se ve inestabilidad temporal. En el menú está activado el motion blur del juego;
su contribución no se puede atribuir al TAA. El archivo `video_fixed_taa.mp4` tiene la misma duración,
pero otro tamaño de frame (2560×1082); esta grabación por sí misma no confirma la corrección del renderizador.
Los frames y secuencias para revisar están en `out/dev/temporal-review/`.

Se identificaron errores en el código, independientemente de la valoración subjetiva del video:

1. **Profundidad FP16 en la historia del TAA.** El paso de half cerca de 1 es de aproximadamente 0.000488.
   Con near ≈ 0.05, las superficies lejanas se vuelven indistinguibles. El umbral de comprobación de la historia
   era menor que ese paso, por lo que la historia podía tanto descartarse por error como mezclarse
   con otra superficie. La historia ahora es RGBA32F.
2. **Cámaras no comparables.** La comprobación anterior comparaba la profundidad del frame anterior con la profundidad
   del actual. Ahora el punto actual se lleva al sistema de la cámara anterior, y la comparación
   se hace con la profundidad esperada allí. La tolerancia se escala según la profundidad en perspectiva.
3. **Anulación de los vectores lejanos.** `depth >= 0.99999` se consideraba cielo y recibía movimiento
   cero. Para una proyección con near ≈ 0.05, far 3000, este umbral afecta a la geometría aproximadamente
   desde 1875 unidades. Ahora solo la clear depth 1 se considera fondo infinito; el fondo recibe el
   movimiento de rotación de la cámara sin traslación. La geometría lejana recibe la reproyección normal.
4. **Profundidad FP16 en el object motion.** En RGBA16F se perdía la profundidad usada para comprobar
   si el vector queda tapado por un draw posterior. El buffer y el formato del pipeline gráfico ahora son
   RGBA32F; la comprobación de profundidad ya no acepta otra superficie lejana con una tolerancia amplia
   y fija. Los vectores finales para FSR siguen siendo RG16F.
5. **Comprobación de profundidad mezclada en los bordes.** El TAA interpolaba la profundidad de la historia entre
   superficies distintas. Ahora los cuatro bilinear taps se comprueban de forma independiente, el color se compone
   solo a partir de los taps coherentes; con cobertura parcial se reduce el peso de la historia.
6. **Acumulación demasiado débil a lo lejos.** La reducción depth-adaptive anterior del peso a 0.8/0.5
   se reemplazó por un peso de 0.98…0.85 en función del movimiento cuando la historia es válida (el peso
   mínimo se alcanza a 8 px/frame). Una ejecución de diagnóstico con peso 0.94 mostró
   oscilaciones residuales de color entre las fases de jitter incluso con la historia aceptada. El RGB de la historia
   se limita al rango de los vecinos del frame actual.
7. **Jitter de profundidad en pendientes y detalles finos.** La profundidad ahora se traslada a la
   posición estable del píxel según el gradiente local unilateral, con protección contra
   discontinuidades de la superficie. Para motion/depth se elige la superficie más cercana en un 3×3;
   el color y el rango de clipping se toman alrededor del píxel de color original. Esto permite que
   los contornos delgados conserven la historia cuando foreground/background se alternan bajo el jitter.
8. **Direccionamiento inestable de la historia con movimiento casi nulo: la causa principal del
   temblor del TAA detectado.** Antes, la parte entera y la fraccionaria de la coordenada bilinear
   se calculaban después de sumar un número de píxel grande con un motion muy pequeño.
   En la GPU esto producía partes incoherentes y la selección del texel vecino. Ahora primero
   se separa el propio motion: `base = p + ivec2(floor(motion))`,
   `fraction = motion - floor(motion)`. La prueba de regresión en el píxel x=2010
   con un movimiento de alrededor de −0.00003 px reproduce el error de la fórmula antigua:
   color 0.250000 en lugar del esperado 0.739985. La fórmula corregida pasa la prueba.

Las correcciones 3–4 se refieren a las entradas comunes de TAA/FSR 3.1/FSR 4/FSR 4.1.1. Los algoritmos y
los assets de ML de AMD no se modificaron. La comprobación de ABI shader/pipeline y el dump de diagnóstico de object
motion se actualizaron junto con el formato del recurso.

## Pruebas y limitaciones

Compilación de `bbgpu`, `taa-shader-test`, `camera-motion-test` mediante `shell.nix`.
En una GPU Vulkan pasaron 18 casos del shader TAA de producción: reset con NaN, unjitter, acumulación,
clipping, desoclusión de superficie, salida del frame, historia NaN, profundidad lejana exacta,
rechazo de otra superficie lejana, traslación de cámara, borde con historia parcialmente válida,
cielo y frontera cielo/geometría, profundidad inclinada con ambos signos de jitter, contorno delgado,
reducción de la persistencia con movimiento y movimiento negativo muy pequeño en una coordenada grande.
Pasaron 6 pruebas del shader camera-motion de producción:
geometría lejana, rotación del cielo, ausencia de traslación del cielo, exclusión del jitter,
object vector válido y obsoleto. Log: `out/dev/temporal-review/tests.log`.
Prueba adicional de unjitter: `out/dev/temporal-review/taa-final-tests.log`.
Reproducción de la regresión de la fórmula antigua y 18 pruebas exitosas de la nueva:
`out/dev/temporal-review/regression-proof.log`.
Prueba final del juego: `out/dev/temporal-review/subpixel-validation.log`.
Pasaron las 64 pruebas de Python existentes (`out/dev/temporal-review/python-tests.log`).

Live smoke: se cargó una copia de la partida guardada en el Sueño del Cazador. En un mismo proceso se probaron
TAA → Off → FSR 3.1 → FSR 4 v07 → FSR 4.1.1 → TAA, salida 2560×1440,
seis frames finales por modo y movimiento de cámara entre cambios.
Los FSR funcionan con entrada de 1706×960; el TAA, con 2560×1440 nativo. Los contextos de AMD
se confirmaron en el log; no hubo sustitución por FSR 3.1. El proceso terminó normalmente;
después de compilar los pipelines, se mantuvo el límite de 60 FPS. Logs y frames raw:
`out/dev/temporal-review/subpixel-validation.log`, `out/dev/temporal-review/far-refined/`.
El motion blur y el AA del juego están desactivados en la configuración de prueba.

Con la cámara quieta, en la zona de la torre lejana (x=2010…2099, y=400…779),
el cambio absoluto medio de RGB entre seis frames de TAA bajó de 1.892 a
0.299 en la escala 0…255, unas 6.3 veces. Tras volver a TAA: 0.279.
En la ejecución final, FSR 3.1: 0.328, FSR 4: 0.278, FSR 4.1.1: 0.364.
Este es un resultado de la escena elegida, no una evaluación universal de calidad: la resolución de entrada
de FSR difiere de la del TAA, y el antes/después aquí compara precisamente la última corrección
del direccionamiento de la historia. Datos: `out/dev/temporal-review/far-refined/stability.json`;
ejecución anterior: `out/dev/temporal-review/final-validation.log`.

Para diagnóstico se agregó `BB_TAA_DIAGNOSTICS=1`: el alfa de la salida del TAA contiene el peso de la historia
aceptada en lugar de 1. Se puede leer en `BB_DUMP_TRIGGER` raw RGBA16F. El RGB no cambia;
el alfa de la historia sigue conteniendo la depth. El modo normal conserva la salida opaca.
Los modos adicionales 2 y 3 muestran el color actual o la historia limitada;
la imagen de diagnóstico de la historia permite comparar la lectura directa con la reproyección.
Estas comparaciones revelaron el error de direccionamiento incluso con la historia aceptada y motion casi nulo.

El código fuente y `out/gpu/libbbgpu.so` están actualizados. Se recompiló
`dist/Bloodborne-bbport-x86_64.AppImage` (832 MiB); el `--vulkan-info` empaquetado
detectó correctamente la RX 7800 XT mediante RADV. Logs: `appimage-build.log` y
`appimage-vulkan.log` en `out/dev/temporal-review/`. La ejecución completa del juego descrita arriba
se hizo con la biblioteca local; no se hizo una ejecución completa aparte del juego con la AppImage.

Estas pruebas confirman correcciones concretas, pero no demuestran que desaparezca cualquier
parpadeo en el juego. El movimiento de objetos según el historial de vértices, las transparencias, los materiales
animados, la selección de LOD y la geometría subpíxel con una fuerte reducción de resolución
siguen requiriendo verificación en escenas específicas.

Costo de la precisión completa: las dos historias del TAA ocupan 253 MiB en lugar de 127 MiB en 4K;
el object motion, 127 MiB en lugar de 63 MiB con render en 4K. Esto también aumenta el consumo
de ancho de banda de memoria. Una posible optimización siguiente es una depth R32F aparte
manteniendo el color y el motion en FP16, con las mismas pruebas de corrección.

Para regresiones:

```sh
nix-shell shell.nix --run 'ninja -C out/gpu taa-shader-test camera-motion-test && out/gpu/taa-shader-test && out/gpu/camera-motion-test'
```

El enfoque con movimiento para todos los píxeles de entrada concuerda con las recomendaciones de
[integración de AMD FSR 3.1](https://gpuopen.com/presentations/2024/FidelityFX_Super_Resolution_3-1_Release-Overview_and_Integration.pdf).
