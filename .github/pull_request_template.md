## Problem and resulting behavior

Describe the trigger, before/after behavior and the affected users.

## Validation

- [ ] Offline tests, Ruff and import architecture gate passed.
- [ ] Package build/import checked if package changed.
- [ ] PostgreSQL migration/ownership tests checked if persistence changed.
- [ ] Docker smoke/restart checked if deployment changed.
- [ ] No secrets, real user fixtures or unreviewed model/schema/vector changes.
- [ ] Errors do not reveal keys/PII; logout and ownership remain isolated.
- [ ] Evidence distinguishes executed checks from pending/skipped checks.
- [ ] Existing schema adoption has reviewed backup/restore evidence where applicable.

## Rollback or limitations

Describe any data compatibility limits and the concrete rollback procedure.
