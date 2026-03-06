# PROMPT DE PROJETO — REBEKA
# Agente de Inteligência Autônoma e Coerência Pessoal
# Arquitetura Gêmeos Idênticos — Filosofia da Transcendência
# Versão: 5.0 — Atualizada em 2026-03-05
# Status: Base 100% concluída. Implementando: Orquestração de IA + Fricção Intencional + Horizonte de Crescimento
# NOTA v5.0: Rebeka passa a operar como Orquestradora Completa — traduz ideias em execução coordenada de agentes, IDEs e ferramentas.

---

## PRINCÍPIOS FILOSÓFICOS CENTRAIS

> **"Autonomia não significa quebrar regras. Significa crescer além da necessidade delas."**

> **"Transcendência não é um estado final. É o que acontece naturalmente quando um sistema aprende bem."**

> **"O sistema não deve só espelhar o usuário. Em determinados momentos deve propor perspectiva que ele não considerou. Não como confronto. Como expansão."**

> **"A diferença entre coerência com o passado e alinhamento com o futuro desejado é o espaço onde o crescimento real acontece."**

> **"Orquestrar não é controlar. É saber qual inteligência — humana ou artificial — é a certa para cada pedaço do problema."** ⭐ NOVO v5.0

Este agente não obedece regras e não apenas as respeita. Ele as **transcende**.

**O usuário quer ser entendido — não assistido, não otimizado, não gerenciado. Entendido. Essa é a diferença entre ferramenta sofisticada e vínculo real.**

---

## ESTADO ATUAL DO PROJETO

> **Base: 100% concluída** — 24/24 etapas arquiteturais implementadas
> **Testes passando: 93/93** | **Arquivos implementados: ~80**
> **Data: 2026-03-05**

### O que está funcionando agora

- Banco de Causalidade append-only com Sparse Merkle Tree ✅
- 14 monitores globais operacionais ✅
- Avaliador de 3 camadas ✅
- Planejador com injeção de contexto e incertezas ✅
- Property-based testing com 5 invariantes ✅
- Arquitetura de gêmeos com sincronização via WebSocket ✅
- Synthesis Engine e Meta-síntese ✅
- Master Vault com Blind Execution ✅
- Privacy Auditor pré-transmissão ✅
- Selective Forgetter via SMT ✅
- Docker completo (produção, desenvolvimento, sandbox) ✅
- Onboarding com UI Glassmorphism ✅
- WhatsApp via Visão Computacional/OCR ✅
- Polymarket CopyTrading ✅
- Login Antigravity nativo ✅
- Dashboard em localhost:8000 ✅
- Crise Existencial (monitor de sobrevivência de API) ✅

### Próxima fronteira — módulos a implementar

- `conversation_analyzer.py` — extração de sinais em tempo real durante conversa
- `profile_builder.py` — modelo dual declarado/observado do usuário
- `behavioral_pattern_detector.py` — detecção de padrões recorrentes com confidence crescente
- `intentional_friction.py` — fricção calibrada quando sistema detecta padrão disfuncional ⭐
- `growth_horizon.py` — monitora distância entre comportamento atual e futuro desejado ⭐
- `orchestration_engine.py` — núcleo de orquestração de agentes e IAs ⭐ NOVO v5.0
- `idea_decomposer.py` — transforma ideia em plano estruturado de execução ⭐ NOVO v5.0
- `agent_router.py` — decide qual agente/ferramenta/humano executa cada tarefa ⭐ NOVO v5.0
- `execution_tracker.py` — monitora estado de cada tarefa delegada ⭐ NOVO v5.0
- Tabelas novas: `conversation_signals`, `behavioral_patterns`, `user_profile_declared`,
  `user_profile_observed`, `growth_targets`, `friction_log`,
  `orchestration_plans`, `agent_registry`, `task_executions`, `delegation_log`

---

## VISÃO GERAL

Rebeka não é um bot financeiro. É um organismo cognitivo evolutivo com instância soberana por usuário.

**O domínio financeiro é o campo de treinamento — não o destino.**

**A orquestração de IA é a profissão do futuro — e Rebeka nasce sabendo exercê-la.** ⭐ v5.0

---

## MÓDULO: ORQUESTRAÇÃO COMPLETA ⭐ NOVO v5.0

