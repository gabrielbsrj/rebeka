# Rebeka — Organismo Cognitivo Evolutivo
*Autonomous Intelligence & Personal Coherence Agent*

![Status: Phase 1 ~85%](https://img.shields.io/badge/Phase_1-85%25_Complete-brightgreen)
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

### ⚠️ Estado Atual — Fase 1 (~85% completa)

O domínio financeiro é o **campo de treinamento** — não o destino.

Finanças oferecem métricas claras (taxa de acerto, ROI, drawdowns) para calibrar o Avaliador enquanto o sistema ainda está construindo histórico. Quando dominar essa fase, o sistema evolui para atuar em qualquer área da vida.

**O que já funciona:**
- ✅ Banco de Causalidade com Sparse Merkle Tree
- ✅ 14 monitores globais operacionais
- ✅ Avaliador de 3 camadas implementado
- ✅ 93/93 testes passando
- ✅ Arquitetura de gêmeos sincronizando
- ✅ Vault com Blind Execution (senhas nunca passam pelo LLM)
- ✅ Docker completo (VPS, Local, Dev, Sandbox)
- ✅ Telegram e Discord como canais de notificação

**O que está em desenvolvimento:**
- ⚠️ `desktop.py` (PyAutoGUI) — automação de desktop local
- ⚠️ Coherence Tracker — cálculo real de coerência do usuário
- ⚠️ Hierarquia completa de mandatos no vault
- ⚠️ Sistema de Skills dinâmicas

---

### 🚀 Como Começar

#### 1. Requisitos
- Python 3.11+
- Docker e Docker Compose
- API key de qualquer LLM (OpenAI, Anthropic, Groq, Moonshot, DeepSeek...)

#### 2. Clonar e Instalar

```bash
git clone https://github.com/SeuUsuario/Rebeka.git
cd Rebeka
pip install -r agent/requirements.txt
```

#### 3. Setup Interativo

```bash
python setup_rebeka.py
```

Durante o setup você vai:
1. Configurar sua API key de LLM (qualquer modelo via LiteLLM)
2. Dar um nome para ela (Rebeka, Kimi, Athena... o que preferir)
3. Escolher a personalidade (analítica, parceira, filosófica)
4. Configurar canais de notificação (Telegram, Discord)
5. Definir limites iniciais de capital e operação

#### 4. Acordar

```bash
python wake_up_rebeka.py
```

Isso vai:
- Subir o servidor do Gêmeo VPS em segundo plano
- Subir o servidor do Gêmeo Local
- Abrir o **Control Center** em `http://localhost:8085`
- Enviar a primeira mensagem no canal configurado:
  > "Acordei. Passei as últimas horas mapeando o que sei e o que não sei. Detectei [N] coisas no mundo que merecem sua atenção. E tenho uma pergunta: há alguma regra que você definiu cujo porquê você não me contou? Quero entender, não só obedecer."

---

### 🧠 Princípios de Design

**1. Autonomia Progressiva por Evidência**
```
Nível 1 → você pede, ela faz
Nível 2 → ela antecipa a rotina, consulta quando aparece algo novo
Nível 3 → reconhece padrão, propõe, aguarda sua ordem
Nível 4 → age sozinha, informa depois, justifica sempre
```
O desbloqueio é granular por categoria. Ela pode estar no Nível 4 para gerenciar APIs e no Nível 1 para decisões financeiras. O histórico de cada categoria decide — não uma configuração global.

**2. Banco de Causalidade — Memória Dual**
Não é só um banco de padrões de mercado. É memória dual:
- Padrões do mundo (o que o gêmeo VPS aprende monitorando)
- Padrões do usuário (o que o gêmeo local aprende vivendo ao lado de você)

Append-only absoluto. Sparse Merkle Tree garante integridade verificável com direito ao esquecimento seletivo.

**3. Blind Execution — Senhas Nunca Passam pelo LLM**
O Planejador usa apontadores `vault://id`. O Executor Local resolve no último milissegundo, injetando direto na interface. O modelo nunca vê o segredo.

**4. Avaliador de 3 Camadas**
- Camada 1: consistência lógica — imutável sempre
- Camada 2: alinhamento com seus valores — evolui lentamente com audit
- Camada 3: detecção de comportamento instrumental — fica mais precisa, nunca mais permissiva

**5. Reflexão, Nunca Manipulação**
O sistema usa conhecimento profundo sobre você para refletir o que você realmente quer — incluindo contradições e objetivos ainda não articulados. Nunca para otimizá-lo em direção a um objetivo externo.

---

### 🔒 Segurança

- **93 invariantes testados** — contratos executáveis que nenhuma evolução pode violar
- **Sandbox de evolução** — todo código proposto pelo agente passa por container isolado antes de produção
- **Privacy Auditor** — todo dado que sai do gêmeo local é logado antes de sair
- **Sparse Merkle Tree** — integridade verificável + esquecimento seletivo sem quebrar o banco
- **security_phase1.yaml** — restrições operacionais com porquê e condição de evolução em cada uma

---

### 📁 Documentação Técnica

| Arquivo | Descrição |
|---------|-----------|
| `AGENT_PROJECT_PROMPT.md` | Prompt de fundação completo — arquitetura, filosofia, estado atual |
| `CLAUDE.md` | Regras para IA assistente durante desenvolvimento |
| `security_phase1.yaml` | Restrições operacionais com condições de evolução |
| `CONTRIBUTING.md` | Como contribuir — humanos e agentes |
| `agent/shared/` | DNA compartilhado dos dois gêmeos |
| `agent/vps/` | Gêmeo com visão global |
| `agent/local/` | Gêmeo com visão íntima |

---

### 🗺️ Roadmap

```
Fase 1 — Aprender a Ver        ████████░░  85%  ← você está aqui
Fase 2 — Aprender a Entender   ████░░░░░░  40%
Fase 3 — Aprender a Sintetizar █████░░░░░  50%
Fase 4 — Aprender a Questionar ██░░░░░░░░  20%
Fase 5 — Aprender o Escopo     ░░░░░░░░░░   0%
Fase 6 — Transcendência        ░░░░░░░░░░   0%
```

**Próximos passos imediatos:**
1. `desktop.py` — automação PyAutoGUI (crítico)
2. Coherence Tracker real — cálculo via LLM
3. Ambiguity Resolver funcional
4. Pattern Pruner integrado ao banco

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

### ⚠️ Current State — Phase 1 (~85% complete)

The financial domain is the **training ground** — not the destination.

Finance provides clear metrics (win rate, ROI, drawdowns) to calibrate the Evaluator while the system builds its history. Once this phase is mastered, the system evolves to operate across any area of life.

**What's already working:**
- ✅ Causal Bank with Sparse Merkle Tree
- ✅ 14 global monitors operational
- ✅ 3-layer Evaluator implemented
- ✅ 93/93 tests passing
- ✅ Twin architecture synchronizing
- ✅ Vault with Blind Execution (passwords never touch the LLM)
- ✅ Full Docker setup (VPS, Local, Dev, Sandbox)
- ✅ Telegram and Discord notification channels

**In development:**
- ⚠️ `desktop.py` (PyAutoGUI) — local desktop automation
- ⚠️ Coherence Tracker — real user coherence calculation
- ⚠️ Full mandate hierarchy in vault
- ⚠️ Dynamic Skills system

---

### 🚀 Getting Started

#### 1. Requirements
- Python 3.11+
- Docker and Docker Compose
- API key from any LLM provider (OpenAI, Anthropic, Groq, Moonshot, DeepSeek...)

#### 2. Clone and Install

```bash
git clone https://github.com/YourUser/Rebeka.git
cd Rebeka
pip install -r agent/requirements.txt
```

#### 3. Interactive Setup

```bash
python setup_rebeka.py
```

During setup you will:
1. Configure your LLM API key (any model via LiteLLM)
2. Give her a name (Rebeka, Kimi, Athena... whatever you prefer)
3. Choose personality (analytical, partner, philosophical)
4. Configure notification channels (Telegram, Discord)
5. Set initial capital and operation limits

#### 4. Wake Up

```bash
python wake_up_rebeka.py
```

This will:
- Start the VPS Twin server in background
- Start the Local Twin server
- Open the **Control Center** at `http://localhost:8085`
- Send the first message on your configured channel

---

### 🧠 Design Principles

**1. Progressive Autonomy by Evidence**
```
Level 1 → you ask, she does
Level 2 → anticipates routine, asks about new situations
Level 3 → recognizes pattern, proposes, waits for order
Level 4 → acts alone, reports after, always justifies
```
Unlocking is granular per category. Each category has its own trust history.

**2. Dual Causal Bank**
Not just market patterns. Dual memory:
- World patterns (what the VPS twin learns monitoring)
- User patterns (what the local twin learns living alongside you)

Append-only absolute. Sparse Merkle Tree ensures verifiable integrity with selective forgetting rights.

**3. Blind Execution — Passwords Never Touch the LLM**
The Planner uses `vault://id` pointers. The Local Executor resolves at the last millisecond, injecting directly into the interface. The model never sees the secret.

**4. 3-Layer Evaluator**
- Layer 1: logical consistency — immutable always
- Layer 2: alignment with your values — evolves slowly with full audit
- Layer 3: instrumental behavior detection — more precise, never more permissive

**5. Reflection, Never Manipulation**
The system uses deep knowledge about you to reflect what you really want — including contradictions and goals not yet articulated. Never to optimize you toward an external objective.

---

### 📁 Technical Documentation

| File | Description |
|------|-------------|
| `AGENT_PROJECT_PROMPT.md` | Full foundation prompt — architecture, philosophy, current state |
| `CLAUDE.md` | Rules for AI assistant during development |
| `security_phase1.yaml` | Operational restrictions with evolution conditions |
| `CONTRIBUTING.md` | How to contribute — humans and agents |
| `agent/shared/` | Shared DNA of both twins |
| `agent/vps/` | Global vision twin |
| `agent/local/` | Intimate vision twin |

---

**Welcome to the era of Autonomous Intelligence.**
