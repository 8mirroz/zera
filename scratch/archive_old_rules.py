import os

def archive_files():
    target_dir = "/Users/user/antigravity-core/configs/rules/"
    files_to_archive = [
        "ANTI_CHAOS.md",
        "AGENT_ONLY.md",
        "WORKSPACE_STANDARD.md",
        "TASK_ROUTING.md",
        "QWEN.md",
        "META_PROMPT.md",
        "ENGINEERING_STANDARDS.md",
        "SECURITY_RULES.md",
        "BUILD_PROFILE.md"
    ]
    
    for filename in files_to_archive:
        old_path = os.path.join(target_dir, filename)
        new_path = old_path + ".old"
        if os.path.exists(old_path):
            try:
                os.rename(old_path, new_path)
                print(f"Archived: {filename}")
            except Exception as e:
                print(f"Failed to archive {filename}: {e}")
        else:
            print(f"Skipped (Not found): {filename}")

if __name__ == "__main__":
    archive_files()
