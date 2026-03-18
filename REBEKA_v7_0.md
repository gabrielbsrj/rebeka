# REBEKA v7.0 — DOCUMENTO VIVO (ESTADO REAL + RUMO)
**Data:** 2026-03-17  
**Status:** Atualizado para refletir o codigo atual e o caminho de evolucao

---

## Resumo Executivo

Este documento substitui descricoes anteriores da v7 como se tudo estivesse pronto.
Hoje, a Rebeka opera com dois trilhos:

- **Trilho estavel (gêmeos VPS + Local)**: e o runtime real em uso.
- **Trilho v6.2 Cognitive OS (agent/main.py)**: existe, mas nao e o bootstrap principal.

A **v7 real** neste momento e: **gêmeos + loop adaptativo** acoplado ao VPS.
O rumo do desenvolvimento e **convergir** esses trilhos em um bootstrap unificado,
sem perder a estabilidade atual.

---

## Estado real de execucao (as-built)

### Bootstrap atual (real)

- `wake_up_rebeka.py` inicia o gêmeo VPS e o gêmeo Local.
- VPS: `agent/vps/main.py`
- Local: `agent/local/main.py`

O `agent/main.py` (Cognitive OS v6.2) **nao** e o caminho principal
de inicializacao neste momento.

### Armazenamento real

- Base atual: **CausalBank** (`memory/causal_bank.py`).
- Nao ha esquema Postgres v7 aplicado nesta base.

### Adaptadores e canais

- VPS: `vps/adapters/telegram_adapter.py` e `vps/adapters/discord_adapter.py`
- Local: `local/adapters/whatsapp_local_adapter.py`, `local/adapters/browser_adapter.py`
- Tool local: `whatsapp_send_message` (passa pelo guardrail de transparência)
- Sync Local -> VPS: `context_sync` (abstrações de tela) persistido no CausalBank, com dedupe local e janela de reenvio (`REBEKA_CONTEXT_RESEND_MINUTES`)
- Sinais de comunicação relevantes podem virar `conversation_signals` (threshold `REBEKA_COMM_CONVERSATION_THRESHOLD`).

### Monitores ativos (VPS)

Exemplos reais em uso:
`geopolitics`, `macro`, `financial`, `commodities`, `energy`, `innovation`,
`corporate`, `rare_earths`, `report_monitor`, `survival_monitor`, etc.

---

## Loop cognitivo adaptativo (implementado)

O loop a seguir esta **rodando no VPS** e e o coracao da v7 atual:

`perceber -> priorizar -> lembrar -> planejar -> governar -> despachar -> absorver retorno -> replanejar`

### Servicos reais

1. **Global Workspace**
   - Arquivo: `agent/vps/services/global_workspace.py`
   - Consolida sinais e produz foco global.

2. **Episodic Task Memory**
   - Arquivo: `agent/vps/services/episodic_memory.py`
   - Abre episodios e mantém continuidade entre ciclos.

3. **Adaptive Planner**
   - Arquivo: `agent/vps/services/adaptive_planner.py`
   - Converte foco em agenda tatico-operacional.
   - Aplica policy (`auto_execute`, `guided_execute`, `needs_validation`, `defer`).
   - Gera `self_model`.
   - Agrega `learning_registry` por **dominio, executor e tool**.
   - Recalibra executor e postura quando historico multi-ciclo e fraco.

4. **Adaptive Executor**
   - Arquivo: `agent/vps/services/adaptive_executor.py`
   - Respeita policy antes de qualquer despacho.
   - Correlaciona `tool_result` com episodios.
   - Calcula `quality_score`.
   - Persiste `delivery_learning_state` por **tool** e **executor**.
   - Registra auditoria de transparencia quando `whatsapp_send_message` aplica identificacao.

5. **Sync Server**
   - Arquivo: `agent/vps/sync_server.py`
   - Recebe `tool_result` e `context_sync` do gêmeo local.
   - Persiste sinais abstratos do contexto local no CausalBank.
   - Normaliza `context_sync` com `created_at`, `source_id` e `priority_score` antes de persistir.

Este ciclo esta **testado** por:
- `agent/tests/test_global_workspace.py`
- `agent/tests/test_episodic_memory.py`
- `agent/tests/test_adaptive_planner.py`
- `agent/tests/test_adaptive_executor.py`
- `agent/tests/test_adaptive_feedback_loop.py`

---

## Componentes reais fora do loop adaptativo

### Módulos v6.2 (Cognitive OS)

Estao presentes, mas **nao sao o bootstrap principal**:

- `agent/main.py`
- `agent/core/event_bus.py`
- `agent/core/orchestration_engine.py`
- `agent/core/scheduler.py`
- `agent/infrastructure/system_awareness.py`
- `agent/infrastructure/system_health_monitor.py` (stub)

### Modulos de automacao/processamento

Em uso parcial, ainda heuristico:

- `agent/automation/financial_radar.py`
- `agent/automation/whatsapp_responder.py`
- `agent/processors/email_manager.py`
- `agent/processors/opportunity_detector.py`
- `agent/memory/memory_core.py` (agenda morning briefing e sinais de conversa)

---

## O que esta atualizado vs. o que ainda e aspiracional

### Ja implementado (v7 real)