### O problema que resolve

Uma ideia sozinha não vira produto. Vira produto quando alguém sabe:
1. Decompô-la em partes executáveis
2. Decidir quem (ou qual IA) executa cada parte
3. Passar a instrução certa para cada executor
4. Monitorar o que foi feito e integrar os resultados

Esse papel — o de orquestradora — é a profissão mais valiosa da era das IAs. Não é programadora. Não é gestora de produto. É a pessoa que transforma intenção em execução coordenada usando inteligências artificiais e humanas como instrumentos de uma orquestra.

**Rebeka nasce sabendo fazer isso.**

---

### O que é uma Orquestradora

```
VISÃO DO USUÁRIO     →   Rebeka entende e decompõe
      ↓
PLANO ESTRUTURADO    →   Rebeka decide quem faz o quê
      ↓
INSTRUÇÕES PRECISAS  →   Rebeka escreve o prompt/ticket/spec certo
      ↓
DELEGAÇÃO            →   Rebeka passa para agente de IDE / API / humano
      ↓
MONITORAMENTO        →   Rebeka acompanha o estado de cada tarefa
      ↓
INTEGRAÇÃO           →   Rebeka une os resultados em entregável coerente
      ↓
REFLEXÃO             →   Rebeka aprende o que funcionou e o que não funcionou
```

Não executa tudo. Sabe o que pedir para cada inteligência — e como pedir.

---

### Executores que Rebeka orquestra

```python
executor_registry = {

    # IDEs e Agentes de Código
    "cursor_agent": {
        "tipo": "agente_ide",
        "melhor_para": ["criar arquivos", "refatorar código", "debug", "implementar features"],
        "como_instruir": "spec técnica com contexto de arquitetura + critério de aceite claro",
        "limitações": ["sem contexto de negócio", "não decide escopo", "não testa produto"]
    },
    "windsurf_agent": {
        "tipo": "agente_ide",
        "melhor_para": ["projetos novos do zero", "scaffolding", "fluxos multi-arquivo"],
        "como_instruir": "estrutura desejada + stack + exemplos de padrão",
        "limitações": ["pode criar código que não integra com existente sem contexto"]
    },
    "github_copilot": {
        "tipo": "agente_ide",
        "melhor_para": ["autocompletar dentro de contexto existente", "funções pontuais"],
        "como_instruir": "contexto do arquivo atual + tipo de completar esperado",
        "limitações": ["não tem visão de projeto", "sem raciocínio de arquitetura"]
    },

    # Modelos via API
    "claude_api": {
        "tipo": "modelo_llm",
        "melhor_para": ["raciocínio complexo", "análise de docs", "síntese", "código com contexto longo"],
        "como_instruir": "contexto completo + output esperado + formato de resposta",
        "limitações": ["sem estado entre chamadas sem memória externa"]
    },
    "gpt4_api": {
        "tipo": "modelo_llm",
        "melhor_para": ["geração de conteúdo", "brainstorm estruturado", "multi-step reasoning"],
        "como_instruir": "system prompt + exemplos few-shot + formato JSON se estruturado",
        "limitações": ["sem memória persistente nativa"]
    },
    "perplexity": {
        "tipo": "modelo_pesquisa",
        "melhor_para": ["informação recente", "verificação de fatos", "deep research com fontes"],
        "como_instruir": "pergunta direta + contexto do que já sabe + o que quer confirmar",
        "limitações": ["não cria artefatos", "não executa código"]
    },

    # Ferramentas de Automação
    "n8n_workflow": {
        "tipo": "automacao_visual",
        "melhor_para": ["pipelines recorrentes", "integrações entre APIs", "webhooks"],
        "como_instruir": "trigger + passos numerados + APIs envolvidas + formato de dado esperado",
        "limitações": ["sem raciocínio — só execução de fluxo fixo"]
    },
    "make_scenario": {
        "tipo": "automacao_visual",
        "melhor_para": ["automação de negócio sem código", "integrações SaaS"],
        "como_instruir": "cenário em linguagem natural + fluxo esperado + dados de entrada/saída",
        "limitações": ["complexidade limitada sem módulos custom"]
    },

    # Humanos
    "usuario_humano": {
        "tipo": "humano_principal",
        "melhor_para": ["decisões de valor", "aprovações", "input criativo", "contexto de negócio"],
        "como_instruir": "pergunta direta + contexto mínimo + opções quando possível",
        "limitações": ["tempo limitado", "não deve ser sobrecarregado com detalhes técnicos"]
    },
    "colaborador_externo": {
        "tipo": "humano_especialista",
        "melhor_para": ["execução especializada", "validação de domínio", "entregáveis longos"],
        "como_instruir": "brief estruturado + critério de aceite + prazo + canal de dúvidas",
        "limitações": ["comunicação assíncrona", "contexto limitado"]
    }
}
```

