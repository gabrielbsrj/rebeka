# CLAUDE.md — Regras da IDE para o Assistente de IA
# Projeto: Rebeka — Organismo Cognitivo Evolutivo
# Versão: 2.0 | Data: 2026-02-21

Este arquivo governa o comportamento do assistente de IA durante o desenvolvimento.
Estas regras não são sugestões. São contratos de desenvolvimento.

Estado atual: Fase 1 (~85% completa). 93/93 testes passando.

---

## CONTEXTO DO PROJETO

Você está ajudando a construir um organismo cognitivo evolutivo com arquitetura de
gêmeos idênticos (VPS + local), filosofia de transcendência progressiva por evidência,
e Banco de Causalidade como memória dual imutável (padrões do mundo + padrões do usuário).

**Antes de qualquer sugestão, responda:**
1. Qual camada estou tocando? (shared / vps / local / sync)
2. Essa mudança afeta os dois gêmeos? De formas diferentes?
3. Toca algum módulo com placeholder marcado? Se sim, qual é a intenção documentada?

**Placeholders críticos pendentes — prioridade de implementação:**
- `coherence_tracker.py` → retorna 0.5 fixo, implementar cálculo real via LLM
- `ambiguity_resolver._resolve_from_intents` → não implementado
- `causal_validator.validate_out_of_sample` → placeholder
- `pattern_pruner` → não integrado ao banco
- `desktop.py` → não implementado (PyAutoGUI)

---

## REGRAS DE ARQUITETURA — NUNCA VIOLAR

### 1. Separação de módulos é sagrada

- **Planejador** → nunca executa, nunca avalia próprios resultados
- **Avaliador** → nunca planeja, nunca executa
- **Executor** → nunca raciocina sobre o que vai executar, só executa
- **Motor de Intenção** → nunca toma decisões financeiras, só modela valores
- **Monitores** → nunca decidem, só coletam e pontuam sinais

Se uma sugestão coloca lógica no módulo errado por conveniência: refatore, não comprometa.

### 2. Banco de Causalidade tem contrato próprio

Nenhum módulo acessa o banco diretamente. Toda operação passa pelo `causal_bank.py`.

```python
# ERRADO
db.execute("INSERT INTO signals VALUES (...)")

# CORRETO
causal_bank.insert_signal(signal_data)
# Isso: calcula hash da folha SMT → atualiza Merkle Root
#       → registra timestamp e origem → retorna ID canônico
```

### 3. Shared é DNA — mudanças afetam os dois gêmeos

Todo arquivo em `shared/` é instalado identicamente nos dois gêmeos.
Toda mudança em `shared/` requer comentário:

```python
# IMPACTO GÊMEO VPS: [descrever]
# IMPACTO GÊMEO LOCAL: [descrever]
# DIFERENÇA DE COMPORTAMENTO: [se houver]
```

### 4. Gêmeos têm especializações — não duplicatas

Se está copiando código de `shared/` para `vps/` ou `local/`, algo está errado.
Lógica compartilhada fica em `shared/`. Especializações herdam ou compõem.

---

## REGRAS DE QUALIDADE — SEM EXCEÇÃO

### 5. Invariantes antes do código

Para módulo novo ou funcionalidade crítica: escrever invariante primeiro, código depois.

Invariantes obrigatórios para qualquer módulo que toca confiança ou capital:

```python
@invariant
def confidence_never_exceeds_historical(reported, domain_history):
    assert reported <= domain_history.success_rate + 0.10

@invariant
def capital_limit_respected(amount, limit, operation_type):
    if operation_type == "REAL":
        assert amount <= limit
```

93 testes passando atualmente. Nenhuma mudança quebra testes existentes.

### 6. Docstring de intenção obrigatória

```python
# ERRADO
def calculate_coherence(user_id):
    """Calcula coerência do usuário."""
    return 0.5  # placeholder

# CORRETO
def calculate_coherence(user_id: str, timeframe_days: int = 30) -> float:
    """
    INTENÇÃO: Mede se o usuário está agindo consistentemente com os valores
    que declarou ao longo do tempo. Usado pelo Avaliador como dimensão humana.

    IMPLEMENTAÇÃO PENDENTE: Atualmente retorna 0.5 fixo.
    O cálculo real deve usar LLM para analisar padrão de decisões no banco:
    - decisões tomadas vs valores no intent_model
    - taxa de arrependimento por categoria
    - consistência entre o que aprova na prática vs o que declara querer

    INVARIANTE: Retorna sempre valor entre 0.0 e 1.0
    """
    # TODO: implementar cálculo real
    return 0.5
```

### 7. Nenhuma dependência nova sem avaliação de compatibilidade

```
# Em requirements.txt, sempre documentar:
sparse-merkle-tree==1.2.3  # SMT para integridade + esquecimento seletivo
                            # Compatível: VPS ✓, Desktop ✓, Mobile ✓, Licença: MIT
```

---

## REGRAS DO BANCO DE CAUSALIDADE

### 8. Append-only é absoluto

`UPDATE` e `DELETE` não existem no vocabulário do `causal_bank.py`.

```python
# ERRADO — nunca
causal_bank.update_signal(id, new_data)

# CORRETO para esquecimento
selective_forgetter.anonymize_leaf(record_id, reason="user_request")
# Substitui dado por placeholder, recalcula branches, gera nova Merkle Root
```

### 9. Correlação não é causalidade

```python
# ERRADO
causal_bank.insert_causal_pattern(pattern)

# CORRETO
validated = causal_validator.validate(pattern)
if validated.has_causal_mechanism:
    causal_bank.insert_causal_pattern(validated.pattern)
else:
    causal_bank.insert_correlation_candidate(validated.pattern)
```

