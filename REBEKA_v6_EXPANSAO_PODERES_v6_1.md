# REBEKA v6.0 — EXPANSÃO DE PODERES
## Análise Completa + Arquitetura dos Novos Módulos
**Data:** 2026-03-06 | **Baseado em:** AGENT_PROJECT_PROMPT_v5.md
**Status:** Plano de implementação — pronto para execução

---

## DIAGNÓSTICO DO PROJETO ATUAL

### O que já existe e está funcionando (Base v5.0)
| Módulo | Status | Relevância para expansão |
|---|---|---|
| WhatsApp via OCR/Visão Computacional | ✅ | Base para auto-resposta |
| Polymarket CopyTrading | ✅ | Base para detecção de oportunidades |
| 14 Monitores Globais (Geopolítica, Macro...) | ✅ | Base para alertas de oportunidade |
| Telegram Notificações | ✅ | Canal de alertas para o usuário |
| Dashboard localhost:8000 | ✅ | Painel central de controle |
| Banco PostgreSQL compartilhado | ✅ | Memória persistente unificada |
| Docker (produção/dev/sandbox) | ✅ | Isolamento dos sistemas |
| Blind Execution + Privacy Auditor | ✅ | Segurança das operações financeiras |
| Orchestration Engine (em andamento) | 🔧 | Base para orquestrar novos módulos |

### O que AINDA NÃO EXISTE e precisa ser construído (v6.0)
1. **Email Manager** — Acesso, triagem, alertas financeiros
2. **Financial Radar** — Detecção de contas a pagar, alertas de vencimento
3. **Opportunity Detector Ativo** — Evento → análise de ativos → Polymarket
4. **System Conflict Checker** — Auditoria de conflitos entre sistemas do usuário
5. **WhatsApp Auto-Responder** — Protocolo de resposta como assistente pessoal
6. **Memory Core** — Problemas, metas, projetos, dificuldades persistentes

---

## ANÁLISE DE CONFLITOS ENTRE SISTEMAS EXISTENTES

> ⚠️ **PRIORIDADE MÁXIMA** — Antes de ligar qualquer coisa nova, Rebeka precisa auditar os sistemas que já existem.

### Sistemas identificados pelo usuário
- **Bot Mercado Livre** — `Desktop/mercado_livre/`
- **SistemaTrader** — `Documentos/sistematrader/` — sistema de trade avançado

### Conflitos potenciais a auditar

#### 1. Conflito de Portas de Rede
```python
# audit/port_conflict_checker.py
import psutil
import subprocess

SISTEMAS = {
    "mercado_livre_bot": {
        "path": "~/Desktop/mercado_livre",
        "portas_tipicas": [8080, 8081, 5000, 3000]
    },
    "sistema_trader": {
        "path": "~/Documents/sistematrader",
        "portas_tipicas": [8000, 8080, 9000, 5432]  # 5432 = PostgreSQL
    },
    "rebeka_dashboard": {
        "path": "agent/",
        "portas_tipicas": [8000]  # CONFLITO POTENCIAL com trader!
    }
}

def verificar_conflitos_porta():
    """
    Verifica se dois sistemas tentam usar a mesma porta.
    Rebeka roda em :8000 — SistemaTrader pode conflitar.
    """
    portas_em_uso = {}
    for conn in psutil.net_connections():
        if conn.status == 'LISTEN':
            portas_em_uso[conn.laddr.port] = conn.pid
    return portas_em_uso
```

#### 2. Conflito de APIs e Rate Limits
```python
# Se Mercado Livre Bot e Rebeka acessam a mesma conta ML,
# podem esgotar rate limits ou criar comportamentos inesperados.

conflitos_api = {
    "mercado_livre_api": {
        "risco": "ALTO",
        "motivo": "Dois processos chamando a mesma API com mesmo token = ban",
        "solucao": "Rebeka MONITORA, não chama. Bot executa. Rebeka lê logs."
    },
    "broker_api_trader": {
        "risco": "CRÍTICO",
        "motivo": "Dois sistemas enviando ordens simultâneas = catástrofe financeira",
        "solucao": "MUTEX obrigatório. Somente um sistema ativo por vez com lock no banco."
    }
}
```

#### 3. Conflito de Banco de Dados
```python
# SistemaTrader pode ter seu próprio banco (SQLite ou PostgreSQL)
# Se usar o mesmo PostgreSQL da Rebeka na mesma porta: conflito de conexões

conflito_banco = {
    "cenario_A": "Trader usa SQLite próprio → SEM conflito",
    "cenario_B": "Trader usa PostgreSQL diferente → SEM conflito",
    "cenario_C": "Trader usa MESMO PostgreSQL da Rebeka → CONFLITO de pool de conexões",
    "verificacao": "Checar config/database.py ou .env do SistemaTrader"
}
```

