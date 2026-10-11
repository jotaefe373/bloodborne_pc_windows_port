> Traducción al español de `docs/DEPTH_ADAPTIVE_TAA.md` (original en ruso). Puede quedar desactualizada si el original cambia.

# Mejoras de TAA adaptativo según la profundidad

**Fecha:** 2026-10-01  
**Estado:** Experimento histórico, reemplazado por la corrección de la temporal reprojection.

Los umbrales y pesos descritos abajo ya no se usan. Reducir el peso del historial a distancia
intensificaba el parpadeo; comparar la device depth entre cámaras distintas y guardar la profundidad
en FP16 no permitían distinguir correctamente las superficies lejanas. El análisis actualizado,
los cambios y los resultados de las pruebas: [TEMPORAL_REVIEW_2026-10-01.md](TEMPORAL_REVIEW_2026-10-01.md).

## Problema

La implementación actual de TAA usa umbrales fijos para:
1. Detectar disocclusion (aparición de superficies nuevas): `0.0005`
2. El peso temporal de acumulación: `0.9` → `0.65` según el movimiento

Estos parámetros no tienen en cuenta la profundidad del píxel, lo que provoca problemas:
- **Objetos lejanos (depth → 1.0)**: inestabilidad temporal, parpadeo
- **Objetos cercanos (depth → 0.0)**: desenfoque excesivo con movimiento rápido

## Solución: umbrales adaptativos según la profundidad

### 1. Umbral de disocclusion adaptativo según la profundidad

**Archivo:** `gpu/shadps4/video_core/host_shaders/taa.comp`

```glsl
float depthThreshold(float depth) {
    // Near: 0.001, Far (>0.95): 0.0002
    return mix(0.001, 0.0002, smoothstep(0.7, 0.95, depth));
}
```

**Lógica:**
- Superficies cercanas (depth < 0.7): umbral `0.001`, admite pequeñas discrepancias
- Superficies lejanas (depth > 0.95): umbral `0.0002`, más estricto, menos falsos positivos
- Transición suave mediante `smoothstep(0.7, 0.95, depth)`

**Uso:**
```glsl
float depthDiff = abs(history.a - depth);
float threshold = depthThreshold(depth);
if (depthDiff < threshold && ...) {
    // Accept history
}
```

### 2. Peso temporal adaptativo según la profundidad

```glsl
float temporalWeight(float depth, float motionLength) {
    // Base weight decreases for distant objects: 0.9 near, 0.8 far
    float baseWeight = mix(0.9, 0.8, smoothstep(0.7, 0.95, depth));
    // Motion reduces weight more aggressively for distant pixels
    float motionFactor = mix(0.65, 0.5, smoothstep(0.7, 0.95, depth));
    return mix(baseWeight, motionFactor, clamp(motionLength / 16.0, 0.0, 1.0));
}
```

**Lógica:**
- **Peso base sin movimiento:**
  - Cerca: `0.9` (acumulación agresiva del historial)
  - Lejos: `0.8` (más conservador, menos parpadeo)
  
- **Con movimiento rápido (motionLength > 16px):**
  - Cerca: baja a `0.65`
  - Lejos: baja a `0.5` (todavía más conservador)

**Uso:**
```glsl
float motionLength = length(motion);
float weight = temporalWeight(depth, motionLength);
result = mix(current, clipped, weight);
```

### 3. Validación de motion vectors (camera_motion.comp)

**Archivo:** `gpu/shadps4/video_core/host_shaders/camera_motion.comp`

```glsl
// Depth-adaptive validation: distant surfaces need tighter depth matching.
float depth_threshold = mix(0.001, 0.0003, smoothstep(0.7, 0.95, depth));
if (object_motion.b > 0.99 && abs(object_motion.a - depth) < depth_threshold &&
    !any(isnan(object_motion.rg)) && !any(isinf(object_motion.rg))) {
    result = object_motion.rg;
}
```

