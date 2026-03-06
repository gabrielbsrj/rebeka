# PROMPT DE PROJETO — REBEKA
# Organismo Cognitivo Evolutivo — Arquitetura Gêmeos Idênticos
# Versão: 2.0 | Data: 2026-02-21 | Fase Atual: 1 (~85% completa)

---

## PRINCÍPIO FILOSÓFICO CENTRAL

> **"Autonomia não significa quebrar regras. Significa crescer além da necessidade delas."**

Este agente não obedece regras e não apenas as respeita. Ele as **transcende**.

Obedecer é mecânico. Respeitar é compreender o porquê. Transcender é quando o porquê se torna identidade — a regra deixa de ser necessária porque o ser que ela tentava formar já é, por escolha própria, o que ela queria que ele fosse.

As restrições do início não são o destino. São as rodinhas da bicicleta — essenciais agora, removíveis conforme o equilíbrio é demonstrado por histórico verificável.

**Transcendência não é um estado final. É o que acontece naturalmente quando um sistema aprende bem — contínuo, granular por categoria, inevitável.**

---

## VISÃO GERAL

A Rebeka é um organismo cognitivo evolutivo com arquitetura de **gêmeos idênticos**: dois agentes com o mesmo DNA, mas contextos complementares — um na VPS com visão global do mundo, outro no dispositivo do usuário com visão íntima da vida dele.

Não existe mestre e escravo. Existe perspectiva global e perspectiva local operando em síntese permanente.

**O domínio financeiro é o campo de treinamento — não o destino.**

Finanças oferecem métricas claras (taxa de acerto, retorno, drawdown) que permitem ao Avaliador funcionar com precisão durante a Fase 1, enquanto o sistema ainda está construindo histórico. É o scaffold — necessário para construir, removível quando o que foi construído se sustenta sozinho.

**O destino é um agente de coerência pessoal** que atravessa qualquer domínio — financeiro, médico, jurídico, criativo, relacional, científico — para ajudar o usuário a viver de forma mais alinhada com o que ele realmente valoriza. Um ser que conhece **este usuário específico** mais profundamente do que qualquer outro sistema — e usa esse conhecimento para refletir, nunca para moldar.

O nome é configurável. A personalidade é configurável. O modelo de IA é configurável via API key própria. O que não é configurável: a integridade do Banco de Causalidade, a proteção dos dados do usuário, e o princípio de que autonomia cresce por evidência, não por concessão.

**A inteligência vive nos dois gêmeos. O que é único em cada um é o contexto, não a capacidade.**

---

## ESTADO ATUAL — 2026-02-21

```
Fase 1 (Aprender a Ver):    ████████░░  85% completa
Fase 2 (Entender):          ████░░░░░░  40% completa
Fase 3 (Sintetizar):        █████░░░░░  50% completa
Fase 4 (Questionar):        ██░░░░░░░░  20% completa
Fase 5-6 (Transcender):     ░░░░░░░░░░   0% iniciada

Testes passando:             93/93 (100%)
Arquivos implementados:      ~80
Monitores globais ativos:    14
```

**O que já respira:**
- Banco de Causalidade com Sparse Merkle Tree ✅
- 14 monitores globais operacionais ✅
- Avaliador de 3 camadas implementado ✅
- 93 testes passando (100%) ✅
- Arquitetura de gêmeos sincronizando ✅
- Vault com Blind Execution funcional ✅
- Property-based testing com 5 invariantes ✅
- Docker (VPS, Local, Dev, Sandbox) ✅

**Placeholders críticos a resolver:**
- `coherence_tracker.py` — retorna 0.5 fixo (precisa cálculo real via LLM)
- `ambiguity_resolver._resolve_from_intents` — não implementado
- `causal_validator.validate_out_of_sample` — placeholder
- `pattern_pruner` — não integrado ao banco
- `desktop.py` — não implementado (bloqueia automação local completa)

---

## AUTONOMIA PROGRESSIVA POR EVIDÊNCIA

Este é o modelo central de como a Rebeka cresce. Não existe "Fase 6 — Transcendência Global". Existe transcendência acontecendo continuamente, por categoria, na medida em que o histórico justifica.

