Your notes cover this. Back up two things: the service data volumes under `/home/avarile/k3s-data`, and the k3s cluster state itself.

**1. Service data (the hostPath PVs)**

On the homelab (Debian) server everything lives under `/home/avarile/k3s-data/`: `postgres`, `redis`, `rabbitmq/{data,log}`, `minio` and `qdrant`. Stop the workloads first so nothing writes while you copy:

```bash
kubectl scale deployment pgvector -n infra --replicas=0
kubectl scale deployment redis    -n infra --replicas=0
kubectl scale deployment rabbitmq -n infra --replicas=0
kubectl scale deployment minio    -n infra --replicas=0
kubectl scale deployment qdrant   -n infra --replicas=0
kubectl get pods -n infra          # wait until they're gone

# The postgres dir isn't readable without root, so use sudo
sudo tar -czf /tmp/k3s-data-backup-$(date +%F).tgz /home/avarile/k3s-data
# or copy it to another machine: rsync -avz /home/avarile/k3s-data/ user@host:/backups/k3s-data/

# Bring them back (repeat for each deployment)
kubectl scale deployment pgvector -n infra --replicas=1
```

If you'd rather not take downtime, your notes say to use each service's own export tool instead: `pg_dump` for Postgres, `BGSAVE`/RDB for Redis, a definitions export plus the queue data for RabbitMQ, and the built-in snapshots for Qdrant.

**Restore:** put the directory back, fix ownership (`sudo chown -R avarile:avarile /home/avarile/k3s-data`), then run `kubectl rollout restart deployment/<name> -n infra` so each pod reopens the restored files.

**2. Cluster state (k3s datastore)**

A single-node k3s uses SQLite by default:

```bash
sudo sqlite3 /var/lib/rancher/k3s/server/db/state.db ".backup /tmp/k3s-backup.db"
```

If the server runs embedded etcd instead, use `sudo k3s etcd-snapshot save` (and `sudo k3s etcd-snapshot list` to see them). You can also schedule it in `/etc/rancher/k3s/config.yaml` with `etcd-snapshot-schedule-cron: "0 */6 * * *"` and `etcd-snapshot-retention: 5`.

The manifests are in the `k3s-infra` repo, so git already backs them up. The secrets (pgvector, redis, rabbitmq, minio) were created by hand, so keep a copy of them somewhere too.

**Things to watch:**
- Nothing is backing this up automatically right now. Your notes say there's "no automated backup, pruning, or retention policy", so the tar/rsync step above needs a cron job if you want it to happen regularly.
- The data-management entry lists `meilisearch` while the homelab guide lists `minio`. Run `ls /home/avarile/k3s-data` on the server to see which one you actually have before you script anything.
- hostPath data is tied to that path. If the hostname or home directory changes, update the PVs in `k3s-infra/storage/persistent-volumes.yaml`.

Sources: **K3S - Data: Management** (`recVJ2Zys9euu8JHsJQ`), **K3S initite on HomeLab** (`recQRRNd3EAQ5arufg1`, sections 1 and 4) and **K3S - Cheatsheet** (`rec9TTSDoktu59fT89i`, §25 Backup & Restore).

Want me to save this as a backup runbook, or add it as a dated update to the K3S - Data: Management entry?
