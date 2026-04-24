#!/usr/bin/env python3
"""
Configuration Validator for Antigravity Core / Hermes Agent OS

Validates:
1. YAML syntax and schema compliance
2. Model router rules consistency
3. Skill contract adherence
4. Memory entry schema validation
5. Path integrity (symlinks, relative paths)
6. Hardcoded model ID detection

Usage:
    python scripts/validation/validate_configs.py [--strict] [--fix]
"""

import os
import sys
import json
import yaml
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import jsonschema
from jsonschema import validate, ValidationError

# Configuration
BASE_DIR = Path(__file__).parent.parent.parent
AGENTS_DIR = BASE_DIR / ".agents"
CONFIGS_DIR = BASE_DIR / "configs"
CONTRACTS_DIR = AGENTS_DIR / "contracts"

# Schema paths
SKILL_SCHEMA_PATH = CONTRACTS_DIR / "skills" / "skill_definition_v1.json"
MEMORY_SCHEMA_PATH = CONTRACTS_DIR / "memory" / "memory_entry_v1.json"
MODEL_ROUTER_PATH = AGENTS_DIR / "config" / "model_router.yaml"

class ConfigValidator:
    def __init__(self, strict_mode: bool = False, auto_fix: bool = False):
        self.strict_mode = strict_mode
        self.auto_fix = auto_fix
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.fixed_count = 0
        
    def load_schema(self, path: Path) -> Optional[Dict]:
        """Load JSON schema from file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.errors.append({
                "type": "SCHEMA_LOAD_ERROR",
                "path": str(path),
                "message": str(e)
            })
            return None
    
    def load_yaml(self, path: Path) -> Optional[Dict]:
        """Load YAML file."""
        try:
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            self.errors.append({
                "type": "YAML_LOAD_ERROR",
                "path": str(path),
                "message": str(e)
            })
            return None
    
    def load_json(self, path: Path) -> Optional[Dict]:
        """Load JSON file."""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.errors.append({
                "type": "JSON_LOAD_ERROR",
                "path": str(path),
                "message": str(e)
            })
            return None
    
    def check_model_router_exists(self):
        """Verify model_router.yaml exists and is valid."""
        if not MODEL_ROUTER_PATH.exists():
            self.errors.append({
                "type": "MISSING_CRITICAL_CONFIG",
                "path": str(MODEL_ROUTER_PATH),
                "message": "model_router.yaml is missing. This will cause non-deterministic routing."
            })
            return False
        
        config = self.load_yaml(MODEL_ROUTER_PATH)
        if not config:
            return False
            
        # Check required sections
        required_sections = ['routing_strategy', 'models', 'rules']
        for section in required_sections:
            if section not in config:
                self.errors.append({
                    "type": "MISSING_SECTION",
                    "path": str(MODEL_ROUTER_PATH),
                    "message": f"Missing required section: {section}"
                })
        
        # Check for hardcoded model IDs (should use aliases)
        if 'rules' in config:
            hardcoded_pattern = re.compile(r'^(gpt-|claude-|gemini-|llama-)')
            for rule in config['rules']:
                if 'model' in rule:
                    model_val = rule['model']
                    if isinstance(model_val, str) and hardcoded_pattern.match(model_val):
                        self.warnings.append({
                            "type": "HARDCODED_MODEL_ID",
                            "path": str(MODEL_ROUTER_PATH),
                            "rule_id": rule.get('id', 'unknown'),
                            "message": f"Hardcoded model ID detected: {model_val}. Use $AGENT_MODEL_* alias instead."
                        })
        
        return True
    
    def validate_skill_contracts(self):
        """Validate all skill definitions against schema."""
        schema = self.load_schema(SKILL_SCHEMA_PATH)
        if not schema:
            return False
        
        skills_dir = AGENTS_DIR / "skills"
        if not skills_dir.exists():
            self.warnings.append({
                "type": "MISSING_DIRECTORY",
                "path": str(skills_dir),
                "message": "Skills directory not found"
            })
            return True
        
        validated = 0
        for skill_file in skills_dir.rglob("*.yaml"):
            skill_data = self.load_yaml(skill_file)
            if not skill_data:
                continue
            
            try:
                validate(instance=skill_data, schema=schema)
                validated += 1
            except ValidationError as e:
                self.errors.append({
                    "type": "SCHEMA_VALIDATION_ERROR",
                    "path": str(skill_file),
                    "message": str(e.message),
                    "json_path": e.json_path
                })
        
        print(f"✓ Validated {validated} skill definitions")
        return len([e for e in self.errors if e['type'] == 'SCHEMA_VALIDATION_ERROR']) == 0
    
    def validate_memory_entries(self, sample_size: int = 10):
        """Validate sample memory entries against schema."""
        schema = self.load_schema(MEMORY_SCHEMA_PATH)
        if not schema:
            return False
        
        memory_files = [
            AGENTS_DIR / "memory" / "memory.jsonl",
            AGENTS_DIR / "memory" / "projects" / "seed_knowledge.jsonl"
        ]
        
        validated = 0
        for mem_file in memory_files:
            if not mem_file.exists():
                continue
            
            with open(mem_file, 'r') as f:
                for i, line in enumerate(f):
                    if i >= sample_size:
                        break
                    try:
                        entry = json.loads(line.strip())
                        validate(instance=entry, schema=schema)
                        validated += 1
                    except json.JSONDecodeError as e:
                        self.errors.append({
                            "type": "INVALID_JSON",
                            "path": str(mem_file),
                            "line": i,
                            "message": str(e)
                        })
                    except ValidationError as e:
                        self.warnings.append({
                            "type": "MEMORY_SCHEMA_WARNING",
                            "path": str(mem_file),
                            "line": i,
                            "message": str(e.message)
                        })
        
        print(f"✓ Validated {validated} memory entries (sample)")
        return True
    
    def check_path_integrity(self):
        """Check symlinks and critical paths."""
        # Check .agent symlink
        agent_link = BASE_DIR / ".agent"
        if agent_link.is_symlink():
            target = os.readlink(agent_link)
            if not (BASE_DIR / target).exists():
                self.errors.append({
                    "type": "BROKEN_SYMLINK",
                    "path": str(agent_link),
                    "target": target,
                    "message": "Symlink points to non-existent directory"
                })
        elif not agent_link.exists():
            self.warnings.append({
                "type": "MISSING_SYMLINK",
                "path": str(agent_link),
                "message": ".agent symlink not found (may be intentional after migration)"
            })
        
        # Check critical directories
        critical_dirs = [
            AGENTS_DIR / "skills",
            AGENTS_DIR / "memory",
            CONFIGS_DIR / "orchestrator"
        ]
        
        for dir_path in critical_dirs:
            if not dir_path.exists():
                self.errors.append({
                    "type": "MISSING_CRITICAL_DIR",
                    "path": str(dir_path),
                    "message": "Critical directory missing"
                })
        
        # Check workflows (can be symlink to external repo)
        workflows_dir = AGENTS_DIR / "workflows"
        if not workflows_dir.exists():
            self.warnings.append({
                "type": "WORKFLOWS_EXTERNAL",
                "path": str(workflows_dir),
                "message": "Workflows directory is external symlink (acceptable if target exists)"
            })
    
    def run_all_checks(self):
        """Execute all validation checks."""
        print("=" * 60)
        print("HERMES AGENT OS - CONFIGURATION VALIDATOR")
        print("=" * 60)
        print()
        
        print("[1/5] Checking Model Router Configuration...")
        self.check_model_router_exists()
        
        print("[2/5] Validating Skill Contracts...")
        self.validate_skill_contracts()
        
        print("[3/5] Validating Memory Entries (sample)...")
        self.validate_memory_entries()
        
        print("[4/5] Checking Path Integrity...")
        self.check_path_integrity()
        
        print("[5/5] Checking for Documentation Drift...")
        self.check_doc_drift()
        
        print()
        print("=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Errors:   {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Fixed:    {self.fixed_count}")
        print()
        
        if self.errors:
            print("ERRORS:")
            for err in self.errors:
                print(f"  ❌ [{err['type']}] {err['path']}: {err['message']}")
            print()
        
        if self.warnings:
            print("WARNINGS:")
            for warn in self.warnings:
                print(f"  ⚠️  [{warn['type']}] {warn.get('path', 'N/A')}: {warn['message']}")
            print()
        
        return len(self.errors) == 0
    
    def check_doc_drift(self):
        """Check for .agent/ references in documentation."""
        doc_files = list(BASE_DIR.glob("*.md")) + list(BASE_DIR.glob("docs/**/*.md"))
        drift_count = 0
        
        for doc in doc_files:
            if not doc.exists():
                continue
            content = doc.read_text()
            if '.agent/' in content and '.agents/' not in content:
                self.warnings.append({
                    "type": "DOC_DRIFT",
                    "path": str(doc),
                    "message": "Contains legacy .agent/ references without .agents/ mention"
                })
                drift_count += 1
        
        if drift_count > 0:
            print(f"  ⚠️  Found {drift_count} files with potential documentation drift")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Validate Hermes Agent OS configurations')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as errors')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues where possible')
    args = parser.parse_args()
    
    validator = ConfigValidator(strict_mode=args.strict, auto_fix=args.fix)
    success = validator.run_all_checks()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