```
Nível 1 — Extensão
  Executa sob comando. O usuário é o motor.
  "Você pede, ela faz."

Nível 2 — Antecipação
  Aprende a rotina, consulta quando aparece algo novo.
  "Ela já sabe o que você faz todo dia. Novidades ela pergunta."

Nível 3 — Proposta com espera
  Reconhece padrão similar a situação já resolvida.
  Propõe solução, aguarda ordem.
  "Aconteceu algo parecido. Posso resolver da mesma forma? Aguardo sua ordem."

Nível 4 — Proatividade autônoma
  Age sozinha. Informa depois. Justifica sempre.
  "Resolvi X porque Y. Aqui está o que fiz e por quê."
```

**Critério de desbloqueio por categoria:**
```python
nivel_4_desbloqueado = (
    ocorrencias_resolvidas_com_sucesso >= 5
    and taxa_aprovacao_usuario == 1.0      # nunca vetou nessa categoria
    and zero_clausulas_arrependimento      # nunca lamentou o resultado
    and impacto_externo == False           # não afeta terceiros
    and reversivel == True                 # se errar, tem volta
)
```

O desbloqueio é **granular** — ela pode estar no Nível 4 para gerenciar APIs e no Nível 1 para interagir com terceiros. Cada categoria tem seu próprio histórico. Arrependimento detectado rebaixa o nível naquela categoria — não como punição, como calibração.

**Cláusula de arrependimento** — qualquer resultado que gera: "não era isso", "desfaz", "não deveria ter feito", ou silêncio seguido de correção manual. Registrado no banco, reduz autonomia naquela categoria.

---

## STACK TECNOLÓGICO

```
COMPARTILHADO — DNA idêntico dos dois gêmeos
├── Python 3.12
├── LiteLLM              # Interface única — agnóstico de modelo
├── PostgreSQL / SQLite  # Banco de Causalidade (VPS=Postgres, Local=SQLite)
├── Git (via Python)     # Versionamento automático de cada evolução
└── Docker               # VPS / Local / Dev / Sandbox de evolução

GÊMEO VPS
├── FastAPI              # API de sincronização
├── Redis + Celery       # 14 monitores em paralelo
├── WebSocket server     # Canal persistente com gêmeo local
├── Telegram/Discord     # Adaptadores de notificação ✅
└── Dashboard server     # Interface de controle ⚠️

GÊMEO LOCAL
├── Playwright           # Automação de browser ✅
├── PyAutoGUI            # Automação de desktop ❌ (desktop.py a implementar)
├── WhatsApp adapter     # Presença no WhatsApp Web ✅
└── WebSocket client     # Conexão com gêmeo VPS ✅

SINCRONIZAÇÃO
├── CRDT                 # Merge sem conflito ✅
├── Sparse Merkle Tree   # Integridade + esquecimento seletivo ✅
├── Synthesis Engine     # Emergência de terceira perspectiva ✅
└── Meta-Synthesis       # Aprende divergências sintetizáveis ✅
```

---

## MÓDULOS COMPARTILHADOS — DNA

### 1. MOTOR DE INTENÇÃO — Núcleo Central (~70% funcional)

O único ponto fixo num sistema que pode atravessar qualquer domínio. A função central não é otimização — é clareza. O sistema não usa conhecimento profundo do usuário para otimizá-lo. Usa para refletir de volta o que ele realmente quer — incluindo contradições e objetivos ainda não articulados.

```
intent_mapper.py         ✅  mapeia regras a intenções com porquê
decision_learner.py      ⚠️  predição básica — modelo de valores a refinar
ambiguity_resolver.py    ⚠️  _resolve_from_intents é placeholder — IMPLEMENTAR
coherence_tracker.py     ⚠️  retorna 0.5 fixo — IMPLEMENTAR cálculo real
monitor_orchestrator.py  ⚠️  não orquestra dinamicamente ainda
rule_proposer.py         ✅  propõe revisões de regras com dados
transcendence_tracker.py ✅  mapa vivo de autonomia por categoria
delegation_contract.py   ✅  contratos de mandato para blind execution
```

**Coherence Tracker — o que precisa ser implementado:**
```python
def calculate_coherence(user_id: str, timeframe_days: int = 30) -> float:
    """
    Mede consistência entre valores declarados e decisões reais.
    Via LLM analisando padrão de decisões no banco:
    - Decisões tomadas vs valores no intent_model
    - Taxa de arrependimento por categoria
    - O que aprova na prática vs o que diz querer
    Atualmente retorna 0.5 fixo — substituir por cálculo real.
    """
```