#### 4. Conflito de Recursos de CPU/Memória
```python
# SistemaTrader rodando backtesting + Rebeka com 14 monitores = CPU alta
# Risco: sistema crítico de trade fica lento em momento importante

recursos = {
    "solucao": "Docker com resource limits explícitos",
    "trader_priority": "cpu_shares: 1024 (alta prioridade)",
    "rebeka_priority": "cpu_shares: 512 (menor prioridade quando trader ativo)",
    "mercado_livre_priority": "cpu_shares: 256 (background)"
}
```

### Protocolo de Auditoria (Rebeka executa ao iniciar)
```python
# system_conflict_checker.py

class SystemConflictChecker:
    def audit_on_startup(self):
        report = {
            "timestamp": now(),
            "sistemas_encontrados": self.scan_known_systems(),
            "conflitos_porta": self.check_port_conflicts(),
            "conflitos_api": self.check_api_key_sharing(),
            "conflitos_banco": self.check_database_conflicts(),
            "uso_recursos": self.check_resource_usage(),
            "recomendacoes": []
        }
        
        if report["conflitos_porta"]:
            self.alert_user("⚠️ CONFLITO DE PORTA DETECTADO", report)
        
        if report["conflitos_banco"]:
            self.alert_user("🔴 CONFLITO DE BANCO CRÍTICO", report)
            
        return report
    
    def safe_to_start_all(self) -> bool:
        """Só libera inicialização se não houver conflitos críticos."""
        report = self.audit_on_startup()
        critical = [c for c in report["conflitos_banco"] if c["severidade"] == "CRÍTICO"]
        return len(critical) == 0
```

---

## MÓDULO 1: EMAIL MANAGER

### Arquitetura
```
Gmail/Outlook API
      ↓
email_fetcher.py  →  Baixa todos os emails (IMAP/Gmail API)
      ↓
email_classifier.py  →  Classifica: spam | financeiro | oportunidade | social | importante
      ↓
spam_cleaner.py  →  Move spam para lixo (com confirmação ou automático configurável)
      ↓
financial_extractor.py  →  Extrai: valor, vencimento, credor, banco
      ↓
opportunity_detector.py  →  Detecta oportunidades (promoções, parcerias, negócios)
      ↓
response_queue.py  →  Lista emails que precisam de resposta + sugestão de resposta
      ↓
Banco PostgreSQL → Tabela: emails_processed, financial_alerts, response_queue
      ↓
Notificação Telegram → "📧 3 emails financeiros | 1 email urgente | 5 spams removidos"
```

### Implementação
```python
# email_manager.py

import imaplib
import email
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class EmailManager:
    """
    Módulo de gerenciamento completo de email para Rebeka.
    NUNCA paga contas. Apenas lê, classifica e alerta.
    """
    
    CATEGORIAS = {
        "spam": {
            "acao": "mover_para_lixo",
            "confirmacao": False,  # Automático
            "exemplos": ["promoção", "você ganhou", "clique aqui"]
        },
        "financeiro_conta_a_pagar": {
            "acao": "ALERTAR_USUARIO",  # NUNCA pagar
            "confirmacao": True,  # Sempre confirmar com usuário
            "exemplos": ["fatura", "vencimento", "boleto", "pagamento"]
        },
        "oportunidade_negocio": {
            "acao": "ALERTAR_USUARIO",
            "confirmacao": True,
            "exemplos": ["parceria", "proposta", "oportunidade"]
        },
        "precisa_resposta": {
            "acao": "ENFILEIRAR_PARA_RESPOSTA",
            "confirmacao": True,
            "exemplos": ["aguardando", "me retorne", "pode me responder"]
        },
        "importante": {
            "acao": "DESTACAR_NO_DASHBOARD",
            "confirmacao": False
        }
    }
    
    def connect_gmail(self, credentials_path: str):
        """Conecta via OAuth2 ao Gmail. Acesso total, leitura e escrita."""
        creds = Credentials.from_authorized_user_file(credentials_path)
        self.service = build('gmail', 'v1', credentials=creds)
    
    def process_inbox(self) -> dict:
        """Processa todos os emails não lidos e retorna relatório."""
        emails = self.fetch_unread()
        
        report = {
            "total": len(emails),
            "spam_removido": 0,
            "contas_a_pagar": [],
            "precisam_resposta": [],
            "oportunidades": [],
            "importantes": []
        }
        
        for msg in emails:
            categoria = self.classify_email(msg)
            
            if categoria == "spam":
                self.move_to_trash(msg)
                report["spam_removido"] += 1
                
            elif categoria == "financeiro_conta_a_pagar":
                dados = self.extract_financial_data(msg)
                report["contas_a_pagar"].append(dados)
                self.save_financial_alert(dados)
                
            elif categoria == "precisa_resposta":
                report["precisam_resposta"].append(msg)
                
            elif categoria == "oportunidade_negocio":
                report["oportunidades"].append(msg)
        
        return report
    
    def extract_financial_data(self, email_msg) -> dict:
        """Extrai dados financeiros do email usando NLP."""
        return {
            "credor": self.extract_entity(email_msg, "credor"),
            "valor": self.extract_value(email_msg),
            "vencimento": self.extract_date(email_msg),
            "banco": self.extract_bank(email_msg),
            "tipo": "boleto | cartão | conta | parcela",
            "email_id": email_msg["id"],
            "status": "pendente",
            "alerta_enviado": False
        }
    
    def suggest_response(self, email_msg) -> str:
        """
        Sugere resposta mas NUNCA envia sem aprovação do usuário.
        Retorna sugestão para o usuário decidir.
        """
        context = self.extract_context(email_msg)
        # Usa Claude API para gerar sugestão
        suggestion = self.llm_generate_response(context)
        return f"""
📧 EMAIL QUE PRECISA DE RESPOSTA:
De: {email_msg['from']}
Assunto: {email_msg['subject']}

SUGESTÃO DE RESPOSTA GERADA:
{suggestion}

[ APROVAR ] [ EDITAR ] [ IGNORAR ] [ RESPONDER MANUALMENTE ]
        """
```