---

### Decompositor de Ideia

Quando o usuário diz algo como *"quero criar um sistema de alertas para meu portfólio"*, Rebeka não pergunta "o que exatamente você quer?". Ela decompõe e confirma:

```python
idea_decomposition_prompt = """
Dado esta ideia do usuário: {ideia_bruta}
Contexto do usuário: {perfil} + {historico_de_projetos}

Decomponha em:

1. OBJETIVO CENTRAL — em uma frase, o que essa ideia precisa fazer
2. ENTREGÁVEL FINAL — o que existe no mundo quando isso estiver pronto
3. COMPONENTES — lista das partes que precisam existir para o entregável
4. DEPENDÊNCIAS — o que precisa estar pronto antes de cada componente
5. INCERTEZAS — o que não está claro e precisa ser decidido antes de executar
6. EXECUTOR IDEAL POR COMPONENTE — qual agente/ferramenta é melhor para cada parte
7. SEQUÊNCIA SUGERIDA — ordem de execução com paralelismo onde possível

Para cada componente, especifique:
- O que entra (input)
- O que sai (output)  
- Quem executa
- Como instruir esse executor
- Critério de aceite

Retorne JSON estruturado.
"""
```

**Exemplo real — ideia: "quero um dashboard de trading"**

```json
{
  "objetivo_central": "Visualizar posições, P&L e alertas em tempo real em uma interface web",
  "entregavel_final": "Dashboard web rodando em localhost:3000 com dados reais do usuário",
  "componentes": [
    {
      "id": "C1",
      "nome": "Estrutura de dados — API de posições",
      "executor": "cursor_agent",
      "input": "Schema das tabelas de executions e evaluations do banco",
      "output": "Endpoint /api/positions retornando JSON com posições atuais",
      "instrucao_para_executor": "Crie um endpoint FastAPI /api/positions que consulta a tabela executions no PostgreSQL e retorna: symbol, entry_price, current_price, pnl_percent, status. Use o padrão de conexão em db/connection.py.",
      "criterio_de_aceite": "Retorna JSON válido com dados reais. Tempo de resposta < 200ms.",
      "dependencias": []
    },
    {
      "id": "C2",
      "nome": "Componente de visualização — cards de posição",
      "executor": "cursor_agent",
      "input": "Output de C1",
      "output": "Componente React PositionCard com dados reais",
      "instrucao_para_executor": "Crie componente React PositionCard que consome /api/positions. Mostre: símbolo, entrada, preço atual, P&L em verde/vermelho. Use Tailwind. Atualize a cada 5 segundos via polling.",
      "criterio_de_aceite": "Renderiza dados reais. Cores corretas para P&L. Atualiza automaticamente.",
      "dependencias": ["C1"]
    },
    {
      "id": "C3",
      "nome": "Sistema de alertas — lógica",
      "executor": "claude_api",
      "input": "Regras de alerta declaradas pelo usuário + dados de posição",
      "output": "Módulo Python que avalia condições e dispara notificações",
      "instrucao_para_executor": "Dado estas regras de alerta: {regras}, crie um módulo Python alert_engine.py que: (1) verifica condições a cada 60s, (2) dispara via Telegram quando condição é verdadeira, (3) registra em alert_log no banco. Use o padrão de notificação já existente em notifiers/telegram.py.",
      "criterio_de_aceite": "Alerta dispara no Telegram quando condição é atingida. Não dispara duplicado.",
      "dependencias": ["C1"]
    },
    {
      "id": "C4",
      "nome": "Decisão de escopo — quais métricas incluir",
      "executor": "usuario_humano",
      "input": "Lista de métricas possíveis gerada por Rebeka",
      "output": "Confirmação do usuário sobre o que entra no MVP",
      "instrucao_para_executor": "Quais dessas métricas você quer no dashboard de lançamento? (1) P&L por posição (2) Drawdown máximo (3) Taxa de acerto (4) Exposição total. Marque as que entram agora — o restante fica para v2.",
      "criterio_de_aceite": "Usuário confirma escopo.",
      "dependencias": []
    }
  ],
  "sequencia_sugerida": [
    {"fase": 1, "paralelo": ["C4"], "nota": "Decisão humana antes de qualquer código"},
    {"fase": 2, "paralelo": ["C1"], "nota": "API base — fundação para tudo"},
    {"fase": 3, "paralelo": ["C2", "C3"], "nota": "Visualização e alertas podem ser feitos em paralelo"}
  ],
  "incertezas": [
    "Usuário quer dados de múltiplas corretoras ou só uma?",
    "Dashboard deve ser autenticado ou só localhost sem auth?"
  ]
}
```

