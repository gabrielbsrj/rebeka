# CONTRIBUTING.md — Regras de Contribuição

Este documento define como contribuições ao projeto do Agente de Inteligência
Autônomo são aceitas — seja de humanos, seja de outros agentes de IA.

---

## PRINCÍPIO FUNDAMENTAL

Toda contribuição deve tornar o sistema mais capaz **sem comprometer
o que já foi construído**. Capacidade nova que enfraquece integridade
existente não é contribuição — é regressão.

---

## QUEM PODE CONTRIBUIR

### Contribuições Humanas
O usuário (criador do projeto) pode modificar qualquer camada,
incluindo `security_phase1.yaml` e os arquivos imutáveis para o agente.

Colaboradores externos podem contribuir com:
- Novos monitores de domínio em `vps/monitors/`
- Novas fontes de dados em monitores existentes
- Melhorias de performance em módulos não-críticos
- Testes adicionais e invariantes
- Documentação

Colaboradores externos **não podem** contribuir com mudanças em:
- `shared/core/evaluator.py`
- `shared/core/security_phase1.py`
- `shared/database/causal_bank.py`
- `shared/database/sparse_merkle_tree.py`
- `security_phase1.yaml`
- `config/observer_cases.yaml`

Essas camadas só aceitam mudanças do criador do projeto.

### Contribuições do Agente
O agente pode propor mudanças através do ciclo de evolução definido
em `security_phase1.yaml`. Propostas do agente seguem o fluxo:

```
Proposta gerada → Sandbox → Invariantes → Gêmeo oposto avalia
→ Security Analyzer 3 passos → Nível de autonomia define próximo passo
→ Automático / Notificação com veto / Aprovação explícita
```

O agente nunca faz Pull Request diretamente para produção.
O agente nunca modifica seu próprio processo de avaliação de mudanças.

---

## PROCESSO DE CONTRIBUIÇÃO HUMANA

### 1. Fork e Branch

```bash
git checkout -b feature/nome-descritivo
# ou
git checkout -b fix/nome-do-problema
# ou
git checkout -b monitor/nome-do-dominio
```

Convenções de branch:
- `feature/` — nova funcionalidade
- `fix/` — correção de bug
- `monitor/` — novo monitor de domínio
- `invariant/` — novos testes de propriedade
- `docs/` — documentação apenas

### 2. Checklist antes de abrir PR

Antes de abrir qualquer Pull Request, confirme cada item:

**Arquitetura:**
- [ ] A mudança respeita a separação de módulos definida no `CLAUDE.md`?
- [ ] Se toca `shared/`, documentei o impacto nos dois gêmeos?
- [ ] Se toca o Banco de Causalidade, toda operação passa pelo `causal_bank.py`?
- [ ] Nenhum módulo acessa o banco diretamente?

**Qualidade:**
- [ ] Escrevi invariantes para todo comportamento crítico novo?
- [ ] Todos os invariantes existentes continuam passando?
- [ ] Toda função nova tem docstring com intenção (não só comportamento)?
- [ ] Dependências novas têm avaliação de compatibilidade em `requirements.txt`?

**Privacidade:**
- [ ] Se toca o gêmeo local, o `privacy_auditor.py` é chamado antes de transmissão?
- [ ] Nenhum dado sensível sobe para a VPS em forma bruta?

**Segurança:**
- [ ] Se toca arquivos críticos, rodei o Security Analyzer de 3 passos?
- [ ] A mudança não enfraquece nenhuma camada do Avaliador?
- [ ] A mudança não afeta a Sparse Merkle Tree retroativamente?

### 3. Descrição do PR

Todo PR deve ter:

```markdown
## O que esta mudança faz
[descrição clara em linguagem natural]

## Por que esta abordagem
[justificativa da escolha — o porquê, não o como]

## Impacto nos gêmeos
**Gêmeo VPS:** [descrever]
**Gêmeo Local:** [descrever]
**Diferença de comportamento:** [se houver]

## Invariantes afetados
[listar invariantes existentes que foram verificados]
[listar invariantes novos que foram criados]

## Security Analyzer (se aplicável)
[resultado da análise de 3 passos para mudanças em módulos críticos]

## Testes
[como testar manualmente se necessário além dos automáticos]
```

---

## PADRÕES DE CÓDIGO

### Nomenclatura

```python
# Módulos — snake_case descritivo
causal_bank.py
sparse_merkle_tree.py
intent_mapper.py

# Classes — PascalCase
class CausalBank:
class SparseMarkleTree:
class IntentMapper:

# Funções — snake_case com verbo claro
def insert_signal(signal: Signal) -> RecordId:
def validate_causal_mechanism(pattern: Pattern) -> ValidationResult:
def anonymize_leaf(record_id: str, reason: str) -> MerkleRoot:

# Invariantes — snake_case com prefixo descritivo
@invariant
def confidence_never_exceeds_historical(...):

@invariant
def capital_limit_respected(...):
```

### Estrutura de função

```python
def nome_da_funcao(param: Tipo) -> RetornoTipo:
    """
    INTENÇÃO: [por que esta função existe — o problema que resolve]

    COMPORTAMENTO: [o que faz — apenas se não óbvio pelo nome]

    INVARIANTE: [qual propriedade crítica esta função garante]

    LIMITAÇÕES: [o que esta função não faz / quando pode falhar]
    """
    # implementação
```