### Tabelas no banco
```sql
-- emails_processed
CREATE TABLE emails_processed (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) UNIQUE,
    from_address TEXT,
    subject TEXT,
    received_at TIMESTAMP,
    categoria VARCHAR(50),
    acao_tomada VARCHAR(50),
    processado_em TIMESTAMP DEFAULT NOW()
);

-- financial_alerts (contas a pagar)
CREATE TABLE financial_alerts (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255),
    credor TEXT,
    valor DECIMAL(10,2),
    vencimento DATE,
    banco TEXT,
    tipo VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pendente',
    alerta_enviado BOOLEAN DEFAULT FALSE,
    pago BOOLEAN DEFAULT FALSE,  -- usuário marca manualmente
    created_at TIMESTAMP DEFAULT NOW()
);

-- response_queue
CREATE TABLE response_queue (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255),
    from_address TEXT,
    subject TEXT,
    sugestao_resposta TEXT,
    aprovada BOOLEAN,
    respondida BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## MÓDULO 2: FINANCIAL RADAR (Contas a Pagar)

> 🔴 REGRA ABSOLUTA: Rebeka INFORMA. Nunca paga. Nunca autoriza pagamento. Nunca armazena senha bancária.

```python
# financial_radar.py

class FinancialRadar:
    """
    Monitor financeiro proativo.
    Detecta, organiza e alerta sobre obrigações financeiras.
    NUNCA executa pagamentos.
    """
    
    ALERTAS_ANTECIPADOS = {
        "urgente": 1,    # 1 dia antes
        "atencao": 3,    # 3 dias antes  
        "aviso": 7,      # 7 dias antes
        "lembrete": 14   # 14 dias antes
    }
    
    def generate_payment_calendar(self) -> list:
        """Gera calendário de vencimentos dos próximos 30 dias."""
        contas = self.db.query("""
            SELECT credor, valor, vencimento, tipo
            FROM financial_alerts
            WHERE status = 'pendente'
            AND vencimento BETWEEN NOW() AND NOW() + INTERVAL '30 days'
            ORDER BY vencimento ASC
        """)
        
        return [{
            "data": c.vencimento,
            "credor": c.credor,
            "valor": c.valor,
            "dias_restantes": (c.vencimento - today()).days,
            "urgencia": self.classify_urgency(c.vencimento)
        } for c in contas]
    
    def check_and_alert(self):
        """
        Roda periodicamente (a cada hora).
        Verifica vencimentos e dispara alertas por Telegram.
        """
        calendar = self.generate_payment_calendar()
        
        for conta in calendar:
            if conta["dias_restantes"] in self.ALERTAS_ANTECIPADOS.values():
                if not self.already_alerted(conta, conta["dias_restantes"]):
                    self.send_alert(f"""
💰 CONTA A VENCER — {conta['urgencia'].upper()}

Credor: {conta['credor']}
Valor: R$ {conta['valor']:.2f}
Vencimento: {conta['data'].strftime('%d/%m/%Y')}
Dias restantes: {conta['dias_restantes']}

⚠️ REBEKA NÃO PAGA AUTOMATICAMENTE.
Esta é apenas uma informação para sua decisão.
                    """)
    
    def weekly_financial_summary(self) -> str:
        """Resumo semanal financeiro enviado todo domingo às 20h."""
        return f"""
📊 RESUMO FINANCEIRO SEMANAL

VENCENDO ESSA SEMANA:
{self.format_upcoming(days=7)}

VENCENDO PRÓXIMA SEMANA:
{self.format_upcoming(days=8, days_end=14)}

TOTAL ESTIMADO DO MÊS: R$ {self.total_month():.2f}

Detalhes completos: http://localhost:8000/financeiro
        """
