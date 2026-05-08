# Alembic Migration Runbook

## Upgrading

```bash
# From backend/ on the VM
venv/bin/alembic upgrade head
# Or via deploy script:
sudo bash infra/deploy.sh --migrate
```

## Rolling back one migration

```bash
venv/bin/alembic downgrade -1
```

Every migration in this repo has a tested `downgrade()` function. Sprint 93+ migrations that only add indexes are instant and data-safe to roll back.

## Checking current revision

```bash
venv/bin/alembic current
```

## Migration authoring rules

1. **Always implement `downgrade()`** — never leave it as `pass`.
2. **Use `_has_table` / `_has_index` guards** when adding indexes (see Sprint 88/93 migrations) so re-running on a partial state doesn't error.
3. **Forward-only for destructive schema changes** — dropping a column or changing a constraint requires two deploys:
   - Deploy 1: ship code that tolerates the old schema
   - Run migration
   - Deploy 2: ship code that requires the new schema
4. **`CREATE INDEX CONCURRENTLY`** for new indexes on large tables — avoids locking production writes. Alembic's `op.create_index` does this by default on PostgreSQL.
5. **Test upgrade + downgrade + upgrade** locally before merging:
   ```bash
   venv/bin/alembic upgrade head && venv/bin/alembic downgrade -1 && venv/bin/alembic upgrade head
   ```

## Code rollback

| Layer | Rollback |
|-------|---------|
| Frontend | Vercel dashboard → previous deployment → "Promote to Production" (~30 sec) |
| Backend | `ssh ubuntu@5.78.114.15 && cd /home/ubuntu/bip && git checkout <sha> && sudo bash infra/deploy.sh` |
| DB indexes (additive) | `venv/bin/alembic downgrade -1` (instant, no data loss) |
| DB schema changes | Use the two-deploy pattern above; downgrade script must exist |

## Feature flags (Sprint 93)

Both flags live in `/etc/bip/env` on the VM and take effect on the next `infra/deploy.sh` restart — no code redeploy needed.

| Flag | Default | Effect |
|------|---------|--------|
| `ENABLE_RATE_LIMIT` | `true` | `false` → rate limits become 10 000/min (effectively off) |
| `ADMIN_API_KEY` | *(unset)* | Unset → admin endpoints open (dev/staging mode). Set to a random hex string in production. |
