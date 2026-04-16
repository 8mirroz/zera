#!/usr/bin/env python3
"""Download GGUF models directly to LM Studio."""

import os
import sys
from huggingface_hub import hf_hub_download

LM_STUDIO_MODELS = os.path.expanduser("~/.lmstudio/models")

MODELS = [
    {
        "repo": "ggml-org/gemma-4-E4B-it-GGUF",
        "file": "gemma-4-E4B-it-Q4_K_M.gguf",
        "local_dir": "gemma-4-e4b-it",
        "desc": "Gemma 4 E4B (Q4_K_M, ~5.3GB)",
    },
    {
        "repo": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "file": "qwen2.5-7b-instruct-q4_k_m.gguf",
        "local_dir": "qwen2.5-7b-instruct",
        "desc": "Qwen2.5 7B Instruct (Q4_K_M, ~4.5GB)",
    },
]

def download_model(model_info):
    repo = model_info["repo"]
    filename = model_info["file"]
    local_dir = os.path.join(LM_STUDIO_MODELS, model_info["local_dir"])
    desc = model_info["desc"]

    print(f"\n{'='*60}")
    print(f"📥 Downloading: {desc}")
    print(f"   Repo: {repo}")
    print(f"   To: {local_dir}")
    print(f"{'='*60}")

    os.makedirs(local_dir, exist_ok=True)

    try:
        result = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=local_dir,
        )
        file_size = os.path.getsize(result) if os.path.exists(result) else 0
        size_gb = file_size / (1024**3)
        print(f"\n✅ Downloaded: {result}")
        print(f"   Size: {size_gb:.2f} GB")
        return True
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


if __name__ == "__main__":
    os.makedirs(LM_STUDIO_MODELS, exist_ok=True)
    
    print("🔵 LM Studio Model Downloader")
    print(f"   Target: {LM_STUDIO_MODELS}")
    
    success_count = 0
    for i, model in enumerate(MODELS, 1):
        print(f"\n[{i}/{len(MODELS)}]")
        if download_model(model):
            success_count += 1
        else:
            print(f"⚠️  Skipped: {model['desc']}")

    print(f"\n{'='*60}")
    print(f"✅ Done: {success_count}/{len(MODELS)} models downloaded")
    print(f"📁 Models location: {LM_STUDIO_MODELS}")
    print(f"💡 Open LM Studio → Models tab → your models will appear")
    print(f"{'='*60}")