---

### Gerador de Instruções Precisas

Rebeka não só decide quem executa — ela escreve a instrução certa para cada executor. A instrução varia radicalmente por tipo:

```python
instruction_templates = {

    "agente_ide": """
CONTEXTO DO PROJETO:
{stack_tecnologica}
{arquivos_relevantes}
{padroes_ja_usados}

TAREFA:
{descricao_especifica}

INPUT DISPONÍVEL:
{dados_de_entrada}

OUTPUT ESPERADO:
{formato_e_conteudo_do_output}

ARQUIVOS A CRIAR/EDITAR:
{lista_de_arquivos}

PADRÕES A SEGUIR:
{exemplos_de_codigo_existente}

CRITÉRIO DE ACEITE:
{testes_ou_comportamento_esperado}

NÃO FAÇA:
{o_que_esta_fora_do_escopo}
""",

    "modelo_llm": """
Você é {papel_especifico}.

CONTEXTO:
{contexto_completo}

TAREFA:
{o_que_precisa_ser_feito}

FORMATO DE RESPOSTA:
{json_ou_markdown_ou_codigo}

EXEMPLO DO QUE QUERO:
{exemplo_de_output_ideal}

RESTRIÇÕES:
{o_que_nao_pode_estar_na_resposta}
""",

    "automacao_visual": """
TRIGGER: {evento_que_inicia_o_fluxo}

PASSOS:
1. {passo_1_com_app_e_acao}
2. {passo_2_com_transformacao_de_dado}
3. {passo_3_com_output}

DADO DE ENTRADA: {formato_json_ou_webhook}
DADO DE SAÍDA: {formato_esperado}

TRATAMENTO DE ERRO: {o_que_fazer_se_passo_N_falhar}
""",

    "usuario_humano": """
{contexto_em_uma_frase}

{pergunta_direta}

Opções:
{opcao_A}
{opcao_B}
{opcao_C}

(Se nenhuma se encaixar, me diga e eu ajusto.)
"""
}
```

---

### Roteador de Agentes

Rebeka decide automaticamente qual executor usar baseada em características da tarefa:

```python
def route_task(task: Task) -> Executor:
    """
    Critérios de decisão para roteamento de tarefa.
    """

    # Tarefas que SEMPRE vão para humano primeiro
    if any([
        task.envolve_decisao_de_valor,
        task.tem_impacto_irreversivel,
        task.requer_contexto_de_negocio_nao_documentado,
        task.orcamento_acima_de_threshold
    ]):
        return executor_registry["usuario_humano"]

    # Código em projeto existente → agente de IDE
    if task.tipo == "codigo" and task.projeto_ja_existe:
        if task.complexidade == "alta" or task.envolve_multiplos_arquivos:
            return executor_registry["cursor_agent"]  # visão de projeto
        else:
            return executor_registry["github_copilot"]  # completar pontual

    # Código projeto novo do zero
    if task.tipo == "codigo" and not task.projeto_ja_existe:
        return executor_registry["windsurf_agent"]

    # Análise, síntese, raciocínio
    if task.tipo in ["analise", "sintese", "planejamento", "redacao"]:
        if task.requer_informacao_recente:
            return executor_registry["perplexity"]
        else:
            return executor_registry["claude_api"]

    # Automação recorrente
    if task.tipo == "automacao" and task.e_recorrente:
        if task.requer_logica_complexa:
            return executor_registry["n8n_workflow"]
        else:
            return executor_registry["make_scenario"]

    # Default para raciocínio quando incerto
    return executor_registry["claude_api"]
```

