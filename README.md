# Cadence

Cadence es un sistema de composición musical para videojuegos/animación con:

- backend Python (`FastAPI` + `LangGraph`) para generar canciones,
- frontend React (`cadence-ui`) para chat, reproducción, visualización y exportación,
- formato de salida `rsong` con metadatos narrativos, armónicos y de validación.

Este README documenta el flujo crítico del agente: parámetros de entrada, decisiones lógicas por nodo y outputs.

## Stack y estructura

- **Backend:** `cadence/`
- **Frontend:** `cadence-ui/`
- **Ejemplos/benchmark:** `examples/`
- **Salidas generadas:** `output/`

## Arranque rápido

### Backend

```bash
cp .env.example .env
uv sync
uv run uvicorn cadence.main:app --reload
```

Health: `http://localhost:8000/health`

### Frontend

```bash
cd cadence-ui
npm install
npm run dev
```

## API principal

### `POST /generate`

Request:

```json
{
  "prompt": "boss battle orchestral dark with rising tension"
}
```

Response (resumen):

- `export_path`: ruta del `.rsong` en `output/`
- `rsong`: payload completo serializado
- `knowledge_level`: técnico/no técnico inferido
- `validation_score`, `validation_passed*`
- `quality_status`
- `request_id`, `retry_count`
- `sections`, `bpm`, `key`, `duration_ms`

### Producciones

- `GET /productions`: lista de `.rsong`
- `GET /productions/{filename}`: contenido `.rsong`
- `GET /productions/{filename}/midi`: `.mid` (genera si no existe o está desactualizado)

## Flujo del agente (LangGraph)

Implementado en `cadence/agent/graph.py`.

Secuencia:

1. `prompt_enhancer`
2. `technical_spec`
3. `prepare`
4. `narrative_planner`
5. `narrative_contract`
6. `structure_planner`
7. `align_sections`
8. `composition_policy`
9. `strategy_planner`
10. `harmony_planner`
11. `development_planner`
12. `instrument_planner`
13. `arrangement_planner`
14. `compose_orchestra`
15. `post_process`
16. `validator`
17. `repair` (condicional)
18. `export`

Routing de calidad:

- Si `validator.passed` o `retry_count >= 3` -> `export`
- Si falla y aún hay reintentos -> `repair` -> reruta a:
  - `arrangement_planner` o
  - `compose_orchestra` o
  - `post_process`

## Parámetros y estado compartido

Modelo de estado: `cadence/schemas/song_state.py` (`SongState`).

Campos clave:

- entrada: `messages`, `creative_brief`
- intención/estilo: `intent`, `style_profile`
- propuesta LLM: `technical_proposal`
- planificación: `narrative`, `narrative_contract`, `structure`, `harmony`, `development`
- estrategias: `strategies`, `pattern_intent`, `pattern_selection_audit`
- orquestación/arreglo: `orchestration_plan`, `arrangement`
- composición: `tracks`
- control de aleatoriedad: `generation_seed`, `node_seeds`
- calidad: `validation_result`, `retry_count`, `repair_target`, `repair_layers`, `repair_actions`
- exportación: `export_path`, `rsong_data`

## Lógica por nodo (entrada -> salida -> decisión)

### 1) `prompt_enhancer`

- **Entrada:** prompt usuario (`messages`)
- **Salida:** `creative_brief`
- **Decisión:** LLM dramático amplía escena/arco emocional; no define BPM/tonalidad.

### 2) `technical_spec`

- **Entrada:** prompt + `creative_brief` + catálogos (género/forma/orquestación/patrones/perfiles inspiración)
- **Salida:** `technical_proposal`
- **Decisión:** LLM técnico define parámetros musicales completos (BPM, key, modo, forma, instrumentos, patrones, curvas por sección, cadencias, jerarquía lead, etc.).

### 3) `prepare`

- **Entrada:** `technical_proposal`, prompt, brief
- **Salida:** `intent`, `style_profile`, `technical_proposal` normalizado, `generation_seed`
- **Decisión:** normalización determinista (estructura, instrumentos, composición, política tonal), merge de géneros y semilla base.

### 4) `narrative_planner`

- **Entrada:** `intent`, `technical_proposal`, brief
- **Salida:** `narrative`
- **Decisión:** arma guion narrativo por plantillas deterministas.

### 5) `narrative_contract`

- **Entrada:** `narrative`, `intent`
- **Salida:** `narrative_contract`
- **Decisión:** congela IDs de sección, arco y firma de intención como contrato inmutable intra-request.

### 6) `structure_planner`

- **Entrada:** `technical_proposal`, `narrative`, `intent`, `narrative_contract`
- **Salida:** `structure`
- **Decisión:** determina macroforma y compases por sección.

### 7) `align_sections`

- **Entrada:** `structure`, `narrative`, `narrative_contract`
- **Salida:** `structure`/`narrative` alineados, `section_alignment`
- **Decisión:** reconcilia IDs canónicos; falla temprano si el mapeo no es confiable.

