import yaml
import os
from typing import Any, Dict, Optional

class ConfigNode:
    """A wrapper for dictionary-based config data allowing attribute access."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            val = self._data[name]
            if isinstance(val, dict):
                return ConfigNode(val)
            return val
        raise AttributeError(f"ConfigNode has no attribute '{name}'")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return self._data

class ModularConfigLoader:
    """Loads modular YAML configs with component delegation."""
    
    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_suite(self, entry_point_path: str) -> Dict[str, Any]:
        """Loads a master config and resolves all delegated components."""
        abs_path = self._resolve_path(entry_point_path)
        
        if abs_path in self._cache:
            return self._cache[abs_path]

        if not os.path.exists(abs_path):
            return {}

        with open(abs_path, 'r') as f:
            base_data = yaml.safe_load(f)

        if not base_data:
            return {}

        # Resolve components if present
        if "components" in base_data:
            resolved_components = {}
            for comp_name, comp_path in base_data["components"].items():
                resolved_components[comp_name] = self.load_suite(comp_path)
            
            # Embed resolved components into the base data
            base_data["_resolved_components"] = resolved_components
            
        self._cache[abs_path] = base_data
        return base_data

    def _resolve_path(self, path: str) -> str:
        """Resolves config paths relative to repo root if not absolute."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.repo_root, path)

    def get(self, config_name: str) -> ConfigNode:
        """Convenience method to load a config from configs/orchestrator."""
        path = f"configs/orchestrator/{config_name}.yaml"
        data = self.load_suite(path)
        return ConfigNode(data)

    @classmethod
    def get_component(cls, data: Dict[str, Any], component_name: str) -> Optional[ConfigNode]:
        """Helper to get a resolved component as a ConfigNode."""
        resolved = data.get("_resolved_components", {}).get(component_name)
        if resolved:
            return ConfigNode(resolved)
        return None