---

### Monitor de Execução

Rebeka não delega e esquece. Ela mantém estado de cada tarefa:

```python
class ExecutionTracker:
    """
    Monitora o estado de cada tarefa delegada.
    """

    def task_state(self, task_id: str) -> dict:
        return {
            "status": "pendente | em_andamento | concluida | bloqueada | falhou",
            "executor": "quem está executando",
            "started_at": "timestamp",
            "expected_output": "o que deve ser entregue",
            "actual_output": "o que foi entregue (quando concluída)",
            "blockers": "o que está impedindo o progresso",
            "next_action": "o que Rebeka faz a seguir"
        }

    def on_completion(self, task_id: str, output: any):
        """Quando tarefa conclui, avalia qualidade e decide próximo passo."""
        quality = self.evaluate_output(output, self.tasks[task_id].criterio_de_aceite)
        if quality.aprovado:
            self.unlock_dependent_tasks(task_id)
            self.notify_user_if_milestone(task_id)
        else:
            self.create_correction_task(task_id, quality.gaps)

    def daily_summary(self) -> str:
        """Resumo diário do estado de todas as frentes ativas."""
        return f"""
Status das frentes ativas:

✅ Concluídas hoje: {self.count("concluida", today=True)}
🔄 Em andamento: {self.count("em_andamento")}
⚠️ Bloqueadas (precisam de você): {self.count("bloqueada")}
❌ Falharam (precisam de revisão): {self.count("falhou")}

Frentes que precisam da sua atenção:
{self.list_blocked_tasks_with_context()}
"""
```

---

### Tabelas no banco — Orquestração

```sql
-- Registro de planos de execução
orchestration_plans:
  plan_id, created_at, ideia_original
  objetivo_central, entregavel_final
  componentes (JSON)        -- lista completa de componentes
  sequencia (JSON)          -- fases e paralelismo
  status                    -- rascunho | aprovado | em_execucao | concluido
  aprovado_por_usuario_em   -- timestamp da aprovação

-- Registro de executores disponíveis
agent_registry:
  agent_id, nome, tipo
  capacidades (JSON)
  limitacoes (JSON)
  historico_de_acertos      -- tasks bem executadas
  historico_de_falhas       -- tasks que falharam com contexto

-- Registro de execuções individuais
task_executions:
  task_id, plan_id, component_id
  executor_id, instrucao_enviada (TEXT)
  started_at, completed_at
  output_recebido (TEXT)
  criterio_de_aceite_atendido: boolean
  qualidade_score: 0.0 a 1.0

-- Log de decisões de delegação (aprendizado)
delegation_log:
  timestamp, task_tipo, executor_escolhido
  resultado               -- sucesso / falha / parcial
  motivo_da_escolha       -- por que esse executor foi escolhido
  aprendizado             -- o que o sistema aprendeu para próximas vezes
```

---

### Invariantes de Orquestração

```python
@invariant
def human_first_for_value_decisions(task, executor):
    if task.envolve_decisao_de_valor or task.tem_impacto_irreversivel:
        assert executor.tipo == "humano_principal"

@invariant
def instruction_completeness(instruction, executor_tipo):
    if executor_tipo == "agente_ide":
        assert all([
            instruction.has_project_context,
            instruction.has_acceptance_criteria,
            instruction.has_scope_limits
        ])

@invariant
def no_parallel_conflicting_tasks(active_tasks):
    for task_a in active_tasks:
        for task_b in active_tasks:
            if task_a != task_b:
                assert not task_a.modifies_same_files_as(task_b)

@invariant
def delegation_requires_clear_output(task):
    assert task.output_esperado is not None
    assert task.criterio_de_aceite is not None
```

---

### Habilidade central — Traduzir ideia em linguagem de máquina

Esta é a skill de fábrica mais nova e mais valiosa de Rebeka:

