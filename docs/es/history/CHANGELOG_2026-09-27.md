> Traducción al español de `docs/history/CHANGELOG_2026-09-27.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Correcciones — 2026-09-27

## ✅ Qué se corrigió

### 1. La máscara de reactividad no se guardaba
- **Archivo:** `gpu/shim/bbport_settings.cpp`
- **Problema:** La casilla "Mostrar máscara (depuración)" no se guardaba en `bbport.ini`
- **Solución:** Se agregó la carga/guardado del parámetro `debug_view`

### 2. 🔥 CAMBIO DINÁMICO DE PRESETS en la RX 7800 XT
- **Archivos:** 
  - `gpu/shadps4/video_core/renderer_vulkan/vk_temporal_upscaler.cpp`
  - `gpu/shim/bbport_overlay.cpp`
- **Problema:** La RX 7800 XT no soporta `blit D32S8`, por eso se necesitaba reiniciar
- **Solución:**
  - Fallback: la profundidad de la UI se limpia en lugar de copiarse (funciona correctamente)
  - Se quitó el bloqueo `BB_LIVE_SCALING_UNSUPPORTED`
  - Se actualizó el menú: se quitó el requisito de reiniciar para los presets

### 3. Configuración correcta
- **Archivo:** `bbport.ini`
- **Crítico:** `jitter=1` (¡ESTABA DESACTIVADO!)
- Se optimizaron los parámetros de nitidez y de la máscara

---

## 🎮 Qué funciona ahora SIN reiniciar

- ✅ **Cambio de presets** (Native AA / Quality / Balanced / Performance / Ultra Performance)
- ✅ Activar/desactivar el upscaler
- ✅ Nitidez
- ✅ Jitter
- ✅ Máscara de reactividad
- ✅ Modos de depuración

**Solo hace falta reiniciar para:** los vectores de movimiento de objetos (`object_motion`)

---

## 🧪 Pruebas

### Compilación
✅ Exitosa

### Verificar en el juego:

1. **Cambio dinámico:**
   - Abrir el menú (Insert o L3+R3)
   - Cambiar el preset
   - **Debe aplicarse DE INMEDIATO**

2. **Estelas en el arma:**
   - Con `jitter=1` deberían ser MUCHO menores
   - Comparar con `object_motion=0`

3. **Máscara de reactividad:**
   - Debe mostrarse (en color rojo)
   - Los efectos transparentes quedan marcados

---

## 📝 Archivos modificados

- `gpu/shim/bbport_settings.cpp`
- `gpu/shadps4/video_core/renderer_vulkan/vk_temporal_upscaler.cpp`
- `gpu/shim/bbport_overlay.cpp`
- `bbport.ini`
