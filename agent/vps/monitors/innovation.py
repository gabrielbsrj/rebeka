# agent/vps/monitors/innovation.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Criação inicial — monitor de inovação, patentes e pesquisas
#
# IMPACTO GÊMEO VPS: Coleta sinais de inovação tecnológica para antecipação de tendências
# IMPACTO GÊMEO LOCAL: Nenhum — sinais sincronizam para contexto global

"""
Innovation Monitor (VPS).

INTENÇÃO: Monitora inovação tecnológica através de patentes, aprovações
regulatórias e pesquisas científicas.

Domínios:
- Patentes (USPTO)
- Aprovações FDA (drogas, dispositivos)
- Papers científicos (arXiv)
- Registros regulatórios

Fontes:
- PatentsView API (USPTO)
- FDA API
- arXiv RSS
- ClinicalTrials.gov
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import feedparser

import httpx

from memory.causal_bank import CausalBank
from vps.monitors.base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class InnovationMonitor(BaseMonitor):
    """
    Monitor de Inovação Tecnológica.
    
    INTENÇÃO: Patentes e pesquisas são indicadores antecipados
    de tendências tecnológicas futuras.
    """
    
    DOMAIN = "innovation"
    UPDATE_INTERVAL_SECONDS = 7200
    
    COMPANIES = ["Apple", "Tesla", "Google", "Microsoft", "Amazon", "NVIDIA", "Meta", "OpenAI"]
    
    HIGH_RELEVANCE_KEYWORDS = [
        "FDA approval", "breakthrough therapy", "patent granted",
        "quantum computing", "fusion", "breakthrough",
        "AI model", "large language model", "autonomous",
    ]
    
    MEDIUM_RELEVANCE_KEYWORDS = [
        "patent", "research", "study", "clinical trial",
        "algorithm", "machine learning", "battery technology",
        "semiconductor", "chip", "processor",
    ]
    
    ARXIV_CATEGORIES = [
        "cs.AI", "cs.LG", "cs.CL", "cs.CV",
        "physics.app-ph", "cond-mat.mes-hall",
    ]
    
    def __init__(self, causal_bank: CausalBank, poll_interval: int = 7200):
        super().__init__(causal_bank, poll_interval)
        self.client = httpx.Client(timeout=30.0)
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        raw_items = []
        
        patents = self._fetch_patents()
        raw_items.extend(patents)
        
        fda_approvals = self._fetch_fda_approvals()
        raw_items.extend(fda_approvals)
        
        papers = self._fetch_arxiv_papers()
        raw_items.extend(papers)
        
        logger.info(f"Innovation: coletou {len(raw_items)} itens")
        return raw_items
    
    def _fetch_patents(self) -> List[Dict]:
        items = []
        
        for company in self.COMPANIES:
            try:
                url = "https://api.patentsview.org/patents/query"
                query = {
                    "q": {"_text_any": {"patent_abstract": company}},
                    "f": ["patent_number", "patent_title", "patent_abstract", "patent_date"],
                    "o": {"per_page": 10},
                }
                
                response = self.client.post(url, json=query)
                if response.status_code == 200:
                    data = response.json()
                    for patent in data.get("patents", []):
                        items.append({
                            "type": "patent",
                            "company": company,
                            "patent_number": patent.get("patent_number"),
                            "title": patent.get("patent_title"),
                            "abstract": patent.get("patent_abstract"),
                            "date": patent.get("patent_date"),
                        })
            except Exception as e:
                logger.warning(f"Erro buscando patentes para {company}: {e}")
        
        return items
    
    def _fetch_fda_approvals(self) -> List[Dict]:
        items = []
        
        try:
            url = "https://api.fda.gov/drug/approval.json"
            params = {
                "search": "action_date:[20240101 TO 20251231]",
                "limit": 10,
                "sort": "action_date:desc",
            }
            
            response = self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for result in data.get("results", []):
                    items.append({
                        "type": "fda_approval",
                        "drug_name": result.get("drug_name"),
                        "application_number": result.get("application_number"),
                        "action_date": result.get("action_date"),
                        "action_type": result.get("action_type"),
                        "sponsor": result.get("sponsor_name"),
                    })
        except Exception as e:
            logger.warning(f"Erro buscando aprovações FDA: {e}")
        
        return items
    
    def _fetch_arxiv_papers(self) -> List[Dict]:
        items = []
        
        for category in self.ARXIV_CATEGORIES[:3]:
            try:
                url = f"http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"cat:{category}",
                    "max_results": 5,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }
                
                response = self.client.get(url, params=params)
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    for entry in feed.entries:
                        items.append({
                            "type": "paper",
                            "category": category,
                            "title": entry.title,
                            "summary": entry.summary[:500],
                            "published": entry.published,
                            "url": entry.link,
                        })
            except Exception as e:
                logger.warning(f"Erro buscando papers arXiv {category}: {e}")
        
        return items
    
    def map_to_signal(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        item_type = raw_item.get("type")
        
        if item_type == "patent":
            return self._map_patent_to_signal(raw_item)
        elif item_type == "fda_approval":
            return self._map_fda_to_signal(raw_item)
        elif item_type == "paper":
            return self._map_paper_to_signal(raw_item)
        
        return None
    
    def _map_patent_to_signal(self, patent: Dict) -> Optional[Dict]:
        title = patent.get("title", "")
        abstract = patent.get("abstract", "")
        company = patent.get("company", "")
        combined = f"{title} {abstract}".lower()
        
        matches = sum(1 for kw in self.HIGH_RELEVANCE_KEYWORDS if kw in combined)
        if matches > 0:
            relevance = min(0.9, 0.5 + matches * 0.1)
        else:
            matches = sum(1 for kw in self.MEDIUM_RELEVANCE_KEYWORDS if kw in combined)
            relevance = min(0.6, 0.3 + matches * 0.1)
        
        if relevance < 0.3:
            return None
        
        return {
            "domain": self.DOMAIN,
            "type": "patent",
            "source": "USPTO",
            "title": f"[{company}] {title[:100]}",
            "content": abstract[:300] if abstract else title,
            "raw_data": patent,
            "relevance_score": relevance,
            "metadata": {
                "company": company,
                "patent_number": patent.get("patent_number"),
                "date": patent.get("date"),
            }
        }
    
    def _map_fda_to_signal(self, fda_item: Dict) -> Optional[Dict]:
        drug_name = fda_item.get("drug_name", "")
        action_type = fda_item.get("action_type", "")
        
        relevance = 0.9
        
        title = f"FDA: {action_type} - {drug_name}"
        content = f"Aprovação FDA: {drug_name}. Tipo: {action_type}."
        
        return {
            "domain": self.DOMAIN,
            "type": "fda_approval",
            "source": "FDA",
            "title": title,
            "content": content,
            "raw_data": fda_item,
            "relevance_score": relevance,
            "metadata": {
                "drug_name": drug_name,
                "action_type": action_type,
                "application_number": fda_item.get("application_number"),
            }
        }
    
    def _map_paper_to_signal(self, paper: Dict) -> Optional[Dict]:
        title = paper.get("title", "")
        summary = paper.get("summary", "")
        combined = f"{title} {summary}".lower()
        
        matches = sum(1 for kw in self.HIGH_RELEVANCE_KEYWORDS if kw in combined)
        if matches > 0:
            relevance = min(0.8, 0.4 + matches * 0.1)
        else:
            matches = sum(1 for kw in self.MEDIUM_RELEVANCE_KEYWORDS if kw in combined)
            relevance = min(0.5, 0.2 + matches * 0.1)
        
        if relevance < 0.2:
            return None
        
        return {
            "domain": self.DOMAIN,
            "type": "paper",
            "source": "arXiv",
            "title": title[:150],
            "content": summary[:300],
            "raw_data": paper,
            "relevance_score": relevance,
            "metadata": {
                "category": paper.get("category"),
                "published": paper.get("published"),
                "url": paper.get("url"),
            }
        }