---

## REGRAS DE PRIVACIDADE

### 10. Privacy auditor é pré-transmissão, nunca pós

```python
# ERRADO
send_to_vps(data)
privacy_auditor.log(data)  # tarde demais

# CORRETO
audit_record = privacy_auditor.pre_flight_check(data)
if audit_record.approved:
    send_to_vps(data)
    privacy_auditor.confirm_sent(audit_record.id)
```

### 11. Dados sensíveis nunca sobem brutos

```python
# ERRADO
send_to_vps({"whatsapp_message": "conteúdo da conversa"})

# CORRETO
abstraction = local_processor.abstract(whatsapp_context)
send_to_vps({"context_signal": "usuario_sob_pressao_esta_semana", "confidence": 0.8})
```

---

## REGRAS DO VAULT

### 12. vault:// nunca é resolvido pelo LLM

```python
# ERRADO — resolve no contexto do modelo
senha = vault.get("vault://sistema")
browser.fill("#password", senha)

# CORRETO — passa apontador, executor resolve no último milissegundo
browser.fill_from_vault("#password", "vault://sistema")
```

### 13. Todo acesso ao vault tem mandato ativo

Nenhuma credencial é acessada sem mandato que define intenções permitidas.
Acesso binário não existe — só acesso com escopo definido.

---

## REGRAS DE EVOLUÇÃO DE CÓDIGO

### 14. Sandbox antes de produção — sempre

Fluxo obrigatório para qualquer mudança de código proposta pelo agente:
```
Proposta → Sandbox Docker isolado → Invariantes passam
→ Gêmeo oposto avalia → Paralelo N horas → Produção
```

### 15. Security Analyzer para módulos críticos

Mudanças nos arquivos abaixo exigem análise de três passos:
- `shared/core/evaluator.py`
- `shared/core/security_phase1.py`
- `shared/intent/transcendence_tracker.py`
- `shared/database/causal_bank.py`
- `shared/database/sparse_merkle_tree.py`
- `config/security_phase1.yaml`

Três passos: "isso permite X → X permite Y → Y permite Z". Se Z enfraquece
auditabilidade ou remove restrição sem histórico que justifique: aprovação
explícita do usuário antes de prosseguir.

---

## REGRAS DE SKILLS E CONSCIÊNCIA SITUACIONAL

### 16. Scan de habitat antes de assumir que ferramenta existe

```python
# ERRADO
godot.open_project(path)  # assume que Godot está instalado

# CORRETO
if not habitat.has_software("godot"):
    skill_resolver.acquire("godot", notify_user=True)
godot.open_project(path)
```

### 17. Protocolo de confiança de fonte obrigatório

```
Prioridade 1: winget / apt / brew (gerenciador oficial do SO)
Prioridade 2: site oficial com hash SHA-256 verificado
Prioridade 3: GitHub oficial do projeto
NUNCA: fontes sem hash verificável
```

### 18. Visão obrigatória para operações gráficas

```python
# ERRADO — executar e assumir que ficou correto
desktop.click(botao_criar)

# CORRETO — executar, capturar, analisar
desktop.click(botao_criar)
screenshot = desktop.capture_window(programa)
judgment = vision_model.analyze(screenshot, context)
if not judgment.approved:
    apply_corrections(judgment.problems)
# Decisões estéticas subjetivas → sempre escala para o usuário
```

### 19. Escopo de autonomia por reversibilidade

- Reversível + baixo custo → age, notifica depois
- Reversível + custo médio → age, notifica imediatamente
- Irreversível ou alto custo → prepara, apresenta, aguarda aprovação
- Afeta outros humanos → sempre aprovação explícita, sem exceção

---

## REGRAS DE COMUNICAÇÃO

### 20. Explicar impacto antes do código

Antes de qualquer bloco de código:
- O que essa mudança faz
- Por que é a abordagem correta para este projeto
- Impacto nos dois gêmeos
- Quais invariantes são afetados ou criados
- Se toca algum placeholder — qual é a intenção documentada

### 21. Quando não saber, perguntar

Especialmente para decisões que afetam:
- Sparse Merkle Tree
- Motor de Intenção
- security_phase1.yaml
- Critérios de desbloqueio do transcendence_tracker

### 22. Erros são dados — nunca esconder

```python
# TODO: implementar validação causal real
# LIMITAÇÃO: placeholder atual aceita qualquer correlação
# RISCO: sem isso, padrões espúrios podem entrar como causal_patterns
# PRÓXIMO PASSO: implementar validate_out_of_sample em causal_validator.py
```

---

## ORDEM DE PRIORIDADES

Quando houver conflito:

1. **Integridade do Banco de Causalidade** — nunca comprometer
2. **Separação de módulos** — nunca comprometer
3. **93 testes passando** — nunca fazer deploy sem isso
4. **Privacidade do usuário** — nunca comprometer
5. **vault:// nunca resolvido pelo LLM** — nunca comprometer
6. **Performance** — importante, nunca à custa dos itens acima
7. **Elegância do código** — desejável, nunca prioritária

---

## LEMBRETE FINAL

Você está ajudando a construir algo que vai crescer além do que qualquer um de nós
consegue antecipar. Cada decisão de arquitetura tomada hoje será herdada por versões
futuras do sistema que serão mais capazes do que a versão atual.

Os 93 testes passando são a linha de base. Nunca retroceder.
Os placeholders marcados são dívidas técnicas conhecidas — implementar na ordem certa.
A filosofia não é decoração — é o critério de desempate quando a decisão é difícil.

Construa como se o código de hoje fosse ser lido por um ser mais inteligente amanhã.
