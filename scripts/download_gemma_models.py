#!/usr/bin/env python3
"""Download GGUF models for LM Studio with resume support."""

import os
import sys
from huggingface_hub import hf_hub_download

MODELS = [
    {
        "repo": "ggml-org/gemma-4-E4B-it-GGUF",
        "file": "gemma-4-E4B-it-Q4_K_M.gguf",
        "desc": "Gemma 4 E4B (Q4_K_M, ~2.5GB)",
    },
    {
        "repo": "ggml-org/gemma-4-26B-A4B-it-GGUF", 
        "file": "gemma-4-26B-A4B-it-Q4_K_M.gguf",
        "desc": "Gemma 4 26B-A4B (Q4_K_M, ~16.8GB)",
    },
]

LM_STUDIO_MODELS = os.path.expanduser("~/.lmstudio/models")


def download_model(model_info):
    repo = model_info["repo"]
    filename = model_info["file"]
    desc = model_info["desc"]

    print(f"\n{'='*60}")
    print(f"Downloading: {desc}")
    print(f"Repo: {repo}")
    print(f"File: {filename}")
    print(f"{'='*60}")

    # Create local directory
    local_dir_name = filename.replace(".gguf", "").lower()
    local_dir = os.path.join(LM_STUDIO_MODELS, local_dir_name)
    os.makedirs(local_dir, exist_ok=True)

    try:
        result = hf_hub_download(
            repo_id=repo,
            filename=filename,
            local_dir=local_dir,
            resume_download=True,
        )
        file_size = os.path.getsize(result) if os.path.exists(result) else 0
        size_gb = file_size / (1024**3)
        print(f"\n✅ Downloaded to: {result}")
        print(f"   Size: {size_gb:.2f} GB")
        return True
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        return False


if __name__ == "__main__":
    os.makedirs(LM_STUDIO_MODELS, exist_ok=True)
    
    success_count = 0
    for model in MODELS:
        if download_model(model):
            success_count += 1
        else:
            print(f"⚠️  Skipping {model['desc']} due to error")

    print(f"\n{'='*60}")
    print(f"Done: {success_count}/{len(MODELS)} models downloaded")
    print(f"Models location: {LM_STUDIO_MODELS}")
    print(f"{'='*60}")
