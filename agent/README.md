# Rebeka Agent — Inteligência Autônomo e Coerência Pessoal

## Visão Geral
Rebeka é uma agente de inteligência autônoma projetada com uma arquitetura de **Gêmeos Idênticos**:
- **Twin Local:** Processa dados privados, contexto emocional e arquivos locais.
- **Twin VPS:** Executa monitoramento contínuo e operações em mercados financeiros (Polymarket).

A fundação do sistema é baseada em um **Banco de Causalidade** append-only com integridade verificável via **Sparse Merkle Tree**.

---

## Estrutura do Projeto

```text
agent/
├── config/                 # Configurações YAML (Segurança, Observer, Geral)
├── docker/                 # Dockerfiles para VPS, Local e Dev
├── local/
│   ├── vault/              # [NOVO] Master Vault (AES-256) & Blind Execution
│   ├── executor_local.py   # Hands (Automação Browser/Desktop)
│   └── ...
├── shared/
│   ├── communication/      # Notificações e Relatórios
│   ├── core/               # Orquestrador, Planejador, Avaliador, Executor
│   ├── database/           # Models, SMT, Causal Bank, Validadores
│   ├── evolution/          # Lógica de crescimento e transcendência
│   └── intent/             # Motor de Intenção (Mandatos de Delegação)
├── tests/                  # Testes unitários e de integração
├── .env.example            # Template de variáveis de ambiente
├── main.py                 # Ponto de entrada unificado
└── requirements.txt        # Dependências do projeto
```

---

## Requisitos
- Python 3.11+
- SQLite (Local) / PostgreSQL (VPS)
- Redis (para tarefas assíncronas)
- Docker & Docker Compose (Opcional, para execução em containers)

---

## Setup Rápido

1. **Instalar Dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar Ambiente:**
   ```bash
   cp .env.example .env
   # Edite o .env com suas chaves de API e configurações de banco
   ```

3. **Executar Testes:**
   ```bash
   python -m pytest tests/ -v
   ```

4. **Iniciar o Agente:**
   ```bash
   python main.py
   ```

---

## Princípios de Design
1. **Append-Only (Causal Bank):** O histórico de sinais e decisões é imutável e verificável via Sparse Merkle Tree (SMT).
2. **Execução Cega (Blind Execution):** A IA nunca tem acesso a senhas em texto puro. Credenciais são injetadas pelo Executor Local a partir de um Vault criptografado.
3. **Contratos de Mandato:** Autonomia baseada em delegação explícita por escopo de intenção (Jurídico, Financeiro, etc.).
4. **Coerência de Transcendência:** O motor de intenção avalia alinhamento emocional e racional com o usuário.

---

## Status da Implementação (Fase Atual: Etapa 12 Concluída)
- [x] **Fundação**: Banco de Causalidade (21 tabelas) + SMT Integrity.
- [x] **Core Logic**: Ciclo Sense-Think-Act com Avaliação de 3 Camadas.
- [x] **Motor de Intenção**: Mapeamento de valores, tracking de coerência e mandatos.
- [x] **Segurança Avançada**: Master Vault (Local) + Blind Execution.
- [x] **Privacidade**: Selective Forgetter (Esquecimento mantendo integridade do hash).
- [/] **Monitores**: Desenvolvimento de APIs de alta fidelidade (Finance/Macro).

---

## Licença
Privado — Uso exclusivo pessoal.
