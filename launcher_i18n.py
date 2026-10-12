"""Launcher translations (launcher.py keeps its English strings).

install_ui_language() translates what the launcher shows: texts of every widget (they all pass
through tkinter's Misc._options, at creation and on configure), window titles, message boxes,
the file dialog title, the option descriptions and the launcher's own log lines. Game output is
logged elsewhere and stays as the game prints it. Keeping the strings in launcher.py untouched
means upstream changes to it merge without conflicts.
"""
import locale
import re
import tkinter as tk
from tkinter import filedialog, messagebox

UI_LANGUAGES = [("English", "en"), ("Español", "es")]

# Exact texts (also single lines of multi-line messages).
ES = {
    # Main window
    "Bloodborne PC Launcher": "Lanzador de Bloodborne PC",
    "Native Windows Port (bbport) Launcher": "Lanzador del port nativo para Windows (bbport)",
    "Game Executable (eboot.bin):": "Ejecutable del juego (eboot.bin):",
    "Browse...": "Examinar...",
    "Performance & Render Options:": "Rendimiento y render:",
    "Frame Rate Target:": "FPS objetivo:",
    "Render Resolution:": "Resolución de render:",
    "Fullscreen": "Pantalla completa",
    "Anisotropic Filtering:": "Filtrado anisotrópico:",
    "Game Language:": "Idioma del juego:",
    "Launcher Language:": "Idioma del launcher:",
    "Present Mode:": "Modo de presentación:",
    "Features & Toggles:": "Funciones:",
    "⚙  All XML Patches...": "⚙  Todos los parches XML...",
    "⌨  Mouse & Keyboard...": "⌨  Ratón y teclado...",
    "Vanilla mode": "Modo original",
    "Everything on": "Todo activado",
    "Upscaler (FSR 3.1)": "Escalado (FSR 3.1)",
    "FPS patch (Uncap / 60 / 90)": "Parche de FPS (sin límite / 60 / 90)",
    "Overlay menu": "Menú del juego",
    "HUD stats": "HUD de rendimiento",
    "Enable mods folder (mods/)": "Carpeta de mods (mods/)",
    "Resolution scaling": "Escalado de resolución",
    "Back up saves on launch": "Respaldar partidas al jugar",
    "Open": "Abrir",
    "Skip Intro & Logos": "Saltar intro y logos",
    "Performance Patch (Kyo)": "Parche de rendimiento (Kyo)",
    "Disable Motion Blur": "Quitar desenfoque de movimiento",
    "▶  LAUNCH BLOODBORNE": "▶  JUGAR BLOODBORNE",
    "■  Stop": "■  Detener",
    "Launcher Log:": "Registro del launcher:",
    "Hide Vulkan warnings": "Ocultar avisos de Vulkan",
    "✓ Verify Setup": "✓ Verificar instalación",
    "Copy log": "Copiar registro",
    "Clear": "Limpiar",
    "Open launcher.log": "Abrir launcher.log",
    # Option descriptions
    "16x anisotropic filtering of scene textures (recommended)":
        "Filtrado anisotrópico 16x de las texturas de la escena (recomendado)",
    "8x anisotropic filtering": "Filtrado anisotrópico 8x",
    "4x anisotropic filtering": "Filtrado anisotrópico 4x",
    "2x anisotropic filtering": "Filtrado anisotrópico 2x",
    "Game's default anisotropic filtering (no override)": "El filtrado propio del juego (sin forzar)",
    "Newest frame replaces a queued one; no tearing (default)":
        "El frame más nuevo reemplaza al que esperaba; sin tearing (por defecto)",
    "Frames wait for the display refresh; no tearing, more latency":
        "Los frames esperan al refresco del monitor; sin tearing, más latencia",
    "Frames are shown at once; lowest latency, may tear":
        "Los frames se muestran al instante; mínima latencia, puede haber tearing",
    # XML patches dialog
    "Search:": "Buscar:",
    "Category:": "Categoría:",
    "Select Visible": "Marcar visibles",
    "Deselect Visible": "Desmarcar visibles",
    "Recommended Defaults": "Recomendados",
    "Save & Apply": "Guardar y aplicar",
    "Cancel": "Cancelar",
    "Performance & Fixes": "Rendimiento y arreglos",
    "Visuals & Camera": "Gráficos y cámara",
    "Gameplay & Cheats": "Jugabilidad y trucos",
    "Framerate & Engine": "FPS y motor",
    "Resolutions & Grids": "Resoluciones y rejillas",
    "Debug & Tools": "Depuración y herramientas",
    # Mouse & keyboard dialog
    "Mouse & Keyboard Settings": "Ajustes de ratón y teclado",
    "Mouse & Keyboard Controls": "Controles de ratón y teclado",
    "Configurable mouse and keyboard controls with real-time in-game synchronization.":
        "Controles de ratón y teclado configurables, aplicados al juego en tiempo real.",
    "Enable Mouse & Keyboard Mode": "Activar ratón y teclado",
    "Camera & Sensitivity Options": "Cámara y sensibilidad",
    "Horizontal Sensitivity (X):": "Sensibilidad horizontal (X):",
    "Vertical Sensitivity (Y):": "Sensibilidad vertical (Y):",
    "Mouse Deadzone:": "Zona muerta del ratón:",
    "Mouse Smoothing:": "Suavizado del ratón:",
    "Invert Horizontal Camera (X)": "Invertir cámara horizontal (X)",
    "Invert Vertical Camera (Y)": "Invertir cámara vertical (Y)",
    "Control Bindings": "Asignación de controles",
    "Left Click (LMB):": "Clic izquierdo:",
    "Shift + Left Click:": "Shift + clic izq.:",
    "Right Click (RMB):": "Clic derecho:",
    "Shift + RMB / Tab:": "Shift + clic der. / Tab:",
    "Middle Click / Q:": "Clic central / Q:",
    "Space:": "Espacio:",
    "Arrow Keys / 1,2,3,4:": "Flechas / 1,2,3,4:",
    "Right Hand Attack (R1) / Trick Normal": "Ataque derecho (R1)",
    "Strong / Charged Attack (R2)": "Ataque fuerte (R2)",
    "Left Hand Weapon / Firearm (L2)": "Arma izquierda (L2)",
    "Trick Weapon Transform (L1)": "Transformar arma (L1)",
    "Lock-On Target / Reset Camera (R3)": "Fijar objetivo (R3)",
    "Character Movement (Left Stick)": "Moverse (stick izq.)",
    "Dodge / Roll / Quickstep / Sprint (Circle)": "Esquivar / correr (Círculo)",
    "Interact / Action / Pick Up / Talk (Cross)": "Interactuar (X)",
    "Use Equipped Quick Item (Square)": "Objeto rápido (Cuadrado)",
    "Use Blood Vial / Heal (Triangle)": "Vial de sangre (Triángulo)",
    "Jump / Gestures (L3)": "Saltar / gestos (L3)",
    "Gestures Menu (Touchpad Left)": "Gestos (touchpad izq.)",
    "Game Menu / Options (Options)": "Menú (OPTIONS)",
    "Blood Bullets & Weapon Cycling (D-Pad)": "Balas / armas (cruceta)",
    "Save & Close": "Guardar y cerrar",
    # Message boxes and dialogs
    "Select Bloodborne eboot.bin": "Selecciona el eboot.bin de Bloodborne",
    "No log yet": "Aún no hay registro",
    "launcher.log is created the first time you launch the game.":
        "launcher.log se crea la primera vez que lanzas el juego.",
    "Please select eboot.bin or the game folder first.": "Primero selecciona eboot.bin o la carpeta del juego.",
    "Invalid Path": "Ruta no válida",
    "Could not find eboot.bin in:": "No se encontró eboot.bin en:",
    "Verification Passed": "Verificación correcta",
    "All components are ready for launch!": "¡Todo está listo para jugar!",
    "Pre-Launch Verification Failed": "Falló la verificación previa",
    "Quit": "Salir",
    "Bloodborne is still running. Stop it and quit?": "Bloodborne sigue abierto. ¿Detenerlo y salir?",
    "Launcher Language": "Idioma del launcher",
    "Restart the launcher to change its language.": "Reinicia el launcher para cambiar su idioma.",
    # Pre-launch verification
    "Missing eboot.bin in game directory:": "Falta eboot.bin en la carpeta del juego:",
    "Please ensure your dumped game folder contains eboot.bin.":
        "Comprueba que la carpeta de tu dump contiene eboot.bin.",
    "eboot.bin is empty (0 bytes) in:": "eboot.bin está vacío (0 bytes) en:",
    "Expected: Bloodborne CUSA03173 with Update 1.09 merged.":
        "Se esperaba: Bloodborne CUSA03173 con la actualización 1.09 fusionada.",
    "Why blocked: Upstream port patches and memory hooks rely strictly on the 1.09 executable layout.":
        "Motivo: los parches y hooks de memoria del port dependen exactamente del ejecutable 1.09.",
    "To bypass (not recommended): set environment variable BB_SKIP_GAME_CHECK=1.":
        "Para saltarlo (no recomendado): define la variable de entorno BB_SKIP_GAME_CHECK=1.",
    "[OK] Game Title & Version: Bloodborne CUSA03173 v1.09 verified":
        "[OK] Título y versión: Bloodborne CUSA03173 v1.09 verificado",
    "[OK] Game asset directory: dvdroot_ps4 detected": "[OK] Datos del juego: dvdroot_ps4 encontrado",
    "[NOTE] dvdroot_ps4 not detected directly under game root (custom layout or loose files)":
        "[NOTA] dvdroot_ps4 no está en la raíz de la carpeta del juego (estructura propia o archivos sueltos)",
    "Launcher script run.bat not found in:": "No se encontró run.bat en:",
    "[OK] Launcher script: run.bat ready": "[OK] Script de arranque: run.bat listo",
    "Compiled game executable 'bbport.exe' was not found in:":
        "No se encontró el ejecutable compilado 'bbport.exe' en:",
    "The source code has not been compiled yet.": "El código aún no se ha compilado.",
    "Please run 'build.bat' in the project directory to compile the project before launching.":
        "Ejecuta 'build.bat' en la carpeta del proyecto para compilarlo antes de jugar.",
    "Compiled 'bbport.exe' is empty (0 bytes) in:": "El 'bbport.exe' compilado está vacío (0 bytes) en:",
    "[OK] GPU subsystem: statically linked into bbport.exe": "[OK] Núcleo GPU: integrado en bbport.exe",
    "[OK] Runtime library: out/SDL3.dll staged": "[OK] Librería: out/SDL3.dll presente",
    "[WARN] Runtime library: out/SDL3.dll not staged in out/": "[AVISO] Librería: falta out/SDL3.dll",
    "Game patch script not found at:": "No se encontró el script de parches en:",
    "[OK] Patch engine: scripts/patches.py ready": "[OK] Motor de parches: scripts/patches.py listo",
    "[OK] Vulkan runtime: vulkan-1.dll loaded successfully": "[OK] Vulkan: vulkan-1.dll cargado",
    "[WARN] Vulkan runtime: vulkan-1.dll not found in standard system paths":
        "[AVISO] Vulkan: no se encontró vulkan-1.dll en las rutas del sistema",
    # Launcher log
    "Ready. Select your eboot.bin and press Launch Bloodborne.":
        "Listo. Selecciona tu eboot.bin y pulsa Jugar Bloodborne.",
    "Preset applied: Vanilla mode (all optional features off, FPS preset=30 native, BB_ANISO=0, all patches off).":
        "Preset aplicado: modo original (funciones opcionales apagadas, 30 FPS nativos, BB_ANISO=0, sin parches).",
    "Preset applied: Everything on (restored all defaults and recommended patches).":
        "Preset aplicado: todo activado (valores por defecto y parches recomendados).",
    "--- Running Pre-Launch Verification Check ---": "--- Verificando la instalación ---",
    "[PRE-LAUNCH] All checks PASSED! System and game files are ready.":
        "[PREVIO] ¡Todo correcto! El sistema y los archivos del juego están listos.",
    "[PRE-LAUNCH] Pre-flight verification passed:": "[PREVIO] Verificación correcta:",
    "Stopping game process tree...": "Deteniendo el juego...",
    "no saves yet": "aún no hay partidas",
    "None": "Ninguno",
}