### 8) `composition_policy`

- **Entrada:** `intent`, `narrative`, `narrative_contract`, `structure`
- **Salida:** `generation_seed`, `node_seeds`, `narrative_anchors`
- **Decisión:** fija semilla global y subsemillas por nodo + límites narrativos de baja variación.

### 9) `strategy_planner`

- **Entrada:** `intent`, `structure`, `technical_proposal`, `style_profile`
- **Salida:** `strategies`, `genre_mix`, `pattern_intent`, `pattern_selection_audit`, `composition_archetype`, `creative_variation`
- **Decisión:** selección de patrones por seed con prioridad a overrides del LLM.

### 10) `harmony_planner`

- **Entrada:** `technical_proposal`, `structure`, `narrative_contract`, `strategies`
- **Salida:** `harmony`
- **Decisión:** progresiones por sección (key/mode/pool + tensión narrativa + `cadence_plan`).

### 11) `development_planner`

- **Entrada:** `structure`, `narrative_contract`, `technical_proposal`, `harmony`
- **Salida:** `development` (+ posible `harmony` enriquecida por segmentos)
- **Decisión:** evolución motívica por sección y micro-arcos.

### 12) `instrument_planner` (orchestration deterministic)

- **Entrada:** `technical_proposal`, `strategies`, `intent`
- **Salida:** `orchestration_plan`, `strategies` ajustadas
- **Decisión:** aplica plan instrumental del LLM con validación determinista.

### 13) `arrangement_planner`

- **Entrada:** `structure`, `narrative_anchors`, `orchestration_plan`, `development`, `technical_proposal`
- **Salida:** `arrangement`, `voice_register_profile`
- **Decisión:** decide capas activas, schedule por compás, call/response, silencios, tensión, textura y cobertura por secciones.

### 14) `compose_orchestra`

- **Entrada:** `arrangement` (+ `repair_layers` opcional)
- **Salida:** `tracks`
- **Decisión:** compone por capa vía registro de instrumentos; soporta recomposición parcial en repair.

### 15) `post_process`

- **Entrada:** `tracks`, `structure`, `technical_proposal`, `narrative_contract`, `development`
- **Salida:** `tracks` post-procesados
- **Decisión:** melody post, asignación GM, crescendo narrativo, humanize, y reparaciones dinámicas específicas.

### 16) `validator`

- **Entrada:** `tracks`, `structure`, `arrangement`, `technical_proposal`, `narrative_*`
- **Salida:** `validation_result`
- **Decisión:** score 0..1 con checks técnicos y perceptuales (cobertura melódica, rango, timing, riqueza instrumental, dinámica, continuidad narrativa, etc.).

### 17) `repair`

- **Entrada:** `validation_result`, estado actual
- **Salida:** `retry_count`, `repair_target`, `repair_layers`, `repair_actions`
- **Decisión:** mapea fallos a plan de corrección mínimo (re-arreglo, recomposición parcial o post-process).

### 18) `export`

- **Entrada:** estado final (`tracks`, `structure`, `validation`, metadatos narrativos/estrategia)
- **Salida:** `rsong_data`, `export_path`
- **Decisión:** serializa `.rsong` completo con metadatos de calidad, seeds, cue points, estrategia, narrativa, armonía y arreglo.

## Formato de salida `.rsong`

El export contiene:

- `header`: `title`, `bpm`, `time_signature`, `key`, `duration_ms`, `genre_tags`, `total_bars`
- `game_meta`:
  - `composition_archetype`, `archetype_reason`
  - `sections`, `bars_per_section`, `cue_points`, `intensity_curve`, `loop_point_ms`
  - `narrative_contract`, `narrative_anchors`, `creative_variation`, `style_profile`
  - `strategies`, `pattern_selection_audit`, `pattern_intent`, `harmony`, `development`, `arrangement`
- `quality`: estado de calidad agregado
- `validation`: score, passed, errores, warnings, retry_count
- `tracks`: eventos MIDI-like por capa

## Benchmark y corpus

Prompts de benchmark: `examples/benchmark_prompts.json`

Ejecución:

```bash
PYTHONPATH=. uv run --no-sync python -m cadence.analysis.midi_benchmark --suite
PYTHONPATH=. uv run --no-sync python -m cadence.analysis.test_benchmark_examples
```

Convención de export:

- `output/cadence_<id>_<timestamp>.rsong`

## Frontend y contrato con backend

`cadence-ui` consume:

- `POST /generate` para crear canción
- `GET /productions*` para historial/reproducción/export MIDI

Además:

- respeta silencios de sesión (`trackMutes`) en export client-side,
- visualiza progreso/secciones/metadata técnica desde `rsong`.

## Notas operativas

- El pipeline usa LLM solo al inicio (`prompt_enhancer`, `technical_spec`).
- El resto prioriza lógica determinista y validación musical.
- El repair loop evita regenerar todo cuando el fallo es local.

## Roadmap/documentación complementaria

- Plan de mejora histórico: `docs/IMPROVEMENT_PLAN.md`