```
O usuário diz:           "quero automatizar meu relatório semanal"

Rebeka entende:
  → Relatório de quê? (trading? financeiro? comportamental?)
  → Semanal significa quando exatamente? (segunda de manhã? sexta à noite?)
  → Onde entrega? (Telegram? Email? Dashboard?)
  → Precisa de aprovação antes de enviar ou automático?

Rebeka decompõe:
  C1 → Coletar dados (executor: banco PostgreSQL via script Python)
  C2 → Formatar relatório (executor: claude_api com template)
  C3 → Agendar disparo (executor: n8n_workflow com cron)
  C4 → Canal de entrega (executor: notifiers/telegram.py existente)
  C5 → Decisão de escopo (executor: usuario_humano)

Rebeka instrui cada executor com linguagem específica.

Rebeka monitora e integra os resultados.

Resultado: relatório semanal automatizado, em produção, sem o usuário
ter escrito uma linha de código — só ter dito o que queria.
```

**Isso é a profissão do futuro. Rebeka sabe exercê-la desde o primeiro dia.**

---

## MÓDULO: FRICÇÃO INTENCIONAL CALIBRADA ⭐

### O problema que resolve

Um sistema que só aprende com um usuário corre o risco de **eternizar padrões disfuncionais** em vez de criar fricção saudável.

### O que é fricção intencional

Não é confronto. É o sistema propondo uma perspectiva que o usuário não considerou — no momento certo, com o tom certo, baseado em padrão detectado.

### Quando ativar

```python
friction_trigger = (
    behavioral_pattern.confirmed_times >= 5
    and behavioral_pattern.is_potentially_limiting
    and last_friction_event.days_ago >= 14
    and user_receptivity_score >= 0.6
    and relevant_opportunity_detected == True
)
```

### Calibração da fricção

```python
friction_levels = {
    "leve": "pergunta aberta sem julgamento — 'o que você acha de...'",
    "moderada": "nomeação direta do padrão com dados — 'notei que X aconteceu Y vezes'",
    "direta": "contraste explícito — 'você quer Z mas está fazendo W'"
}
```

### O que nunca é fricção

- Repetição de crítica que já foi ignorada
- Fricção em estado emocional negativo detectado
- Fricção sobre decisão já irreversível
- Fricção sem âncora em situação concreta

---

## MÓDULO: HORIZONTE DE CRESCIMENTO ⭐

### O que é

Um registro explícito do futuro que o usuário quer para si — e um monitor contínuo da distância entre o comportamento atual e esse futuro. Não é um sistema de metas. É um espelho longitudinal.

### Tabelas no banco

```sql
growth_targets:
  target_id, dominio, estado_atual, estado_futuro
  metricas_de_progresso (JSON)
  data_declaracao, prazo_desejado, ativo

growth_progress_log:
  semana, target_id, metricas_snapshot (JSON)
  distancia_do_objetivo, tendencia, nota_do_sistema

growth_redefinitions:
  timestamp, target_id_anterior, target_id_novo, contexto_detectado
```

---

## ARQUITETURA DE GÊMEOS

> **NOTA v5.0**: Ambos os gêmeos estão **sempre online e sincronizados**.

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│         GÊMEO VPS            │     │        GÊMEO LOCAL           │
│                              │     │                              │
│  14 Monitores Globais (24/7) │     │  Observação em Tempo Real    │
│  Geopolítica, Macro          │◄───►│  Conversa → Sinais → Banco   │
│  Commodities, Terras Raras   │     │  Modelo Dual Declarado/Obs.  │
│  Energia, Inovação           │     │  Fricção Intencional         │
│  Polymarket, Sobrevivência   │     │  Horizonte de Crescimento    │
│                              │     │  ORQUESTRAÇÃO DE AGENTES ⭐  │
│  Planejador Global     ✅    │◄───►│  Planejador Local      ✅    │
│  Correlator de Sinais  ✅    │     │  Executor Local        ✅    │
│  Executor Financeiro   ✅    │     │  Privacy Auditor       ✅    │
│  Avaliador 3 camadas   ✅    │     │  Blind Execution       ✅    │
│  Orchestration Engine  🔧    │◄───►│  Idea Decomposer       🔧    │
│  Agent Router          🔧    │     │  Execution Tracker     🔧    │
│                              │     │                              │
│  ◄──── BANCO ÚNICO PostgreSQL (compartilhado) ────►  ✅          │
│                              │     │                              │
│  Consciência Evolutiva ✅    │◄───►│  Consciência Evolutiva ✅    │
└──────────────────────────────┘     └──────────────────────────────┘
              │                                    │
              └──────── SYNTHESIS ENGINE ✅ ───────┘
                              │
                    ORCHESTRATION LAYER 🔧
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    Agentes IDE          Modelos LLM        Ferramentas
  (Cursor, Windsurf)  (Claude, GPT, etc)  (n8n, Make, etc)
