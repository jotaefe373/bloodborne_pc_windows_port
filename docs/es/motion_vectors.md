> Traducción al español de `docs/motion_vectors.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Vectores de movimiento: mejoras tras el video del 2026-09-26

Material de partida: `video_2026-09-26_04-19-53.mp4`, FSR 3.1 Performance,
render 960×540 → salida 1920×1080, y `out/dev/t71.log`.
Esta es una descripción de los cambios actuales del árbol de trabajo, no una confirmación de la calidad en el juego.

Una pasada común para todos los G-buffer draws resultó demasiado cara: Performance funcionaba a aproximadamente
49 FPS con ella y a 77–78 FPS sin ella. Ahora los vectores de objetos están activados por defecto solo
para shaders con buffer de pose/huesos (tamaño de 640–16384 bytes, excepto el buffer común de la escena
de 864 bytes; paso de 16 bytes). En una ejecución de prueba con un umbral más estrecho de 1024 bytes,
esto redujo el número de draws procesados a unos 140 por frame, eliminó el desbordamiento
de la historia y dio unos 81–87 FPS. Los demás draws conservan los vectores de cámara baratos.
`BB_OBJECT_MOTION=0` desactiva toda la función, `BB_OBJECT_MOTION_ALL=1` restaura la pasada
común para A/B. El canal alfa del target auxiliar guarda la profundidad: si un draw normal posterior
tapó el objeto, su vector no se usa. La calidad del personaje y del arma en movimiento
tras la selección todavía hay que verificarla visualmente.

## Qué se detectó

- Al final del log original, en 600 frames: 257400 G-buffer draws, 256200 declarados
  en movimiento, solo 30000 recibieron posiciones anteriores (~11,7% de todos los draws).
  Esto es cobertura de dibujados, no porcentaje de píxeles. El contador antiguo no distinguía
  la causa de cada omisión.
- Para la historia se reservaba el tamaño de todo el vertex buffer, multiplicado por el número de
  instancias **junto con firstInstance**. Para los submeshes de buffers compartidos son posiciones
  sobrantes; el presupuesto era de 2097152 posiciones por frame.
- La historia no tenía una barrera propia entre escrituras/lecturas de los vertex shaders;
  la reutilización del anillo de parámetros host no esperaba a la GPU.
- Las escrituras desactivadas de todos los vértices se dirigían a un único elemento scratch.
- `CameraMotion::OnDisplayPass` reiniciaba Depth() antes de calcular las jitter phases:
  Performance recibía 8 fases en lugar de 32. En la reconstrucción de la posición a partir de la profundidad
  tampoco se tenía en cuenta el desplazamiento del viewport.

## Cambios

- El rango de la historia se determina por el min/max de los índices reales teniendo en cuenta baseVertex
  y primitive restart. FirstInstance se resta en el shader, en lugar de consumir memoria.
- Se guardan todos los draws directos de G-buffer que califican, desde su primera aparición.
  Se eliminó la heurística de cambio de constantes: consideraba en movimiento casi todos los draws
  y se saltaba el inicio del movimiento. La lectura solo es posible si coincide con el frame anterior.
- La clave incluye todas las descripciones de vertex streams, el shader, la dirección y el hash del contenido
  de los índices, el rango de vértices, las instancias y el número entre draws idénticos.
  Un cambio de topología o un frame omitido reinicia la historia correspondiente.
- Presupuesto: 4194304 posiciones/frame; los dos arrays juntos ocupan 128 MiB en lugar de 64 MiB.
  Si falta memoria, quedan los vectores de cámara. El log muestra por separado los guardados,
  las coincidencias, la falta de historia, la falta de memoria y los rangos no válidos.
- Se agregaron vertex-to-vertex barriers, espera de la GPU antes de reutilizar
  los parámetros host, coherent host memory y un seguimiento independiente del layout de la imagen de movimiento.
  La lectura repetida de la imagen no borra el indicador de presencia de vectores.
- Los accesos desactivados se evitan mediante ramificación. Para invocations repetidas de un mismo
  vértice indexado se usan escrituras atómicas de los componentes de la posición.
  Las posiciones detrás de la cámara y los vectores no numéricos/infinitos no se usan.
- Performance recibe 32 fases de jitter tras crear el FSR context. Los vectores de cámara
  se reconstruyen a partir de coordenadas unjittered; los vectores de objetos ya se obtenían
  de las clip positions antes del desplazamiento del viewport.

## Pruebas

Compilación y pruebas de CPU:

```bash
cd native_probe
nix-shell shell.nix --run 'bash build.sh && ninja -C out/gpu motion-history-test motion-shader-test && out/gpu/motion-history-test && out/gpu/motion-shader-test out/motion-shaders'
```

`test_motion_history.cpp` comprueba rangos u16/u32, restart, baseVertex negativo,
firstInstance, draws repetidos, cambio de topología, frame omitido, agotamiento del presupuesto,
desbordamiento y número de fases. También se superó una ejecución con AddressSanitizer/UBSan.

`test_motion_shaders.cpp` usa el backend SPIR-V real y crea VS/PS con
vectores y sin ellos. Los cuatro resultados pasaron `spirv-val --target-env vulkan1.3`.
Para repetirlo hace falta `spirv-val` de SPIRV-Tools:

```bash
for shader in out/motion-shaders/*.spv; do
    spirv-val --target-env vulkan1.3 "$shader" || exit
done
```

Logs de compilación/pruebas: `out/dev/motion-validation.log`. En el entorno de verificación no hay acceso a `/dev/dri`:
la calidad en la RX 7800 XT, los FPS y el porcentaje de cobertura tras los cambios
todavía no se han verificado. Una validación SPIR-V exitosa no demuestra que la imagen sea correcta.

## Próxima ejecución en el juego

Desde `game_files`:

```bash
BB_FRAME_STATS=1 BB_TOGGLE_FILE=out/dev/motion-toggles bash native_probe/run.sh 2>&1 | tee native_probe/out/dev/motion-run.log
```

El bit 29 en el archivo de toggles temporal desactiva solo la escritura de la historia. Para una
comparación correcta del rendimiento hay que ejecutar el juego con `BB_OBJECT_MOTION=0` y sin él:
la elección del pipeline y el target adicional se definen al iniciar el proceso.
Después de cambiar, dale a FSR algunos frames para actualizar la historia.
Comparar una misma escena: personaje/arma al correr, giro de cámara, combate, cámara quieta.
Tras ~600 frames, revisar `Object motion:`: `with history`, `capacity skips`, `unmatched`.

Limitaciones restantes: las mallas idénticas se emparejan según el orden de los draws, que
puede cambiar con el culling de objetos; el cambio de direcciones de los vertex buffers dinámicos
pierde la coincidencia. Los indirect draws, los tessellation/geometry shaders, MSAA y las pasadas
fuera del G-buffer siguen con vectores de cámara. La transparencia/partículas, la UI borrosa y el traslado
del escalado al nivel del renderizador no se resuelven con este cambio. El costo de escanear
índices y de las escrituras atómicas hay que medirlo en una ejecución real.

## 29 de septiembre: armas y esqueletos pequeños (ghosting de la sierra giratoria)

Video `video_2026-09-29_23-08-26.mp4`: el personaje está quieto, el disco de la sierra gira y deja
una estela. El log `BB_MOTION_SELECT_LOG=1` mostró la causa: el segundo buffer del vertex shader es
la paleta de huesos de 48 bytes cada uno (3x4), y en armas/utilería es de 96–384 bytes (2–8 huesos).
La regla «desde 640 bytes» no incluía esos dibujados; el disco solo recibía vectores de cámara,
es decir, para FSR estaba inmóvil.

Cambios:

- `Motion::ClassifyBuffer` (`motion_history.h`): 864 es la escena, ≥640 es el esqueleto de un personaje,
  96..639 múltiplo de 48 es un esqueleto pequeño. Los pipelines con cualquier esqueleto reciben la variante
  con vectores.
- Hay alrededor de mil esqueletos pequeños por frame; la mayoría son partes estáticas del mapa.
  Por eso pasan por un «gate»: el hash de la paleta se compara con el del frame anterior mediante una clave
  barata (`History::Moving`) antes de escanear los índices. Si coincide, el vector de cámara es exacto y
  no se escribe nada. Si cambió, se guardan las posiciones y, desde el frame siguiente, se usa el vector del
  objeto. El hash con el buffer de 416 bytes no sirve: cambia junto con la cámara en casi todos
  (verificado: desbordamiento de la historia y caída de FPS a ~40).
- Menú: «Mostrar vectores de movimiento (depuración)». Rojo/verde: |x|/|y|; azul: el
  píxel recibió un vector de objeto. `BB_MOTION_SELECT_LOG=1` imprime los shaders de G-buffer
  con los tamaños de buffers y la decisión.

Medición `out/motion-gated.log`: ~225 dibujados guardados y ~600 «inmóviles» por frame,
sin desbordamiento, 58–80 FPS en escenas del juego. Visualmente, la desaparición de la estela
en la sierra todavía hay que confirmarla.
