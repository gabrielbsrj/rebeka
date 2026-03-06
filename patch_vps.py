#!/usr/bin/env python3
import sys

path = sys.argv[1]
content = open(path).read()

# Replace the Gemini fallback with a direct login trigger
old_marker = "Usando Gemini (fallback)"
if old_marker not in content:
    print("ALREADY_PATCHED_OR_NOT_FOUND")
    sys.exit(0)

# Find and replace the entire fallback block
old = """                # FALLBACK: Se n\u00e3o houver credenciais, use Gemini gratuito (GOOGLE_API_KEY)
                if not provider.creds:
                    logger.warning(f"Credenciais Antigravity ausentes. Usando Gemini (fallback) para {self.model}")
                    response = completion(
                        model="gemini/gemini-2.0-flash",
                        messages=self.history,
                        tools=tools,
                        temperature=0.6,
                        api_key=os.getenv("GOOGLE_API_KEY"),
                    )"""

new = """                # Se n\u00e3o houver credenciais, disparar login automaticamente
                if not provider.creds:
                    logger.warning(f"Credenciais Antigravity ausentes. Disparando login para {self.model}")
                    return {
                        "content": "Voc\u00ea ainda n\u00e3o est\u00e1 autenticado no Google Antigravity. Estou abrindo o navegador para fazer o login...",
                        "tool_calls": [
                            SimpleNamespace(
                                id="auto_login_call",
                                type="function",
                                function=SimpleNamespace(
                                    name="google_antigravity_login",
                                    arguments="{}"
                                )
                            )
                        ]
                    }"""

if old in content:
    content = content.replace(old, new)
    open(path, 'w').write(content)
    print("PATCHED")
else:
    print("EXACT_MATCH_NOT_FOUND")
