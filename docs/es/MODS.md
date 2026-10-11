> Traducción al español de `docs/MODS.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Mods de archivos

En el launcher apareció el grupo **Mods**: selección de carpeta, un interruptor general,
activación de cada mod y flechas para el orden de carga. Los cambios se aplican en el
siguiente arranque. El mod activado que está más abajo tiene mayor prioridad; cuando
coinciden archivos, en el registro se indica qué mod reemplazó al anterior.

Por defecto se usa `bbport/mods/`, y en AppImage,
`~/.local/share/bbport/mods/`. Descomprime el mod descargado así:

```text
mods/
  Nombre del mod/
    dvdroot_ps4/
      chr/...
      param/...
      menu/...
```

También se aceptan:

- `Nombre del mod/app0/dvdroot_ps4/...` y `Nombre del mod/CUSA03173/dvdroot_ps4/...`;
- una carpeta contenedora sobrante, como la que queda tras descomprimir un archivo en una carpeta con su nombre:
  `Nombre del mod/Nombre del mod v1.2/dvdroot_ps4/...` (al lado puede haber readme/imágenes);
- un mod sin `dvdroot_ps4`, que contiene directamente las carpetas del juego: `Nombre del mod/chr/...`,
  `Nombre del mod/parts/...` (`chr`, `parts`, `map`, `menu`, `msg`, `param`, `sfx`,
  `sound`, `font` y otras carpetas de `dvdroot_ps4`).

Las mayúsculas y minúsculas de los nombres en el mod no importan: `DVDROOT_PS4/Chr/C0000.chrbnd.dcx` de un mod armado
en Windows reemplaza el `dvdroot_ps4/chr/c0000.chrbnd.dcx` del juego. Antes, un archivo así
se agregaba al lado con su propio nombre y el juego no lo veía. En el registro de arranque se ve cuántos
archivos del juego reemplazó el mod y cuántos agregó: `Mods: 12 game files replaced, 0 added`.
Si el mod debería reemplazar archivos, pero muestra `0 game files replaced`, revisa las rutas dentro del mod.
Los archivos ZIP/7z hay que descomprimirlos antes. Se admiten reemplazos ya preparados
de archivos de `dvdroot_ps4`: texturas, modelos, parámetros, interfaz, sonido y fuentes.
El gestor no combina el contenido de dos archivos `.dcx`/`.bnd` iguales: el último
reemplazo gana por completo.

Para una carpeta de shadPS4 ya preparada funciona el directorio vecino
`CUSA03173-mods/dvdroot_ps4/...` junto a `CUSA03173/`. Se conecta automáticamente
antes de los mods de la lista. El interruptor general también lo desactiva. También puedes elegir
como carpeta de mods una carpeta que contenga directamente `dvdroot_ps4`; esa carpeta
se conecta completa, sin lista de mods individuales.
La convención `-mods` se verificó con el
[código fuente de shadPS4](https://github.com/shadps4-emu/shadPS4/blob/main/src/core/file_sys/fs.cpp).

Los originales del juego no se sobrescriben. Durante el arranque se crea un árbol
combinado de enlaces aparte en el directorio de datos `out/mod-game-*`; la lectura, stat y
el listado de directorios ven los reemplazos elegidos y el resto de los archivos originales.
Los `/app0` y `/hostapp` del juego son de solo lectura. Las partidas guardadas permanecen
en la misma carpeta de antes y se pueden escribir. Al terminar normalmente o al detener desde el
launcher, el árbol temporal se elimina. Después de un SIGKILL/apagado por fallo puede
quedar; esos directorios no se usan en el siguiente arranque.

Los mods que reemplazan `eboot.bin`, `sce_module` o `sce_sys`, los inyectores de DLL y los plugins
de scripts no son compatibles con este cargador. Los parches de código ejecutable siguen
en el sistema existente `patches/` / `BB_PATCHES`. No se aceptan enlaces simbólicos dentro del mod.
La compatibilidad de un mod concreto con CUSA03173 1.09 la determina
su autor.

Para ejecutar desde la terminal:

```sh
BB_GAME_DIR=/path/to/CUSA03173 BB_MODS_DIR=/path/to/mods bash run.sh
BB_GAME_DIR=/path/to/CUSA03173 BB_MODS_ENABLED=0 bash run.sh
```

El orden y las desactivaciones se guardan en el directorio de datos `mods.json`:

```json
{"order": ["Primero", "Segundo"], "disabled": ["Primero"]}
```

Las carpetas nuevas se activan automáticamente y se agregan al final en orden alfabético.
`BB_MODS_CONFIG` cambia la ruta del perfil. `BB_MOD_TRACE=1` con `BB_MODS_DIR` muestra
las primeras lecturas de los archivos realmente conectados, para diagnóstico.

# Parches de terceros (XML de shadPS4)

La carpeta `patches/` en el directorio de datos (en AppImage, `~/.local/share/bbport/patches/`; en el launcher,
el grupo **Parches de terceros**, donde también puedes elegir otra carpeta). Sirven los archivos XML de parches en
formato shadPS4/GoldHEN: se toman los `Metadata` para `AppVer="01.09"` y `eboot.bin`; los archivos con
`TitleID` de otros juegos se omiten. La activación por defecto viene del `isEnabled` del archivo; la selección en el
launcher se guarda en `patches.json` del directorio de datos:

```json
{"enabled": ["archivo.xml/Nombre del parche"], "disabled": ["archivo.xml/Otro parche"]}
```

Se admiten líneas `bytes`, `bytes16/32/64`, `float32/64`, `utf8`, `utf16`.
Un parche con líneas `mask` (búsqueda por patrón) o con una dirección fuera del eboot se omite por completo,
con un mensaje en el registro. Los parches de terceros se aplican después de los integrados
(`patches/Bloodborne.xml`): si se superponen, gana el de terceros. Desde la terminal:
`BB_PATCHES_DIR=/ruta BB_PATCHES_CONFIG=/ruta/patches.json bash run.sh`.

Los parches que reemplazan punteros en tablas (como `60 FPS++` y `90 FPS++`), el cargador
los traslada a la dirección real de la imagen. Antes, esos parches detenían el arranque con el error
`patch overlaps a relocation`.

# Nitidez de TAA

Los ajustes `sharpen` y `sharpness` ahora también funcionan para TAA, en el launcher y en el
menú del juego. El rango es **0…1**; con 0 o con el interruptor desactivado no hay pasada
adicional. RCAS se aplica a la escena terminada antes del HUD. En el historial de TAA se guarda
el color previo al aumento de nitidez, para que esta no se intensifique con la acumulación repetida.
Las zonas uniformes conservan el color original, incluido HDR; no hace falta un buffer adicional.
