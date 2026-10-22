# Evaluación del estimador de ocupación

Esta carpeta no trae resultados: trae el método para producirlos.

## Protocolo sugerido

1. Elegir salones y franjas (por ejemplo, 3 salones × 5 días × cada 5 minutos en horario de clase).
2. En cada instante registrar lo que el sistema recibe (`yolo_people` si hay cámara, `co2_ppm`, `wifi_devices`, `outdoor_co2_ppm`) y el **conteo de referencia** `true_people`, hecho por una persona sin registrar identidades.
3. Guardar las filas en un CSV con las columnas de `plantilla_conteos.csv`, ordenadas por tiempo dentro de cada salón.
4. Separar una parte del CSV para ajustar parámetros y otra, distinta, para medir. No medir con los mismos datos con que se ajustó.
5. Ejecutar:

   ```sh
   python eval/evaluate.py conteos.csv --tolerance 2 --json resultados.json
   ```

6. Revisar n, MAE, RMSE y sesgo globales, por salón y con/sin cámara, además de la tabla de calibración. Acompañar el resultado con la versión del servicio, el CSV y las condiciones (luz, oclusiones, ventilación).

El evaluador valida que las mediciones sean finitas y estén dentro de los rangos de la API; indica el número de fila cuando un registro no cumple el contrato. La tolerancia de error debe ser finita y no negativa.

## Cómo leer `confidence_pct`

Es la estabilidad interna del filtro, calculada de su varianza. Solo podría llamarse "probabilidad de acierto" si la tabla de calibración muestra que, por ejemplo, las lecturas con confianza 85–100 aciertan dentro de la tolerancia cerca del 85–100 % de las veces. Mientras no se mida, no se presenta como probabilidad.
