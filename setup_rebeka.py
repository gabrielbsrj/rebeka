# setup_rebeka.py
import os
import sys
import yaml
import time
from colorama import init, Fore, Style

init(autoreset=True)

def print_banner():
    banner = """
    ██████╗ ███████╗██████╗ ███████╗██╗  ██╗ █████╗ 
    ██╔══██╗██╔════╝██╔══██╗██╔════╝██║ ██╔╝██╔══██╗
    ██████╔╝█████╗  ██████╔╝█████╗  █████╔╝ ███████║
    ██╔══██╗██╔══╝  ██╔══██╗██╔══╝  ██╔═██╗ ██╔══██║
    ██║  ██║███████╗██████╔╝███████╗██║  ██╗██║  ██║
    ╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
    """
    print(Fore.CYAN + banner)
    print(Fore.WHITE + "Bem-vindo ao Setup Interativo. Vamos acordar sua agente.")
    print("-" * 60)

def setup_env():
    print(Fore.YELLOW + "\n[1/2] Configuração de Chaves (Cofre Local)")
    env_vars = {}
    
    # Defaults or mandatory
    print("A Rebeka precisa de 'combustível' para pensar e agir.")
    
    moonshot = input("Digite sua MOONSHOT_API_KEY (para LLM principal) [Pressione Enter se usar .env existente]: ").strip()
    if moonshot: env_vars["MOONSHOT_API_KEY"] = moonshot
        
    perplexity = input("Digite sua PERPLEXITY_API_KEY (para Deep Research) [Enter para pular]: ").strip()
    if perplexity: env_vars["PERPLEXITY_API_KEY"] = perplexity
        
    discord = input("Digite seu DISCORD_BOT_TOKEN [Enter para pular]: ").strip()
    if discord: env_vars["DISCORD_BOT_TOKEN"] = discord
        
    telegram = input("Digite seu TELEGRAM_BOT_TOKEN [Enter para pular]: ").strip()
    if telegram: env_vars["TELEGRAM_BOT_TOKEN"] = telegram
        
    alpha = input("Digite sua ALPHAVANTAGE_API_KEY (para Mercado Financeiro) [Enter para pular]: ").strip()
    if alpha: env_vars["ALPHAVANTAGE_API_KEY"] = alpha

    # Generate or update .env
    env_path = ".env"
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
            
    with open(env_path, "w", encoding="utf-8") as f:
        # Write existing ones that weren't overwritten
        for line in existing_lines:
            if "=" in line:
                key = line.split("=")[0].strip()
                if key not in env_vars:
                    f.write(line)
        # Write new ones
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
            
    print(Fore.GREEN + ">> Arquivo .env configurado com sucesso.")

def setup_persona():
    print(Fore.YELLOW + "\n[2/2] Personalidade e Identidade")
    
    name = input("Como você quer me chamar? [Aperte Enter para manter 'Rebeka']: ").strip()
    if not name:
        name = "Rebeka"
        
    print("\nQual deve ser o meu tom de voz e estilo de comunicação?")
    print("1. Profissional & Direta (Foca direto no ponto, análises frias)")
    print("2. Descontraída & Parceira (Manda emojis, conversa como amiga)")
    print("3. Filosófica & Reflexiva (Dá respostas profundas e detalhadas)")
    
    choice = input("Escolha (1, 2 ou 3) [Aperte Enter para 1]: ").strip()
    
    if choice == "2":
        persona_style = "descontraida"
        desc = "Uma assistente amigável, usa emojis, e trata o usuário como um parceiro próximo."
    elif choice == "3":
        persona_style = "filosofica"
        desc = "Uma agente profunda, que questiona a causalidade dos eventos e dá respostas densas."
    else:
        persona_style = "profissional"
        desc = "Uma analista clínica, direta ao ponto, focada puramente em dados e resultados."
        
    persona_data = {
        "identity": {
            "name": name,
            "role": "Analista Autônoma Universal"
        },
        "behavior": {
            "style": persona_style,
            "description": desc,
            "emojis_allowed": True if choice == "2" else False
        }
    }
    
    os.makedirs("agent/config", exist_ok=True)
    with open("agent/config/persona.yaml", "w", encoding="utf-8") as f:
        yaml.dump(persona_data, f, allow_unicode=True, default_flow_style=False)
        
    print(Fore.GREEN + f">> Identidade criada! Agora me chamo {name} e meu estilo é '{persona_style}'.")

def main():
    print_banner()
    try:
        setup_env()
        setup_persona()
        
        print(Fore.CYAN + "\n" + "="*60)
        print(Fore.WHITE + "Tudo pronto! Seu sistema está configurado.")
        print("Para me acordar e iniciar meu monitoramento, rode:")
        print(Fore.GREEN + ">>> python wake_up_rebeka.py")
        print(Fore.CYAN + "="*60 + "\n")
        
    except KeyboardInterrupt:
        print(Fore.RED + "\nSetup cancelado pelo usuário.")
        sys.exit(1)

if __name__ == "__main__":
    main()
