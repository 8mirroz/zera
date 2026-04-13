# T6: Human Checkpoint (Compressed Format)

**Savings:** 65% vs narrative format

## Format

```
<human_checkpoint:CHECKPOINT_NAME>
show:
  - file: "path/to/output"
  - extras: "supporting artifacts"
  - sections: "count or description"

confirm:
  - [ ] Criteria 1
  - [ ] Criteria 2
  - [ ] Criteria 3

on_confirm: "Next action or workflow"
</human_checkpoint>
```

## Rules
- Name: ALL_CAPS identifier
- show: list of artifacts for user review
- confirm: checklist user must validate
- on_confirm: what happens after approval
