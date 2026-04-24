import os
import yaml
import argparse
import hashlib
from jinja2 import Environment, FileSystemLoader, meta, Template

class PromptAutomationEngine:
    """
    Antigravity Prompt Automation Engine (PAE) v1.0.
    Handles loading, rendering, and caching of prompts from the centralized library.
    """
    
    def __init__(self, base_path="/Users/user/zera/configs/prompts", runtime_path="/Users/user/zera/.agents/runtime/prompts"):
        self.base_path = base_path
        self.runtime_path = runtime_path
        self.manifest_path = os.path.join(base_path, "manifest.yaml")
        self.env = Environment(loader=FileSystemLoader(self.base_path))
        self._ensure_paths()
        self.manifest = self._load_manifest()

    def _ensure_paths(self):
        os.makedirs(self.runtime_path, exist_ok=True)

    def _load_manifest(self):
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")
        with open(self.manifest_path, 'r') as f:
            return yaml.safe_load(f)

    def get_prompt_by_id(self, prompt_id):
        for p in self.manifest.get('prompts', []):
            if p['id'] == prompt_id:
                return p
        return None

    def render(self, prompt_id, context=None):
        """
        Loads the YAML prompt, extracts content, and renders it with context using Jinja2.
        """
        metadata = self.get_prompt_by_id(prompt_id)
        if not metadata:
            raise ValueError(f"Prompt ID '{prompt_id}' not found in manifest.")
        
        prompt_file_path = os.path.join(self.base_path, metadata['path'])
        with open(prompt_file_path, 'r') as f:
            prompt_data = yaml.safe_load(f)
        
        template_text = prompt_data.get('content', '')
        template = Template(template_text)
        rendered_content = template.render(context or {})
        
        # Save to cache
        cache_file = self._save_to_cache(prompt_id, rendered_content, context)
        
        return rendered_content, cache_file

    def _save_to_cache(self, prompt_id, content, context):
        """
        Saves rendered prompt to runtime cache with a hash of context for uniqueness.
        """
        ctx_hash = hashlib.md5(str(context).encode()).hexdigest()[:8]
        filename = f"{prompt_id}_{ctx_hash}.rendered.md"
        filepath = os.path.join(self.runtime_path, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"<!-- Rendered from {prompt_id} at runtime -->\n")
            f.write(content)
        
        return filepath

def main():
    parser = argparse.ArgumentParser(description="Zera Prompt Automation Engine CLI")
    parser.add_argument("--id", required=True, help="Prompt ID from manifest.yaml")
    parser.add_argument("--ctx", help="JSON string representing the context for injection")
    parser.add_argument("--output", action="store_true", help="Only output the rendered content")
    
    args = parser.parse_args()
    
    import json
    context = json.loads(args.ctx) if args.ctx else {}
    
    engine = PromptAutomationEngine()
    try:
        content, cache_path = engine.render(args.id, context)
        if args.output:
            print(content)
        else:
            print(f"✅ Prompt rendered successfully.")
            print(f"📍 Cache: {cache_path}")
            print("-" * 20)
            print(content[:500] + "..." if len(content) > 500 else content)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