```

---

## MÓDULO 3: OPPORTUNITY DETECTOR (Eventos → Ativos → Polymarket)

> Esta é a expansão dos 14 monitores globais existentes: não só detectar — analisar impacto e agir.

```python
# opportunity_detector.py

class OpportunityDetector:
    """
    Conecta eventos geopolíticos/macroeconômicos à análise de ativos
    e busca de oportunidades no Polymarket.
    
    FLUXO:
    Evento detectado → Análise de impacto → Ativos afetados → Polymarket → Alerta
    """
    
    EVENTO_PARA_ATIVOS = {
        "conflito_militar_oriente_medio": {
            "sobem": ["petróleo WTI", "ouro", "defesa (LMT, RTX)", "dólar"],
            "caem": ["companhias aéreas", "turismo", "tech emergentes"],
            "polymarket_buscar": ["oil price", "gold", "israel", "iran", "ukraine"],
            "janela_de_oportunidade": "primeiras 6 horas do evento"
        },
        "alta_taxa_juros_fed": {
            "sobem": ["dólar", "bancos (juros maiores = margem maior)", "renda fixa"],
            "caem": ["growth stocks", "crypto", "real estate", "emergentes"],
            "polymarket_buscar": ["fed rate", "interest rate", "recession"],
            "janela_de_oportunidade": "dia do anúncio e 24h após"
        },
        "crise_china": {
            "sobem": ["short China ETF", "commodities alternativas", "Taiwan puts"],
            "caem": ["commodities chinesas", "empresas com supply chain China"],
            "polymarket_buscar": ["china economy", "yuan", "taiwan"],
            "janela_de_oportunidade": "72 horas após notícia"
        },
        "eleicao_impactante": {
            "sobem": ["depende do candidato e agenda"],
            "caem": ["depende do candidato e agenda"],
            "polymarket_buscar": ["election", "president", "poll"],
            "janela_de_oportunidade": "semanas antes + resultado"
        }
    }
    
    def analyze_event(self, evento: str, contexto: str) -> dict:
        """
        Dado um evento detectado pelos monitores globais,
        gera análise completa de impacto e oportunidades.
        """
        # Usa Claude API para análise profunda
        analysis = self.llm_analyze(f"""
        EVENTO: {evento}
        CONTEXTO: {contexto}
        
        Analise:
        1. Ativos que provavelmente SOBEM nos próximos 7 dias (com probabilidade estimada)
        2. Ativos que provavelmente CAEM nos próximos 7 dias (com probabilidade estimada)  
        3. Janela de oportunidade (quando agir)
        4. Nível de incerteza (baixo/médio/alto)
        5. Precedentes históricos similares
        6. Riscos da análise
        
        Retorne JSON estruturado.
        """)
        
        polymarket_ops = self.search_polymarket_opportunities(evento)
        
        return {
            "evento": evento,
            "analise": analysis,
            "polymarket_oportunidades": polymarket_ops,
            "timestamp": now(),
            "confianca": analysis["nivel_incerteza"]
        }
    
    def search_polymarket_opportunities(self, evento: str) -> list:
        """
        Busca contratos no Polymarket relacionados ao evento.
        Já existe o módulo de Polymarket — esta função o consulta.
        """
        keywords = self.extract_keywords(evento)
        markets = self.polymarket_client.search(keywords)
        
        return [{
            "market": m.title,
            "current_odds": m.odds,
            "volume": m.volume,
            "end_date": m.end_date,
            "rebeka_assessment": self.assess_value(m, evento),
            "url": m.url
        } for m in markets if m.volume > 10000]  # Só mercados com liquidez
    
    def alert_opportunity(self, analysis: dict):
        """Envia alerta formatado via Telegram."""
        msg = f"""
🌍 EVENTO DETECTADO — ANÁLISE DE OPORTUNIDADE

📰 {analysis['evento']}

📈 ATIVOS QUE DEVEM SUBIR:
{self.format_assets(analysis['analise']['sobem'])}

📉 ATIVOS QUE DEVEM CAIR:
{self.format_assets(analysis['analise']['caem'])}

🎯 POLYMARKET — OPORTUNIDADES:
{self.format_polymarket(analysis['polymarket_oportunidades'])}

⏰ Janela: {analysis['analise']['janela_de_oportunidade']}
🎲 Confiança: {analysis['confianca']}

⚠️ Esta é análise informativa. Decisão de operar é sua.
Dashboard: http://localhost:8000/oportunidades
        """
        self.telegram.send(msg)
