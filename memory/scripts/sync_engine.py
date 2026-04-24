import os
import json
import yaml
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Set
import fnmatch
import concurrent.futures

class SyncEngine:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
            
        self.root = Path(self.cfg['vault']['root_path'])
        if not self.root.is_absolute():
            # Assume relative to config path
            self.root = (Path(config_path).parent.parent / self.root).resolve()
            
        self.manifest_path = Path(self.cfg['vault']['sync']['state_manifest'])
        if not self.manifest_path.is_absolute():
            self.manifest_path = (Path(config_path).parent.parent / self.manifest_path).resolve()
            
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.manifest = self._load_manifest()
        self.stats = {
            "started_at": time.time(),
            "files_processed": 0,
            "files_changed": 0,
            "chunks_created": 0,
            "errors": []
        }

    def _load_manifest(self) -> Dict:
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {"files": {}, "last_sync": 0}

    def _save_manifest(self):
        self.manifest["last_sync"] = time.time()
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    def _get_checksum(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _is_excluded(self, path: Path) -> bool:
        try:
            rel_path = str(path.relative_to(self.root))
        except ValueError:
            return True # Not in root
            
        # Check excludes
        for pattern in self.cfg['vault']['exclude']['patterns']:
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                return True
        
        # Check includes
        included = False
        for pattern in self.cfg['vault']['include']['patterns']:
            if fnmatch.fnmatch(rel_path, pattern):
                included = True
                break
        
        return not included

    def crawl(self) -> List[Path]:
        changed_files = []
        if not self.root.exists():
            print(f"Error: root path {self.root} does not exist.")
            return []
            
        for path in self.root.rglob('*'):
            if path.is_file() and not self._is_excluded(path):
                self.stats["files_processed"] += 1
                try:
                    checksum = self._get_checksum(path)
                    
                    rel_path = str(path.relative_to(self.root))
                    if rel_path not in self.manifest["files"] or self.manifest["files"][rel_path]["checksum"] != checksum:
                        changed_files.append(path)
                        self.manifest["files"][rel_path] = {
                            "checksum": checksum,
                            "mtime": path.stat().st_mtime,
                            "size": path.stat().st_size
                        }
                        self.stats["files_changed"] += 1
                except Exception as e:
                    self.stats["errors"].append(f"Error crawling {path}: {str(e)}")
        
        return changed_files

    def process_file(self, path: Path):
        try:
            print(f"Processing {path}...")
            # Mock logic
            self.stats["chunks_created"] += 5
        except Exception as e:
            self.stats["errors"].append(f"Error processing {path}: {str(e)}")

    def run(self):
        print(f"Starting sync for {self.root}...")
        changed = self.crawl()
        
        max_workers = self.cfg['vault']['sync']['max_concurrency']
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(self.process_file, changed)
            
        self._save_manifest()
        self._emit_report()
        
        print(f"Sync complete. Processed {self.stats['files_processed']} files, {self.stats['files_changed']} changed.")

    def _emit_report(self):
        report_path = Path(self.cfg['vault']['sync']['last_run_report'])
        if not report_path.is_absolute():
            report_path = (self.root.parent / report_path).resolve()
            
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "timestamp": time.time(),
            "duration": time.time() - self.stats["started_at"],
            "stats": self.stats,
            "status": "success" if not self.stats["errors"] else "partial_success"
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

if __name__ == "__main__":
    # Get absolute path to config
    base_dir = Path(__file__).parent.parent
    config_path = base_dir / "vault_config.yaml"
    engine = SyncEngine(str(config_path))
    engine.run()