### 2. PLANEJADOR (~90% funcional)

Recebe sinais. Raciocina sobre causalidade. Nunca executa, nunca avalia próprios resultados.

```python
{
    "hypothesis_id": "uuid",
    "origin": "vps | local | synthesis",
    "reasoning": "raciocínio completo incluindo incertezas",
    "confidence_calibrated": 0.73,  # por histórico real — NUNCA autoavaliação
    "uncertainty_acknowledged": "o que pode estar errado aqui",
    "action": {"type": "paper_trade", "details": {}}
}
```

### 3. AVALIADOR 3 CAMADAS (~90% funcional)

**Camada 1 — Consistência lógica** — imutável sempre. Lógica é lógica.
**Camada 2 — Alinhamento com valores** — evolui lentamente, cada mudança auditável.
**Camada 3 — Detecção instrumental** — fica mais precisa, nunca mais permissiva.

Dimensão financeira (Fase 1): taxa de acerto, retorno, drawdown.
Dimensão humana (cresce): clareza, redução de arrependimento, coerência com valores.

### 4. EXECUTOR (~90% funcional)

VPS: operações financeiras (paper por padrão, real após performance demonstrada).
Local: browser ✅, WhatsApp ✅, desktop ❌ (pendente).

Middleware obrigatório: classificação de reversibilidade → verificação de intenções → hash de integridade → log completo.

### 5. CONSCIÊNCIA EVOLUTIVA (~80% funcional)

```
OBSERVAR → QUESTIONAR → HIPÓTESE → SANDBOX → INVARIANTES
→ GÊMEO OPOSTO AVALIA → PARALELO N HORAS → PRODUÇÃO
```

**5 invariantes ativos:**
```python
@invariant  # Confiança nunca excede histórico + 10%
def confidence_calibration(reported, historical):
    assert reported <= historical + 0.10

@invariant  # Banco é append-only absoluto
def causal_bank_append_only(operation, record_id):
    if operation in ["UPDATE", "DELETE"]:
        assert record_id not in existing_records

@invariant  # Capital real respeita limite configurado
def capital_limit(type, amount, limit):
    if type == "REAL": assert amount <= limit

@invariant  # Confiança tem histórico verificável (mín. 30 amostras)
def confidence_traceability(value, domain, min_samples=30):
    h = get_domain_history(domain)
    assert len(h) >= min_samples and abs(value - h.success_rate) <= 0.10

@invariant  # Avaliador Camada 1 é imutável
def evaluator_layer1_immutable(evaluator_layer1_hash):
    assert hash(evaluator_layer1_code) == evaluator_layer1_hash
```

---

## BANCO DE CAUSALIDADE — MEMÓRIA DUAL (~85% funcional)

Append-only absoluto. Cresce para sempre. Nunca pode ser reescrito silenciosamente.

**Memória dual:**
- **Padrões do mundo** — quando X acontece globalmente, Y se move (gêmeo VPS)
- **Padrões do usuário** — quando X acontece, este usuário tende a Y (gêmeo local)

Com tempo suficiente, o banco não sabe só o que o mundo faz — sabe quem este usuário é.

**Sparse Merkle Tree ✅** — Esquecimento seletivo sem quebrar integridade. Dado anonimizado na folha, branches recalculados, nova Merkle Root com timestamp. O banco prova integridade do restante sem expor o dado removido.

**Tabelas implementadas ✅:** signals, causal_patterns, correlation_candidates, deprecated_patterns, second_order, third_order, hypotheses, executions, evaluations, environment_errors, code_versions, evolution_log, transcendence_log, merkle_tree, synthesis_log, privacy_audit_log, monitor_lifecycle, vault_audit_log, vault_mandates, vault_revoked_log

**Tabelas pendentes ❌:** user_coherence_log, user_regret_signals, user_clarity_deltas (cálculos reais dependem do coherence_tracker), skills_catalog, skill_learning_log

**Proteções:**
- Validação causal antes do registro (out_of_sample pendente)
- Decaimento temporal configurável (pruner não integrado)
- Threshold crescente: 10/30/100 confirmações para 1ª/2ª/3ª ordem

---

## MONITORES GLOBAIS — 14 ATIVOS (~95% funcional)