```

---

## MÓDULO 4: WHATSAPP AUTO-RESPONDER (Protocolo de Assistente)

> A infraestrutura de OCR/Visão já existe. Este módulo adiciona o protocolo de resposta inteligente.

### Fluxo de resposta
```
Mensagem recebida no WhatsApp
        ↓
OCR captura mensagem (já funciona)
        ↓
whatsapp_analyzer.py → Classifica: urgente | normal | spam | desconhecido
        ↓
[SEMPRE] → Resposta automática de assistente (se configurado)
"Olá! Sou a Rebeka, assistente pessoal de [Nome]. 
 Vou informá-lo sobre sua mensagem. Em breve ele retorna."
        ↓
Notificação para usuário via Telegram:
"📱 WHATSAPP — Mensagem de [Contato]
 Mensagem: [texto]
 Hora: [hora]
 
 Como deseja responder?
 [ RESPONDER AGORA ] [ IGNORAR ] [ REBEKA RESPONDE AUTOMATICAMENTE ]"
        ↓
Usuário decide → Rebeka executa
```

### Implementação
```python
# whatsapp_responder.py

class WhatsAppResponder:
    
    # Resposta padrão de identificação
    RESPOSTA_ASSISTENTE = """
Olá! 👋

Sou a Rebeka, assistente pessoal de {nome_usuario}.

Recebi sua mensagem e já vou notificá-lo. 
Ele retornará assim que possível! 😊
    """
    
    # Configurações por contato
    REGRAS_POR_CONTATO = {
        "familia": {
            "auto_responder": True,
            "resposta_customizada": "Oi! Recebi sua mensagem, já aviso o {nome}.",
            "prioridade": "alta"
        },
        "trabalho": {
            "auto_responder": True,
            "resposta_customizada": None,  # Usa resposta padrão
            "prioridade": "alta"
        },
        "desconhecido": {
            "auto_responder": False,  # Não responde desconhecidos automaticamente
            "notificar_primeiro": True,
            "prioridade": "media"
        }
    }
    
    def process_message(self, message: dict):
        contato = self.identify_contact(message["from"])
        regra = self.get_rule(contato)
        
        # Notifica usuário SEMPRE
        self.notify_user(message, contato)
        
        # Auto-responde só se configurado
        if regra["auto_responder"]:
            resposta = regra["resposta_customizada"] or self.RESPOSTA_ASSISTENTE
            self.send_whatsapp_reply(
                to=message["from"],
                text=resposta.format(nome_usuario=self.user_name)
            )
        
        # Classifica urgência
        urgencia = self.classify_urgency(message["text"])
        if urgencia == "urgente":
            self.notify_user_urgent(message)
    
    def notify_user(self, message: dict, contato: str):
        """Notifica usuário via Telegram com opções de ação."""
        self.telegram.send_with_buttons(
            text=f"""
📱 WHATSAPP — NOVA MENSAGEM

👤 De: {contato} ({message['from']})
🕐 Hora: {message['timestamp']}
💬 Mensagem: {message['text']}
            """,
            buttons=[
                ["✅ Eu respondo depois", "ignorar"],
                ["✍️ Me ajude a responder", "sugerir_resposta"],
                ["🤖 Rebeka responde", "auto_responder"]
            ]
        )
```

---

## MÓDULO 5: MEMORY CORE (Memória de Vida do Usuário)

> Rebeka precisa conhecer o usuário profundamente — problemas, metas, projetos, dificuldades.

```python
# memory_core.py