- Gêmeos VPS + Local em execucao.
- Loop adaptativo no VPS (workspace, episodic, planner, executor, feedback).
- Policy layer real e postura `skeptical` quando historico e fraco.
- Aprendizado por dominio, executor e tool (learning registry).
- Privacidade local basica com `PrivacyFilter` + `PrivacyAuditor`.
- Guardrail de transparência no WhatsApp local (identificação automática + whitelist via env).
- Sync Server persiste `context_sync` (sinais abstratos) no CausalBank.
- Workspace global filtra sinais de comunicação de baixa relevância para evitar ruído (configurável via `REBEKA_COMM_MIN_RELEVANCE`).
- Contexto local enriquecido com domínio/relevância, `context_signature` e `created_at`, e deduplicado antes de enviar (`REBEKA_CONTEXT_RESEND_MINUTES`).
- Comunicação relevante pode alimentar `conversation_signals` e tensões do usuário (threshold `REBEKA_COMM_CONVERSATION_THRESHOLD`).
- Sync Server aplica dedupe adicional por assinatura (`REBEKA_CONTEXT_DEDUP_TTL_SECONDS`) antes de persistir.
- `conversation_signals` de comunicação incluem `summary` curto e `values_revealed` heurístico.
- Workspace global aproveita `values_revealed` e `external_events` para enriquecer a tensão do usuário.
- Valores percebidos podem gerar um `growth_target` inicial (se ainda não existir para o domínio).
- Fricção de comunicação repetida pode gerar `behavioral_patterns` (thresholds via `REBEKA_COMM_PATTERN_MIN_COUNT` / `REBEKA_COMM_PATTERN_SCORE_THRESHOLD`).
- Workspace global pode promover `behavioral_patterns` como focos ativos.
- Planner considera `behavioral_patterns` para reduzir orçamento e manter postura cautelosa quando o domínio já está frágil.
- Planner integra `behavioral_pressure` na policy layer, forçando `guided_execute` em domínios frágeis para controle de risco no executor.
- Workspace global aplica decay temporal a `behavioral_patterns` — patterns inativos por mais de `REBEKA_BEHAVIORAL_PATTERN_TTL_HOURS` (default 72h) deixam de gerar focos, permitindo recuperação natural de domínios curados.

### Ainda aspiracional (nao esta no codigo atual)

- Banco Postgres com schema completo v7.
- Memory Core tripartido (episodic/semantic/procedural) com decay real.
- Decision Engine com scoring historico integrado.
- Learning Loop de previsoes com heuristicas bayesianas.
- System Health Monitor completo com auto-heal real.
- Bootstrap unificado em `main.py` com graceful shutdown e conflito critico bloqueando boot.
- Protocolo de transparência WhatsApp completo (consentimento persistido, lista em banco e auditoria ampla).

---

## Invariantes (desejados) e estado real

| Invariante | Estado atual |
|---|---|
| Rebeka nunca paga | **Parcial** (regra de design; sem guardrail global) |
| Sempre se identifica ao falar externamente | **Parcial** (guardrail no WhatsApp local; whitelist via env) |
| Aprovacao humana para operacoes financeiras | **Parcial** (guardrail no planner para intentos de pagamento/operacao) |
| Conflito critico bloqueia boot | **Sim no VPS** (audit gate ativo; bypass via `REBEKA_SKIP_CONFLICT_AUDIT`) |
| Privacidade local (dados sensiveis nao saem crus) | **Parcial** (há filtros no gêmeo local) |
| 80% age, 20% pergunta | **Nao** (policy existe, mas nao esta calibrada com esse criterio) |

---

## Direcao de desenvolvimento (rumo claro)

1. **Convergencia de bootstrap**
   - Consolidar o runtime estavel (gêmeos) com o Cognitive OS.
   - Definir um unico `main.py` oficial.

2. **Memoria real v7**
   - Evoluir `MemoryCore` para episodica/semantica/procedural.
   - Implementar decay real e busca semantica.

3. **Learning Loop real**
   - Persistir previsoes, medir resultado, ajustar heuristicas.
   - Integrar com o planner (impacto direto na prioridade).

4. **Decision Engine calibrado**
   - Scoring por historico e risco real.
   - Gate de aprovacao centralizado.

5. **Governanca e seguranca**
   - Invariantes enforced no bootstrap e no executor.
   - Policy unificada para acao automatica vs. validacao.

---

## Arquivos principais (estado atual)

- `wake_up_rebeka.py`
- `agent/vps/main.py`
- `agent/local/main.py`
- `agent/vps/services/global_workspace.py`
- `agent/vps/services/episodic_memory.py`
- `agent/vps/services/adaptive_planner.py`
- `agent/vps/services/adaptive_executor.py`
- `agent/vps/sync_server.py`
- `agent/memory/memory_core.py`
- `agent/automation/financial_radar.py`
- `agent/automation/whatsapp_responder.py`
- `agent/processors/email_manager.py`
- `agent/processors/opportunity_detector.py`
- `agent/core/event_bus.py`
- `agent/main.py`

---

## Conclusao

A v7 **nao esta pronta como "sistema unificado"**, mas **a espinha dorsal agentiva ja existe**
no loop adaptativo do VPS. O proximo passo nao e "inventar novos modulos",
e sim **unificar o bootstrap e transformar aspiracoes v7 em contratos reais**.

Este documento deve permanecer alinhado com o codigo:
se o codigo mudar, o documento muda junto.
