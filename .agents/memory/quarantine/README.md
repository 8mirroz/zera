# Memory Quarantine Area

This directory contains memory entries that failed quality gates or schema validation.

## Purpose
- Isolation of low-confidence or high-noise writes.
- Buffer for manual review by a Librarian or Audit agent.
- Prevention of database pollution.

## Lifecycle
- Items in this folder are NOT searchable by default.
- Retention: 14 days (defined in `memory_catalog.yaml`).
- Action: review → promote OR review → purge.