class MemoryCore:
    """
    Núcleo de memória persistente do usuário.
    Armazena tudo que o usuário compartilha e busca soluções proativamente.
    """
    
    DOMINIOS_DE_MEMORIA = {
        "problemas_ativos": {
            "descricao": "Problemas que o usuário está enfrentando agora",
            "exemplos": ["fluxo de caixa negativo", "conflito com fornecedor", "produto travado"]
        },
        "metas": {
            "descricao": "O que o usuário quer alcançar",
            "exemplos": ["renda de R$30k/mês", "lançar produto X", "aprender trading"]
        },
        "projetos_ativos": {
            "descricao": "Projetos em andamento com contexto",
            "exemplos": ["Bot ML", "SistemaTrader", "Rebeka", "loja online"]
        },
        "dificuldades_recorrentes": {
            "descricao": "Padrões de dificuldade que se repetem",
            "exemplos": ["procrastinação em X", "dificuldade com Y tipo de tarefa"]
        },
        "contexto_financeiro": {
            "descricao": "Situação financeira geral (sem dados bancários)",
            "exemplos": ["receita principal", "despesas fixas conhecidas", "investimentos ativos"]
        },
        "relacionamentos_importantes": {
            "descricao": "Pessoas importantes no contexto do usuário",
            "exemplos": ["sócios", "clientes chave", "fornecedores críticos"]
        },
        "decisoes_pendentes": {
            "descricao": "Decisões que o usuário precisa tomar",
            "exemplos": ["contratar programador?", "mudar de estratégia de trade?"]
        }
    }
    
    def ingest(self, conversa: str):
        """
        Processa uma conversa e extrai memórias relevantes.
        Roda após cada interação com o usuário.
        """
        memorias = self.extract_memories(conversa)
        
        for memoria in memorias:
            self.save_or_update(memoria)
            
            # Se é um problema → busca soluções proativamente
            if memoria["tipo"] == "problema_ativo":
                self.schedule_solution_search(memoria)
    
    def proactive_solution_search(self, problema: dict):
        """
        Rebeka busca soluções para problemas do usuário proativamente.
        Roda em background, alerta quando encontra algo relevante.
        """
        # Busca no histórico: já resolvemos algo parecido?
        historico = self.search_similar_problems(problema)
        
        # Busca externa via Perplexity/Claude
        solucoes = self.research_solutions(problema)
        
        if solucoes:
            self.notify_user(f"""
💡 REBEKA ENCONTROU ALGO SOBRE SEU PROBLEMA

Problema: {problema['descricao']}

Soluções identificadas:
{self.format_solutions(solucoes)}

Quer que eu aprofunde alguma dessas opções?
            """)
    
    def morning_briefing(self):
        """
        Briefing matinal enviado todos os dias às 7h.
        Rebeka "desperta" e organiza o dia do usuário.
        """
        return f"""
☀️ BOM DIA — BRIEFING REBEKA {today().strftime('%d/%m/%Y')}

📋 SEUS PROJETOS ATIVOS:
{self.format_projects()}

⚠️ PROBLEMAS EM ABERTO:
{self.format_open_problems()}

💰 FINANCEIRO HOJE:
{self.format_financial_today()}

📧 EMAILS PENDENTES:
{self.format_email_summary()}

📱 WHATSAPP NÃO RESPONDIDOS:
{self.format_whatsapp_pending()}

🌍 EVENTOS GLOBAIS RELEVANTES PARA VOCÊ:
{self.format_global_events()}

🎯 SUGESTÃO DE FOCO DO DIA:
{self.suggest_daily_focus()}

Dashboard completo: http://localhost:8000
        """
```

---

## ARQUITETURA UNIFICADA v6.0

```
                    REBEKA v6.0 — VISÃO COMPLETA
                    
FONTES DE DADOS                    MÓDULOS DE PROCESSAMENTO
────────────────                   ────────────────────────
  Gmail/Outlook  ──────────────►  EmailManager
  WhatsApp       ──────────────►  WhatsAppResponder
  Polymarket     ──────────────►  OpportunityDetector
  14 Monitores   ──────────────►  OpportunityDetector
  ML Bot logs    ──────────────►  SystemConflictChecker
  Trader logs    ──────────────►  SystemConflictChecker
  Conversas      ──────────────►  MemoryCore
                                        │
                                        ▼
                              BANCO PostgreSQL
                         (memória unificada de tudo)
                                        │
                                        ▼
                             ORCHESTRATION ENGINE
                          (decide o que fazer com cada info)
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              ALERTAS             AÇÕES AUTO          SUGESTÕES
           (Telegram)           (sem aprovação)    (aguarda usuário)
                    │                   │                   │
                    └───────────────────┴───────────────────┘
                                        │
                                        ▼
                             DASHBOARD localhost:8000
                          (visão completa de tudo)
