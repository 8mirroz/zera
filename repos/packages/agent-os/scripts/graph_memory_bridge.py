import os
import re
import json
from pathlib import Path

class GraphMemoryBridge:
    """Bridges Obsidian's relational graph with Antigravity."""
    
    def __init__(self, vault_path, sub_folders=None):
        self.vault_path = Path(vault_path)
        self.sub_folders = sub_folders # List of subdirectories to scan
        self.graph = {} # note_name -> list of linked notes
        self.titles = {} # lowercase_title -> original_title
        
    def build_graph(self, catalog_path=None):
        # 1. Scan Vault
        if self.vault_path.exists():
            target_dirs = self.sub_folders if self.sub_folders else ["brain", "docs", "Zera"]
            for d in target_dirs:
                dir_path = self.root / d if hasattr(self, "root") else self.vault_path / d
                if not dir_path.exists(): continue
                
                for root, dirs, files in os.walk(dir_path):
                    # Ignore noisy directories
                    dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__"}]
                    for file in files:
                        if file.endswith(".md"):
                            path = Path(root) / file
                            title = file[:-3]
                            self.titles[title.lower()] = title
                            with open(path, "r", encoding="utf-8") as f:
                                content = f.read()
                            links = re.findall(r'\[\[(.*?)(?:\|.*?)?\]\]', content)
                            self.graph[title] = links

        # 2. Integrate Catalog Assets
        if catalog_path and os.path.exists(catalog_path):
            with open(catalog_path, "r") as f:
                catalog = json.load(f)
            for cat, items in catalog.items():
                if not isinstance(items, list): continue
                for item in items:
                    name = item["name"]
                    self.titles[name.lower()] = name
                    # Optional: link asset to its category node if it existed
                    if cat not in self.graph: self.graph[cat] = []
                    self.graph[cat].append(name)
                    # Skills can link to their triggers as well
                    if "triggers" in item:
                        for t in item["triggers"]:
                            t_node = f"trigger:{t}"
                            self.titles[t_node.lower()] = t_node
                            if name not in self.graph: self.graph[name] = []
                            self.graph[name].append(t_node)
                    
    def find_related(self, query_topic, depth=1):
        """Finds related notes by traversing the graph."""
        query_topic = query_topic.lower()
        start_nodes = []
        
        # 1. Direct title matching
        if query_topic in self.titles:
            start_nodes.append(self.titles[query_topic])
        
        # 2. Fuzzy/keyword matching if no direct hit
        if not start_nodes:
            for t_low, t_orig in self.titles.items():
                if query_topic in t_low:
                    start_nodes.append(t_orig)
                    
        visited = set()
        queue = [(node, 0) for node in start_nodes]
        related = []
        
        while queue:
            current, current_depth = queue.pop(0)
            if current in visited or current_depth > depth:
                continue
            
            visited.add(current)
            if current not in start_nodes:
                related.append(current)
                
            links = self.graph.get(current, [])
            for link in links:
                if link not in visited:
                    queue.append((link, current_depth + 1))
                    
        return {
            "query": query_topic,
            "starting_points": start_nodes,
            "related_nodes": related
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", default=".", help="Path to Obsidian vault")
    parser.add_argument("--query", help="Topic to find relations for")
    parser.add_argument("--depth", type=int, default=1, help="Graph traversal depth")
    args = parser.parse_args()
    
    bridge = GraphMemoryBridge(args.vault)
    bridge.build_graph()
    
    if args.query:
        results = bridge.find_related(args.query, args.depth)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"Graph loaded with {len(bridge.graph)} nodes.")