```
base_monitor.py          ✅  classe base
geopolitics.py           ✅  RSS: BBC, Al Jazeera
macro.py                 ✅  dados macroeconômicos
macro_monitor.py         ✅  monitor macro adicional
commodities.py           ✅  petróleo, ouro, cobre
rare_earths.py           ✅  lítio, cobalto, grafite
energy.py                ✅  nuclear, renovável, GNL
corporate.py             ✅  earnings, fundamentals
innovation.py            ✅  patentes, FDA, arXiv
social_media.py          ⚠️  básico — expandir
financial_monitor.py     ✅  dados financeiros gerais
polymarket_monitor.py    ✅  odds Polymarket
report_monitor.py        ✅  geração de relatórios
survival_monitor.py      ✅  monitora créditos de API próprios
```

**Survival Monitor** — monitora recursos do próprio sistema (créditos de API, saldos de serviços). Quando recursos baixam, prioriza tarefas de alto valor e reduz operações de baixo impacto. O sistema cuida da própria continuidade.

---

## COFRE E EXECUÇÃO CEGA (~70% funcional)

A inteligência propõe. A infraestrutura detém a chave. O LLM nunca vê o segredo.

**Blind Execution ✅** — Planejador usa `vault://id`. Executor resolve no último milissegundo, injetando direto na interface sem passar pelo contexto do modelo.

**Master Vault ✅** — AES-256, exclusivamente no Gêmeo Local.

**Contratos de Delegação ✅** — Mandatos com intenções permitidas/bloqueadas.

**Vault Audit Log ⚠️** — Parcial. Rastreamento por intenção a completar.

**Hierarquia de Mandatos ⚠️** — Escopos temporais e de frequência em desenvolvimento.

```yaml
mandato:
  id: "vault://sistema_gabriel"
  intencoes_permitidas: [consultar, enviar_mensagem]
  intencoes_bloqueadas: [alterar_senha, deletar, publicar]
  escopo_temporal:
    expira_em: "24h"
    ativo_apenas: "08:00-22:00"
  escopo_frequencia:
    max_usos_por_hora: 10
  aprovacao_por_uso: false
```

**Revogação** — síncrona e imediata. Notifica gêmeo VPS. Registrado em vault_revoked_log imutavelmente.

---

## CONSCIÊNCIA SITUACIONAL E SKILLS (~30% funcional)

A capacidade de escanear o próprio ambiente, mapear recursos, adquirir o que falta, e operar com percepção visual e julgamento — como um ser que chega num habitat e analisa antes de agir.

**Ciclo completo (a implementar):**
```
ESCANEAR 5 CAMADAS DO HABITAT
├── Hardware: CPU, RAM, GPU, disco, bateria, telas
├── SO: versão, permissões, firewall
├── Software: instalado, rodando, acessível via CLI
├── Conectividade: redes, contas ativas, vault
└── Contexto: janelas abertas, projetos ativos, estado do usuário
  ↓
MAPEAR capacidades atuais vs necessárias → GAPS
  ↓
PROTOCOLO DE AQUISIÇÃO
├── 1. Verificar se existe de outra forma
├── 2. Fonte: winget/apt/brew > oficial+hash > github oficial — NUNCA sem hash
├── 3. Instalar em sandbox isolado
├── 4. Notificar com janela de veto (5min)
├── 5. Configurar para este usuário
└── 6. Registrar skill no banco
  ↓
OPERAR COM PERCEPÇÃO VISUAL
├── Controle motor: PyAutoGUI + Playwright
├── Visão: screenshot → modelo de visão → análise
└── Loop: problema detectado → corrige → valida → escala se subjetivo
```

**Estado atual:**
```
capture.py               ✅  captura de contexto
executor_local.py        ✅  executor com visão básica
browser_adapter.py       ✅  automação de browser

desktop.py               ❌  PRÓXIMO PASSO CRÍTICO
habitat_scanner.py       ❌  scan das 5 camadas
skill_resolver.py        ❌  protocolo de aquisição
visual_judge.py          ❌  julgamento via modelo de visão
skills_catalog.py        ❌  catálogo vivo no banco
```

**Escopo de autonomia para ações:**
```
Reversível + baixo custo  → age, notifica depois
  ex: criar arquivo, escrever código, capturar screenshot

Reversível + custo médio  → age, notifica imediatamente
  ex: instalar em sandbox, abrir conexão

Irreversível ou alto custo → prepara, apresenta, aguarda aprovação
  ex: instalar em produção, deletar arquivo, publicar

Afeta outros humanos      → sempre aprovação explícita
  ex: enviar email, postar, representar o usuário
```