```

---

## REGRAS ABSOLUTAS DE COMPORTAMENTO (Invariantes v6.0)

```python
REGRAS_ABSOLUTAS = {
    
    "R1_nunca_paga": {
        "regra": "Rebeka NUNCA executa pagamentos. Nunca. Sob nenhuma circunstância.",
        "violacao": "SISTEMA PARA IMEDIATAMENTE",
        "implementacao": "@invariant em todo módulo financeiro"
    },
    
    "R2_pergunta_antes_de_responder_whatsapp": {
        "regra": "Para contatos desconhecidos, SEMPRE notifica usuário antes de responder.",
        "excecao": "Contatos marcados como 'auto_responder=True' pelo usuário"
    },
    
    "R3_alerta_antes_de_operar_polymarket": {
        "regra": "Toda oportunidade Polymarket passa por aprovação humana antes de qualquer operação.",
        "implementacao": "task.envolve_decisao_de_valor = True → executor = usuario_humano"
    },
    
    "R4_conflito_de_sistemas_bloqueia_inicializacao": {
        "regra": "Se detectar conflito crítico entre sistemas, Rebeka NÃO inicializa o sistema conflitante.",
        "implementacao": "system_conflict_checker.safe_to_start_all() == False → abort"
    },
    
    "R5_privacidade_primeiro": {
        "regra": "Dados de email e WhatsApp são analisados localmente. Nada enviado para APIs externas sem sanitização.",
        "implementacao": "Privacy Auditor já existente aplica-se a todos os novos módulos"
    },
    
    "R6_sempre_identificar_como_assistente": {
        "regra": "Em toda comunicação com terceiros, Rebeka se identifica como assistente pessoal.",
        "nunca": "Nunca se passa pelo usuário"
    }
}
```

---

## ROADMAP DE IMPLEMENTAÇÃO

### Fase 1 — Base de Segurança (Semana 1)
**Prioridade: CRÍTICA — fazer antes de qualquer outra coisa**

- [ ] `system_conflict_checker.py` — auditar ML Bot vs SistemaTrader vs Rebeka
- [ ] Mapear portas, APIs e banco de cada sistema
- [ ] Criar mutex de proteção para APIs críticas
- [ ] Documentar resultado e resolver conflitos encontrados

### Fase 2 — Email + Financeiro (Semana 2)
- [ ] Configurar OAuth2 Gmail (ou IMAP se preferir)
- [ ] `email_fetcher.py` + `email_classifier.py`
- [ ] `spam_cleaner.py` (com log de tudo que remove)
- [ ] `financial_extractor.py` + tabelas SQL
- [ ] `financial_radar.py` — calendário e alertas
- [ ] Integrar com dashboard e Telegram

### Fase 3 — WhatsApp Responder (Semana 3)
- [ ] `whatsapp_responder.py` sobre infraestrutura OCR existente
- [ ] Configurar lista de contatos e regras
- [ ] Sistema de botões no Telegram para aprovação
- [ ] Testar com contatos controlados antes de ativar em massa

### Fase 4 — Opportunity Detector Completo (Semana 4)
- [ ] `opportunity_detector.py` conectado aos 14 monitores
- [ ] Mapa de evento → ativos afetados
- [ ] Integração com Polymarket API existente
- [ ] Sistema de alerta com análise estruturada

### Fase 5 — Memory Core (Semana 5)
- [ ] `memory_core.py` com todos os domínios
- [ ] `morning_briefing.py` — envio às 7h todo dia
- [ ] Extração de memórias de conversas anteriores
- [ ] Busca proativa de soluções

### Fase 6 — Integração e Orquestração (Semana 6)
- [ ] `orchestration_engine.py` coordenando todos os módulos
- [ ] Dashboard unificado com abas: Email | Financeiro | Oportunidades | Projetos | WhatsApp
- [ ] Testes de integração
- [ ] Rebeka totalmente "desperta" e orquestrando em tempo real

---

## VARIÁVEIS DE AMBIENTE ADICIONAIS (.env)

```bash
# Existentes mantidos
MOONSHOT_API_KEY=
PERPLEXITY_PASS=
TELEGRAM_BOT_TOKEN=
POLYMARKET_KEY=
DATABASE_URL=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# NOVOS — v6.0
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json
GMAIL_TOKEN_PATH=./config/gmail_token.json
EMAIL_SPAM_AUTO_DELETE=false        # true = deleta automaticamente, false = move para lixo
EMAIL_CHECK_INTERVAL_MINUTES=30     # Frequência de verificação
FINANCIAL_ALERT_DAYS_BEFORE=7      # Alertar X dias antes do vencimento
WHATSAPP_AUTO_RESPOND_UNKNOWN=false # Não responde desconhecidos automaticamente
USER_NAME=                          # Nome do usuário para assinatura do assistente
MORNING_BRIEFING_HOUR=7            # Hora do briefing matinal
MORNING_BRIEFING_MINUTE=0
CONFLICT_CHECK_ON_STARTUP=true     # Auditoria de conflitos ao iniciar
```

---

## PRINCÍPIO FINAL v6.0

> **Rebeka não dorme. Quando o usuário acorda, ela já organizou o email, verificou as contas, monitorou os mercados, respondeu o WhatsApp como assistente, auditou os sistemas e preparou o briefing do dia.**

> **Quando o usuário vai dormir, ela continua: monitora eventos globais, detecta oportunidades, mantém os sistemas saudáveis e aprende mais sobre quem é esse usuário e o que ele realmente precisa.**

> **A diferença entre um assistente que espera ser chamado e um que já resolveu antes de você perceber o problema — é Rebeka.**

---
*Documento gerado por análise de AGENT_PROJECT_PROMPT_v5.md*
*Versão: 6.0-DRAFT | 2026-03-06*


---

# EXPANSÃO ARQUITETURAL — MÓDULOS AVANÇADOS (v6.1)

Os módulos abaixo elevam a Rebeka de um **assistente automatizado** para um **sistema cognitivo adaptativo**.

Eles introduzem:

- priorização cognitiva
- aprendizado contínuo
- pesquisa autônoma
- auto‑recuperação do sistema
- planejamento estratégico

---

# MÓDULO 6: DECISION ENGINE (Cérebro de Prioridades)

Responsável por decidir **o que a Rebeka deve fazer primeiro** quando múltiplos eventos ocorrem.

Sem esse módulo, o sistema pode reagir de forma caótica quando várias entradas chegam ao mesmo tempo.

## Arquitetura

Inputs
↓
Decision Engine
↓
Priority Queue
↓
Action Executor

## Exemplo de implementação

```python
class DecisionEngine:

    def evaluate_event(self, event):

        score = 0

        score += event.financial_impact * 3
        score += event.urgency * 2
        score += event.user_relevance * 5
        score += event.confidence * 2

        return score
