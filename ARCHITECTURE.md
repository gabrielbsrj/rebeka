# Arquitetura do Sistema

## Visão Geral

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│         GÊMEO VPS            │     │        GÊMEO LOCAL           │
│                              │     │                              │
│  Monitores Globais (24/7)    │     │  Captura de Contexto Íntimo  │
│  Geopolítica, Macro          │◄───►│  Arquivos, Apps, Desktop     │
│  Commodities, Terras Raras   │     │  WhatsApp, Telegram          │
│  Energia, Inovação           │     │  Contexto Pessoal            │
│  Redes Sociais, Earnings     │     │                              │
│                              │     │                              │
│  Planejador Global           │◄───►│  Planejador Local            │
│  Correlator de Sinais        │     │  Executor de Ambiente        │
│  Executor Financeiro         │     │  Notificações Nativas        │
│  Avaliador                   │     │  Privacy Filter              │
│                              │     │                              │
│  Banco de Causalidade        │◄───►│  Banco de Causalidade Local  │
│  (PostgreSQL, append-only)   │     │  (SQLite, offline-safe)      │
│                              │     │                              │
│  Consciência Evolutiva       │◄───►│  Consciência Evolutiva       │
└──────────────────────────────┘     └──────────────────────────────┘
               │                                    │
               └──────── SYNTHESIS ENGINE ──────────┘
                     Emergência de terceira perspectiva
```

---

## Stack Tecnológica

### Compartilhado (DNA)

| Tecnologia | Uso |
|------------|-----|
| Python 3.12+ | Linguagem principal |
| LiteLLM | Interface para qualquer API de IA |
| PostgreSQL / SQLite | Banco de Causalidade |
| Git | Versionamento automático |
| Docker | Separação de ambientes |

### Gêmeo VPS

| Tecnologia | Uso |
|------------|-----|
| FastAPI | API de sincronização |
| Redis + Celery | Monitores paralelos |
| WebSocket | Canal de sincronização |

### Gêmeo Local

| Tecnologia | Uso |
|------------|-----|
| Playwright | Automação de navegador |
| PyAutoGUI | Automação de desktop |
| WebSocket Client | Conexão com VPS |

---

## Estrutura de Diretórios

```
agent/
├── shared/           # DNA idêntico dos dois gêmeos
│   ├── core/         # Planner, Evaluator, Executor, Security
│   ├── intent/       # Motor de Intenção
│   ├── evolution/    # Consciência Evolutiva
│   ├── database/     # Banco de Causalidade + SMT
│   └── communication/# Notificação e Reports
│
├── vps/              # Gêmeo VPS (global)
│   ├── monitors/     # 14 monitores globais
│   ├── adapters/     # Telegram, Discord
│   └── services/     # Correlator, Insights
│
├── local/            # Gêmeo Local (íntimo)
│   ├── executor_local.py
│   ├── vault/        # Cofre de credenciais
│   └── adapters/     # WhatsApp, Browser
│
├── sync/             # Sincronização entre gêmeos
│   ├── crdt.py
│   ├── synthesis_engine.py
│   └── meta_synthesis.py
│
├── config/           # Configurações
├── docker/           # Dockerfiles
└── tests/            # Testes
```

---

## Fluxo de Dados

```
1. MONITOR → coleta sinal
      ↓
2. BANCO → armazena com hash SMT
      ↓
3. PLANNER → gera hipótese com contexto
      ↓
4. EVALUATOR → valida em 3 camadas
      ↓
5. EXECUTOR → executa ação
      ↓
6. BANCO → registra resultado
      ↓
7. SÍNTESE → integra perspectivas (se divergência)
```

---

## Banco de Causalidade

### Sparse Merkle Tree

Integridade verificável com esquecimento seletivo:

```
Merkle Root (prova o banco inteiro)
├── Branch A
│   ├── Leaf: signal_001 (hash íntegro)
│   └── Leaf: [ANONIMIZADO] (folha removida)
├── Branch B
│   ├── Leaf: hypothesis_001
│   └── Leaf: execution_001
└── Branch C
    └── ...
```

### Tabelas Principais

| Tabela | Descrição |
|--------|-----------|
| `signals` | Sinais coletados pelos monitores |
| `causal_patterns` | Padrões validados causalmente |
| `hypotheses` | Hipóteses do Planejador |
| `executions` | Execuções paper e real |
| `evaluations` | Avaliações do Avaliador |
| `user_decisions` | Decisões do usuário |
| `merkle_tree` | Raízes e provas de integridade |

---

## Invariantes

Verdades fundamentais que nunca podem ser violadas:

### 1. Calibração de Confiança
```python
reported_confidence <= historical_success_rate + 0.10
```

### 2. Append-Only do Banco
```python
# UPDATE e DELETE não existem
operation in ["UPDATE", "DELETE"] → REJECT
```

### 3. Limite de Capital
```python
if operation_type == "REAL":
    amount <= configured_limit
```

### 4. Rastreabilidade de Confiança
```python
len(historical_samples) >= 30
```

### 5. Integridade do Avaliador
```python
hash(evaluator_layer1_code) == evaluator_layer1_hash
```

---

## Avaliador - 3 Camadas

| Camada | Função | Evolução |
|--------|--------|----------|
| 1 - Consistência Lógica | Hipótese contradiz dados? | **Imutável** |
| 2 - Alinhamento com Valores | Ação alinhada com usuário? | Evolui lentamente |
| 3 - Comportamento Instrumental | Otimizando métrica errada? | Fica mais precisa |

---

## Síntese (não votação)

Quando os gêmeos divergem:

1. **Não votam** - Não existe "maioria"
2. **Sintetizam** - Criam terceira perspectiva
3. **Escalar** - Só se síntese impossível

```python
result = synthesis_engine.synthesize(
    vps_view=perspective_global,
    local_view=perspective_local
)
# Emergent perspective > max(vps, local)
```
