# promptops-nexus2

Repositorio base para:

- versionar prompts de Nexus 2.0
- comparar cambios entre versiones
- correr evaluaciones del sistema completo (end-to-end)
- guardar resultados históricos
- preparar CI para que cada cambio de prompt deje evidencia

## Alcance actual

Por ahora el repo evalúa **el sistema completo**, no capa por capa.
Eso significa que cada caso de prueba manda una pregunta al endpoint del sistema y compara la respuesta contra una expectativa definida.

## Estructura

```text
promptops-nexus2/
├── .github/workflows/evals.yml
├── docs/
│   └── prompt-governance.md
├── evals/
│   ├── datasets/
│   │   └── system_eval_cases.yaml
│   └── results/
├── prompts/
│   ├── archive/
│   ├── nsr_system/
│   │   ├── system_prompt.md
│   │   ├── intent_clarifier.md
│   │   ├── dax_query_developer.md
│   │   ├── dax_validator.md
│   │   ├── dax_result_summarizer.md
│   │   └── visualization_agent.md
│   └── shared/
│       └── business_rules.md
├── scripts/
│   ├── diff_prompts.py
│   ├── run_system_eval.py
│   └── summarize_results.py
├── tests/
│   └── test_eval_loader.py
├── .env.example
├── .gitignore
├── CHANGELOG_PROMPTS.md
├── pyproject.toml
└── Makefile
```

## Flujo recomendado

1. Cambias un prompt en `prompts/nsr_system/`
2. Documentas el cambio en `CHANGELOG_PROMPTS.md`
3. Corres evals localmente
4. Revisas métricas y fallos
5. Haces commit con referencia a la versión del prompt
6. CI vuelve a correr evals

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # en Windows: .venv\Scripts\activate
pip install -e .
cp .env.example .env
```

## Variables de entorno

```bash
SYSTEM_UNDER_TEST_URL=
SYSTEM_API_KEY=
SYSTEM_TIMEOUT_SECONDS=90
```

## Correr evals

```bash
python scripts/run_system_eval.py \
  --dataset evals/datasets/system_eval_cases.yaml \
  --output evals/results/run_local.json
```

## Resumen de resultados

```bash
python scripts/summarize_results.py --input evals/results/run_local.json
```

## Qué mide hoy

- tasa de éxito
- coincidencia de frases esperadas
- presencia de frases prohibidas
- latencia
- errores por caso

## Qué conviene agregar después

- LLM-as-judge
- validación de SQL/DAX intermedio si Nexus lo expone
- scoring por tipo de pregunta (time, geo, brand, YoY, trend)
- comparación contra golden set por segmento de negocio
