You've got this written down already. Your note **"K3S - Data: Management"** (knowledge #45, deployment - k8s) covers it, and **"K3S - Cheatsheet"** §25 covers the cluster-state side. Here's the procedure from those notes, plus a few gaps I found when I checked them against your newer **"K3s-Infras"** note (31 Aug).

## How your setup stores data

Your homelab runs single-node k3s. All service data lives on `hostPath` PVs under **`/home/avarile/k3s-data/`**, bound by `/home/avarile/k3s-infra/storage/persistent-volumes.yaml`. Backing up k3s on this box means backing up three things:

1. **Service data** in `/home/avarile/k3s-data/*`
2. **Cluster state**, which is k3s's own datastore (SQLite on a single node)
3. **Manifests + secrets**: the `k3s-infra` repo is in git, but `**/secret.yaml` is gitignored, so the secrets need their own backup

## 1. Quick version (what your note says)

```bash
# Optional: stop writes first for a consistent copy of the active stores
kubectl scale deployment --all -n infra --replicas=0

sudo tar -czf /tmp/k3s-data-backup-$(date +%F).tgz /home/avarile/k3s-data

kubectl scale deployment --all -n infra --replicas=1
```

`sudo` is required because the PostgreSQL directory isn't readable by your user. The note recommends stopping or restarting the workload before a file-level copy of a live database. Copying it while it runs can give you a corrupt copy.

## 2. Safer version: service-native dumps (the note's preference)

Use these alongside the tar, or instead of it for the databases:

```bash
B=~/backups/k3s/$(date +%F); mkdir -p $B

# PostgreSQL / pgvector: all DBs (embedding_db, plane, twenty)
kubectl exec -n infra deploy/pgvector -- pg_dumpall -U pgadmin > $B/postgres-all.sql

# Redis: force a fresh RDB, then copy it from the data dir
kubectl exec -n infra deploy/redis -- redis-cli -a "$REDIS_PASSWORD" BGSAVE
sudo cp /home/avarile/k3s-data/redis/dump.rdb $B/

# RabbitMQ: definitions (users, vhosts, queues) via the management API
curl -u mqadmin:"$RABBITMQ_PASSWORD" http://192.168.0.103:31672/api/definitions > $B/rabbitmq-definitions.json

# Qdrant: full storage snapshot (no auth on your instance)
curl -X POST http://192.168.0.103:30333/snapshots

# Meilisearch: create a dump
curl -X POST http://192.168.0.103:30770/dumps -H "Authorization: Bearer $MEILI_MASTER_KEY"
```

The Postgres, Redis, RabbitMQ and Meilisearch credentials are all in your **K3s-Infras** note. I can pull them up if you want them inline.

## 3. Cluster state (from your Cheatsheet §25)

```bash
# Single-node default = SQLite
sudo sqlite3 /var/lib/rancher/k3s/server/db/state.db ".backup /tmp/k3s-state-$(date +%F).db"
sudo cp /var/lib/rancher/k3s/server/token /tmp/k3s-token.bak   # needed to restore that DB
# (If you ever switch to embedded etcd: sudo k3s etcd-snapshot save)
```

Also copy the gitignored `secret.yaml` files out of `k3s-infra`, or export them with `kubectl get secret -n infra -o yaml > secrets.yaml`. Store them somewhere encrypted.

## Restoring

Put the directory back, then restart the workloads so they reopen the files:

```bash
kubectl rollout restart deployment/pgvector deployment/redis deployment/rabbitmq deployment/meilisearch deployment/qdrant -n infra
```

## Gaps I noticed

- **The data note is out of date.** It lists 6 services: Postgres, Redis, RabbitMQ, Meilisearch, Qdrant and RabbitMQ logs. Your K3s-Infras note (Aug) shows the cluster now also runs **MySQL** (app_db + gitea), **MongoDB** (librechat), **MinIO** (plane/twenty files) and **Vaultwarden** (SQLite). None of those appear in the backup layout. Run `kubectl get pv -o custom-columns=NAME:.metadata.name,PATH:.spec.hostPath.path` to confirm where they store data. For proper dumps of those four: `mysqldump --all-databases --single-transaction`, `mongodump --archive --gzip`, `mc mirror` for MinIO, and `sqlite3 db.sqlite3 ".backup ..."` for Vaultwarden. **Vaultwarden is the one you really don't want to lose.**
- **Nothing is automated.** The note says outright that there is no automated backup, pruning or retention. `/tmp` is also a bad place to keep a backup. Copy it off the box: another machine, the RAID, or MinIO-to-elsewhere.
- I've assumed the deployment names (`pgvector`, `redis`, …) from the restart commands in your note. Check them with `kubectl get deploy -n infra`.

I can write this up as a cron-able `k3s-backup.sh` with retention. I can also update the "K3S - Data: Management" note with the missing services, if you'd like.