# Texts with variable parts: each group is translated too, then put in the template.
ES_PATTERNS = [(re.compile(p), t) for p, t in [
    (r"Bloodborne XML Patch Manager \((\d+) Patches\)", "Gestor de parches XML de Bloodborne ({0} parches)"),
    (r"(\d+) of (\d+) active", "{0} de {1} activos"),
    (r"by (.+)", "por {0}"),
    (r"\[(.+)\]", "[{0}]"),
    (r"Could not open (.+):", "No se pudo abrir {0}:"),
    (r"Game File Verification Failed \((.+)\):", "Falló la verificación de los archivos del juego ({0}):"),
    (r"\[OK\] Game executable: eboot\.bin \((.+) MiB\)", "[OK] Ejecutable del juego: eboot.bin ({0} MiB)"),
    (r"\[NOTE\] Game version check check skipped: (.*)", "[NOTA] Comprobación de versión omitida: {0}"),
    (r"\[OK\] Compiled binary: bbport\.exe \((.+) MiB, built (.+)\)",
     "[OK] Binario compilado: bbport.exe ({0} MiB, compilado {1})"),
    (r"\[OK\] GPU library: bbgpu\.dll \((.+) MiB, built (.+)\)",
     "[OK] Librería GPU: bbgpu.dll ({0} MiB, compilada {1})"),
    (r"\[OK\] GPU subsystem: statically linked via libbbgpu\.a \((.+) MiB, built (.+)\)",
     "[OK] Núcleo GPU: enlazado desde libbbgpu.a ({0} MiB, compilado {1})"),
    (r"\[PATCHES\] Saved (\d+) active patch\(es\): (.*)", "[PARCHES] Guardados {0} parche(s) activo(s): {1}"),
    (r"\[M&K\] Settings updated: (.*)", "[RATÓN Y TECLADO] Ajustes actualizados: {0}"),
    (r"\[ERROR\] Could not save (.+?): (.*)", "[ERROR] No se pudo guardar {0}: {1}"),
    (r"Selected executable: (.*)", "Ejecutable seleccionado: {0}"),
    (r"\[PRE-LAUNCH ERROR\] Verification failed: (.*)", "[ERROR PREVIO] Falló la verificación: {0}"),
    (r"\[PRE-LAUNCH ERROR\] (.*)", "[ERROR PREVIO] {0}"),
    (r"\[BACKUP\] Saves: (.*)", "[RESPALDO] Partidas: {0}"),
    (r"\[BACKUP\] Could not back up saves: (.*)", "[RESPALDO] No se pudieron respaldar las partidas: {0}"),
    (r"unchanged since (.+)", "sin cambios desde {0}"),
    (r"copied to (.+) \((\d+) files, keeping the last (\d+)\)",
     "copiadas a {0} ({1} archivos; se conservan las últimas {2})"),
    (r"Starting Bloodborne from: (.*)", "Iniciando Bloodborne desde: {0}"),
    (r"\[LOG\] Could not archive the previous launcher\.log: (.*)",
     "[LOG] No se pudo archivar el launcher.log anterior: {0}"),
    (r"XML Patches \((\d+) active\): (.*)", "Parches XML ({0} activos): {1}"),
    (r"Launch Error: (.*)", "Error al lanzar: {0}"),
    (r"\((\d+) Vulkan warning lines hidden; full output is in launcher\.log\)",
     "({0} avisos de Vulkan ocultos; el registro completo está en launcher.log)"),
    (r"Process finished with code: (.*)", "El proceso terminó con código: {0}"),
    (r"\[WARNING\] Feature switch discrepancy: (.*)", "[AVISO] Una función no coincide con lo marcado: {0}"),
]]