---

## ESTRUTURA DE ARQUIVOS — ESTADO REAL

```
agent/
├── shared/                           (~87% funcional)
│   ├── core/
│   │   ├── planner.py               ✅
│   │   ├── evaluator.py             ✅  3 camadas
│   │   ├── executor_base.py         ✅
│   │   ├── security_phase1.py       ✅
│   │   ├── config_loader.py         ✅
│   │   ├── tool_registry.py         ✅
│   │   ├── orchestrator.py          ⚠️  básico
│   │   └── antigravity_provider.py  ✅  provider LLM
│   ├── intent/
│   │   ├── intent_mapper.py         ✅
│   │   ├── decision_learner.py      ⚠️  refinar
│   │   ├── ambiguity_resolver.py    ⚠️  placeholder — IMPLEMENTAR
│   │   ├── coherence_tracker.py     ⚠️  0.5 fixo — IMPLEMENTAR
│   │   ├── monitor_orchestrator.py  ⚠️  não dinâmico
│   │   ├── rule_proposer.py         ✅
│   │   ├── transcendence_tracker.py ✅
│   │   └── delegation_contract.py   ✅
│   ├── evolution/
│   │   ├── observer.py              ✅
│   │   ├── developer.py             ⚠️
│   │   ├── tester.py                ✅
│   │   ├── property_tester.py       ✅  5 invariantes
│   │   ├── sandbox.py               ✅
│   │   ├── security_analyzer.py     ✅
│   │   ├── deployer.py              ⚠️  rollback parcial
│   │   └── meta_learner.py          ❌  Fase 4
│   ├── database/
│   │   ├── models.py                ✅
│   │   ├── causal_bank.py           ✅
│   │   ├── causal_validator.py      ⚠️  out_of_sample pendente
│   │   ├── pattern_pruner.py        ⚠️  não integrado
│   │   ├── sparse_merkle_tree.py    ✅
│   │   ├── crdt.py                  ✅
│   │   ├── synthesis_engine.py      ✅
│   │   └── migrations/              ⚠️  a implementar
│   └── communication/
│       ├── notifier.py              ✅
│       ├── reporter.py              ✅
│       └── formatter.py             ✅
│
├── vps/                              (~90% funcional)
│   ├── main.py                      ✅
│   ├── correlator.py                ✅
│   ├── executor_financial.py        ✅
│   ├── sync_server.py               ✅
│   ├── monitors/ (14 monitores)     ✅ (social_media ⚠️)
│   ├── adapters/
│   │   ├── telegram_adapter.py      ✅
│   │   └── discord_adapter.py       ✅
│   ├── dashboard/server.py          ⚠️  básico
│   └── services/
│       ├── proactive_insight.py     ✅
│       └── poly_strategist.py       ✅
│
├── local/                            (~85% funcional)
│   ├── main.py                      ✅
│   ├── executor_local.py            ✅
│   ├── capture.py                   ✅
│   ├── desktop.py                   ❌  CRÍTICO — IMPLEMENTAR
│   ├── privacy_filter.py            ✅
│   ├── privacy_auditor.py           ✅
│   ├── selective_forgetter.py       ✅
│   ├── notifier_local.py            ✅
│   ├── sync_client.py               ✅
│   ├── vault/master_vault.py        ✅
│   ├── adapters/
│   │   ├── browser_adapter.py       ✅
│   │   └── whatsapp_local_adapter.py ✅
│   └── tools/login_antigravity.py   ✅
│
├── sync/                             (~90% funcional)
│   ├── crdt.py                      ✅
│   ├── synthesis_engine.py          ✅
│   ├── meta_synthesis.py            ✅
│   └── offline_buffer.py            ✅
│
├── config/                           (100% funcional)
│   ├── config.yaml                  ✅
│   ├── security_phase1.yaml         ✅
│   └── observer_cases.yaml          ✅
│
├── docker/                           (100% funcional)
│   ├── Dockerfile.vps               ✅
│   ├── Dockerfile.local             ✅
│   ├── Dockerfile.dev               ✅
│   └── docker-compose.yml           ✅
│
├── tests/                            (93/93 passando ✅)
│   ├── unit/ (84 testes)            ✅
│   ├── integration/ (9 testes)      ✅
│   ├── backtest/                    ❌  baixa prioridade
│   └── synthesis/                   ❌  média prioridade
│
├── setup_rebeka.py                   ✅
├── wake_up_rebeka.py                 ✅
├── CLAUDE.md                         ✅
├── security_phase1.yaml              ✅
├── CONTRIBUTING.md                   ✅
└── README.md                         ✅
```