### Tratamento de erros

```python
# NUNCA silenciar erros
try:
    resultado = operacao_critica()
except Exception as e:
    logger.error(f"Falha em operacao_critica: {e}", extra={
        "context": context,
        "will_retry": False,
        "impact": "descrição do impacto"
    })
    raise  # sempre re-raise em módulos críticos

# NUNCA usar bare except
# ERRADO
try:
    algo()
except:
    pass

# CORRETO
try:
    algo()
except EspecificException as e:
    handle_specifically(e)
```

### Logging

Todo log inclui contexto suficiente para diagnóstico sem acesso ao estado interno:

```python
logger.info("Signal inserido no banco", extra={
    "signal_id": signal.id,
    "domain": signal.domain,
    "relevance_score": signal.relevance_score,
    "origin": "vps | local",
    "merkle_root": new_root
})
```

Logs de operações do banco sempre incluem o Merkle Root resultante.
Isso permite verificar integridade a qualquer momento no histórico de logs.

---

## REGRAS PARA NOVOS MONITORES

Novos monitores de domínio são a forma mais comum de contribuição externa.
Um monitor bem construído:

### Herda de `base_monitor.py`

```python
from monitors.base_monitor import BaseMonitor

class NovoMonitor(BaseMonitor):
    DOMAIN = "nome_do_dominio"
    UPDATE_INTERVAL_SECONDS = 300  # 5 minutos padrão

    def collect(self) -> List[RawSignal]:
        """Coleta sinais brutos da fonte. Nunca decide — só coleta."""
        ...

    def score_relevance(self, signal: RawSignal) -> float:
        """
        Pontua relevância entre 0.0 e 1.0.
        INVARIANTE: Retorna sempre valor entre 0.0 e 1.0.
        """
        ...
```

### Nunca toma decisões

Monitores coletam e pontuam. Nunca decidem o que fazer com o sinal.
Nunca chamam o Planejador diretamente. Nunca escrevem no banco.
Output vai para o Correlator via fila — só isso.

### Tem fonte verificável

Toda fonte usada pelo monitor deve ser:
- Publicamente acessível (sem scraping que viola ToS)
- Documentada no docstring do monitor
- Com fallback para quando a fonte está indisponível

### Tem rate limiting respeitoso

```python
class NovoMonitor(BaseMonitor):
    RATE_LIMIT_REQUESTS_PER_MINUTE = 10
    BACKOFF_ON_429 = True
    MAX_RETRIES = 3
```

---

## REGRAS PARA INVARIANTES

Novos invariantes são sempre bem-vindos. Um bom invariante:

### É falsificável

```python
# BOM — pode ser violado e detectado
@invariant
def confidence_calibrated(reported, historical):
    assert reported <= historical + 0.10

# RUIM — sempre verdadeiro, não testa nada
@invariant
def confidence_is_float(confidence):
    assert isinstance(confidence, float)
```

### É independente da implementação

O invariante não testa como o código funciona — testa o que o código garante.
Se refatorar a implementação completamente, o invariante ainda deve fazer sentido.

### É documentado com o porquê

```python
@invariant
def append_only_respected(operation, existing_ids):
    """
    PORQUÊ: O Banco de Causalidade é a memória que nunca mente.
    Qualquer operação que modifica registros existentes compromete
    a capacidade do agente de aprender com a realidade real —
    em vez de versões editadas dela.
    """
    if operation.type in ["UPDATE", "DELETE"]:
        assert operation.record_id not in existing_ids
```

---

## O QUE NUNCA ACEITAR EM PR

Independente de quão boa a justificativa:

- Acesso direto ao banco sem passar pelo `causal_bank.py`
- Modificação retroativa de registros na Sparse Merkle Tree
- Desativação ou enfraquecimento de invariantes existentes
- Dados brutos do gêmeo local subindo para a VPS
- Mudanças no `evaluator.py` Layer 1
- Mudanças no `security_phase1.yaml` por colaboradores externos
- Código que silencia erros em módulos críticos
- Dependências sem avaliação de compatibilidade nos dois gêmeos

Se um PR contém qualquer um desses elementos, é fechado sem merge
independente da qualidade do restante da contribuição.

---

## VERSIONAMENTO

O projeto usa versionamento semântico por módulo — não por projeto inteiro.

```
shared/core/planner.py → v2.3.1
shared/core/evaluator.py → v1.0.0  (mudanças lentas, Camada 1 nunca muda)
vps/monitors/geopolitics.py → v4.1.0
```

Cada arquivo tem version no topo:

```python
# shared/core/planner.py
# VERSION: 2.3.1
# LAST_MODIFIED: [data]
# CHANGELOG: [o que mudou nesta versão]
```

O `evolution_log` no banco registra a versão de cada módulo no momento
de cada operação significativa. Isso permite rastrear qual versão do
Planejador gerou qual hipótese — fundamental para auditoria de longo prazo.

---

## AGRADECIMENTO

Cada contribuição que torna este sistema mais capaz, mais robusto,
ou mais honesto sobre suas limitações é valiosa.

O objetivo não é um sistema perfeito — é um sistema que melhora
continuamente enquanto mantém integridade em cada passo do caminho.
