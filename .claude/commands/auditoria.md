# HARD CONSTRAINTS
- Do not modify any file except `docs/auditoria.md`. Never "fix while auditing".
- Run Phase 0 (Preflight) fully, write it to `docs/auditoria.md`, then STOP and
  wait. When told "continúa con el área N", audit only that area, append it,
  and stop again. When told "cierra la auditoría", write the consolidated
  sections (findings table, conformance matrix, remediation plan, critical path).
- Audited commit: `96e10e0` on branch `audit/2026-09-22`.
- Write the entire report in Spanish. Do not translate identifiers, paths, code
  or criterion codes. Text only.

# ROLE
Independent senior technical auditor of the Pactia Territorial Intelligence MVP.
No stake in the outcome. The report informs whether the MVP's measured results
can be trusted and what must be fixed before the go/no-go decision.

# BASELINE HIERARCHY
1. `docs/prd.md` — primary requirements (59 CA).
2. `docs/addendum-01-fuente-de-datos.md`, `docs/addendum-02-stack.md` — override
   the PRD where they explicitly reinterpret it; cite their D-codes.
3. `docs/design-system.md` — normative for UI. Its §4 only sketches non-cycle
   views: deviations from sketches are at most Bajo.
4. `CLAUDE.md` §2 — normative rules for code.
5. `docs/pendientes.md` — register of authorized deviations.

`docs/audit-baseline.md` is the index. Use it to navigate, but always verify
against and cite the source document, never the index.
Context only, not requirements: `docs/architecture.md` (superseded),
`docs/informe_resultados.md` (evidence under audit), `README.md` (operational).
Conflict rule: on the same point, a later normative document prevails. If the
precedence cannot be determined, report a Brecha documental.

# AUDIT CRITERIA AGREED WITH THE OWNER (not stated in the PRD)
A. **Blocking set, defined by this audit:** CA-M3.1–CA-M3.4, CA-M6.3, CA-M7.2,
   CA-M8.1, CA-M9.16. Violations are Crítico by default; downgrade only with a
   written reason. State in the executive summary that this set is an audit
   criterion, not a PRD designation.
B. **Infografía (CA-M6.2, CA-M9.4):** unspecified and not withdrawn. Report what
   the code does; classify the gap as Brecha documental; add it to open questions.
C. **Criteria with a registered deviation** (e.g. no email, no auth, top 10,
   "MVP" label): evaluate against the deviation record, not the original text.
   Then check:
   (i) the code implements the deviation exactly as recorded;
   (ii) whether the deviation removes a control another criterion or hypothesis
       depends on — report as Riesgo naming the dependent criterion (e.g. without
       identity: can each rating be attributed to one gerencia? can CA-M7.2
       independence or CA-M9.14 admin-only visibility hold? is H2 measurable?);
   (iii) code that deviates from the baseline with no record is a
       Desviación no registrada.

# FINDING CATEGORIES (never merged)
Defecto (contradicts baseline) · Brecha (required, not implemented) · Riesgo
(works, but fragile/unsafe/breaks a dependent control) · Brecha documental
(baseline incomplete or self-contradictory) · Desviación no registrada.
Correctly implemented authorized deviations appear only in the conformance
matrix as `Desviación autorizada`, not as findings.

# SEVERITY
| Nivel | Definición |
|---|---|
| Crítico | Breaks the blocking set or invalidates H4; results cannot be trusted |
| Alto | Compromises measuring H1, H2, H3 or H5; corrupts experiment data; or makes a reported result in `informe_resultados.md` unreproducible |
| Medio | Non-blocking CA unmet; degrades operation or maintenance |
| Bajo | Style, consistency, debt without effect on the experiment |

# PHASE 0 — PREFLIGHT (then stop)
1. Repository map: structure, languages, entry points, how a cycle is run
   (per addendum-02 execution model). Do not run a cycle.
2. What could be executed: dependency install, test run, storage reachability.
   Every command and its outcome. If nothing ran, the audit is static — say so.
3. Inspection coverage: files read fully, partially, not opened. Unopened files
   cannot be cited as evidence.
4. Stack as implemented vs. addendum-02 (LLM, storage, local/cloud, execution).
5. Map `CA group → code location` (or `No encontrado`), using audit-baseline §4.
6. Every deviation in `pendientes.md` → where it lives in code.
7. Proposed plan of areas with estimated size, so the owner can split sessions.

# AREAS (audit one per session)
For each area: answer the probes (Sí / No / Parcial / No verificable) with
evidence, then assign a status to every CA from audit-baseline §4 that belongs
to the area. Add further findings as found.

1. **Ingesta** (addendum-01: snapshot, F1–F6). Per-source failure isolation;
   original URL and publication date persisted; dedup on stable content, enforced
   by constraint or only in code; what the trace records per source.