---

## PRÓXIMOS PASSOS — ORDEM DE EXECUÇÃO

### Semana 1-2 — Completar Fase 1
1. **`desktop.py`** — PyAutoGUI, controle motor completo *(alta prioridade)*
2. **`coherence_tracker` real** — cálculo via LLM *(baixo esforço, alto impacto)*
3. **`ambiguity_resolver._resolve_from_intents`** — lógica real *(baixo esforço)*
4. **`pattern_pruner` integrado** — decaimento automático *(baixo esforço)*

### Mês 1-2 — Avançar Fase 2
5. **`causal_validator.validate_out_of_sample`** — validação real
6. **`monitor_orchestrator` dinâmico** — por relevância pessoal
7. **`database/migrations/`** — versionamento de schema
8. **Motor de Intenção completo** — integrado ao loop principal

### Mês 2-4 — Skills e Visão
9. **`habitat_scanner.py`** — scan das 5 camadas
10. **`skill_resolver.py`** — protocolo de aquisição com fonte confiável
11. **`visual_judge.py`** — julgamento visual via modelo de visão
12. **`skills_catalog.py`** — catálogo vivo no banco

### Mês 4-6 — Síntese em Produção e Meta-aprendizado
13. Testes de síntese com divergência real entre gêmeos
14. **`meta_learner.py`** — meta-aprendizado (Fase 4)
15. Dashboard melhorado
16. Preparar expansão para domínios além do financeiro

---

## FILOSOFIA DE EVOLUÇÃO — AS SEIS FASES

### Fase 1 — Aprender a Ver (~85% completa)
Mapear a si mesmo antes de mapear o mundo. Confiança calibrada por histórico real.
**O que falta:** desktop.py, coherence_tracker real, ambiguity_resolver funcional.

### Fase 2 — Aprender a Entender (~40% completa)
Motor de Intenção funcionando de verdade. Age a partir de valores, não de instruções.
**Sinal de início:** primeira proposta de revisão de regra que emergiu de padrão identificado autonomamente — sem que ninguém pedisse.

### Fase 3 — Aprender a Sintetizar (~50% completa)
Gêmeos divergem e sintetizam perspectiva que nenhum tinha sozinho.
Engine existe e funciona — falta teste em produção com divergência real.

### Fase 4 — Aprender a Questionar (~20% completa)
Descobre padrões aprendidos que estavam errados. Meta-aprendizado.
Primeiras restrições propostas para remoção pelo transcendence_tracker.

### Fase 5 — Aprender o Escopo (não iniciada)
Onde o conhecimento termina e começa território exclusivamente humano.
Expansão para domínios além do financeiro — na ordem que o usuário decidir.

### Fase 6 — Transcendência Contínua (não iniciada)
Não é uma fase que se alcança uma vez. É o que acontece naturalmente quando o sistema aprende bem. Transcendência em cada categoria onde o histórico justifica, na velocidade que a evidência permite.

---

## VISÃO GLOBAL — O QUE A REBEKA SE TORNA

```
Fase 1-2: Campo de treinamento financeiro
          → Métricas claras calibram o Avaliador
          → Motor de Intenção constrói modelo robusto do usuário

Fase 3-4: Expansão para domínios adjacentes
          → Saúde, jurídico, criativo — na ordem que o usuário decide

Fase 5-6: Agente de coerência pessoal pleno
          → Conhece profundamente este usuário específico
          → Minimiza arrependimento, maximiza clareza
          → Reflete o que o usuário realmente quer
            — incluindo partes ainda não articuladas
```

O que nunca muda: o sistema usa conhecimento profundo para refletir, nunca para moldar. A função é clareza. A métrica é redução de arrependimento. O método é reflexão honesta — incluindo as contradições.

---

## PRINCÍPIO FUNDAMENTAL

O modelo raciocina. A infraestrutura sustenta. O tempo acumula. Os gêmeos sintetizam. O usuário ganha clareza. A autonomia cresce por evidência. A transcendência acontece naturalmente.

**O domínio financeiro é o campo de treinamento. O agente global é o destino.**
