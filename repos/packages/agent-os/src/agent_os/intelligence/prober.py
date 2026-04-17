import logging
import time
import yaml
import os
import urllib.request
import json
from datetime import datetime
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ModelProber:
    def __init__(self,
                 repo_root: str = ".",
                 config_path: str = "configs/orchestrator/models.yaml",
                 overlay_path: str = ".agents/runtime/model_ovl.yaml",
                 ollama_host: str = "http://localhost:11434"):
        self.repo_root = repo_root
        self.config_path = config_path if os.path.isabs(config_path) else os.path.join(repo_root, config_path)
        self.overlay_path = overlay_path if os.path.isabs(overlay_path) else os.path.join(repo_root, overlay_path)
        self.ollama_host = ollama_host

    def check_ollama(self) -> Tuple[bool, List[str]]:
        try:
            with urllib.request.urlopen(f"{self.ollama_host}/api/tags", timeout=1) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    return True, [m['name'] for m in data.get('models', [])]
        except Exception as exc:
            logger.debug("Ollama not reachable: %s", exc)
        return False, []

    def run_probe(self) -> Dict:
        if not os.path.exists(self.config_path):
            return {"error": f"{self.config_path} not found"}

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)
        
        models = config.get("models", {})
        cloud_probes = ["MODEL_ENGINEER_PRIMARY", "MODEL_ARCHITECT_PRIMARY", "MODEL_FAST_PRIMARY"]
        
        ollama_online, local_models = self.check_ollama()
        
        overlay = {
            "version": "1.1-hybrid", 
            "timestamp": datetime.now().isoformat(),
            "metrics": {}, 
            "overrides": {},
            "local_status": {
                "online": ollama_online,
                "available_models": local_models
            }
        }
        
        for p in cloud_probes:
            model_id = models.get(p)
            if not model_id: continue
            
            # Simple simulation of cloud probe
            latency = 0.4
            success = True
            
            overlay["metrics"][p] = {"latency": latency, "status": "online" if success else "offline"}
            
            if latency > 5 or not success:
                fallback = models.get(p.replace('_PRIMARY', '_STABILITY'))
                if fallback:
                    overlay["overrides"][p] = fallback

        if ollama_online:
            local_aliases = [k for k in models.keys() if k.startswith("MODEL_LOCAL_")]
            for alias in local_aliases:
                full_id = models[alias]
                clean_id = full_id.replace("ollama/", "")
                is_downloaded = any(clean_id in m for m in local_models)
                overlay["metrics"][alias] = {
                    "status": "available" if is_downloaded else "missing",
                    "id": full_id
                }

        os.makedirs(os.path.dirname(self.overlay_path), exist_ok=True)
        with open(self.overlay_path, "w") as f:
            yaml.dump(overlay, f)
            
        return overlay
