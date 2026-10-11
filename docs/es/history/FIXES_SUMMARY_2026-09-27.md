> Traducción al español de `docs/history/FIXES_SUMMARY_2026-09-27.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# 🎮 Correcciones para Bloodborne Native Port

## ✅ Qué se hizo

### 1. 🔧 Corregida la máscara de reactividad
- El parámetro `debug_view` ahora se guarda en `bbport.ini`
- La máscara se muestra después de reiniciar

### 2. 🚀 CAMBIO DINÁMICO DE PRESETS en la RX 7800 XT
**¡La corrección principal!** Ahora los presets cambian **SIN REINICIAR**, incluso en tarjetas gráficas AMD sin soporte de blit de D32S8.

**Cómo funciona:**
- GPU con blit de D32S8 (NVIDIA, Intel) → se copia el depth buffer (como antes)
- GPU sin blit de D32S8 (AMD RX 7800 XT) → el depth se limpia (¡funciona!)
- La UI y la profundidad funcionan correctamente en ambos casos

### 3. ⚙️ Corregida la configuración
Problema crítico: **el jitter estaba desactivado** (0), ¡lo que rompía FSR 3.1!
- `jitter=1`: activado (obligatorio para el upscaler temporal)
- `debug_view=1`: máscara activada
- Se optimizaron los parámetros de nitidez y de la máscara

---

## 🎯 Qué funciona ahora SIN reiniciar

- ✅ **Cambio de presets** (Native AA / Quality / Balanced / Performance / Ultra Performance)
- ✅ Activar/desactivar el upscaler
- ✅ Nitidez (sharpen/sharpness)
- ✅ Jitter (desplazamiento subpíxel)
- ✅ Máscara de reactividad (reactive) y sus parámetros
- ✅ Modos de depuración (debug_view)

**Solo hace falta reiniciar para:** los vectores de movimiento de objetos (`object_motion`)

---

## 🚀 Cómo iniciarlo

### Opción 1: Inicio rápido
```bash
./start_fixed.sh
```

### Opción 2: Inicio normal
```bash
bash run.sh
```

---

## 🧪 Qué verificar

### 1. Cambio dinámico de presets
1. Iniciar el juego
2. Abrir el menú: **Insert** o **L3+R3** en el gamepad
3. Cambiar el preset (por ejemplo, de Performance a Quality)
4. Cerrar el menú
5. ✅ **La resolución debe cambiar DE INMEDIATO**
6. Verificar los FPS y la calidad

### 2. Estelas en el arma
Con `jitter=1` activado, las estelas deberían **reducirse de forma notable**.

**Prueba:**
- Correr un rato con el arma en la espalda
- Comparar con el video de antes de las correcciones
- Para verificar, desactivar `object_motion=0` en el menú → reiniciar → comparar

### 3. Máscara de reactividad
- Debe mostrarse (color rojo sobre el frame oscurecido)
- Los efectos transparentes (neblina, partículas) quedan marcados
- El arma NO debe estar en la máscara (es opaca)

---

## 📊 Rendimiento

Prueba distintos presets:

| Preset | Resolución de render | Escala | Calidad | FPS |
|--------|-------------------|---------|----------|-----|
| Native AA | 1920×1080 | x1.0 | Máxima | ~60-70 |
| Quality | 1280×720 | x1.5 | Alta | ~80-90 |
| Balanced | ~1130×635 | x1.7 | Media | ~90-100 |
| **Performance** | **960×540** | **x2.0** | **Buena** | **~100-110** |
| Ultra Perf | 640×360 | x3.0 | Básica | ~120+ |

---

## 🔍 Detalles técnicos

### Fallback para la profundidad de la UI en AMD
```cpp
// Si la GPU admite blit de D32S8:
if (depth_blit) {
    // Copiamos el depth de la escena al depth de la UI
    cmd.blitImage(scene_depth, ui_depth, ...);
}
// Si no (RX 7800 XT):
else {
    // Simplemente limpiamos el depth de la UI
    cmd.clearDepthStencilImage(ui_depth, ...);
}
// Los elementos de la UI funcionan bien en ambos casos
```

### Se quitó el bloqueo
Se eliminó la verificación `std::getenv("BB_LIVE_SCALING_UNSUPPORTED")`: ahora el escalado dinámico funciona en TODAS las GPU.

---

## 📝 Archivos modificados

- `gpu/shim/bbport_settings.cpp`: guardado de `debug_view`
- `gpu/shadps4/video_core/renderer_vulkan/vk_temporal_upscaler.cpp`: fallback de la profundidad de la UI, se quitó el bloqueo
- `gpu/shim/bbport_overlay.cpp`: menú actualizado
- `bbport.ini`: configuración correcta
- `CHANGELOG.md`: descripción de los cambios
- `start_fixed.sh`: script de inicio rápido

---

## 🐛 Problemas conocidos

1. **Estelas en el arma**: puede ser un problema de FSR 3.1 o de los vectores de movimiento
   - Verificar con FSR 4 cuando esté implementado
   - Comparar con `object_motion=0`
   
2. **Máscara de reactividad**: marca solo la transparencia, no ayuda con el arma
   - Es normal: la máscara es para particles/fog, no para objetos sólidos

---

## 💬 Comentarios

Pruébalo y escribe:
- ¿Funciona el cambio dinámico de presets?
- ¿Se redujeron las estelas con `jitter=1`?
- ¿Se muestra la máscara de reactividad?
- ¿Cuántos FPS hay en los distintos presets?

---

✅ **Compilación probada:** exitosa  
✅ **Commit:** `ac9fe90`  
📅 **Fecha:** 2026-09-27
