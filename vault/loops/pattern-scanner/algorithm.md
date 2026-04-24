# Pattern Scanner Algorithm

## Objective
Systematically scan the Zera skill ecosystem for patterns, anomalies, and improvement opportunities.

## Scan Sequence

### Phase 1: Inventory
```
find ~/.hermes/profiles/zera/skills -name "SKILL.md" | wc -l
find ~/.hermes/profiles/zera/skills -name "SKILL.md" -exec wc -c {} \; | sort -n
ls ~/.hermes/profiles/zera/skills/
```

### Phase 2: Stub Detection
Detect skills that describe CLI interfaces but have no actual implementation.
Criteria: description mentions a command, but skill contains no `terminal()`, `execute_code()`, or `delegate_task()` calls with actual implementation.

**Stubs found:**
- `zera-validate` (1250 bytes): describes `validate` CLI, references `scripts/zera_validate.sh` → MISSING
- `zera-critic-review` (1376 bytes): describes `critic` CLI, references `scripts/zera_critic.sh` → MISSING

### Phase 3: Broken References
Grep for path references in skills, verify with `ls`:
- `qwen-code-integration`: `/Users/user/antigravity-core/configs/qwen/` → MISSING
- `qwen-code-integration`: `/Users/user/antigravity-core/scripts/zera-qwen-wrapper.sh` → MISSING
- `qwen-code-integration`: `/Users/user/antigravity-core/.agent/skills/qwen-integration/` → MISSING

### Phase 4: Dead Dependencies
Check each referenced CLI tool:
```bash
for tool in imsg remindctl memo blogwatcher himalaya yq; do
  command -v "$tool" || echo "MISSING: $tool"
done
```
**Missing:** imsg, remindctl, memo, blogwatcher, himalaya, yq

### Phase 5: Duplicate Detection
```bash
grep -h "^name:" ~/.hermes/profiles/zera/skills/*/SKILL.md | sort | uniq -c | sort -rn
```
**Result:** No duplicates (all 111 unique names)

### Phase 6: Size Anomalies
- **Largest:** pytorch-fsdp (160KB, 129 lines) — scraper-generated, legitimate
- **Smallest:** zera-validate (1250 bytes) — STUB
- **Second smallest:** obsidian (1264 bytes) — minimal but functional

### Phase 7: Cross-Reference Analysis
Skills referencing missing tools:
- `apple-reminders`: remindctl (MISSING)
- `imessage`: imsg (MISSING)
- `apple-notes`: memo (MISSING)
- `blogwatcher`: blogwatcher-cli (MISSING)
- `himalaya` skill: himalaya (MISSING)

### Phase 8: Memory Gaps
Check from evolve-state.json:
- `vault/memory/zera/meta-memory.json` → MISSING (action item since cycle 1)
- `vault/memory/decisions/` → mostly empty
- `vault/memory/sessions/` → needs verification

## Output Artifacts
- `config.yaml` — scan configuration and metadata
- `algorithm.md` — this file
- `evolution.jsonl` — mutations/rejections log
- `research-findings.md` — detailed findings
