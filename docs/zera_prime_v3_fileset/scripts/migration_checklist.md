# Zera × Hermes Migration Checklist

## Before

- [ ] Backup `/Users/user/zera`
- [ ] Backup `/Users/user/.hermes`
- [ ] Export list of Hermes profiles
- [ ] Export list of duplicate skills
- [ ] Export list of duplicate vaults
- [ ] Preserve unique loops from Hermes profiles

## Install

- [ ] Create `/Users/user/zera-core`
- [ ] Copy zera-core files
- [ ] Copy hermes-runtime files
- [ ] Replace `.hermes/SOUL.md` with runtime contract
- [ ] Create symlinks
- [ ] Run drift check

## Cleanup

- [ ] Archive `zera_beta`
- [ ] Archive `zera-beta`
- [ ] Archive `zera-local`
- [ ] Inspect checkpoint dependency
- [ ] Remove duplicate persona files
- [ ] Remove duplicate vault copies
- [ ] Replace duplicated skills with symlinks

## Verify

- [ ] Zera identity has one source
- [ ] Hermes has no persona copy
- [ ] Memory writes require approval
- [ ] Runtime returns evidence packets
- [ ] Autonomy L5 is forbidden
