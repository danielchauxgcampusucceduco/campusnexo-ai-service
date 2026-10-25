# CampusNexo · Servicio de IA

Aprendizaje automático y visión de **CampusNexo**, el gemelo digital del campus Pasto de la Universidad Cooperativa de Colombia. Es uno de los tres repositorios del sistema:

| Repositorio | Papel |
|---|---|
| `campusnexo-backend` | Lógica del sistema en Java: el gemelo, las reglas, la seguridad y las bases de datos. **Es el único que llama a este servicio.** |
| `campusnexo-frontend` | Tablero web (Vercel). Nunca llama a este servicio. |
| `campusnexo-ai-service` (este) | API de ML para el backend, programas del dispositivo de borde y entrenamiento. |

```
Cámara ─▶ edge/ (YOLO + homografía, en el salón) ─HTTPS─▶ backend Java ─HTTPS + X-API-Key─▶ app/ (este servicio)
```

Ninguna imagen sale del salón: el borde envía posiciones en el piso y conteos.

## API para el backend (`app/`)

| Ruta | Qué hace |
|---|---|
| `POST /v1/occupancy/estimate` y `/batch` | Fusión sin estado de cámara, CO₂ y Wi-Fi con **el mismo modelo y parámetros** que el filtro de Kalman del gemelo en Java. Ambos repos prueban `tests/fusion_golden_cases.csv`. |
| `POST /v1/rooms/assignment` | Asignación óptima curso → salón (húngaro rectangular) que minimiza la potencia nominal. |
| `POST /v1/sensors/anomalies` | Salud de sensores: valores fuera de rango, sensores pegados y saltos bruscos (MAD robusta). |
| `POST /v1/occupancy/forecast` | Pronóstico por franja horaria con perfil semanal suavizado, aprendido del historial del salón (MongoDB). |
| `POST /v1/vision/count` | Conteo YOLO opcional (extra `vision`); sin el extra responde 503, nunca un conteo inventado. |
| `GET /health`, `/ready`, `/v1/capabilities` | Estado y límites publicados. |

Con `AI_API_KEY` (mínimo 24 caracteres; obligatoria en producción) toda ruta salvo `/health` y `/ready` exige `X-API-Key`. `confidence_pct` es margen de error relativo al aforo, **no** una probabilidad (ver `eval/`).

## Borde del salón (`edge/`)

| Programa | Para qué |
|---|---|
| `calibrar.py` | Una vez al instalar la cámara: se marcan las 4 esquinas del piso y se guarda `calibracion-<salón>.json`. |
| `yolo_edge_publisher.py` | YOLO + ByteTrack; proyecta cada persona al piso y envía frames por HTTPS (o MQTT). Modos `--descubrir`, `--auditar` y `--emparejar`. |
| `agente_pc.py` | En cada PC: latido cada minuto (la cámara no ve las torres) y patrón a pantalla completa durante su ranura de emparejamiento. Solo biblioteca estándar. |

**Registro automático de puestos:**
1. Con el salón vacío, `--descubrir` agrupa monitores, sillas y mesas en puestos (A1…E6) y envía la propuesta.
2. Cada PC muestra su patrón en su ranura y `--emparejar` ve en qué monitor apareció.
3. El administrador revisa y confirma en el tablero. Nada se registra sin su confirmación.

## Entrenamiento con atributos de calidad (`entrenamiento/`)

- `atributos_calidad.json` contiene los umbrales de la piloto: MAE de conteo ≤ 1, docente detectado ≥ 95 %, recall ≥ 0,95, precisión ≥ 0,90 e inferencia ≤ 250 ms.
- `compuerta_calidad.py` sale con código 1 si una medición no los cumple. Nada se promueve sin pasarla.
- **Hoy, sin hardware**, `ajustar_parametros.py` usa miles de escenas sintéticas (`escena_sintetica.py`) con ruido de detector:
  - Elige la confianza mínima del borde por menor varianza del error. El MAE no sirve como criterio: una persona falsa "compensa" a una perdida, pero en un salón vacío es ocupación fantasma.
  - Calcula la `KALMAN_CAMERA_VARIANCE` del backend.
  - Escribe `parametros.json`. La CI vuelve a correr este ajuste en cada push.
- **Con cámara** el flujo tiene tres pasos:
  1. `captura.py` captura imágenes, solo con acta de consentimiento y fuera de git.
  2. Se etiquetan en CVAT o Label Studio con las clases de `dataset.yaml`. Incluye `cpu`, que COCO no tiene.
  3. `entrenar.py` hace el ajuste fino de YOLO y lo pasa por la compuerta.

## Evaluación y carga

- `eval/evaluate.py` calcula MAE, RMSE, sesgo y calibración de `confidence_pct` a partir de conteos reales de una sesión en el salón.
- `carga/prueba_carga.py` mide p95 y error de la ingesta del backend (QA-3: p95 < 300 ms con 107 salones a 1 Hz). Solo debe correrse contra el `docker compose` local.
- `scripts/exportar_openapi.py` escribe el contrato OpenAPI; `tests/test_contrato_backend.py` comprueba que existan las rutas que llama el backend Java, y la CI publica el contrato como artefacto.

## Uso local

```bash
cp .env.example .env   # AI_API_KEY, CAMPUSNEXO_BACKEND_URL y CAMPUSNEXO_SENSOR_KEY
python -m venv .venv && .venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/python -m pytest -q
uvicorn app.main:app --port 8001
```

Extras disponibles: `vision` (YOLO y OpenCV), `edge` (MQTT) y `carga` (httpx). La imagen Docker no incluye visión por defecto (`WITH_VISION=true` para incluirla).