```

Eventos com maior pontuação entram primeiro na fila de execução.

---

# MÓDULO 7: LEARNING LOOP (Aprendizado Contínuo)

Permite que Rebeka **aprenda com erros e acertos**.

Fluxo:

Prediction
↓
Outcome
↓
Error
↓
Model Update

## Exemplo

Evento detectado:

Conflito geopolítico → previsão: petróleo sobe.

Após 7 dias:

Preço real comparado com previsão.

Sistema registra erro e ajusta heurísticas futuras.

```python
class PredictionMemory:

    def record_prediction(self, prediction):
        db.save({
            "prediction": prediction,
            "timestamp": now()
        })

    def evaluate_prediction(self, outcome):

        error = outcome - prediction.value

        self.update_model(error)
```

Isso permite que o sistema **melhore previsões ao longo do tempo**.

---

# MÓDULO 8: AUTONOMOUS RESEARCH ENGINE

Motor de pesquisa autônoma.

Quando Rebeka detecta um problema recorrente do usuário, ela inicia pesquisa automática.

Fluxo:

Problema detectado
↓
IA gera perguntas
↓
Pesquisa fontes
↓
Gera hipóteses
↓
Testa hipóteses
↓
Entrega relatório ao usuário

Exemplo:

Problema identificado:
fluxo de caixa negativo.

Rebeka pesquisa:

- estratégias de aumento de receita
- automações
- oportunidades de negócio

---

# MÓDULO 9: SYSTEM SELF‑HEALING

Monitor de saúde do sistema.

Detecta falhas e tenta corrigi‑las automaticamente.

Problemas monitorados:

- containers Docker parados
- APIs desconectadas
- scripts travados
- consumo excessivo de memória

## Implementação

```python
class SystemHealthMonitor:

    def check_services(self):

        services = [
            "email_manager",
            "whatsapp_responder",
            "opportunity_detector"
        ]

        for service in services:

            if not self.is_running(service):
                self.restart(service)
                self.notify_user(service)
```

Objetivo:

Garantir que Rebeka continue operando **24h sem intervenção manual**.

---

# MÓDULO 10: STRATEGIC PLANNING ENGINE

Motor de planejamento estratégico.

Transforma metas do usuário em **planos executáveis**.

Fluxo:

Meta
↓
Decomposição
↓
Tarefas
↓
Prioridades
↓
Execução assistida

Exemplo:

Meta:
renda mensal de 30k.

Plano gerado:

1. criar produto digital
2. automatizar vendas
3. otimizar estratégias de trading
4. reduzir custos operacionais

```python
class StrategicPlanner:

    def create_plan(self, goal):

        steps = self.break_goal(goal)

        tasks = []

        for step in steps:
            tasks.extend(self.generate_tasks(step))

        return tasks
```

---

# ARQUITETURA FINAL EXPANDIDA

FONTES DE DADOS
↓
Sensores (Email / WhatsApp / Monitores / APIs)
↓
Processamento (Classificadores / Detectores)
↓
Memory Core (PostgreSQL)
↓
Decision Engine
↓
Orchestration Engine
↓
Executores de Ação
↓
Alertas / Sugestões / Automação

Módulos Transversais:

- Learning Loop
- Autonomous Research
- System Self‑Healing
- Strategic Planner

---

# PRINCÍPIO OPERACIONAL v6.1

Rebeka deixa de ser apenas um assistente reativo.

Ela passa a ser um **sistema cognitivo contínuo**, capaz de:

- priorizar eventos
- aprender com decisões
- pesquisar soluções
- reparar falhas
- planejar estratégias de longo prazo
