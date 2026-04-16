import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent_os.memory.layered_retriever import LayeredMemoryRetriever

def verify():
    repo_root = Path("/Users/user/zera")
    retriever = LayeredMemoryRetriever(repo_root)
    
    query = "Omniroute combos"
    print(f"Searching memory for: '{query}'...")
    results = retriever.retrieve(query, top_k=3)
    
    if not results:
        print("No results found in memory.")
        return
        
    for i, r in enumerate(results):
        print(f"\nResult {i+1} (Score: {r.final_score}):")
        print(f"Layer: {r.source_layer}")
        print(f"File:  {r.source_file}")
        print(f"Content: {r.content}")

if __name__ == "__main__":
    verify()
