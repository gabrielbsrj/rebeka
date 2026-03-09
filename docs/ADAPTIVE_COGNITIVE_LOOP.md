# Adaptive Cognitive Loop

## Objetivo

Este documento descreve o ciclo cognitivo adaptativo que foi acoplado a trilha estavel do gemeo Debian/VPS da Rebeka.

A ideia nao e declarar AGI pronta. O objetivo desta camada e aproximar o sistema de um comportamento agentivo geral, fechando um loop operacional continuo:

`perceber -> priorizar -> lembrar -> planejar -> governar -> despachar -> absorver retorno -> replanejar`

## Onde isso roda hoje

Runtime estavel atual:

- `wake_up_rebeka.py` inicia o gemeo remoto e o gemeo local.
- `agent/vps/main.py` e o entrypoint da trilha VPS.
- `agent/local/main.py` continua sendo o executor do lado local.

O ciclo adaptativo novo foi encaixado no lado VPS, sem substituir o bootstrap principal dos gemeos.

## Servicos envolvidos

### 1. Global Workspace

Arquivo: `agent/vps/services/global_workspace.py`

Responsabilidades:

- consolidar sinais do mundo;
- puxar tensoes recentes do usuario;
- considerar horizontes de crescimento ativos;
- formar um conjunto curto de focos priorizados;
- persistir snapshots relevantes no banco.

Evento persistido:

- `global_workspace_snapshot`

Saida principal:

- `snapshot` com `signature`, `summary` e `focuses` ranqueados.

### 2. Episodic Task Memory

Arquivo: `agent/vps/services/episodic_memory.py`

Responsabilidades:

- abrir episodios para focos ativos;
- manter continuidade entre ciclos;
- fechar episodios que saem do workspace;
- atualizar `orchestration_plan` e `task_execution` no banco causal.

Estado mantido por episodio:

- `focus_id`
- `plan_id`
- `task_id`
- `executor_id`
- `recommended_action`
- `priority`
- `planning_horizon`
- `tactical_instruction`
- `execution_status`
- `result_summary`
- `follow_up_action`
- `pending_follow_up_action`

### 3. Adaptive Planner

Arquivo: `agent/vps/services/adaptive_planner.py`

Responsabilidades:

- escolher o modo cognitivo atual;
- transformar focos em agenda tatico-operacional;
- anotar episodios com metadados de execucao;
- reagir a feedback de ferramentas com `replan_hint`;
- gerar uma `follow_up_action` estruturada;
- promover follow-ups pendentes para a agenda do ciclo seguinte;
- gerar um `self_model` operacional com postura, limites e confianca por dominio;
- consolidar um `learning_registry` por dominio e executor;
- recalibrar `executor_id` quando um executor acumula historico fragil;
- aplicar uma `policy layer` explicita com decisoes `auto_execute`, `guided_execute`, `needs_validation` e `defer`.

Modos cognitivos atuais:

- `defense`
- `care`
- `growth`
- `balance`
- `standby`

Eventos persistidos:

- `adaptive_execution_plan`
- `adaptive_replan_request`
- `adaptive_strategy_review`
- `adaptive_learning_update`
- `adaptive_policy_snapshot`
- `adaptive_self_model_snapshot`
- `adaptive_learning_registry_snapshot`

Contrato de feedback atual:

Quando um resultado de ferramenta volta, o planner devolve um payload com:

- `replan_hint`
- `mode`
- `quality_score`
- `confidence_band`
- `follow_up_action`
- `strategic_review`
- `learning_state`

A `follow_up_action` tem um contrato leve e explicito:

- `title`
- `recommended_action`
- `executor_id`
- `horizon`
- `instruction`
- `dispatch_immediately`
- `source=adaptive_feedback`

Heuristica atual:

- sucesso com `quality_score` suficiente gera `follow_up` imediato e seguro, hoje em formato `chat`;
- sucesso com qualidade baixa gera validacao estruturada, nao acao imediata;
- falha gera uma acao estruturada de replanejamento, sem auto-despacho imediato no mesmo retorno;
- cada retorno tambem gera um `strategic_review` com veredito, postura e sinal de aprendizado;
- cada retorno tambem gera um `learning_state` cumulativo por foco;
- o `strategic_review` carrega `priority_delta` e `priority_policy` para o ciclo seguinte;
- o planner monta um `self_model`, um `learning_registry` e uma `policy snapshot` por ciclo antes de liberar a agenda;
- historico fraco pode recalibrar o `executor_id` e derrubar a autonomia para uma postura `skeptical`;
- follow-up nao imediato pode ser promovido pelo planner para a agenda do ciclo seguinte.

### 4. Adaptive Executor

Arquivo: `agent/vps/services/adaptive_executor.py`

Responsabilidades:

- consumir `immediate_actions` do planner;
- usar o canal VPS -> gemeo local para pesquisa profunda;
- correlacionar `tool_result` com o episodio certo;
- calcular `quality_score` para o retorno operacional;
- persistir feedback operacional;
- respeitar `policy_decision` antes de qualquer despacho de ferramenta;
- consumir um plano ja modulado por `learning_registry`, budget e policy;
- disparar follow-up seguro quando o planner devolver uma acao imediata;
- assumir follow-ups pendentes promovidos pelo planner no ciclo seguinte.

