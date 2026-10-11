> Traducción al español de `README.ru.md` (original en ruso). Puede quedar desactualizada si el original cambia.
> Este README corresponde al port original para **Linux** de deadinside28; para la versión de Windows, ver `README.md` (en inglés).

# bbport — port nativo de Bloodborne para Linux

[English](README.md) · [Русский](README.ru.md) · **Español**

bbport ejecuta el ejecutable original de *Bloodborne* para PlayStation 4 (CUSA03173,
versión del juego 1.09) directamente en una PC con Linux x86-64. No es un emulador universal: el propio
código x86-64 del juego se ejecuta de forma nativa, las bibliotecas del sistema de PS4 las reemplaza un pequeño runtime
escrito para este juego, y el trabajo de la GPU se traduce a Vulkan mediante un renderer basado en
[shadPS4](https://github.com/shadps4-emu/shadPS4), muy adaptado a Bloodborne, hasta llegar
al upscaling temporal AMD FSR 3.1, FSR 4 y FSR 4.1.1.

> **En el repositorio no hay archivos del juego.** Necesitas tu propio dump de Bloodborne (CUSA03173, v1.09).
> El proyecto no está afiliado a Sony Interactive Entertainment, FromSoftware ni AMD.

**Estado: experimental, jugable.** El juego arranca, carga las partidas guardadas y
se puede jugar (el Sueño del Cazador y varias zonas de Yharnam) con sonido,
gamepad y guardado. No se ha comprobado una partida completa; se ha probado a fondo una sola máquina
(Linux, AMD Radeon RX 7800 XT, Mesa/RADV).

## Qué se ha hecho

- **Ejecución nativa.** El eboot se convierte de antemano en una imagen de memoria plana, a la que se enlazan como
  código nativo libc y libSceFios2 de PS4. Sin emulación de CPU ni
  traducción de instrucciones: el código del juego corre a toda velocidad.
- **Frame rate desbloqueado.** Los parches de la comunidad (`patches/Bloodborne.xml`) pasan
  la simulación al tiempo real de frame; ~90 FPS en 4K con FSR 4 Balanced en una RX 7800 XT, ~150 FPS en
  1440p con FSR 4 Quality. Hay modos de 30/60/90 FPS.
- **Upscaling temporal adaptado a este juego.** Bloodborne no tiene velocity buffer, así que el port
  calcula los motion vectors por su cuenta: el movimiento de la cámara, a partir de la profundidad y las matrices de la escena; el movimiento
  de los objetos (personajes, tela, armas), a partir de las posiciones de los vértices del frame anterior. La escena se desplaza
  con un jitter subpíxel (Halton) y se dibuja a resolución reducida; el upscaler completa
  la salida (720p para Steam Deck, 1080p, 1440p o 2160p), y la interfaz se dibuja directamente a la resolución de salida.
  - **FSR 3.1** (FireBurn/FSR-Vulkan).
  - **FSR 4 (INT8, modelo v07)** en tarjetas gráficas con las capacidades de shaders de Vulkan necesarias,
    incluidas RDNA2/3 (ver requisitos).
  - **FSR 4.1.1 (INT8)**: la DLL de AMD 4.1.1 se graba una sola vez bajo vkd3d-proton, y sus pases
    se reproducen de forma nativa en Vulkan; el resultado **coincide bit a bit** con la DLL. Los assets
    se generan en tu máquina a partir de tus propias DLL (`tools/fsr4cap`).
  - Más rápido que los shaders de la propia AMD en RDNA3: los pases finales de FSR 4 y 4.1.1 se reescribieron con escritura
    a través de shared memory (3.5 y 2.3 veces más rápidos, bit a bit iguales); FSR 4 en 4K en una RX 7800 XT
    cuesta ~4 ms en lugar de ~6.
- **Procesamiento multihilo de comandos de GPU.** El flujo de comandos de PS4 se analiza en un hilo, y
  el enlazado de recursos y la grabación de draws en otro (pipeline de dos etapas), además de un hilo aparte de
  grabación de comandos Vulkan e hilos auxiliares para las copias de memoria. Al inicio del proyecto, el único
  hilo de GPU limitaba el juego a ~26 FPS; ahora 90–150 FPS según la resolución y la escena.
- **Menú dentro del juego** (Insert o L3+R3): upscaler, preset, nitidez, resolución de salida, efectos
  del juego (aberración, DoF, desenfoque de movimiento, SSAO, antialiasing del juego, SSR, nivel de detalle de los modelos).
- **Launcher en GTK4** y **AppImage** para Steam Deck.

## En qué se diferencia de shadPS4

| | shadPS4 | bbport |
|---|---|---|
| Alcance | Emulador universal de PS4, muchos juegos | Un solo juego: Bloodborne v1.09 |
| Carga | Cargador ELF propio y emulación del kernel en tiempo de ejecución | El eboot se convierte de antemano (`scripts/`) en una imagen con libc/Fios2 de PS4 enlazadas; un cargador en C la mapea y le pasa el control al juego (cargador y runtime: ~5 mil líneas) |
| Bibliotecas del sistema | HLE amplio del SO de PS4 | Un runtime pequeño (`src/runtime_*.c`) justo para lo que llama Bloodborne: memoria, hilos, sincronización, archivos, sonido (incluido ATRAC9), gamepad, partidas guardadas, AppContent |
| GPU | Núcleo de video y recompilador de shaders de shadPS4 | El mismo núcleo (incluido, GPL) con ~200 cambios marcados (`bbport:`) y módulos nuevos: pipeline de draws de dos etapas, memoización del estado del pase y de los conjuntos de texturas, targets de escena reducidos, motion vectors, FSR 3.1/4/4.1.1, captura de frames, profiler de GPU |
| Hilo de GPU | Un solo hilo procesa todo el flujo de comandos (cuello de botella en Bloodborne) | El análisis y la grabación de draws van en hilos distintos; el trabajo escala según el número de hilos (incluido el Steam Deck) |
| Upscaling | — | Temporal (FSR 3.1, FSR 4, FSR 4.1.1) con motion vectors propios y jitter del juego |
| Parches del juego | Los archivos de parche los aplica el emulador | Los mismos parches de la comunidad se compilan al arrancar (`scripts/patches.py`); resolución de render, efectos y FPS, desde el launcher |

Sin shadPS4, bbport no existiría: su renderer y su recompilador de shaders son la base de la parte gráfica.

## Requisitos

- Linux x86-64, tarjeta gráfica con Vulkan 1.3. Probado: AMD RX 7800 XT, Mesa 26 (RADV).
  FSR 4 / 4.1.1 requieren shader Float16, Int8/Int16, productos punto enteros,
  linear compute derivatives y extended storage image formats; FSR 4.1.1 además
  requiere `VK_VALVE_shader_mixed_float_dot_product`. Una opción no soportada se reemplaza
  por FSR 3.1 antes del primer frame y no está disponible en el menú del juego.
- Tu propio dump descifrado del juego: la carpeta `CUSA03173` (eboot.bin, sce_module, ...), versión 1.09.
- Para compilar: GCC, CMake, Ninja, Python 3, glslang, SDL3, headers de Vulkan y las bibliotecas de
  `shell.nix`. Con [Nix](https://nixos.org) todo se toma de `shell.nix` automáticamente.

## Compilación y ejecución

```bash
git clone --recursive <este repositorio> bbport && cd bbport
bash build.sh                        # compila out/bb-probe y out/gpu/libbbgpu.so
BB_GAME_DIR=/ruta/a/CUSA03173 bash run.sh
```

o mediante el launcher (elegir la carpeta del juego, la configuración, «Iniciar»):

```bash
bash launcher/bb-launcher.sh         # launcher/install-desktop.sh lo añade al menú de aplicaciones
```

Por defecto, la carpeta del juego se busca junto al repositorio (`../CUSA03173`). Las partidas guardadas y la caché de shaders
van en `user/` (en el launcher puedes elegir otra carpeta), y la configuración en `bbport.ini`. Gamepad mediante
SDL3; hay una distribución de teclado de respaldo.

**Cambio de resolución y presets:** para una salida distinta de 1080p (720p en Steam Deck, 1440p, 4K), todo el juego
se dibuja a la resolución del preset, que define un parche al arrancar; es la ruta más rápida.
En ese caso, cambiar la salida o el preset en el menú del juego requiere «Aplicar y reiniciar el juego».
La opción «Cambio de resolución en vivo» (launcher, menú del juego, `bbport.ini`
`live_resolution=0|1|auto`; **desactivada por defecto**) en cambio deja el juego en 1080p y
escala sus targets sobre la marcha: 720p/1080p/1440p/4K y los presets cambian sin reiniciar. Esto
es más costoso: el juego cree que dibuja a 1080p y dibuja más (por ejemplo, unas 8 veces más
fuentes de luz pequeñas), y parte de los targets se copia entre tamaños; actívala solo en tarjetas gráficas
de escritorio potentes (`auto` la activa en GPUs dedicadas con 8+ GB, excepto NVIDIA anteriores a
Turing). La salida 1080p y TAA siempre usan la ruta en vivo.

**TAA:** opción de antialiasing independiente en el launcher y en el menú del juego; se cambia sobre la marcha.
Funciona a la resolución de salida sin el modelo de FSR; el preset de FSR se conserva para volver
a cambiar. El Native AA de FSR ejecuta la reconstrucción sobre la resolución completa y
puede ser más pesado que tener el antialiasing desactivado. TAA también añade procesamiento al frame.

**Mods:** el launcher carga mods descomprimidos desde carpetas independientes (con `dvdroot_ps4/`, con una carpeta
contenedora adicional o directamente con carpetas del juego como `chr/`; no importa si los nombres van en mayúsculas o minúsculas), con interruptores
y orden de carga. **Parches de terceros:** archivos XML en formato shadPS4 en la carpeta `patches/` del directorio
de datos; se activan en el launcher. Más detalles: [mods y parches](docs/MODS.md).

**Idioma del launcher:** ruso o inglés (por defecto, el del sistema).

**Cámara libre y debug menu del juego** (v1.09): activa las casillas correspondientes en el launcher
o en el menú del juego y reinicia el juego. Para la cámara se usa
[el parche de Lance McDonald de GoldHEN](https://github.com/GoldHEN/GoldHEN_Patch_Repository/blob/main/patches/xml/Bloodborne-Orbis.xml):
mantén Cross y pulsa L3 para cambiar de modo (teclado: Space + Z).
La cámara no necesita fuentes; es incompatible con el parche Enemy Control.
Para el debug menu, primero instala `DbgFont14h.ccm` y `DbgFont14h.tpf` de
[Debug Menu and XML Patch](https://www.nexusmods.com/bloodborne/mods/253) en
`dvdroot_ps4/font/` dentro de la carpeta del juego. Si los archivos no están o están vacíos, el arranque se detendrá
con una explicación. El menú se abre con el touchpad izquierdo / Tab; el touchpad derecho es Backspace.
Las coordenadas de toque se transmiten desde los gamepads SDL; Back/Select reemplaza el clic izquierdo en gamepads
sin superficie táctil. El menú de configuración del port se sigue abriendo con Insert / L3+R3.

Las consultas de occlusion de la GPU por ahora devuelven contadores de píxeles artificiales
(`PixelPipeStatDump`), y `IT_SET_PREDICATION` no está implementado. La cámara libre permite
comprobar la visibilidad, pero no añade GPU occlusion culling.

**Assets de los upscalers** (no están en el repositorio; FSR 3.1 no los necesita):

```bash
bash tools/fetch_fsr4_assets.sh      # FSR 4 v07 (MIT, compilados por Q2RTX desde el código de AMD)
# FSR 4.1.1: desde tus propias DLL de AMD (por ejemplo, FSR4_LATEST de OptiScaler); requiere Proton (GE-Proton):
bash tools/fsr4cap/build_assets.sh <amd_fidelityfx_upscaler_dx12.dll> <amd_fidelityfx_loader_dx12.dll>
```

**AppImage** (Steam Deck): `bash build.sh && bash packaging/appimage.sh` →
`dist/Bloodborne-bbport-x86_64.AppImage`; los datos en `~/.local/share/bbport`, `--play` inicia
el juego sin la ventana del launcher (modo de juego). Los modelos de FSR 4.1.1 no se incluyen en el paquete: genéralos (ver
arriba) en `~/.local/share/bbport/fsr4_411` (`BB_PACKAGE_FSR411=1` mete la `fsr4_411` local en el
AppImage para tus propios dispositivos). En Steam Deck elige la salida 1280×720 (el juego es 16:9; en la
pantalla de 1280×800 habrá franjas estrechas).

**Agregar el AppImage a Steam** («Agregar un juego que no es de Steam»): no hace falta configurar nada,
la herramienta de compatibilidad no importa. (Steam carga su overlay en todos los juegos que no son de Steam; el AppImage
lo quita antes de iniciar sus programas, por eso no hay overlay de Steam en el juego.) Si Steam inicia los juegos sin FUSE (NixOS: el sandbox FHS de Steam; el AppImage entonces termina con
*Cannot mount AppImage*), en las opciones de lanzamiento indica

```
TMPDIR=$HOME/.cache APPIMAGE_EXTRACT_AND_RUN=1 NO_CLEANUP=1 %command%
```

Así, en el primer arranque el AppImage se descomprimirá (~2 GB, `~/.cache/appimage_extracted_*`, ~10 s),
y a partir de entonces ejecutará esa copia; una versión nueva del AppImage se descomprimirá de nuevo, y la copia antigua se puede
borrar. Sin `TMPDIR`, la descompresión iría a `/tmp` de Steam, que ahí está en la memoria RAM.
` --play` después de `%command%`: inicio sin el launcher.

**NVIDIA en el AppImage:** el paquete busca automáticamente el driver Vulkan de NVIDIA de 64 bits instalado en la máquina
y lo carga junto con los drivers de AMD/Intel incluidos. Se usan
las bibliotecas de NVIDIA de esa máquina, para que su versión coincida con el módulo del kernel. En las distribuciones
de Linux habituales están disponibles en `/usr/lib*`; en NixOS, el `/nix/store` interno del AppImage puede ocultar
el driver del host. En ese caso hay que copiar las bibliotecas de NVIDIA a una carpeta accesible e indicar
`BB_NVIDIA_LIB_DIR=/ruta/a/las/librerías` (el manifiesto de NVIDIA también debe ser accesible).
Los `VK_DRIVER_FILES`/`VK_ICD_FILENAMES` explícitos se respetan. Para comprobar el driver dentro del paquete:

```bash
./Bloodborne-bbport-x86_64.AppImage --vulkan-info 2>&1 | tee bbport-vulkan.log
```

Un usuario confirmó que arranca con FSR 3 en una GTX 1060 6GB (Fedora 44, NVIDIA 580.178.04);
elegir FSR 4 producía una ventana negra. En esa configuración usa FSR 3.

MangoHud viene incluido en el AppImage; activa su casilla en el launcher.
Al ejecutar desde el código fuente, MangoHud hay que instalarlo aparte. Un arranque de diagnóstico
con `VK_LOADER_LAYERS_DISABLE=~implicit~` también desactiva MangoHud.

Variables útiles: `BB_FRAME_STATS=1` (estadísticas de frames), `BB_GPU_PROFILE=1` (tiempo de GPU por
pase), `BB_FSR4_PROFILE=1` (tiempo de cada pase de FSR 4), `BB_UPSCALER=taa|fsr3|fsr4|fsr411|off|none`,
`BB_FRAMES_AHEAD=N` (cuántos frames puede adelantarse el flujo de comandos a la GPU; por defecto 1, 0: sin
límite), `BB_PRESENT_THREAD=0` (presentación en el hilo de vblank, como antes), `BB_LIVE_RES=1` (cambio
de resolución sin reiniciar en lugar del parche al arrancar para salidas distintas de 1080p),
`BB_PAD_RECORD=archivo` / `BB_PAD_REPLAY=archivo` (grabación de un recorrido con F9 y su repetición en las pruebas),
`BB_GC_BUDGET_MB=N` (presupuesto de la caché de texturas, como en GPUs integradas), `BB_PRESENT_DUMP_TRIGGER=archivo`
con `BB_PRESENT_DUMP_COUNT=N` (captura de N frames presentados seguidos).
Más detalles en [docs/](docs); últimos cambios: [docs/CHANGES_2026-10-02.md](docs/CHANGES_2026-10-02.md),
[docs/CHANGES_2026-10-03.md](docs/CHANGES_2026-10-03.md).

## Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `src/` | Cargador (`probe.c`) y runtime HLE |
| `scripts/` | Preparación de la imagen del juego, enlazado de módulos, compilador de parches |
| `gpu/` | Biblioteca del renderer: núcleo de video de shadPS4 con los cambios del port (`gpu/VENDOR.txt`), capas intermedias, menú ImGui, runtime de FSR 4.1.1 (`gpu/shadps4/video_core/renderer_vulkan/fsr411`) |
| `launcher/`, `packaging/` | Launcher GTK4; paquete Nix y AppImage |
| `patches/` | Parches de la comunidad para Bloodborne |
| `tools/` | Utilidades de desarrollo: ejecuciones por script, interruptores A/B, benchmark de FSR, reescritura de shaders de FSR 4, `fsr4cap` (grabación y extracción de FSR 4.1.1) |
| `tests/` | Pruebas del cargador, el runtime, los parches y el renderer |
| `docs/` | Notas y mediciones ([upscaler](docs/upscaler.md), [GPU multihilo](docs/parallel_gpu.md), [motion vectors](docs/motion_vectors.md), [plan](docs/ROADMAP.md), [registro de desarrollo](docs/DEVELOPMENT_LOG.ru.md)) |

Pruebas: `bash build.sh --test`, `python3 -m unittest discover -s tests` y
`ninja -C out/gpu motion-history-test ui-composition-test scene-resolution-test motion-shader-test`.

## Qué viene después

- Más paralelismo de CPU en el procesamiento de comandos de GPU (mayor división de la etapa de grabación de draws)
  con escalado a todos los hilos; es lo más importante para el Steam Deck.
- Async compute para el upscaler (en 4K el frame queda limitado por la GPU).
- XeSS (superresolución) y generación de frames XeFG mediante un helper bajo Wine con memoria compartida de Vulkan
  (prototipo del puente de memoria: `tools/bridge_helper`); DLSS para quienes tienen NVIDIA; entradas del upscaler
  en un formato compatible con el enfoque de OptiScaler.
- Generación de frames (primero FSR 3.1 FG), máscaras de reactividad y transparencia para partículas y niebla.
- Corrección de las condiciones de carrera en los shaders de FSR 4.1.1 de AMD cuando el ancho de salida no es múltiplo de 64 (por ejemplo,
  1600×900), igual que ya se corrigió la condición de carrera junto al borde izquierdo en FSR 4 v07 a 1080p.
- Prueba del AppImage en Steam Deck; salida HDR.

## Agradecimientos y licencias

bbport se distribuye bajo la **GNU GPL v2 o posterior** ([LICENSE](LICENSE)), ya que contiene código de shadPS4
(GPL-2.0-or-later). Los componentes de terceros conservan sus licencias:
núcleo de video y recompilador de shaders [shadPS4](https://github.com/shadps4-emu/shadPS4) (GPL-2.0+),
[sirit](https://github.com/shadps4-emu/sirit), [half](https://half.sourceforge.net/),
[FSR-Vulkan](https://github.com/FireBurn/FSR-Vulkan) de FireBurn (MIT; FSR 3.1 sobre Vulkan y
el proveedor de FSR 4 v07), AMD FidelityFX SDK (MIT), [LibAtrac9](https://github.com/Thealexbarney/LibAtrac9)
(MIT), [Dear ImGui](https://github.com/ocornut/imgui) (MIT), fuentes DejaVu,
[dxil-spirv](https://github.com/HansKristian-Work/dxil-spirv) (MIT, para generar los assets de FSR 4.1.1).
Parches del juego: Kyo, Lance McDonald, auser1337, illusion, emoose y otros miembros de la comunidad
(`patches/Bloodborne.xml`). Las DLL y los datos del modelo FSR 4 de AMD no se distribuyen aquí.
