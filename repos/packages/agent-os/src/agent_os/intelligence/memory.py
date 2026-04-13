import logging
import os
import yaml
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExperienceBuffer:
    def __init__(self, 
                 registry_skills_path: str = "configs/registry/skills",
                 quarantine_path: str = "wiki/_quarantine"):
        self.registry_skills_path = registry_skills_path
        self.quarantine_path = quarantine_path

    def _find_skill_file(self, skill_id: str) -> Optional[Dict]:
        for root, _, files in os.walk(self.registry_skills_path):
            for f in files:
                if f.endswith(".yaml"):
                    path = os.path.join(root, f)
                    with open(path, 'r', encoding='utf-8') as file:
                        try:
                            data = yaml.safe_load(file)
                            if data and data.get('id') == skill_id:
                                return data
                        except Exception as exc:
                            logger.debug("Failed to parse skill YAML %s: %s", path, exc)
        return None

    def capture(self, skill_id: str, content: str, status: str = "SUCCESS", metadata: Dict = None) -> Optional[str]:
        if metadata is None: metadata = {}
        
        skill_data = self._find_skill_file(skill_id)
        if not skill_data:
            return None
            
        capture_config = skill_data.get("knowledge_capture", {})
        if not capture_config.get("writeback"):
            return "skipped"
            
        timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        is_quarantine = status != "SUCCESS"
        prefix = "QUARANTINE_" if is_quarantine else ""
        
        target_dir = self.quarantine_path if is_quarantine else capture_config.get("target", "wiki/_logs")
        os.makedirs(target_dir, exist_ok=True)
        
        file_name = f"{prefix}{skill_id}_{timestamp_slug}.md"
        file_path = os.path.join(target_dir, file_name)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"type: {skill_id}\n")
            f.write(f"status: {'quarantine' if is_quarantine else 'accepted'}\n")
            f.write(f"timestamp: {datetime.now().isoformat()}\n")
            f.write("tags:\n")
            
            if "agent_id" in metadata:
                f.write(f"  - {metadata['agent_id']}\n")
            if "keywords" in metadata:
                for kw in metadata["keywords"]:
                    f.write(f"  - {kw.lower().replace(' ', '-')}\n")
            f.write("---\n\n")
            
            if is_quarantine:
                f.write("> [!CAUTION]\n> This record is in QUARANTINE due to failed verification.\n\n")
            
            f.write(f"# Experience Record: {skill_id.capitalize()}\n\n")
            f.write(content)
            f.write("\n")
            
        return file_path