Eventos persistidos:

- `adaptive_action_dispatch`
- `adaptive_action_result`
- `adaptive_follow_up_dispatch`

Garantias atuais do executor:

- evita despachos duplicados por assinatura de plano e por `action_id` de follow-up;
- nao dispara follow-up automatico de ferramenta apos feedback;
- follow-up imediato usa `tool_budget_available=False`, o que forca comportamento seguro;
- `guided_execute` em acao tool-backed vira conducao em `chat`, nao disparo automatico;
- `needs_validation` e `defer` viram fila tatica, nao autoexecucao;
- falhas viram memoria de replanejamento, nao recursao automatica.

### 5. Sync Server

Arquivo: `agent/vps/sync_server.py`

Responsabilidades nesta camada:

- receber `tool_result` do gemeo local;
- publicar relatorio no chat;
- notificar consumidores de resultado;
- entregar o retorno ao executor adaptativo.

## Fluxo completo

1. `GlobalWorkspaceService` monta um snapshot.
2. `EpisodicTaskMemory` abre ou atualiza episodios.
3. `AdaptivePlannerService` transforma focos em plano.
4. `AdaptiveExecutorService` despacha acoes imediatas.
5. O gemeo local responde com `tool_result` via `SyncServer`.
6. O executor correlaciona o retorno ao episodio ativo.
7. O executor calcula `quality_score` para o resultado.
8. O planner gera `replan_hint`, `follow_up_action`, `strategic_review` e `learning_state` com base nesse score.
9. O `strategic_review` registra veredito, postura, aprendizado e ajuste de prioridade no episodio.
10. O planner tambem monta um `self_model` operacional com postura de autonomia, capacidade e confianca por dominio.
11. O planner agrega um `learning_registry` com sinais historicos por dominio e executor.
12. Antes do despacho, o planner aplica uma `policy layer` explicita a cada acao da agenda.
13. No ciclo seguinte, o planner aplica `priority_delta`, `priority_policy` e padrao de aprendizado aos focos vivos e aos follow-ups pendentes.
14. Se a acao for segura e marcada com `dispatch_immediately=True`, o executor a despacha no mesmo ciclo.
15. Caso contrario, a acao fica armada no episodio ou em fila tatica, conforme a policy.
16. No ciclo seguinte, o planner pode promover esse follow-up pendente para a agenda.
17. O executor assume essa nova frente quando ela virar acao imediata.

## O que isso permite agora

Esta camada ja permite que a Rebeka:

- mantenha foco global em vez de reagir so a eventos isolados;
- abra frentes operacionais persistentes;
- transforme foco em agenda tatico-operacional;
- despache pesquisa profunda para o gemeo local;
- absorva retorno da ferramenta;
- diferencie retorno forte de retorno fraco antes de agir;
- gere uma revisao estrategica persistida a cada retorno material;
- consolide aprendizado curto entre ciclos;
- molde a prioridade do ciclo seguinte com base nessa revisao;
- opere com um `self_model` explicito de capacidade e postura;
- consolide aprendizado por dominio e executor entre ciclos;
- aplique uma policy explicita para decidir quando autoexecutar, guiar, validar ou adiar;
- recalibre executor e autonomia com base no historico agregado por dominio e executor;
- gere follow-up seguro a partir do aprendizado imediato;
- recoloque replanejamentos pendentes na agenda sem depender de memoria manual;
- mantenha continuidade entre ciclos.

## Limites atuais

O sistema ainda nao e AGI. Hoje esta camada continua sendo AGI-adjacent.

Limites importantes:

- o planejamento ainda e heuristico;
- nao existe modelo de self completo;
- a policy layer ainda e heuristica, embora agora j? considere sinais multi-ciclo;
- nao ha governanca multiobjetivo madura;
- follow-up automatico imediato esta restrito ao caminho seguro de `chat`;
- a promocao de replanejamentos ainda e heuristica e depende do que ficou persistido no episodio.

## Proximos passos recomendados

1. Refinar a `policy layer` com historico multi-ciclo de custo, risco e qualidade por dominio.
2. Separar memoria episodica, semantica e procedural com politicas mais claras.
3. Medir generalidade com benchmarks entre dominios, nao so testes unitarios.
4. Refinar confianca por dominio com historico maior de execucao.
5. Criar politicas de promocao mais finas para distinguir follow-up urgente, tatico e exploratorio.

## Arquivos principais

- `agent/vps/services/global_workspace.py`
- `agent/vps/services/episodic_memory.py`
- `agent/vps/services/adaptive_planner.py`
- `agent/vps/services/adaptive_executor.py`
- `agent/vps/sync_server.py`
- `agent/vps/main.py`
- `agent/tests/test_global_workspace.py`
- `agent/tests/test_episodic_memory.py`
- `agent/tests/test_adaptive_planner.py`
- `agent/tests/test_adaptive_executor.py`
- `agent/tests/test_adaptive_feedback_loop.py`