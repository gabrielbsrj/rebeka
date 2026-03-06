import os
import sys

# Adicionar o diretório agent ao path
agent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, agent_dir)

# Rodar o dashboard
os.environ["PYTHONPATH"] = agent_dir

from vps.dashboard.server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8086)
