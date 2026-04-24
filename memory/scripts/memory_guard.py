import json
import yaml
import re
from pathlib import Path

class MemoryGuard:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        self.base_path = Path(config_path).parent.parent
        self.gates = self.cfg['quality_gates']

    def validate_sync_report(self, report_path: str) -> bool:
        path = self.base_path / Path(report_path)
        if not path.exists(): return False
        with open(path, 'r') as f:
            report = json.load(f)
        stats = report.get('stats', {})
        processed = stats.get('files_processed', 0)
        errors = len(stats.get('errors', []))
        if processed > 0:
            success_rate = (processed - errors) / processed
            if success_rate < self.gates['sync_success_rate_min']: return False
        return errors <= self.gates['max_failed_files']

    def check_pii(self, text: str) -> bool:
        if not self.cfg['governance']['pii_guard']['enabled']: return True
        patterns = [r'[\w\.-]+@[\w\.-]+\.\w+', r'(?:sk-|AIza)[0-9a-zA-Z-_]{20,}', r'password\s*[:=]\s*[^\s]+']
        return not any(re.search(p, text, re.IGNORECASE) for p in patterns)

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "vault_config.yaml"
    guard = MemoryGuard(str(config_path))
