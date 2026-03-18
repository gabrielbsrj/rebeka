# agent/local/message_bridge.py
# Ponte de comunicação entre Rebeka e Claude Desktop
# Permite que a Rebeka chame o Claude Desktop e vice-versa

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Any, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MESSAGE_DIR = Path("C:/Users/Aridelson/Desktop/rebeka2/agent/local/vault/messages")
MESSAGE_DIR.mkdir(parents=True, exist_ok=True)

REQUEST_FILE = MESSAGE_DIR / "requests.json"
RESPONSE_FILE = MESSAGE_DIR / "responses.json"


def write_request(request: dict) -> str:
    """Rebeka escreve uma requisição para o Claude Desktop."""
    request_id = f"rebecka_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    request["id"] = request_id
    request["timestamp"] = datetime.now().isoformat()
    request["status"] = "pending"
    
    requests = []
    if REQUEST_FILE.exists():
        try:
            with open(REQUEST_FILE, "r", encoding="utf-8") as f:
                requests = json.load(f)
        except:
            requests = []
    
    requests.append(request)
    
    with open(REQUEST_FILE, "w", encoding="utf-8") as f:
        json.dump(requests, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Requisição escrita: {request_id}")
    return request_id


def read_responses(request_id: str, timeout: int = 30) -> Optional[dict]:
    """Lê a resposta do Claude Desktop para uma requisição."""
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        if not RESPONSE_FILE.exists():
            time.sleep(1)
            continue
        
        try:
            with open(RESPONSE_FILE, "r", encoding="utf-8") as f:
                responses = json.load(f)
            
            for resp in responses:
                if resp.get("request_id") == request_id:
                    resp["status"] = "read"
                    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
                        json.dump(responses, f, ensure_ascii=False, indent=2)
                    return resp
        except:
            pass
        
        time.sleep(1)
    
    return None


def write_response(request_id: str, result: Any, status: str = "completed"):
    """Claude Desktop escreve uma resposta."""
    response = {
        "request_id": request_id,
        "result": result,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    responses = []
    if RESPONSE_FILE.exists():
        try:
            with open(RESPONSE_FILE, "r", encoding="utf-8") as f:
                responses = json.load(f)
        except:
            responses = []
    
    responses.append(response)
    
    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
        json.dump(responses, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Resposta escrita para: {request_id}")


def call_claude_desktop(tool: str, args: dict) -> dict:
    """
    Rebeka chama o Claude Desktop para executar uma tarefa.
    Retorna o resultado.
    """
    request = {
        "type": "tool_call",
        "tool": tool,
        "args": args
    }
    
    request_id = write_request(request)
    
    response = read_responses(request_id, timeout=60)
    
    if response:
        return response.get("result", {})
    else:
        return {"status": "timeout", "message": "Claude Desktop não respondeu a tempo"}


def search_news_via_claude(query: str, date: Optional[str] = None) -> dict:
    """Busca notícias usando o Claude Desktop."""
    return call_claude_desktop("rebeka_search_news", {
        "query": query,
        "date": date
    })


def write_article_via_claude(title: str, content: str, category: str = "futuro-da-ia", language: str = "pt") -> dict:
    """Escreve artigo usando o Claude Desktop."""
    return call_claude_desktop("rebeka_write_article", {
        "title": title,
        "content": content,
        "category": category,
        "language": language
    })


def get_pending_requests() -> List[Dict]:
    """Retorna requisições pendentes (para o Claude Desktop ler)."""
    if not REQUEST_FILE.exists():
        return []
    
    try:
        with open(REQUEST_FILE, "r", encoding="utf-8") as f:
            requests = json.load(f)
        return [r for r in requests if r.get("status") == "pending"]
    except:
        return []


def mark_request_processed(request_id: str):
    """Marca uma requisição como processada."""
    if not REQUEST_FILE.exists():
        return
    
    try:
        with open(REQUEST_FILE, "r", encoding="utf-8") as f:
            requests = json.load(f)
        
        for r in requests:
            if r.get("id") == request_id:
                r["status"] = "processed"
        
        with open(REQUEST_FILE, "w", encoding="utf-8") as f:
            json.dump(requests, f, ensure_ascii=False, indent=2)
    except:
        pass
