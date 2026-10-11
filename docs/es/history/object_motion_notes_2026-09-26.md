> Traducción al español de `docs/history/object_motion_notes_2026-09-26.md` (original en ruso). Puede quedar desactualizada si el original cambia.

La primera versión de los vectores de movimiento de objetos está compilada, el juego arrancó y no hay errores al iniciar. Pero todavía no la he verificado dentro del juego: los shaders del G-buffer con el código nuevo solo se compilan al cargar un nivel, así que la verificación principal está por venir.

Cómo funciona:
- El vertex shader de cada draw al G-buffer guarda las posiciones finales de los vértices y lee las posiciones de esos mismos vértices en el frame anterior.
- El pixel shader escribe la diferencia en un target adicional del G-buffer.
- Donde el objeto se movió, FSR recibe este vector; en los demás lugares, el vector de cámara.
- Las posiciones se guardan solo para los draws en movimiento: aquellos cuyas constantes del vertex shader cambiaron (matriz del objeto, huesos). La geometría estática no gasta memoria.
- Esto tiene en cuenta cualquier animación que calcule el vertex shader: skinning, armas, tela, enemigos.

Por favor, carga una partida en el juego y escribe «listo». Revisaré el log: cuántos draws se mueven y en cuántos se encontraron las posiciones del frame anterior. Después corre un rato con la sierra en la espalda. Para comparar, podré desactivar los vectores de objetos sobre la marcha y quedarán solo los vectores de cámara.
