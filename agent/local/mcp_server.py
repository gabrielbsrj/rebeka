# agent/local/mcp_server.py
# MCP Server para comunicar Rebeka com Claude Desktop
# Permite que o Claude Code use a Rebeka como ferramenta e vice-versa

import asyncio
import json
import logging
from typing import Any, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar servidor MCP
server = Server("rebeka-local")

# Estado do servidor
connected_clients = set()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Lista as ferramentas disponíveis para o Claude Desktop."""
    return [
        Tool(
            name="rebeka_search_news",
            description="Busca notícias de tecnologia e IA usando a Rebeka. "
                       "Use para pesquisar tendências, lançamentos, notícias do dia.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de pesquisa"},
                    "date": {"type": "string", "description": "Data opcional (ex: 17/03/2026)"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="rebeka_write_article",
            description="Escreve um artigo de tecnologia usando a Rebeka. "
                       "Cria conteúdo HTML otimizado para o site.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Título do artigo"},
                    "content": {"type": "string", "description": "Conteúdo do artigo"},
                    "category": {"type": "string", "description": "Categoria (futuro-da-ia, produtividade, reviews)"},
                    "language": {"type": "string", "description": "Idioma (pt, en, es)", "default": "pt"}
                },
                "required": ["title", "content", "category"]
            }
        ),
        Tool(
            name="rebeka_get_context",
            description="Pega o contexto atual da Rebeka (estado, histórico, padrões comportamentais).",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domínio específico (opcional)"}
                }
            }
        ),
        Tool(
            name="rebeka_read_site",
            description="Lê o conteúdo do site TechFront para entender estrutura e artigos existentes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Caminho dentro do site"}
                }
            }
        ),
        Tool(
            name="rebeka_list_articles",
            description="Lista os artigos existentes no site.",
            inputSchema={
                "type": "object",
                "properties": {
                    "language": {"type": "string", "description": "Idioma (pt, en, es)", "default": "pt"}
                }
            }
        ),
        Tool(
            name="rebeka_execute_task",
            description="Executa uma tarefa arbitrária usando as ferramentas da Rebeka.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Descrição da tarefa"},
                    "tools": {"type": "array", "description": "Ferramentas permitidas", "items": {"type": "string"}}
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="call_claude_desktop",
            description="Chama o Claude Desktop para executar uma tarefa. Escreve uma requisição e espera resposta.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Ferramenta a chamar (ex: rebeka_search_news)"},
                    "args": {"type": "object", "description": "Argumentos para a ferramenta"}
                },
                "required": ["tool", "args"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    """Executa uma ferramenta chamada pelo Claude Desktop."""
    try:
        if name == "rebeka_search_news":
            result = await search_news(arguments.get("query", ""), arguments.get("date"))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "rebeka_write_article":
            result = await write_article(
                arguments.get("title", ""),
                arguments.get("content", ""),
                arguments.get("category", "futuro-da-ia"),
                arguments.get("language", "pt")
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "rebeka_get_context":
            result = await get_context(arguments.get("domain"))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "rebeka_read_site":
            result = await read_site(arguments.get("path", ""))
            return [TextContent(type="text", text=result)]
        
        elif name == "rebeka_list_articles":
            result = await list_articles(arguments.get("language", "pt"))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "rebeka_execute_task":
            result = await execute_task(arguments.get("task", ""), arguments.get("tools", []))
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        elif name == "call_claude_desktop":
            result = await call_claude_desktop_async(
                arguments.get("tool", ""),
                arguments.get("args", {})
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Ferramenta desconhecida: {name}")]
    
    except Exception as e:
        logger.error(f"Erro na ferramenta {name}: {e}")
        return [TextContent(type="text", text=f"Erro: {str(e)}")]


async def search_news(query: str, date: Optional[str] = None) -> dict:
    """Busca notícias usando browser_search."""
    from local.executor_local import LocalExecutor
    
    executor = LocalExecutor()
    
    search_query = query
    if date:
        search_query = f"{query} {date}"
    
    result = await executor.browser_search(search_query)
    return result


async def write_article(title: str, content: str, category: str, language: str = "pt") -> dict:
    """Escreve um artigo em HTML."""
    import os
    from datetime import datetime
    
    # Criar nome da pasta a partir do título
    slug = title.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")[:50]
    
    # Caminho do site
    site_base = Path("C:/Users/Aridelson/Desktop/site")
    article_dir = site_base / language / "artigos" / slug / "index.html"
    
    # Criar diretório
    article_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Gerar HTML
    html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | TechFront</title>
    <meta name="description" content="{title}">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        a {{ color: #0066cc; }}
    </style>
</head>
<body>
    <article>
        <h1>{title}</h1>
        <p class="meta">Publicado em {datetime.now().strftime('%d/%m/%Y')}</p>
        <div class="content">
{content}
        </div>
    </article>
</body>
</html>"""
    
    # Salvar arquivo
    with open(article_dir, "w", encoding="utf-8") as f:
        f.write(html)
    
    return {
        "status": "success",
        "file": str(article_dir),
        "title": title,
        "category": category,
        "language": language
    }


