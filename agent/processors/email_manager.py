# email_manager.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 2 - Gerenciamento de Email (integrado ao Vault existente)

import imaplib
import re
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import email as email_module
from email import policy
from email.parser import BytesParser

logger = logging.getLogger(__name__)


class EmailCategory(Enum):
    SPAM = "spam"
    FINANCEIRO_CONTA_A_PAGAR = "financeiro_conta_a_pagar"
    OPORTUNIDADE = "oportunidade_negocio"
    PRECISA_RESPOSTA = "precisa_resposta"
    IMPORTANTE = "importante"
    NORMAL = "normal"


@dataclass
class EmailMessage:
    """Representa um email processado."""
    id: str
    from_address: str
    subject: str
    body: str
    received_at: datetime
    categoria: EmailCategory
    raw_email: Any


@dataclass
class FinancialAlert:
    """Dados financeiros extraídos de um email."""
    creditor: str
    valor: float
    vencimento: datetime
    banco: str
    tipo: str
    email_id: str
    status: str = "pendente"


def get_gmail_credentials() -> Optional[Dict[str, str]]:
    """
    Obtém credenciais do Gmail usando o sistema de OAuth existente.
    Tenta primeiro usar token do Vault, depois OAuth próprio.
    """
    # Tentar carregar do Vault
    try:
        vault_path = os.path.join(os.path.dirname(__file__), "..", "local", "vault", "secrets.enc")
        if os.path.exists(vault_path):
            # Tentar usar OAuth token armazenado
            # Por agora, retorna None para usar OAuth flow
            pass
    except:
        pass
    
    # Tentar variável de ambiente para IMAP (app password)
    email_user = os.getenv("GMAIL_IMAP_USER")
    email_pass = os.getenv("GMAIL_IMAP_PASSWORD")
    
    if email_user and email_pass:
        return {
            "type": "imap",
            "email": email_user,
            "password": email_pass
        }
    
    return None


class EmailCategory(Enum):
    SPAM = "spam"
    FINANCEIRO_CONTA_A_PAGAR = "financeiro_conta_a_pagar"
    OPORTUNIDADE = "oportunidade_negocio"
    PRECISA_RESPOSTA = "precisa_resposta"
    IMPORTANTE = "importante"
    NORMAL = "normal"


@dataclass
class EmailMessage:
    """Representa um email processado."""
    id: str
    from_address: str
    subject: str
    body: str
    received_at: datetime
    categoria: EmailCategory
    raw_email: Any


@dataclass
class FinancialAlert:
    """Dados financeiros extraídos de um email."""
    creditor: str
    valor: float
    vencimento: datetime
    banco: str
    tipo: str  # boleto, cartão, conta, parcela
    email_id: str
    status: str = "pendente"