_language = "en"


def system_ui_language() -> str:
    """'es' when Windows is in Spanish, else 'en'."""
    name = (locale.getlocale()[0] or "").lower()
    return "es" if name.startswith(("es", "spanish")) else "en"


def translate(text):
    """text in the launcher language (unchanged in English or when no translation is known)."""
    if _language != "es" or not isinstance(text, str) or not text:
        return text
    if text in ES:
        return ES[text]
    stripped = text.lstrip(" ")
    if stripped != text:
        return text[:len(text) - len(stripped)] + translate(stripped)
    for pattern, template in ES_PATTERNS:
        match = pattern.fullmatch(text)
        if match:
            return template.format(*(translate(group) for group in match.groups()))
    if "\n" in text:
        return "\n".join(translate(line) for line in text.split("\n"))
    return text


def _translate_kw(kw: dict, *keys) -> dict:
    return {**kw, **{k: translate(kw[k]) for k in keys if k in kw}}


def install_ui_language(language: str, launcher_globals: dict):
    """Translates the launcher from now on; call before building its widgets. English: no-op."""
    global _language
    if language != "es" or _language == "es":
        return
    _language = "es"

    original_options = tk.Misc._options

    def _options(self, cnf, kw=None):
        if isinstance(cnf, dict) and "text" in cnf:
            cnf = _translate_kw(cnf, "text")
        if kw and "text" in kw:
            kw = _translate_kw(kw, "text")
        return original_options(self, cnf, kw)
    tk.Misc._options = _options

    original_title = tk.Wm.wm_title

    def wm_title(self, string=None):
        return original_title(self, translate(string))
    tk.Wm.wm_title = tk.Wm.title = wm_title

    for name in ("showinfo", "showwarning", "showerror", "askokcancel", "askyesno"):
        original = getattr(messagebox, name)

        def box(title=None, message=None, _original=original, **options):
            return _original(translate(title), translate(message), **options)
        setattr(messagebox, name, box)

    original_open = filedialog.askopenfilename

    def askopenfilename(**options):
        return original_open(**_translate_kw(options, "title"))
    filedialog.askopenfilename = askopenfilename

    for name in ("ANISO_CHOICES", "PRESENT_CHOICES"):
        choices = launcher_globals[name]
        choices[:] = [(*choice[:-1], translate(choice[-1])) for choice in choices]

    launcher = launcher_globals["BloodborneLauncher"]
    original_log = launcher.log
    launcher.log = lambda self, message: original_log(self, translate(message))
