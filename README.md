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

## Lógica por nodo (entrada -> salida -> justificación y efecto esperado)

### 1) `prompt_enhancer`

- **Entrada:** prompt usuario (`messages`)
- **Salida:** `creative_brief`
- **Justificación:** separar la expansión narrativa del diseño musical evita mezclar creatividad textual con restricciones técnicas demasiado pronto.
- **Efecto esperado:** brief dramático más rico, concreto y consistente, que mejora la calidad del `technical_spec` sin introducir parámetros musicales prematuros.

### 2) `technical_spec`

- **Entrada:** prompt + `creative_brief` + catálogos (género/forma/orquestación/patrones/perfiles inspiración)
- **Salida:** `technical_proposal`
- **Justificación:** concentrar las decisiones musicales de alto nivel en un solo nodo mejora coherencia global y trazabilidad de intención.
- **Efecto esperado:** propuesta técnica completa y usable por nodos deterministas, con menos contradicciones entre forma, armonía, arreglo y energía.

### 3) `prepare`

- **Entrada:** `technical_proposal`, prompt, brief
- **Salida:** `intent`, `style_profile`, `technical_proposal` normalizado, `generation_seed`
- **Justificación:** estandarizar y sanear la salida del LLM antes de planificar reduce ambigüedad y evita errores aguas abajo.
- **Efecto esperado:** estado base robusto, reproducible y compatible con todos los nodos posteriores.

### 4) `narrative_planner`

- **Entrada:** `intent`, `technical_proposal`, brief
- **Salida:** `narrative`
- **Justificación:** traducir intención y brief a una narrativa estructurada permite que la progresión musical responda a una lógica dramática explícita.
- **Efecto esperado:** secciones con propósito narrativo claro (inicio, tensión, clímax, resolución) y continuidad expresiva.

### 5) `narrative_contract`

- **Entrada:** `narrative`, `intent`
- **Salida:** `narrative_contract`
- **Justificación:** fijar un contrato canónico evita que cada nodo reinterprete nombres de sección o intención de forma incompatible.
- **Efecto esperado:** alineación estable entre narrativa, estructura, armonía y arreglo durante todo el request.

### 6) `structure_planner`

- **Entrada:** `technical_proposal`, `narrative`, `intent`, `narrative_contract`
- **Salida:** `structure`
- **Justificación:** definir macroforma y duración relativa por sección es necesario para ordenar el resto de decisiones temporales del pipeline.
- **Efecto esperado:** arquitectura temporal coherente y usable por armonía, desarrollo, arreglo y composición.

### 7) `align_sections`

- **Entrada:** `structure`, `narrative`, `narrative_contract`
- **Salida:** `structure`/`narrative` alineados, `section_alignment`
- **Justificación:** resolver desalineaciones de IDs inmediatamente previene bugs silenciosos muy costosos en nodos tardíos.
- **Efecto esperado:** correspondencia 1:1 confiable entre sección narrativa y sección estructural, o fallo temprano explícito.

### 8) `composition_policy`

- **Entrada:** `intent`, `narrative`, `narrative_contract`, `structure`
- **Salida:** `generation_seed`, `node_seeds`, `narrative_anchors`
- **Justificación:** gobernar aleatoriedad por política común garantiza reproducibilidad sin perder control narrativo.
- **Efecto esperado:** variación acotada, resultados repetibles por semilla y menor deriva estilística entre nodos.

### 9) `strategy_planner`

- **Entrada:** `intent`, `structure`, `technical_proposal`, `style_profile`
- **Salida:** `strategies`, `genre_mix`, `pattern_intent`, `pattern_selection_audit`, `composition_archetype`, `creative_variation`
- **Justificación:** convertir intención y estilo en estrategias operativas permite seleccionar patrones y arquetipos de forma auditable.
- **Efecto esperado:** decisiones estratégicas coherentes con el brief y trazables vía `pattern_selection_audit`.

### 10) `harmony_planner`

- **Entrada:** `technical_proposal`, `structure`, `narrative_contract`, `strategies`
- **Salida:** `harmony`
- **Justificación:** la armonía debe reflejar tanto restricciones tonales como la intención dramática de cada sección.
- **Efecto esperado:** progresiones funcionales por sección con tensión/resolución alineadas al arco narrativo.

### 11) `development_planner`

- **Entrada:** `structure`, `narrative_contract`, `technical_proposal`, `harmony`
- **Salida:** `development` (+ posible `harmony` enriquecida por segmentos)
- **Justificación:** planificar variación temática antes de componer evita repetición plana y conserva identidad melódica.
- **Efecto esperado:** motivos reconocibles que evolucionan por micro-arcos sin romper coherencia global.

### 12) `instrument_planner` (orchestration deterministic)

- **Entrada:** `technical_proposal`, `strategies`, `intent`
- **Salida:** `orchestration_plan`, `strategies` ajustadas
- **Justificación:** validar de forma determinista la orquestación propuesta reduce combinaciones inviables o redundantes.
- **Efecto esperado:** paleta instrumental ejecutable, equilibrada y consistente con roles musicales esperados.

### 13) `arrangement_planner`

- **Entrada:** `structure`, `narrative_anchors`, `orchestration_plan`, `development`, `technical_proposal`
- **Salida:** `arrangement`, `voice_register_profile`
- **Justificación:** materializar “cuándo y cómo entra cada capa” es clave para traducir intención narrativa a dinámica real.
- **Efecto esperado:** arreglo con densidad controlada, contraste seccional y cobertura instrumental adecuada.

### 14) `compose_orchestra`

- **Entrada:** `arrangement` (+ `repair_layers` opcional)
- **Salida:** `tracks`
- **Justificación:** separar composición por capas facilita modularidad, depuración y reparaciones locales sin regenerar todo.
- **Efecto esperado:** tracks coherentes por rol/capa y capacidad de recomposición parcial cuando falla validación.

### 15) `post_process`

- **Entrada:** `tracks`, `structure`, `technical_proposal`, `narrative_contract`, `development`
- **Salida:** `tracks` post-procesados
- **Justificación:** el material compuesto en bruto necesita refinamiento para mejorar interpretabilidad, realismo y mezcla funcional.
- **Efecto esperado:** salida más musical y estable (dinámica, articulación, continuidad), lista para validación final.

### 16) `validator`

- **Entrada:** `tracks`, `structure`, `arrangement`, `technical_proposal`, `narrative_*`
- **Salida:** `validation_result`
- **Justificación:** un score compuesto permite medir calidad de forma objetiva y detectar fallos concretos reparables.
- **Efecto esperado:** diagnóstico accionable (errores/warnings) y criterio claro para aprobar, reparar o exportar.

### 17) `repair`

- **Entrada:** `validation_result`, estado actual
- **Salida:** `retry_count`, `repair_target`, `repair_layers`, `repair_actions`
- **Justificación:** reparar por impacto mínimo preserva lo que ya funciona y reduce costo de iteración.
- **Efecto esperado:** corrección localizada de fallos con menor riesgo de regresión en componentes sanos.

### 18) `export`

- **Entrada:** estado final (`tracks`, `structure`, `validation`, metadatos narrativos/estrategia)
- **Salida:** `rsong_data`, `export_path`
- **Justificación:** consolidar toda la trazabilidad del pipeline en el artefacto final facilita reproducción, auditoría y consumo frontend.
- **Efecto esperado:** `.rsong` completo, portable y auditable, listo para reproducción, análisis y exportación a MIDI.

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