class EmailManager:
    """
    Módulo de gerenciamento de email para Rebeka.
    NUNCA paga contas. Apenas lê, classifica e alerta.
    
    Suporta: Gmail (OAuth2) e IMAP
    """
    
    # Palavras-chave para classificação
    SPAM_KEYWORDS = [
        "promoção", "você ganhou", "clique aqui", "gratuito", "urgente",
        "comprar agora", "oferta imperdível", "loteria", "prêmio",
        "ganhou", "prêmio", "bitcoin", "criptomoeda", "work from home"
    ]
    
    FINANCEIRO_KEYWORDS = [
        "fatura", "vencimento", "boleto", "pagamento", "conta",
        "parcela", "cobrança", "débitos", "valor a pagar",
        " sua fatura", "comprovante de pagamento", "título",
        "invoice", "bill", "payment due"
    ]
    
    RESPOSTA_KEYWORDS = [
        "aguardo", "me retorne", "pode me responder", "preciso de resposta",
        "waiting for", "please reply", "feedback", "em resposta"
    ]
    
    OPORTUNIDADE_KEYWORDS = [
        "parceria", "proposta", "oportunidade", "proposta comercial",
        "business proposal", "partnership", "collaboration", "investimento"
    ]
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
        self.service = None
        
    def connect_gmail_oauth(self, credentials_path: str, token_path: str) -> bool:
        """
        Conecta ao Gmail via OAuth2.
        Requer credentials.json e token.json do Google Cloud Console.
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds = Credentials.from_authorized_user_file(token_path)
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Conectado ao Gmail via OAuth2")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar Gmail OAuth2: {e}")
            return False
    
    def connect_imap(self, email: str, password: str, imap_server: str = "imap.gmail.com") -> bool:
        """Conecta via IMAP (precisa de app password para Gmail)."""
        try:
            self.connection = imaplib.IMAP4_SSL(imap_server)
            self.connection.login(email, password)
            logger.info(f"Conectado via IMAP: {email}")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar IMAP: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do servidor de email."""
        if self.connection:
            try:
                self.connection.logout()
                logger.info("Desconectado do servidor de email")
            except:
                pass
    
    def fetch_unread_emails(self, limit: int = 50) -> List[EmailMessage]:
        """Busca emails não lidos."""
        emails = []
        
        if self.service:
            # Usando Gmail API
            try:
                results = self.service.users().messages().list(
                    userId='me',
                    q='is:unread',
                    maxResults=limit
                ).execute()
                
                messages = results.get('messages', [])
                for msg in messages:
                    email_data = self.service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    
                    email_msg = self._parse_gmail_message(email_data)
                    if email_msg:
                        emails.append(email_msg)
            except Exception as e:
                logger.error(f"Erro ao buscar emails: {e}")
                
        elif self.connection:
            # Usando IMAP
            try:
                self.connection.select('INBOX')
                typ, data = self.connection.search(None, 'UNSEEN')
                email_ids = data[0].split()
                
                for email_id in email_ids[:limit]:
                    typ, msg_data = self.connection.fetch(email_id, '(RFC822)')
                    email_msg = self._parse_imap_message(msg_data)
                    if email_msg:
                        emails.append(email_msg)
            except Exception as e:
                logger.error(f"Erro ao buscar emails IMAP: {e}")
        
        return emails
    
    def _parse_gmail_message(self, msg_data: Dict) -> Optional[EmailMessage]:
        """Parseia email da API do Gmail."""
        try:
            headers = msg_data.get('payload', {}).get('headers', {})
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extrair body
            body = ""
            parts = msg_data.get('payload', {}).get('parts', [])
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    body = part.get('data', '')
                    break
            
            return EmailMessage(
                id=msg_data['id'],
                from_address=from_addr,
                subject=subject,
                body=body,
                received_at=datetime.now(),
                categoria=EmailCategory.NORMAL,
                raw_email=msg_data
            )
        except Exception as e:
            logger.error(f"Erro ao parsear email Gmail: {e}")
            return None
    
    def _parse_imap_message(self, msg_data) -> Optional[EmailMessage]:
        """Parseia email via IMAP."""
        try:
            msg = email.message_from_bytes(msg_data[0][1])
            
            return EmailMessage(
                id=msg['Message-ID'] or "",
                from_address=msg['From'],
                subject=msg['Subject'],
                body=self._get_email_body(msg),
                received_at=email.utils.parsedate_to_datetime(msg['Date']),
                categoria=EmailCategory.NORMAL,
                raw_email=msg
            )
        except Exception as e:
            logger.error(f"Erro ao parsear email IMAP: {e}")
            return None
    
    def _get_email_body(self, msg) -> str:
        """Extrai o corpo do email."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True)
                    break
        else:
            body = msg.get_payload(decode=True)
        return body if body else ""
    
    def classify_email(self, email_msg: EmailMessage) -> EmailCategory:
        """Classifica o email em uma categoria."""
        text = f"{email_msg.subject} {email_msg.body}".lower()
        
        # Verificar spam primeiro
        if any(kw in text for kw in self.SPAM_KEYWORDS):
            return EmailCategory.SPAM
        
        # Verificar financeiro
        if any(kw in text for kw in self.FINANCEIRO_KEYWORDS):
            return EmailCategory.FINANCEIRO_CONTA_A_PAGAR
        
        # Verificar oportunidade
        if any(kw in text for kw in self.OPORTUNIDADE_KEYWORDS):
            return EmailCategory.OPORTUNIDADE
        
        # Verifica se precisa resposta
        if any(kw in text for kw in self.RESPOSTA_KEYWORDS):
            return EmailCategory.PRECISA_RESPOSTA
        
        return EmailCategory.NORMAL
    
    def extract_financial_data(self, email_msg: EmailMessage) -> Optional[FinancialAlert]:
        """Extrai dados financeiros do email."""
        text = f"{email_msg.subject} {email_msg.body}"
        
        # Extrair valor
        valor = self._extract_value(text)
        if not valor:
            return None
            
        # Extrair credor
        creditor = self._extract_creditor(email_msg.from_address, text)
        
        # Extrair vencimento
        vencimento = self._extract_due_date(text)
        
        # Extrair banco
        banco = self._extract_bank(text)
        
        # Determinar tipo
        tipo = self._determine_type(text)
        
        return FinancialAlert(
            creditor=creditor,
            valor=valor,
            vencimento=vencimento,
            banco=banco,
            tipo=tipo,
            email_id=email_msg.id
        )
    
    def _extract_value(self, text: str) -> Optional[float]:
        """Extrai valor monetário do texto."""
        # Padrões: R$ 1.234,56 ou $1234.56
        patterns = [
            r'R\$\s?([\d.,]+)',
            r'\$\s?([\d.,]+)',
            r'USD\s?([\d.,]+)',
            r'€\s?([\d.,]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value_str = match.group(1).replace(',', '.')
                try:
                    return float(value_str)
                except:
                    pass
        return None
    
    def _extract_creditor(self, from_addr: str, text: str) -> str:
        """Extrai o nome do credor."""
        # Do endereço de email
        if '<' in from_addr:
            return from_addr.split('<')[0].strip()
        
        # De palavras-chave no texto
        keywords = ["de ", "enviado por ", "from "]
        for kw in keywords:
            if kw in text.lower():
                idx = text.lower().find(kw) + len(kw)
                return text[idx:idx+50].strip()
        
        return from_addr
    
    def _extract_due_date(self, text: str) -> datetime:
        """Extrai data de vencimento."""
        # Tentar encontrar datas no texto
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{1,2})/(\d{1,2})',
            r'vencimento.*?(\d{1,2})[/-](\d{1,2})'
        ]
        
        today = datetime.now()
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    day = int(groups[0])
                    month = int(groups[1])
                    year = int(groups[2]) if len(groups) == 3 else today.year
                    try:
                        return datetime(year, month, day)
                    except:
                        pass
        
        # Default: 30 dias
        return today + timedelta(days=30)
    
    def _extract_bank(self, text: str) -> str:
        """Extrai nome do banco."""
        bancos = ["itau", "bradesco", "santander", "caixa", "bb", "nubank", "inter", "safe", "bank"]
        text_lower = text.lower()
        
        for banco in bancos:
            if banco in text_lower:
                return banco.title()
        
        return "Não identificado"
    
    def _determine_type(self, text: str) -> str:
        """Determina o tipo de conta."""
        text_lower = text.lower()
        
        if "fatura" in text_lower or "cartão" in text_lower:
            return "cartão"
        elif "boleto" in text_lower:
            return "boleto"
        elif "conta" in text_lower and ("luz" in text_lower or "água" in text_lower or "internet" in text_lower):
            return "conta"
        elif "parcela" in text_lower:
            return "parcela"
        
        return "outros"
    
    def move_to_trash(self, email_id: str) -> bool:
        """Move email para lixo."""
        try:
            if self.service:
                self.service.users().messages().trash(
                    userId='me',
                    id=email_id
                ).execute()
                return True
            elif self.connection:
                self.connection.move(email_id, '[Gmail]/Lixeira')
                return True
        except Exception as e:
            logger.error(f"Erro ao mover para lixo: {e}")
        return False
    
    def mark_as_read(self, email_id: str) -> bool:
        """Marca email como lido."""
        try:
            if self.service:
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                return True
        except Exception as e:
            logger.error(f"Erro ao marcar como lido: {e}")
        return False
    
    def process_inbox(self) -> Dict[str, Any]:
        """
        Processa todos os emails não lidos.
        Retorna relatório completo.
        """
        emails = self.fetch_unread_emails(limit=50)
        
        report = {
            "total_processados": len(emails),
            "spam_removido": 0,
            "contas_a_pagar": [],
            "precisam_resposta": [],
            "oportunidades": [],
            "importantes": [],
            "erros": []
        }
        
        for email_msg in emails:
            try:
                # Classificar
                categoria = self.classify_email(email_msg)
                email_msg.categoria = categoria
                
                if categoria == EmailCategory.SPAM:
                    self.move_to_trash(email_msg.id)
                    report["spam_removido"] += 1
                    
                elif categoria == EmailCategory.FINANCEIRO_CONTA_A_PAGAR:
                    financial_data = self.extract_financial_data(email_msg)
                    if financial_data:
                        report["contas_a_pagar"].append({
                            "email_id": email_msg.id,
                            "from": email_msg.from_address,
                            "subject": email_msg.subject,
                            **financial_data.__dict__
                        })
                    else:
                        report["contas_a_pagar"].append({
                            "email_id": email_msg.id,
                            "from": email_msg.from_address,
                            "subject": email_msg.subject
                        })
                        
                elif categoria == EmailCategory.PRECISA_RESPOSTA:
                    report["precisam_resposta"].append({
                        "email_id": email_msg.id,
                        "from": email_msg.from_address,
                        "subject": email_msg.subject
                    })
                    
                elif categoria == EmailCategory.OPORTUNIDADE:
                    report["oportunidades"].append({
                        "email_id": email_msg.id,
                        "from": email_msg.from_address,
                        "subject": email_msg.subject
                    })
                
                # Marcar como lido
                self.mark_as_read(email_msg.id)
                
            except Exception as e:
                report["erros"].append({
                    "email_id": email_msg.id,
                    "erro": str(e)
                })
        
        return report


def create_email_manager(config: Dict[str, Any]) -> EmailManager:
    """Factory para criar EmailManager."""
    return EmailManager(config)


if __name__ == "__main__":
    # Teste básico
    config = {
        "type": "imap",
        "email": "test@example.com",
        "password": "password"
    }
    manager = EmailManager(config)
    print("Email Manager criado com sucesso!")
