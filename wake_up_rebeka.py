# wake_up_rebeka.py
import subprocess
import time
import os
import sys
import webbrowser
import logging
from dotenv import load_dotenv

# Carregar configurações do .env
load_dotenv(os.path.join(os.path.dirname(__file__), "agent", ".env"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RebekaAwakening")

def wake_up():
    logger.info("🌅 INICIANDO PROCESSO DE DESPERTAR DA REBEKA...")
    
    # 1. Configurações de Ambiente
    env = os.environ.copy()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    env["PYTHONPATH"] = f"{base_dir};{os.path.join(base_dir, 'agent')}"

    remote_host = os.getenv("REMOTE_VPS_HOST", "127.0.0.1")
    remote_port = os.getenv("REMOTE_VPS_PORT", "22")
    remote_path = os.getenv("REMOTE_VPS_PATH", "~/rebeka2")
    remote_pass = os.getenv("REMOTE_VPS_PASS")
    local_only = os.getenv("REBEKA_LOCAL_ONLY", "").strip().lower() in {"1", "true", "yes"}
    if local_only:
        remote_host = ""
        env["REMOTE_VPS_HOST"] = ""
        env["VPS_WS_URL"] = "ws://localhost:8000/ws/sync"

    # 2. Iniciar Gêmeo VPS com Túnel SSH
    vps_proc = None
    if remote_host:
        logger.info(f"🌐 Conectando à VPS em {remote_host}:{remote_port}...")
        remote_cmd = f"cd {remote_path}/agent && export PYTHONPATH=.:$PYTHONPATH && ~/rebeka_venv/bin/python3 vps/main.py"
        
        import shutil
        plink_path = shutil.which("plink.exe")
        
        if remote_pass and plink_path:
            logger.info("🔐 Estabelecendo Túnel SSH e iniciando VPS...")
            # -L mapeia portas da VM para o localhost do Windows
            # Adicionado -batch para evitar parar em perguntas interativas
            full_ssh_cmd = (
                f'plink.exe -batch -pw {remote_pass} -P {remote_port} '
                f'-hostkey "SHA256:/C983q4jCYf8LidvQDzGIyUsh4eTduMniNmfFdLWFLs" '
                f'-L 8000:localhost:8000 -L 8086:localhost:8086 '
                f'{remote_host} "{remote_cmd}"'
            )
        else:
            full_ssh_cmd = f'ssh -p {remote_port} -o StrictHostKeyChecking=no {remote_host} "{remote_cmd}"'
        
        try:
            vps_proc = subprocess.Popen(
                full_ssh_cmd,
                shell=True,
                env=env,
                stdout=None,
                stderr=None
            )
            logger.info("📡 Túnel e VPS em inicialização...")
        except Exception as e:
            logger.error(f"❌ Falha ao disparar SSH: {e}")
            return
    else:
        logger.info("🚀 Iniciando Gêmeo VPS LOCAL (Fallback)...")
        vps_proc = subprocess.Popen(
            [sys.executable, "agent/vps/main.py"],
            shell=False,
            env=env,
            stdout=None,
            stderr=None
        )

    # 3. Aguardar 10 segundos para o túnel e servidor remoto estabilizarem
    time.sleep(10)

    # 4. Iniciar Gêmeo Local
    logger.info("🏠 Iniciando Gêmeo Local (Perspectiva Íntima)...")
    local_proc = subprocess.Popen(
        [sys.executable, "agent/local/main.py"],
        env=env,
        stdout=None,
        stderr=None
    )

    # 5. Abrir Dashboard automaticamente
    logger.info("📊 Abrindo Dashboard Rebeka...")
    webbrowser.open("http://localhost:8086")

    # 6. Ciclo de Demonstração (Trigger Rotina)
    logger.info("💡 Rebeka está se situando... Aguarde o Relatório de Despertar no Chat.")
    
    # Simular trigger da rotina matinal via código (em um cenário real seria agendado)
    # Por agora, o ProactiveInsightService já inicia em background.
    # Vamos rodar um script de trigger separado que injeta um sinal de despertar se necessário
    # ou simplesmente esperar que o monitor de sobrevivência e outros façam seu trabalho.
    
    try:
        while True:
            if vps_proc and vps_proc.poll() is not None:
                logger.error("Gêmeo VPS encerrou inesperadamente.")
                break
            if local_proc.poll() is not None:
                logger.error("Gêmeo Local encerrou inesperadamente.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("💤 Colocando Rebeka para dormir... Encerrando processos.")
        if vps_proc: vps_proc.terminate()
        local_proc.terminate()
        logger.info("Sistemas offline.")

if __name__ == "__main__":
    wake_up()