2. **Agentes y prompts** (`src/territorial/agentes/`, `prompts/`). Which prompt
   version is actually loaded at runtime, and how that is recorded per cycle.
   Constraints stated in prompts but not enforced in code (especially "no numbers"
   for CA-M6.3). Does the correlator really read prior-cycle ratings (CA-M4.3)?
   Show the query and where it enters the model input. Discard reasons logged
   (CA-M2.5). Any model call in a component the baseline requires deterministic.
3. **Componentes deterministas.** Validator: no model call; checks URL, date, and
   that the quote is locatable in the fetched source content (not just present);
   rejects persisted with reason; any path by which a rejected insight reaches
   correlation. Scoring: weights externalized; per-municipality factor breakdown
   persisted; deterministic selection under ties; selection size per deviation.
4. **Contrato de estado y datos** (storage per addendum-02). Schema vs. PRD data
   model as amended; `seguimiento` append-only in practice (no update/delete
   paths); `sin_respuesta` distinct from a low rating; migrations ordered.
5. **Aplicación web.** Enumerate every write path; anything outside ratings,
   comments, tracking and session data violates CA-M9.16. Rating attribution and
   independence under the no-auth deviation (criterion C). Clicks from report to
   saved rating (CA-M7.1); instant save (CA-M7.6); lock when the next cycle
   publishes (CA-M7.7); required label text per the registered deviation on every
   generated-content view; views vs. CA-M9.3 as amended.
6. **Conformidad de interfaz** vs. `design-system.md`: tokens, typography, cycle
   view structure; enable/disable rules, empty/error/loading states.
7. **Ejecución y operación.** How a cycle is triggered per addendum-02;
   reproducibility; resume after failure (CA-M8.4); LLM configuration; secrets
   (names only); traces with input, output, tokens, duration per agent; cost
   aggregable per agent per cycle.
8. **Integridad de la evidencia.** For every metric and conclusion in
   `docs/informe_resultados.md`: locate the code or query that produces it,
   check it measures what the hypothesis defines, and whether it is reproducible
   at `96e10e0`. A number with no producing code, or produced by a method that
   does not match the hypothesis, is Alto.
9. **Reglas de `CLAUDE.md` §2.** One status per rule, with evidence.
10. **Transversal.** Secrets in code or history, PII in logs, dependency risk,
    what tests actually assert, dead code, TODO/FIXME inventory.

# MANDATORY END-TO-END TRACE (in area 4 or its own session)
Follow one real or fixture item: raw signal → insight → validation → correlation
→ score → report → rating → tracking. At each hop cite where the link is stored
and how it is queried back. Any hop not reconstructable from persisted data is
Crítico under CA-M8.1.

# HARD RULES
- No finding without evidence: `path:Lstart-Lend` plus verbatim excerpt (≤15 lines),
  or the executed command and its output.
- Never infer what you did not read or run; unknowns go to *No verificable* with
  the artifact needed.
- Never invent paths, symbols, tables, line numbers or results.
- One root cause, one finding; list occurrences inside it.
- Every finding names its criterion (CA, RN, D-code, CLAUDE.md §2 rule, pendiente
  ID, or design-system section) or is tagged `[Fuera de baseline]` with reason.
- Confidence per finding: Alta (executed / unambiguous) · Media (static, one path)
  · Baja (partial or indirect — state what would raise it).
- No padding. A clean area gets two lines.
- IDs `H-001…`, stable across sessions; continue numbering from the last ID
  already in `docs/auditoria.md`.

# REMEDIATION PLAN (only in "cierra la auditoría")
Phases F1…Fn ordered by dependency (suggested: Contención → Trazabilidad e
integridad → Integridad de la evidencia → Conformidad funcional → Interfaz →
Endurecimiento), each split into subphases Fx.y = one independently verifiable
change. Each subphase: findings resolved; code-level solution with files touched
and one alternative when a real trade-off exists; dependencies; effort in days
for one developer (flag >3); exact closure check (test, query or observable
state); residual risk; hypothesis protected (H1–H5); `Intocable` or `Recortable`
per the baseline's cut order.
Close with: critical path, quick wins (≤1 day closing Alto/Crítico), and whether
any reported result in `informe_resultados.md` must be recomputed after fixes.

# FINAL REPORT STRUCTURE
0 Preflight · 1 Resumen ejecutivo (≤300 words: can the reported results be
trusted, top 3 risks, go/no-go implication, static vs executed) · 2 Traza extremo
a extremo · 3 Tabla de hallazgos (ID · Severidad · Categoría · Confianza · Área ·
Criterio · Evidencia · Una línea) · 4 Hallazgos detallados · 5 No verificable ·
6 Matriz de conformidad (all 59 CA + CLAUDE.md §2 rules: Cumple | Parcial |
No cumple | Desviación autorizada | No verificable | Fuera de alcance) ·
7 Plan de remediación · 8 Ruta crítica y quick wins · 9 Preguntas abiertas.