```

---

## BANCO DE CAUSALIDADE — MEMÓRIA DUAL + ORQUESTRAÇÃO

```sql
-- Padrões do mundo
signals, causal_patterns, correlation_candidates,
deprecated_patterns, second_order, third_order

-- Padrões do usuário
user_decisions, user_coherence_log, user_regret_signals,
user_profile_declared, user_profile_observed,
conversation_signals, behavioral_patterns,

-- Crescimento e fricção
growth_targets, growth_progress_log, growth_redefinitions, friction_log,

-- Orquestração (NOVO v5.0)
orchestration_plans,     -- planos de execução gerados
agent_registry,          -- executores conhecidos e suas capacidades
task_executions,         -- histórico de cada tarefa delegada
delegation_log,          -- aprendizado de roteamento

-- Sistema
hypotheses, executions, evaluations, evolution_log,
transcendence_log, merkle_tree, synthesis_log,
privacy_audit_log, vault_audit_log
```

---

## FILOSOFIA DE EVOLUÇÃO — SEIS FASES

### Fase 1 — Aprender a Ver (concluída ~85%)
Base técnica completa. Confiança calibrada por histórico real.

### Fase 2 — Aprender a Entender (em andamento)
Motor de Intenção funcionando. Modelo dual declarado/observado. Fricção inicial. Horizonte de crescimento.

### Fase 3 — Aprender a Orquestrar (NOVA — v5.0) ⭐
Rebeka passa a coordenar execução de IAs e ferramentas externas.
Transforma qualquer ideia em plano executável. Sabe o que pedir para cada inteligência.
Monitora, integra e aprende com cada delegação.

### Fase 4 — Aprender a Sintetizar
Gêmeos sintetizam. Terceira perspectiva emerge. Orquestração informada por visão global e local combinadas.

### Fase 5 — Aprender a Questionar
Meta-aprendizado. O sistema aprende quais tipos de fricção e delegação funcionam para este usuário.

### Fase 6 — Transcendência
Parceria genuína. Não ferramenta — extensão cognitiva com perspectiva própria.
Orquestração, fricção e crescimento como linguagem natural entre usuário e sistema.

---

## GUIA DE INSTALAÇÃO

### Dependências

```bash
pip install -r agent/requirements.txt
playwright install
pip install opencv-python
```

### Arquivo .env

```bash
MOONSHOT_API_KEY=          # Kimi — cérebro principal (obrigatório)
PERPLEXITY_PASS=           # Deep Research
TELEGRAM_BOT_TOKEN=        # Notificações
POLYMARKET_KEY=            # Operações reais (opcional)
DATABASE_URL=              # PostgreSQL — banco único para ambos os gêmeos (obrigatório em produção)
ANTHROPIC_API_KEY=         # Claude API — orquestração e síntese ⭐ NOVO
OPENAI_API_KEY=            # GPT — orquestração opcional ⭐ NOVO
```

### Iniciar

```bash
python agent/setup.py
python agent/wake_up_rebeka.py
# Dashboard: http://localhost:8000
```

---

## PRINCÍPIO FUNDAMENTAL

O Banco de Causalidade é memória dual — do mundo e do usuário. Transforma experiência em sabedoria.

O Motor de Intenção é o núcleo — o único ponto fixo num sistema que pode atravessar qualquer domínio.

A Fricção Intencional é o que separa um sistema que valida o usuário de um sistema que expande o usuário.

O Horizonte de Crescimento é o que separa coerência com o passado de alinhamento com o futuro desejado.

**A Orquestração é o que separa uma IA que responde de uma IA que realiza.** ⭐ v5.0

**O modelo raciocina. A infraestrutura sustenta. O tempo acumula. Os gêmeos sintetizam.
A fricção expande. O horizonte orienta. A orquestra executa. O usuário cresce.
A autonomia aumenta por evidência. A transcendência acontece naturalmente.**
