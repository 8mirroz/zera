import os
import shutil
import json
import time
import yaml
from pathlib import Path
from typing import Optional

class IndexManager:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
            
        self.base_path = Path(config_path).parent.parent
        self.index_path = self.base_path / Path(self.cfg['index']['path'])
        self.backup_dir = self.base_path / Path(self.cfg['index']['backup']['path'])
        self.keep_last = self.cfg['index']['backup']['keep_last']
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def create_backup(self):
        if not self.index_path.exists():
            print("No index to backup.")
            return

        timestamp = int(time.time())
        backup_path = self.backup_dir / f"faiss_{timestamp}.index"
        shutil.copy2(self.index_path, backup_path)
        print(f"Created backup: {backup_path}")
        
        manifest_path = self.base_path / Path(self.cfg['index']['manifest'])
        if manifest_path.exists():
            shutil.copy2(manifest_path, self.backup_dir / f"index_manifest_{timestamp}.json")

        self._rotate_backups()

    def _rotate_backups(self):
        backups = sorted(self.backup_dir.glob("faiss_*.index"), key=os.path.getmtime, reverse=True)
        if len(backups) > self.keep_last:
            for old_backup in backups[self.keep_last:]:
                print(f"Removing old backup: {old_backup}")
                old_backup.unlink()
                ts = old_backup.stem.split('_')[1]
                m_path = self.backup_dir / f"index_manifest_{ts}.json"
                if m_path.exists():
                    m_path.unlink()

    def verify_index(self, path: Optional[Path] = None) -> bool:
        target = path or self.index_path
        if not target.exists():
            return False
            
        try:
            manifest_path = self.base_path / Path(self.cfg['index']['manifest'])
            if not manifest_path.exists():
                return False
                
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                
            return manifest.get('dim') == self.cfg['embedding']['dim']
        except Exception:
            return False

    def rollback(self):
        backups = sorted(self.backup_dir.glob("faiss_*.index"), key=os.path.getmtime, reverse=True)
        if not backups: return False
            
        for backup in backups:
            if self.verify_index(backup):
                shutil.copy2(backup, self.index_path)
                ts = backup.stem.split('_')[1]
                m_backup = self.backup_dir / f"index_manifest_{ts}.json"
                if m_backup.exists():
                    shutil.copy2(m_backup, self.base_path / Path(self.cfg['index']['manifest']))
                return True
        return False

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "vault_config.yaml"
    mgr = IndexManager(str(config_path))
