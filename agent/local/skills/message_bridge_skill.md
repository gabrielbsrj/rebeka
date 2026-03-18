# Skill: Message Bridge Rebeka

## Quando usar
Use esta skill sempre que precisar verificar se a Rebeka enviou alguma requisição para o Claude Desktop.

## Como funciona
1. A Rebeka escreve requisições em `C:/Users/Aridelson/Desktop/rebeka2/agent/local/vault/messages/requests.json`
2. Você verifica esse arquivo periodicamente
3. Se houver requisições pendentes, processe-as
4. Escreva a resposta em `responses.json`

## Comandos

### Verificar requisições pendentes
```python
import json
from pathlib import Path

requests_file = Path("C:/Users/Aridelson/Desktop/rebeka2/agent/local/vault/messages/requests.json")
if requests_file.exists():
    with open(requests_file) as f:
        requests = json.load(f)
    pending = [r for r in requests if r.get("status") == "pending"]
    print(f"Requisições pendentes: {len(pending)}")
    for r in pending:
        print(f"- {r.get('id')}: {r.get('type')} - {r.get('tool')}")
```

### Processar uma requisição
```python
# 1. Ler a requisição
request_id = "rebecka_20260317_194500_123456"

# 2. Executar a ferramenta
result = await rebeka_search_news(query="IA tecnologia", date="17/03/2026")

# 3. Escrever a resposta
response = {
    "request_id": request_id,
    "result": result,
    "status": "completed"
}

responses_file = Path("C:/Users/Aridelson/Desktop/rebeka2/agent/local/vault/messages/responses.json")
responses = []
if responses_file.exists():
    with open(responses_file) as f:
        responses = json.load(f)
responses.append(response)
with open(responses_file, "w") as f:
    json.dump(responses, f, indent=2)
```

## Ferramentas disponíveis para chamar
- `rebeka_search_news` - Buscar notícias
- `rebeka_write_article` - Escrever artigo
- `rebeka_list_articles` - Listar artigos
- `rebeka_read_site` - Ler o site

## Fluxo completo
1. **Verificar** se há requisições pendentes
2. **Processar** cada requisição
3. **Escrever** a resposta
4. **Marcar** a requisição como processada

## Exemplo de uso
Você pode periodicamente verificar por novas requisições da Rebeka e processá-las automaticamente.
