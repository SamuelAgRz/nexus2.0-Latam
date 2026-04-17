# Prompt Governance

## Objetivo
Tener trazabilidad de cada cambio de prompt y su impacto en el sistema completo.

## Reglas mínimas
1. Ningún cambio de prompt va directo a main sin evals.
2. Cada cambio debe actualizar `CHANGELOG_PROMPTS.md`.
3. Cada corrida debe guardar resultados en `evals/results/`.
4. Cada caso de prueba debe tener un ID estable.
5. Cuando una respuesta correcta cambia por negocio, se actualiza el dataset y se documenta la razón.

## Convención de versionado
- `v0.x`: cambios exploratorios
- `v1.x`: cambios estables de comportamiento
- `v1.x.y`: ajustes menores o fixes

## Convención para prompts
- Un archivo por agente
- Reglas compartidas en `prompts/shared/business_rules.md`
- No duplicar reglas críticas en múltiples prompts si se puede evitar

## Convención para evals
Separar por categorías:
- time intelligence
- geography
- channel
- brand / trademark
- YoY / variance
- top / bottom
- trends
- ambiguity / clarification
