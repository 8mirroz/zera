#!/usr/bin/env python3
import os
import requests
import json
import logging
from datetime import datetime
from pathlib import Path

# === Конфигурация ===
ENV_FILE = os.path.expanduser("~/.hermes/profiles/zera/.env")
JOURNAL_PATH = os.path.expanduser("~/Documents/Obsidian/AntigravityVault/Trends_Journal.md") # Пример пути Obsidian
LOG_FILE = os.path.expanduser("~/.hermes/profiles/zera/logs/scout.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_env():
    env_vars = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, val = line.strip().split('=', 1)
                    env_vars[key] = val.strip("'\"")
    return env_vars

def scout_trends(exa_key):
    """Ищет новые хайповые связки и фреймворки через Exa API."""
    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": exa_key
    }
    # Ищем актуальные статьи за последний месяц
    payload = {
        "query": "New advanced LLM frameworks, agentic workflows, fine-tuning configurations, and deep learning stack improvements",
        "useAutoprompt": True,
        "type": "neural",
        "numResults": 5,
        "contents": {"text": True, "highlights": True}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def save_to_journal(data):
    """Сохраняет результаты в вольт (Журнал)."""
    # Если папки Obsidian нет, сохраняем локально в директории гермеса
    target_path = Path(JOURNAL_PATH)
    if not target_path.parent.exists():
        target_path = Path(os.path.expanduser("~/.hermes/profiles/zera/logs/trends_journal.md"))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    with open(target_path, "a") as f:
        f.write(f"\n## AMLL Scout Digest: {date_str}\n\n")
        results = data.get("results", [])
        for res in results:
            title = res.get("title", "Untitled")
            url = res.get("url", "#")
            f.write(f"### [{title}]({url})\n")
            
            highlights = res.get("highlights", [])
            if highlights:
                f.write(f"> {highlights[0]}\n")
            elif "text" in res:
                f.write(f"> {res['text'][:200]}...\n")
            f.write("\n")
            f.write("- **Expected ROI Category**: TBD by Curator\n\n")
            
    logging.info(f"Saved {len(results)} trends to {target_path}")

def main():
    env = load_env()
    exa_key = env.get("EXA_API_KEY")
    if not exa_key:
        logging.error("EXA_API_KEY not found in .env")
        print("Scout failed: missing EXA_API_KEY")
        return
        
    try:
        logging.info("Starting Scout phase...")
        data = scout_trends(exa_key)
        save_to_journal(data)
        print("Scout phase completed successfully.")
    except Exception as e:
        logging.error(f"Scout phase failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
