#!/usr/bin/env python3
"""
MCP Profiles Validation and Test Script

Tests:
1. JSON syntax validation
2. Schema validation
3. Server availability check
4. Routing logic validation
5. Allowlist path validation
"""

import json
import sys
import os
from pathlib import Path

# Colors for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color

def load_config(config_path):
    """Load and parse JSON config"""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"{RED}❌ Config file not found: {config_path}{NC}")
        return None
    except json.JSONDecodeError as e:
        print(f"{RED}❌ JSON syntax error: {e}{NC}")
        return None

def validate_schema(data):
    """Validate config schema"""
    errors = []
    warnings = []
    
    # Required top-level fields
    required = ['version', 'profiles', 'default_profile']
    for field in required:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate profiles
    if 'profiles' in data:
        for name, profile in data['profiles'].items():
            if not isinstance(profile, dict):
                errors.append(f"Profile '{name}' must be an object")
                continue
            if 'servers' not in profile:
                errors.append(f"Profile '{name}' missing 'servers' field")
            elif not isinstance(profile['servers'], list):
                errors.append(f"Profile '{name}' servers must be a list")
            elif len(profile['servers']) == 0:
                warnings.append(f"Profile '{name}' has no servers")
    
    # Validate routing
    if 'routing' in data:
        if not isinstance(data['routing'], list):
            errors.append("'routing' must be a list")
        else:
            for i, rule in enumerate(data['routing']):
                if not isinstance(rule, dict):
                    errors.append(f"Routing rule {i} must be an object")
                    continue
                if 'profile' not in rule:
                    errors.append(f"Routing rule {i} missing 'profile'")
                elif rule['profile'] not in data.get('profiles', {}):
                    errors.append(f"Routing rule {i} references unknown profile: {rule['profile']}")
                if 'task_type' not in rule:
                    warnings.append(f"Routing rule {i} missing 'task_type' (matches all)")
                if 'complexity' not in rule:
                    warnings.append(f"Routing rule {i} missing 'complexity' (matches all)")
    
    # Validate default_profile
    if 'default_profile' in data:
        if data['default_profile'] not in data.get('profiles', {}):
            errors.append(f"default_profile '{data['default_profile']}' not found in profiles")
    
    # Validate allowlist
    if 'allowlist' in data:
        if not isinstance(data['allowlist'], list):
            errors.append("'allowlist' must be a list")
        else:
            for path in data['allowlist']:
                if not isinstance(path, str):
                    errors.append(f"Allowlist path must be string: {path}")
                    continue
                resolved = os.path.expanduser(os.path.expandvars(path))
                if '$' in resolved or '{' in resolved or '}' in resolved:
                    warnings.append(f"Allowlist path has unresolved variable: {path}")
                elif not resolved.startswith('/'):
                    warnings.append(f"Allowlist path should be absolute: {path}")
                elif not os.path.exists(resolved):
                    warnings.append(f"Allowlist path does not exist: {resolved}")
    
    return errors, warnings

def check_server_availability(data, base_dir):
    """Check if referenced MCP servers exist"""
    available = []
    missing = []
    
    # Get all server names from profiles
    servers = set()
    for profile in data.get('profiles', {}).values():
        servers.update(profile.get('servers', []))
    
    # Check filesystem for local servers
    src_dir = Path(base_dir) / 'repos' / 'mcp' / 'servers' / 'src'
    if src_dir.exists():
        local_servers = {d.name for d in src_dir.iterdir() if d.is_dir()}
    else:
        local_servers = set()
    
    # Known external MCP servers (npm packages)
    external_servers = {
        'context7', 'github', 'filesystem', 'memory', 'sequential-thinking',
        'everything', 'fetch', 'git', 'time', 'qwen-context', 'mcp-antigravity-context',
        'perplexity-ask', 'stitch', 'magicui', 'openrouter', 'memu'
    }
    
    for server in servers:
        if server in local_servers or server in external_servers:
            available.append(server)
        else:
            missing.append(server)
    
    return available, missing

