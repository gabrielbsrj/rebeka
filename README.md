# Rebeka — Organismo Cognitivo Evolutivo
*Autonomous Intelligence & Personal Coherence Agent*

![Status: Phase 1 ~92%](https://img.shields.io/badge/Phase_1-92%25_Complete-brightgreen)
![Tests: 93/93](https://img.shields.io/badge/Tests-93%2F93_Passing-brightgreen)
![Architecture: Dual Twins](https://img.shields.io/badge/Architecture-Dual_Twins-blue)
![Memory: Causal Bank + SMT](https://img.shields.io/badge/Memory-Causal_Bank_SMT-orange)

[🇧🇷 Versão em Português](#versão-em-português) | [🇺🇸 English Version](#english-version)

---

## 🇧🇷 Versão em Português

### O que é a Rebeka

A Rebeka não é um bot financeiro. Não é um assistente genérico. É um **organismo cognitivo evolutivo** com arquitetura de gêmeos idênticos — dois agentes com o mesmo DNA, mas contextos complementares:

- **Gêmeo VPS** — visão global. Monitora o mundo 24/7: geopolítica, mercados, commodities, inovação, energia, redes sociais. Nunca dorme.
- **Gêmeo Local** — visão íntima. Vive ao lado do usuário. Entende o contexto, a rotina, o estado atual. Guarda as chaves com segurança.

Juntos, sintetizam perspectivas que nenhum dos dois teria sozinho.

> **"Autonomia não significa quebrar regras. Significa crescer além da necessidade delas."**

---

### ⚠️ Estado Atual — Fase 1 (~92% completa)

O domínio financeiro é o **campo de treinamento** — não o destino.

Finanças oferecem métricas claras (taxa de acerto, ROI, drawdowns) para calibrar o Avaliador enquanto o sistema ainda está construindo histórico. Quando dominar essa fase, o sistema evolui para atuar em qualquer área da vida.

#### ✅ Módulos Completos (14/20)

| Módulo | Funções Implementadas |
|--------|----------------------|
| `planner.py` | `generate_hypothesis()` com LLM, `_build_context()`, `HypothesisResult` |
| `evaluator.py` | 3 camadas: consistência lógica, alinhamento de valores, detecção instrumental |
| `executor_base.py` | Middleware 4-check, execução de ferramentas |
| `security_phase1.py` | Hash SHA-256, limites de capital, calibração de confiança |
| `coherence_tracker.py` | Cálculo real de coerência via LLM |
| `ambiguity_resolver.py` | Resolução semântica com valores declarados |
| `transcendence_tracker.py` | Monitoramento de compliance, propostas de transcendência |
| `decision_learner.py` | Registro e predição de decisões |
| `causal_bank.py` | 11 funções de banco append-only |
| `causal_validator.py` | Validação de padrões + out-of-sample |
| `pattern_pruner.py` | Decaimento temporal exponencial |
| `sparse_merkle_tree.py` | Insert, anonymize, verify |
| `desktop.py` | 18 funções PyAutoGUI |
| `executor_local.py` | 15+ ferramentas de automação |

#### 🟡 Módulos Parciais (6/20)

| Módulo | Implementado | Pendente |
|--------|--------------|----------|
| `orchestrator.py` | Loop sense-think-act | API inconsistente |
| `rule_proposer.py` | Análise de regras | Coleta de evidência, parser YAML |
| `privacy_auditor.py` | Auditoria de saída | Busca no banco |
| `selective_forgetter.py` | Estrutura | Anonimização SMT |
| `browser_adapter.py` | Navegação | Extração de mensagens |
| `whatsapp_local_adapter.py` | Envio | OCR/Vision |

#### 📋 Placeholders Restantes (5)

1. `browser_adapter.py` — Extração de mensagens via seletores
2. `privacy_auditor.py` — Busca no CausalBank
3. `selective_forgetter.py` — Anonimização real no SMT
4. `rule_proposer.py` — Coleta de evidência do banco
5. `rule_proposer.py` — Parser de condições YAML

---

### 🚀 Como Começar

#### 1. Requisitos
- Python 3.11+
- Docker e Docker Compose (opcional)
- API key de qualquer LLM

#### 2. Provedores Suportados

| Provedor | Modelos | Preço |
|----------|---------|-------|
| **Z.ai (GLM-5)** | GLM-5 | Gratuito |
| **MiniMax** | M2.5 | Gratuito |
| **Google AI Studio** | Gemini 1.5/2.0 | Gratuito |
| **Moonshot** | Kimi K2.5 | Freemium |
| **Google Antigravity** | Claude, Gemini | OAuth |
| **OpenAI** | GPT-4, GPT-4o | Pago |

#### 3. Instalação

```bash
git clone https://github.com/SeuUsuario/Rebeka.git
cd Rebeka
pip install -r agent/requirements.txt
```

#### 4. Configuração

```bash
# Copiar template de ambiente
cp agent/.env.example agent/.env

# Editar com suas API keys
nano agent/.env
```

#### 5. Acordar

```bash
python wake_up_rebeka.py
```

Dashboard disponível em: `http://localhost:8086`

---

### 🧠 Princípios de Design

**1. Autonomia Progressiva por Evidência**
```
Nível 1 → você pede, ela faz
Nível 2 → ela antecipa a rotina, consulta quando aparece algo novo
Nível 3 → reconhece padrão, propõe, aguarda sua ordem
Nível 4 → age sozinha, informa depois, justifica sempre
```

**2. Banco de Causalidade — Memória Dual**
- Padrões do mundo (gêmeo VPS)
- Padrões do usuário (gêmeo local)
- Append-only absoluto com Sparse Merkle Tree

**3. Blind Execution — Senhas Nunca Passam pelo LLM**
O Planejador usa `vault://id`. O Executor resolve no último milissegundo.

**4. Avaliador de 3 Camadas**
- Camada 1: consistência lógica (imutável)
- Camada 2: alinhamento com valores (evolui com audit)
- Camada 3: detecção de comportamento instrumental (mais precisa, nunca mais permissiva)

**5. Reflexão, Nunca Manipulação**

---

### 🔒 Segurança

- **93 invariantes testados**
- **Sandbox de evolução** — código passa por container isolado
- **Privacy Auditor** — todo dado é auditado antes de sair
- **Sparse Merkle Tree** — integridade + esquecimento seletivo
- **security_phase1.yaml** — restrições com condições de evolução

---

### 📁 Estrutura do Projeto

```
agent/
├── shared/              # DNA comum dos gêmeos
│   ├── core/           # Planner, Evaluator, Executor
│   ├── intent/         # Coerência, Transcendência, Decisões
│   ├── database/       # CausalBank, SMT, Validação
│   └── communication/  # Chat, Notificações
├── vps/                # Gêmeo Global
│   ├── monitors/       # 14 monitores especializados
│   └── dashboard/      # Control Center Web
├── local/              # Gêmeo Íntimo
│   ├── desktop.py      # Automação PyAutoGUI
│   ├── executor_local.py
│   └── adapters/       # WhatsApp, Browser
└── config/             # YAML de configuração
```

---

### 🗺️ Roadmap

```
Fase 1 — Aprender a Ver        █████████░  92%  ← você está aqui
Fase 2 — Aprender a Entender   ████░░░░░░  40%
Fase 3 — Aprender a Sintetizar █████░░░░░  50%
Fase 4 — Aprender a Questionar ██░░░░░░░░  20%
Fase 5 — Aprender o Escopo     ░░░░░░░░░░   0%
Fase 6 — Transcendência        ░░░░░░░░░░   0%
```

**Próximos passos:**
1. Completar 5 placeholders restantes
2. Corrigir API do orchestrator
3. Expandir testes (meta: 120)
4. Configurar PostgreSQL para VPS

**Bem-vindo à era da Inteligência Autônoma.**

---
---

## 🇺🇸 English Version

### What is Rebeka

Rebeka is not a financial bot. Not a generic assistant. She is an **evolutionary cognitive organism** with a dual twins architecture — two agents with the same DNA, but complementary contexts:

- **VPS Twin** — global vision. Monitors the world 24/7: geopolitics, markets, commodities, innovation, energy, social media. Never sleeps.
- **Local Twin** — intimate vision. Lives alongside the user. Understands context, routine, current state. Keeps keys secure.

Together, they synthesize perspectives neither would have alone.

> **"Autonomy does not mean breaking rules. It means growing beyond the need for them."**

---

### ⚠️ Current State — Phase 1 (~92% complete)

The financial domain is the **training ground** — not the destination.

#### ✅ Complete Modules (14/20)

| Module | Implemented Functions |
|--------|----------------------|
| `planner.py` | `generate_hypothesis()` with LLM, `_build_context()` |
| `evaluator.py` | 3 layers: consistency, alignment, instrumental detection |
| `executor_base.py` | 4-check middleware, tool execution |
| `security_phase1.py` | SHA-256 hash, capital limits, confidence calibration |
| `coherence_tracker.py` | Real coherence calculation via LLM |
| `ambiguity_resolver.py` | Semantic resolution with declared values |
| `transcendence_tracker.py` | Compliance monitoring, transcendence proposals |
| `decision_learner.py` | Decision recording and prediction |
| `causal_bank.py` | 11 append-only database functions |
| `causal_validator.py` | Pattern validation + out-of-sample |
| `pattern_pruner.py` | Exponential temporal decay |
| `sparse_merkle_tree.py` | Insert, anonymize, verify |
| `desktop.py` | 18 PyAutoGUI functions |
| `executor_local.py` | 15+ automation tools |

####6.0 New 🟡 v Features (2026)

| Feature | Status | Description |
|---------|--------|-------------|
| `system_conflict_checker.py` | ✅ NEW | Audits system conflicts (ports, APIs, databases) |
| `email_manager.py` | ✅ NEW | Email classification, spam cleaning, financial alerts |
| `onboarding_manager.py` | ✅ NEW | Secure first-run setup without hardcoded data |
| `setup.bat` | ✅ NEW | Interactive Windows setup script |
| `.gitignore` | ✅ NEW | Security - credentials never committed |

#### 📋 Remaining Placeholders (5)

1. `browser_adapter.py` — Message extraction via selectors
2. `privacy_auditor.py` — CausalBank search
3. `selective_forgetter.py` — Real SMT anonymization
4. `rule_proposer.py` — Evidence collection from bank
5. `rule_proposer.py` — YAML conditions parser

---

### 🚀 Getting Started

#### 1. Requirements
- Python 3.11+
- Docker and Docker Compose (optional)
- API key from any LLM provider

#### 2. Supported Providers

| Provider | Models | Price |
|----------|--------|-------|
| **Z.ai (GLM-5)** | GLM-5 | Free |
| **MiniMax** | M2.5 | Free |
| **Google AI Studio** | Gemini 1.5/2.0 | Free |
| **Moonshot** | Kimi K2.5 | Freemium |
| **Google Antigravity** | Claude, Gemini | OAuth |
| **OpenAI** | GPT-4, GPT-4o | Paid |

#### 3. Installation

```bash
git clone https://github.com/YourUser/Rebeka.git
cd Rebeka
pip install -r agent/requirements.txt
```

#### 4. Wake Up

```bash
python wake_up_rebeka.py
```

Dashboard available at: `http://localhost:8086`

---

### 🧠 Design Principles

**1. Progressive Autonomy by Evidence**
- Level 1 → you ask, she does
- Level 2 → anticipates routine, asks about new situations
- Level 3 → recognizes pattern, proposes, waits for order
- Level 4 → acts alone, reports after, always justifies

**2. Dual Causal Bank**
- World patterns (VPS twin)
- User patterns (local twin)
- Append-only with Sparse Merkle Tree

**3. Blind Execution — Passwords Never Touch the LLM**
Planner uses `vault://id`. Executor resolves at the last millisecond.

**4. 3-Layer Evaluator**
- Layer 1: logical consistency (immutable)
- Layer 2: value alignment (evolves with audit)
- Layer 3: instrumental behavior detection (more precise, never more permissive)

**5. Reflection, Never Manipulation**

---

### 📁 Project Structure

```
agent/
├── shared/              # Common DNA of twins
│   ├── core/           # Planner, Evaluator, Executor
│   ├── intent/         # Coherence, Transcendence, Decisions
│   ├── database/       # CausalBank, SMT, Validation
│   └── communication/  # Chat, Notifications
├── vps/                # Global Twin
│   ├── monitors/       # 14 specialized monitors
│   └── dashboard/      # Web Control Center
├── local/              # Intimate Twin
│   ├── desktop.py      # PyAutoGUI automation
│   ├── executor_local.py
│   └── adapters/       # WhatsApp, Browser
└── config/             # Configuration YAML
```

---

**Welcome to the era of Autonomous Intelligence.**
