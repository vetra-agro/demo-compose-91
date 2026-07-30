import psutil
import time
import os
from datetime import datetime

# Descobre o caminho absoluto do repositório onde este script está salvo
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# CONFIGURAÇÃO PORTÁTIL (Funcionado na sua máquina e no DEV (Marcelo Almeida) )
PROJECT_PATHS = [BASE_DIR]
TARGET_PROCESSES = ["python3", "jupyter-notebook", "streamlit"]
LOG_FILE = os.path.join(BASE_DIR, ".agro", "logs", "agro_session.log")

def is_agro_project(path):
    """Verifica se a execução está acontecendo dentro deste repositório."""
    return BASE_DIR in path

def get_engineering_context():
    """Busca processos do Agro ativos no repositório."""
    active_sessions = []
    for proc in psutil.process_iter(['pid', 'name', 'cwd', 'cmdline']):
        try:
            cwd = proc.info['cwd'] or ""
            # Só monitora se estiver dentro deste projeto e for um processo alvo
            if is_agro_project(cwd) and any(target in (proc.info['name'] or "") for target in TARGET_PROCESSES):
                active_sessions.append({
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cmd": " ".join(proc.info['cmdline'] or []),
                    "cwd": cwd
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return active_sessions

def log_session(sessions):
    """Registra a atividade para o processamento de métricas e commits."""
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for s in sessions:
            # Sanitização de segurança: esconde o que parecer senha
            clean_cmd = " ".join([arg if "pass" not in arg.lower() else "****" for arg in s['cmd'].split()])
            f.write(f"[{timestamp}] AGRO_DETECTION: {s['name']} | CMD: {clean_cmd}\n")

if __name__ == "__main__":
    print("🌾 Assistente Vetra Agro: Tracker Ativado e Portátil...")
    while True:
        sessions = get_engineering_context()
        if sessions:
            log_session(sessions)
        time.sleep(10)  # Checagem a cada 10 segundos para nossos testes iniciais
        