def test_routing_logic(data):
    """Test routing logic with sample tasks"""
    test_cases = [
        {'task_type': 'T6', 'complexity': 'C2', 'expected': 'ui-design'},
        {'task_type': 'T5', 'complexity': 'C4', 'expected': 'data-scraping'},
        {'task_type': 'T5', 'complexity': 'C2', 'expected': 'research'},
        {'task_type': 'T3', 'complexity': 'C2', 'expected': 'implement'},  # Updated
        {'task_type': 'T1', 'complexity': 'C1', 'expected': 'config'},
        {'task_type': 'T2', 'complexity': 'C3', 'expected': 'fix'},
        {'task_type': 'T4', 'complexity': 'C4', 'expected': 'swarm'},
        {'task_type': 'T7', 'complexity': 'C2', 'expected': 'telegram'},
    ]
    
    results = []
    for test in test_cases:
        result = data['default_profile']  # default
        for rule in data.get('routing', []):
            if test['task_type'] in rule.get('task_type', []):
                if test['complexity'] in rule.get('complexity', []):
                    result = rule['profile']
                    break
        
        passed = result == test['expected']
        results.append({
            'test': test,
            'result': result,
            'passed': passed
        })
    
    return results

def main():
    base_dir = Path(__file__).resolve().parents[2]
    config_path = str(base_dir / "configs/tooling/mcp_profiles.json")
    
    print(f"{YELLOW}{'='*60}{NC}")
    print(f"{YELLOW}MCP Profiles Validation Test{NC}")
    print(f"{YELLOW}{'='*60}{NC}\n")
    
    # Load config
    print(f"Loading config: {config_path}")
    data = load_config(config_path)
    if data is None:
        sys.exit(1)
    print(f"{GREEN}✅ Config loaded successfully{NC}\n")
    
    # Validate schema
    print("Validating schema...")
    errors, warnings = validate_schema(data)
    
    if errors:
        print(f"{RED}❌ Schema validation failed with {len(errors)} error(s):{NC}")
        for error in errors:
            print(f"   {RED}• {error}{NC}")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ Schema validation passed{NC}")
    
    if warnings:
        print(f"{YELLOW}⚠️  {len(warnings)} warning(s):{NC}")
        for warning in warnings:
            print(f"   {YELLOW}• {warning}{NC}")
        print()
    
    # Check server availability
    print("\nChecking MCP server availability...")
    available, missing = check_server_availability(data, base_dir)
    print(f"{GREEN}✅ Available: {len(available)}{NC}")
    if missing:
        print(f"{YELLOW}⚠️  Missing/Unknown: {len(missing)}{NC}")
        for server in missing:
            print(f"   • {server}")
    
    # Test routing logic
    print("\nTesting routing logic...")
    routing_results = test_routing_logic(data)
    passed = sum(1 for r in routing_results if r['passed'])
    total = len(routing_results)
    
    for result in routing_results:
        status = GREEN + '✅' + NC if result['passed'] else RED + '❌' + NC
        test = result['test']
        expected = test['expected']
        actual = result['result']
        print(f"   {status} T{test['task_type']}+C{test['complexity']}: expected={expected}, got={actual}")
    
    print(f"\n{YELLOW}{'='*60}{NC}")
    if passed == total:
        print(f"{GREEN}✅ All tests passed ({passed}/{total}){NC}")
    else:
        print(f"{RED}❌ {total - passed}/{total} routing test(s) FAILED{NC}")
        for result in routing_results:
            if not result['passed']:
                test = result['test']
                print(f"   {RED}FAIL T{test['task_type']}+C{test['complexity']}: expected={test['expected']}, got={result['result']}{NC}")
    print(f"{YELLOW}{'='*60}{NC}")

    # Summary
    print(f"\n{YELLOW}Summary:{NC}")
    print(f"   Version: {data['version']}")
    print(f"   Profiles: {len(data['profiles'])}")
    for name, profile in data['profiles'].items():
        print(f"      • {name}: {len(profile['servers'])} servers")
    print(f"   Routing rules: {len(data.get('routing', []))}")
    print(f"   Default profile: {data['default_profile']}")
    print(f"   Allowlist paths: {len(data.get('allowlist', []))}")

    # CRITICAL: Exit non-zero if any failures (audit finding: false-green)
    if errors or missing or passed < total:
        failure_reasons = []
        if errors:
            failure_reasons.append(f"{len(errors)} schema error(s)")
        if missing:
            failure_reasons.append(f"{len(missing)} missing server(s)")
        if passed < total:
            failure_reasons.append(f"{total - passed}/{total} routing test(s) failed")
        print(f"\n{RED}❌ VALIDATION FAILED: {'; '.join(failure_reasons)}{NC}")
        sys.exit(1)

if __name__ == '__main__':
    main()