**Qué cambió:**
- Umbral anterior: fijo, `0.001`
- Umbral nuevo: `0.001` → `0.0003` para superficies lejanas
- Evita usar object motion vectors de píxeles incorrectos

### 4. Visualización mejorada de los modos de depuración

**Archivo:** `gpu/shadps4/video_core/host_shaders/camera_motion.comp`

Los modos de `BB_DEBUG_MOTION=1` ahora están estructurados:
```glsl
if (mode == 1) {
    // Raw depth visualization
    imageStore(color_img, pixel, vec4(fract(depth * 4.0), depth, depth < 0.0 ? 1.0 : 0.0, 1.0));
} else if (mode == 2) {
    // View-space depth visualization (z / 50)
    const float v = z / 50.0;
    imageStore(color_img, pixel, vec4(fract(v * 4.0), v, v < 0.0 ? 1.0 : 0.0, 1.0));
}
```

## Mejoras esperadas

### Objetos lejanos
- ✅ Menos parpadeo en paredes lejanas y en el cielo
- ✅ Historial más estable con pequeños movimientos de cámara
- ✅ Menos disocclusion falsas por errores numéricos de profundidad

### Objetos cercanos
- ✅ Menos desenfoque con movimientos rápidos (personaje, arma)
- ✅ Object motion vectors más precisos
- ✅ Mejor equilibrio entre acumulación y capacidad de respuesta

### Zona adaptativa (depth 0.7-0.95)
- Transición suave entre modos
- Evita artefactos bruscos en el límite

## Pruebas

### Verificación visual
```bash
# TAA a resolución nativa
BB_UPSCALER=taa bash run.sh

# Comprobar:
# 1. Parpadeo de paredes lejanas (Hunter's Dream, pisos superiores)
# 2. Desenfoque del arma al girar rápido
# 3. Estabilidad con movimiento lento de cámara
# 4. Disocclusion al rodear esquinas
```

### Modos de depuración
```bash
# Visualización de la profundidad
BB_DEBUG_MOTION=1 bash run.sh
# Toggle: (1<<21) = raw depth, (1<<22) = view-space z

# Comprobación de motion vectors
# Toggle: (1<<20) = blended motion, (1<<23) = reprojection, (1<<24) = difference
```

### Comparación A/B
```bash
# Crear el archivo para alternar en tiempo de ejecución
echo "0" > /tmp/bb_toggle

# En el juego, alternar los bits para comparar
# Hará falta un mecanismo temporal para los pesos antiguos/nuevos
```

## Riesgos potenciales

1. **Pesos demasiado conservadores en objetos lejanos**
   - Puede aumentar el emborronamiento en giros rápidos
   - Solución: ajustar `baseWeight` (0.8 → 0.85?)

2. **Umbral de profundidad demasiado estricto para object motion**
   - Puede descartar vectores válidos
   - Solución: `0.0003` → `0.0005` para depth > 0.95

3. **El rango de smoothstep 0.7-0.95 puede no ser óptimo**
   - Bloodborne: near=0.05, far=3000
   - La mayor parte de la geometría está en el rango 0.1-0.9
   - Solución: perfilar la distribución de profundidad en escenas típicas

## Próximos pasos

1. ✅ Implementar los umbrales adaptativos según la profundidad
2. ⏳ Compilar y probar en el juego
3. ⏳ Recopilar estadísticas de la distribución de profundidad
4. ⏳ Ajustar los umbrales con base en datos reales
5. ⏳ Agregar alternancia en tiempo de ejecución para pruebas A/B
6. ⏳ Documentar los parámetros finales

## Referencias

- [upscaler.md](upscaler.md): arquitectura general del upscaler
- [motion_vectors.md](motion_vectors.md): vectores de movimiento
- Shader de TAA: `gpu/shadps4/video_core/host_shaders/taa.comp`
- Camera motion: `gpu/shadps4/video_core/host_shaders/camera_motion.comp`