async def get_context(domain: Optional[str] = None) -> dict:
    """Pega contexto da Rebeka."""
    try:
        from memory.causal_bank import CausalBank
        bank = CausalBank(origin="local")
        
        context = {
            "active_patterns": [],
            "recent_signals": [],
            "domains": {}
        }
        
        if domain:
            patterns = bank.get_active_patterns(domain=domain)
            context["domains"][domain] = {"patterns": [p.__dict__ for p in patterns]}
        else:
            for d in ["finance", "tech", "productivity"]:
                patterns = bank.get_active_patterns(domain=d)
                if patterns:
                    context["domains"][d] = {"patterns": [p.__dict__ for p in patterns]}
        
        return context
    
    except Exception as e:
        return {"error": str(e)}


async def read_site(path: str) -> str:
    """Lê conteúdo do site."""
    import os
    from pathlib import Path
    
    site_base = Path("C:/Users/Aridelson/Desktop/site")
    
    if not path:
        # Listar estrutura
        result = []
        for lang in ["pt", "en", "es"]:
            articles_dir = site_base / lang / "artigos"
            if articles_dir.exists():
                articles = [d.name for d in articles_dir.iterdir() if d.is_dir()]
                result.append(f"{lang}: {len(articles)} artigos")
        return "\n".join(result)
    
    # Ler arquivo específico
    file_path = site_base / path
    if file_path.exists():
        if file_path.is_file():
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()[:5000]  # Limitar tamanho
        elif file_path.is_dir():
            return " ".join([f.name for f in file_path.iterdir()])
    
    return f"Caminho não encontrado: {path}"


async def list_articles(language: str = "pt") -> dict:
    """Lista artigos do site."""
    from pathlib import Path
    
    site_base = Path("C:/Users/Aridelson/Desktop/site")
    articles_dir = site_base / language / "artigos"
    
    if not articles_dir.exists():
        return {"status": "error", "message": f"Diretório não encontrado: {articles_dir}"}
    
    articles = []
    for d in articles_dir.iterdir():
        if d.is_dir():
            # Verificar se tem index.html
            index_file = d / "index.html"
            if index_file.exists():
                # Ler título do HTML
                try:
                    with open(index_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        if "<title>" in content:
                            title = content.split("<title>")[1].split("</title>")[0]
                        else:
                            title = d.name
                except:
                    title = d.name
                
                articles.append({
                    "slug": d.name,
                    "title": title,
                    "path": str(index_file)
                })
            else:
                articles.append({
                    "slug": d.name,
                    "title": d.name,
                    "path": str(d)
                })
    
    return {
        "language": language,
        "count": len(articles),
        "articles": articles
    }


async def call_claude_desktop_async(tool: str, args: dict) -> dict:
    """Chama o Claude Desktop através do message bridge."""
    from local.message_bridge import call_claude_desktop
    result = call_claude_desktop(tool, args)
    return result


async def execute_task(task: str, tools: list[str]) -> dict:
    """Executa uma tarefa arbitrária."""
    # Implementação básica - pode ser expandida
    return {
        "status": "received",
        "task": task,
        "tools": tools,
        "message": "Tarefa recebida. Implementação detalhada em desenvolvimento."
    }


async def main():
    """Inicia o servidor MCP."""
    logger.info("Iniciando MCP Server da Rebeka...")
    logger.info("Claude Desktop pode теперь conectar-se")
    
    async with stdio_server() as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
