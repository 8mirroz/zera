#!/usr/bin/env python3
import os
import subprocess
import psutil
import logging
import sys
from datetime import datetime
from pathlib import Path

# === Настройки ===
IDLE_CPU_THRESHOLD = 40.0  # % загрузки CPU, ниже которого считаем систему свободной
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXEC = os.environ.get("IDLE_RL_PYTHON_EXEC", sys.executable or "python3")
RECIPES_DIR = str(PROJECT_ROOT / "external/tinker-cookbook/tinker_cookbook/recipes")
LOG_FILE = os.path.expanduser("~/.hermes/profiles/zera/logs/idle_rl.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Список задач для обучения
TASKS = [
    {
        "name": "Arithmetic RL (Small)",
        "cmd": [PYTHON_EXEC, f"{RECIPES_DIR}/math_rl/train.py", 
                "--env", "arithmetic", 
                "--groups_per_batch", "32", 
                "--max_steps", "5", 
                "--wandb_project", "hermes-idle-rl",
                "--behavior_if_log_dir_exists", "overwrite"]
    },
    {
        "name": "GSM8K RL (Research)",
        "cmd": [PYTHON_EXEC, f"{RECIPES_DIR}/math_rl/train.py", 
                "--env", "gsm8k", 
                "--groups_per_batch", "16", 
                "--max_steps", "3", 
                "--wandb_project", "hermes-idle-rl",
                "--behavior_if_log_dir_exists", "overwrite"]
    }
]

def is_hermes_active():
    """Проверяет, запущен ли процесс, похожий на активную сессию Hermes."""
    active_process_names = ['hermes-agent', 'hermes', 'python3']
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if any(name in (proc.info['name'] or '') for name in active_process_names):
                # Проверяем, что это не наш собственный скрипт
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'idle_rl_daemon' not in cmdline and 'train.py' not in cmdline:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def check_system_idle():
    cpu_usage = psutil.cpu_percent(interval=2)
    if cpu_usage > IDLE_CPU_THRESHOLD:
        return False, f"CPU usage too high ({cpu_usage}%)"
    
    if is_hermes_active():
        # Если нагрузка от python3 выше 50%, считаем что кто-то работает
        return False, "Hermes or other heavy Python task is active"
    
    return True, "System is idle"

def run_idle_task():
    is_idle, reason = check_system_idle()
    if not is_idle:
        logging.info(f"Skipping training: {reason}")
        print(f"Skipping: {reason}")
        return

    # Простая ротация задач на основе минут часа
    task_idx = (datetime.now().minute // 30) % len(TASKS)
    task = TASKS[task_idx]
    
    logging.info(f"--- Starting Autonomous RL Cycle: {task['name']} ---")
    print(f"Starting: {task['name']}")
    
    try:
        # Запускаем с низким приоритетом
        subprocess.run(["nice", "-n", "19"] + task["cmd"], check=True)
        logging.info(f"Cycle {task['name']} completed.")
    except Exception as e:
        logging.error(f"Cycle {task['name']} failed: {e}")

if __name__ == "__main__":
    run_idle_task()
