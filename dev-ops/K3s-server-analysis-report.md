# K3s-server — Full Setup & Services Analysis

- **Analysed:** 2026-10-31 (read-only, unprivileged SSH as `avarile`)
- **Access:** `ssh K3s-server` → `avarile@58.179.152.43` (key `~/.ssh/avarile-mbp`), LAN `192.168.0.103`, Tailscale `100.109.221.25`
- **Hostname:** `k8s-micro-server`
- **Limits of this analysis:** `sudo` needs a password, so these were **not inspected** (root-only): nftables rules, fail2ban status, `/etc/rancher/k3s/registries.yaml`, full `journalctl`, `crictl` image usage, `/var/lib/rancher` internals, `/var/lib/docker` contents, root crontab. `kubectl` works without sudo (`~/.kube/config`). Nothing was modified on the server.

---

## 1. Executive summary

A single-node **k3s v1.34.3** cluster on a Debian 13 mini-PC hosts ~15 self-built/self-hosted applications (project management, CRM, agentic chat UI, code-interpreter, Git/registry, blog, password vault, draw.io) on a shared `infra` namespace of databases and brokers. **Caddy runs on the host** as the public TLS front door and reverse-proxies each domain to a NodePort on 127.0.0.1. All state lives on **hostPath PVs under `~/k3s-data`** on the single NVMe system disk. Nightly DB dumps go to `~/db-backups` (local only).

Health is good right now: 0 failed systemd units, all 39 pods Running, CPU ~3 %, memory 61 %, disk 32 %. The main risks are **no off-host backups**, **plaintext credentials in a README on the server**, **backing-service NodePorts open to the LAN**, a **single point of failure** (one node, one disk), and **~40 GB of reclaimable stale Docker images + 7 GB of data for a scaled-down Prometheus**.

---

## 2. Hardware & OS

| Item | Value |
|---|---|
| CPU | Intel i5-12500T, 6C/12T (12 logical CPUs), idle clock ~22 % |
| RAM | 15 GiB (9.8 used, 5.4 cache, 5.5 available) |
| Swap | 15.7 GiB partition (`nvme1n1p3`), 46 MiB used |
| Disk 1 `nvme1n1` (477 G) | p1 `/boot/efi` 975 M · p2 `/` 460 G ext4 (137 G used, 32 %) · p3 swap |
| Disk 2 `nvme0n1` (238 G) | p1 ext4 mounted `/mnt/storage` — **completely empty (2 MB used)** |
| OS | Debian GNU/Linux 13 (trixie), kernel 6.12.95+deb13 (6.12.105 available) |
| Uptime | 5d 13h (current boot since 2026-10-26 02:40 EDT; previous boot ended 10-25 00:44, ~26 h gap) |
| Temps | 44–45 °C |
| Inodes | 19 % used |

## 3. Network & access

| Interface | Address | Role |
|---|---|---|
| `enp0s31f6` | 192.168.0.103/24 + IPv6 | LAN (router 192.168.0.1); public IP 58.179.152.43 (forwarded) |
| `tailscale0` | 100.109.221.25 | Tailnet (peers: macbook-pro, lightstation, mobile-station, mobilestation) |
| `cni0` / `flannel.1` | 10.42.0.1/24, 10.42.0.0 | k3s pod network (flannel), ~40 veth pairs |
| `docker0` | 172.17.0.1 | Docker, DOWN, no containers |

- **Externally reachable (verified from the Mac):** TCP **22, 80, 443** only. All NodePorts, 6443 and 10250 appear closed/filtered from outside.
- **LAN-reachable (verified from the server to its LAN IP):** NodePorts 30306 (MySQL), 30017 (Mongo), 30898 (Postgres), 30490 (Redis), 30672/31672 (RabbitMQ), 30900 (MinIO), 30770 (Meilisearch), 30333 (Qdrant) are **open to the whole LAN**.
- **SSH (`sshd_config`):** `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`; `X11Forwarding yes` (unneeded). `fail2ban` is running (status unreadable without root).
- **Recent logins:** LAN (192.168.0.1/.121) and external 49.185.158.2, 49.183.37.53, 110.175.221.182 (Oct 27–30; presumably the owner).

## 4. Host-level services (systemd)

Running: `k3s`, `containerd`, **`caddy`**, `docker`, `fail2ban`, `tailscaled`, `ssh`, `cron`, `systemd-timesyncd`, `systemd-journald`. No failed units.

Other host process: `~/apps/k3s-inspector/k3s-inspector --serve --listen 127.0.0.1:8080` (started by hand at 06:00 today, loopback only — reached via SSH tunnel; not a systemd unit).

**k3s config** (`/etc/rancher/k3s/config.yaml`): only `disable: [traefik]`. No Ingress objects, no cert-manager; **TLS is handled entirely by Caddy** (ACME, email in Caddyfile). Default storage class `local-path` plus manual hostPath PVs. `servicelb` is *not* disabled.

**Cron (user `avarile`):** `0 1 * * *` → `~/dev-ops/k3s-deployment/scripts/backup-databases.sh` (log `~/db-backups/backup.log`). Env: `KUBECONFIG=/home/avarile/.kube/config`.
**systemd timers:** apt-daily, apt-daily-upgrade, logrotate, man-db, fstrim, e2scrub, dpkg-db-backup, tmpfiles-clean.

## 5. Public routing (Caddy → NodePort)

Config: `/etc/caddy/Caddyfile` (root-owned; source copies in `~/dev-ops/caddy/` and `~/dev-ops/k3s-deployment/supports/20-reverse-proxy-caddy/`; deploy with `caddy_deploy.sh`; backup `/etc/caddy/Caddyfile.bak`).

| Domain | Upstream | App |
|---|---|---|
| `avarile.com` | static files from `/home/avarile/projects/cybernetics-centralization/` (zstd/gzip, hides `.git`/src, clean URLs, custom 404) | Main website (Next.js export) |
| `www.avarile.com` | redirect → avarile.com | |
| `gitea.avarile.com`, `registry.avarile.com` | 127.0.0.1:30380 | Gitea + container registry (registry hostname must be Cloudflare DNS-only) |
| `drawio.avarile.com` | :30880 | draw.io |
| `blog.avarile.com` | :30368 | Ghost |
| `projects.avarile.com` | :30808 | Plane-based "cybernetics-project" |
| `rag.avarile.com` | :30301 | cybernetics app (port 3001) |
| `cybernetics.avarile.com` | :30300 | cybernetics main app |
| `crm.avarile.com` | :30310 | Twenty-based "cybernetics-crm" |
| `admin.avarile.com` | :30820 | Vaultwarden |
| `agentic.avarile.com` | :30080 | LibreChat-based "cybernetics-agentic-ui" |
| `agentic-admin.avarile.com` | :30081 | LibreChat admin panel; origin answers **only Cloudflare IP ranges** (Cloudflare Access in front) |

TLS (live check): all valid; most expire **2026-12-16** (auto-renew by Caddy), `registry` 2027-01-23. A commented-out `main-website` block remains.

## 6. Kubernetes workloads

Single node `k8s-micro-server` (control-plane, Ready, 119 d old). 15 namespaces, 39 pods, all Running; restart counts (1–5) all date to the 10-26 reboot. No jobs/cronjobs/HPA/ResourceQuota/Ingress/cert-manager.

### 6.1 `infra` — shared backing services (NodePort, hostPath PV, Retain)

| Service | Image | NodePort | PV | Mem now |
|---|---|---|---|---|
| pgvector (Postgres 17) + postgres-exporter | pgvector/pgvector:pg17 | 30898 | 10Gi | 253 Mi |
| mysql 8.4.10 + mysqld-exporter | mysql:8.4.10 | 30306 | 10Gi | 667 Mi |
| mongo 8.0.20 + mongodb_exporter | mongo:8.0.20 | 30017 | 10Gi | 243 Mi |
| redis 7.4 + redis_exporter | redis:7.4-alpine | 30490 | 5Gi | 46 Mi |
| rabbitmq 3.13.7-management | | 30672 / 31672 | 5Gi + 2Gi | 144 Mi (109 m CPU — top CPU pod) |
| minio RELEASE.2025-04-22 | | 30900 / 30901 | 20Gi | 290 Mi |
| qdrant v1.13.4 | | 30333 / 30334 | 10Gi | 53 Mi |
| meilisearch v1.22.1 | | 30770 | 10Gi | 61 Mi |
| prometheus, node-exporter, kube-state-metrics, blackbox-exporter | | 30990 | 10Gi | **scaled to 0** |

Plane reaches DB/Redis/MQ/MinIO through ExternalName aliases (`plane-db`, `plane-redis`, `plane-mq`, `plane-minio`).

### 6.2 Applications

| Namespace | Workloads | Image (build tag) | Notes |
|---|---|---|---|
| `plane` | admin, api, beat-worker, live, proxy, space, web, worker, iframely | `cybernetics-project-*` (2026-10-20; live/proxy 2026-09-23), iframely v1.2.0 | Branded Plane; **worker 996 Mi (highest in cluster)** |
| `twenty` | twenty-server, twenty-worker | `cybernetics-crm` 2026-10-13 | 710 + 768 Mi |
| `librechat` | librechat, admin-panel, rag-api | `cybernetics-agentic-ui-api` 2026-10-24 | rag-api uses pgvector |
| `cybernetics` | cybernetics (3000 app / 3001 RAG) | release 2026-10-31T06:46 | redeployed ~3 h before analysis; 931 Mi |
| `code-interpreter` | api, egress-gateway, file-server, redis, sandbox-runner, service-worker, tool-call-server | `codeapi-*` 2026-08-25 | **sandbox-runner is `privileged` + `/dev/kvm` hostPath**; NetworkPolicies on all components; own `local-path` Redis PVC |
| `gitea` | gitea 1.26.4 | | NodePorts 30380 (web/registry), **30722 (git SSH)**; data 8.8 G |
| `ghost` | ghost:5-alpine | | blog; PV 5Gi |
| `vaultwarden` | 1.37.1-alpine | | `local-path` PVC (the only app on dynamic provisioning besides codeapi-redis) |
| `drawio` | jgraph/drawio 31.0.2 | | |
| `main-website` | `main-website:latest` | | **scaled to 0** (replaced by Caddy static serving) |
| `kube-system` | coredns, local-path-provisioner, metrics-server | | Traefik removed |

Image convention: apps are built on the server with Docker, tagged `release.<UTC timestamp>.1`, mirrored to the Gitea registry `gitea.avarile.com/registry-bot/*`, and pulled by k3s via `registries.yaml`. Upstream images are re-tagged into the same registry (`publish-custom-images.sh`).

### 6.3 Storage (all `Retain`, no snapshots)

17 PVCs, backing dirs under `/home/avarile/k3s-data/<svc>`. On-disk size: gitea 8.8 G · **prometheus 7.2 G** · ghost 429 M · minio 156 M · mysql 109 M · meilisearch 70 M · rabbitmq 24 M · mongo 14 M · redis 6 M · others <2 M. (`postgres` is 999-owned/0700, unreadable here.) The Postgres PV is named `postgres-pv` while the deployment is `pgvector`.

## 7. Folder structure (server)

```
/home/avarile
├── apps/k3s-inspector/            # single Go binary, run by hand on 127.0.0.1:8080
├── backups/                       # 4.5 MB tarball + dir of cybernetics-centralization (2026-10-23)
├── db-backups/                    # nightly dumps: postgres/ mysql/ mongo/ (6 days kept) + backup.log (440 KB)
├── dev-ops/                       # IaC (top level is NOT a git repo; sub-dirs are)
│   ├── caddy/                     # Caddyfile + caddy_deploy.sh
│   ├── docker-deployment/         # legacy docker-compose stack (apps/, infra/, scripts/, .env, own .git) – not running
│   ├── k3s-deployment/            # CURRENT: kustomize manifests (own .git)
│   │   ├── apps/<app>/            # code-interpreter cybernetics drawio ghost gitea librechat main-website plane plane-task twenty vaultwarden
│   │   ├── infra/<svc>/           # postgres mysql mongo redis rabbitmq minio qdrant meilisearch prometheus exporters
│   │   ├── install/               # install-k3s.sh, prepare-storage.sh, configure-hostpaths.sh, cluster.env
│   │   ├── scripts/               # backup-*.sh, new-app.sh, new-infra.sh, rebuild-backend.sh, check-fail2ban.sh, set-lan-ip.sh
│   │   ├── supports/              # numbered host bring-up: 00-host-base 05-static-ip 10-k3s-server-host 20-reverse-proxy-caddy
│   │   │                          #   25-image-registry 30-firewall-nftables 40-fail2ban 90-cluster-reference, restore.sh
│   │   ├── system/                # cert-manager, traefik (unused)
│   │   └── docs/  README.md  migration.md
│   ├── scripts/                   # daily-check.sh, security-check(s).sh, log-cleaner.sh, log-cleanup.log, k3s-operational-commandlist
│   └── README.MD                  # ⚠ contains plaintext credentials
├── k3s-data/                      # ALL persistent volume data (17 GB) — see 6.3
├── k3s-secret-backups/            # 1 secret YAML backup (0700)
├── k3s-state/                     # replicas-20260815.txt (scale-down snapshot)
├── scripts/k3s-graceful-stop.sh   # graceful shutdown helper
├── librechat-release/             # one-off release scratch (jobs, configmap/secret backups, manifest-backups)
├── plane-releases/release.2026-10-20…/
├── projects/                      # btop (upstream), cybernetics-centralization (live website), …centralization.prev, cybernetics-crm (dev), main-website
├── .claude/  .claude.json         # Claude Code state on the server
├── .kube/config  .docker/  .cache/  logs/ (empty)
/mnt/storage                       # empty second NVMe
/etc/caddy/Caddyfile{,.bak}   /etc/rancher/k3s/{config.yaml,k3s.yaml,registries.yaml}
```

## 8. Resource consumption (snapshot)

| Metric | Value |
|---|---|
| Node CPU | 381 m (3 %); load avg ~1.0 |
| Node memory | 9.6 GiB (61 %); `k3s server` 545 MB RSS, containerd 170 MB |
| Requests / limits (cluster) | CPU 6.05 / 29.5 cores (**245 % limit overcommit**); memory 10.3 / 29.3 GiB (65 % requested, **186 %** limits) |
| Top memory pods | plane-worker 996 Mi, cybernetics 931 Mi, twenty-worker 768 Mi, twenty-server 710 Mi, mysql 667 Mi, librechat 526 Mi, iframely 507 Mi, sandbox-runner 353 Mi, plane-api 345 Mi, minio 290 Mi |
| Top CPU pods | rabbitmq 109 m, sandbox-runner 21 m, pgvector 19 m, redis 19 m, cybernetics 17 m |
| Disk `/` | 137 G / 460 G (32 %) |
| `~/k3s-data` | 17 G; `~/db-backups` 155 M; `~/projects` 569 M; `/var/log` 1.1 G (mostly journal) |
| Host Docker images (not used by k3s) | 36 images, **41.8 GB, 96 % reclaimable** |
| Swap | 46 MiB used |

CPU and disk headroom are ample; memory is the tightest resource (5.5 GiB available, limits sum to ~2× RAM — simultaneous spikes could trigger the OOM killer).

## 9. Backups & recovery

- **Exists:** nightly logical dumps of Postgres, MySQL and Mongo (cron 01:00 local, 6 daily copies kept); one-off tarballs in `~/backups`; one secret backup; `supports/restore.sh` and documented bring-up in `supports/`.
- **Not covered:** MinIO, Gitea repos/registry (8.8 G), Ghost content, Vaultwarden vault (SQLite on `local-path`), Qdrant, Meilisearch, RabbitMQ, Redis, Caddy ACME state, k3s datastore snapshots. **Nothing is copied off the machine.** The empty 238 GB `/mnt/storage` is an obvious second local target, but still the same box.
- No evidence that a restore has ever been tested.

## 10. Current issues (ranked)

### High
1. **Plaintext credentials on the server.** `~/dev-ops/README.MD` lists usernames and a reused password for Gitea, Plane and Ghost (not reproduced here). `.env` files also exist (`docker-deployment/.env`, `docker-deployment/infra/.env`, `k3s-deployment/install/cluster.env`) and `~/.bash_history` (39 KB) may hold secrets. *Action:* rotate the reused password everywhere, move credentials to Vaultwarden / k8s Secrets, delete them from the README.
2. **No off-site backup; single disk, single node.** See §9.
3. **Backing-service NodePorts exposed to the whole LAN.** MySQL, Postgres, Mongo, Redis, RabbitMQ, MinIO, Qdrant, Meilisearch accept connections from any LAN host. Not reachable from the internet today, but that relies on the router and on an nftables ruleset I could not verify. The Caddyfile header itself lists this as an unresolved TODO. *Action:* `kube-proxy-arg=nodeport-addresses=127.0.0.1` (Caddy, SSH tunnel and Tailscale suffice) or confirm nftables drops 30000–32767 from non-loopback.
4. **Meilisearch runs with `MEILI_ENV=development`** — the master key is not enforced. Switch to `production` (key already in a Secret).
5. **`codeapi-sandbox-runner` is privileged with `/dev/kvm`.** Intended for the sandbox, but it is a host-escape blast radius on the node that also holds the vault. Keep its NetworkPolicies; consider isolating it.

### Medium
6. **Pending OS updates:** kernel 6.12.105 and security updates (openssl/libssl, util-linux, bind9, expat, python3.13), Docker 29.6.1→29.7.2, containerd.io 2.2.6→2.3.3. Kernel needs a reboot.
7. **Stale log-cleanup job.** `~/dev-ops/scripts/log-cleanup.log` is full of `…/log-cleanup.sh: not found` — something (possibly a root crontab) still calls the old name; the script is now `log-cleaner.sh`. Needs sudo to confirm.
8. **Resource limits.** Limits total 186 % of RAM; `local-path-provisioner` has no requests/limits and `metrics-server` has no limits. No ResourceQuota/LimitRange.
9. **Documentation drift.** `k3s-deployment/README.md` says "Fedora 42" and "Traefik ships with k3s"; the host is Debian 13 with Traefik disabled and Caddy in front. The Caddyfile header still says "topology undecided" and its step C (disable servicelb) is not applied. `docker-deployment/` is a legacy stack.
10. **Uncommitted work on the production web root.** `~/projects/cybernetics-centralization` (served for avarile.com) has 120 uncommitted changes (`.prev` copy 78). `dev-ops/` top level and `projects/main-website` are not git repos.
11. **Ghost readiness probe warning** (only warning event in cluster): probe over http receives a 301 to https. Harmless; send `X-Forwarded-Proto: https` in the probe.
12. **Everything is single-replica** on one node; any restart or reboot is user-visible downtime (the 10-25/26 reboot window was ~26 h).

### Low
13. `X11Forwarding yes`; `/mnt/storage` unused; `k3s-inspector` not under systemd; Claude Code auth state stored on the server.
14. Monitoring effectively off: Prometheus, node-exporter, kube-state-metrics, blackbox-exporter at 0 replicas (only DB sidecar exporters run). No alerting.
15. nftables and fail2ban state unverified (root needed); repo has `supports/30-firewall-nftables` and `40-fail2ban`, but whether they're installed is unknown.

## 11. Cleanup opportunities

| Item | Size / effect | Suggested action |
|---|---|---|
| Host Docker images (36, 0 in use; duplicates via `gitea.avarile.com/registry-bot/*` retags; old tags e.g. agentic-ui-api 10-22, crm 09-17, codeapi-* 08-25, makeplane `*-commercial` v2.6.3 ≈ 9 GB) | **≈ 40 GB** | `docker image prune -a` after confirming the Gitea registry holds what you need; keep the last 2 releases per app as rollback |
| `~/k3s-data/prometheus` + scaled-to-0 monitoring stack | 7.2 GB | Revive with a retention flag (recommended) or delete PV + manifests |
| `projects/cybernetics-centralization.prev` | small | Commit the live copy, then archive/delete |
| `~/backups`, `~/librechat-release`, `~/plane-releases`, `~/k3s-state`, `~/k3s-secret-backups` | <10 MB | Archive into a dated folder; move secret backups to the vault |
| `dev-ops/docker-deployment` (legacy compose) | 7 MB | Archive once k3s is confirmed the only runtime |
| `main-website` deployment (0 replicas), commented Caddy block, `postgres-pv` naming | — | Remove or document |
| `~/db-backups/backup.log` | 440 KB, grows daily (verbose mongodump) | logrotate or quieter flags |
| `/var/log/journal` | ~1.1 GB on disk | `sudo journalctl --vacuum-size=200M`; set `SystemMaxUse=` |
| Old kernels 6.12.63 and 6.12.94 | ~1 GB | `sudo apt autoremove` after next reboot |
| Empty `~/logs`, `.bashrc.bak.20260716` | trivial | Tidy |

## 12. Recommended action plan

1. **Today:** rotate the reused password, scrub README / bash history; set `MEILI_ENV=production`.
2. **This week:** bind NodePorts to loopback (or verify nftables); `apt full-upgrade` + reboot via `~/scripts/k3s-graceful-stop.sh`; prune Docker images.
3. **This month:** extend backups to MinIO, Gitea, Ghost, Vaultwarden, Qdrant, Meilisearch and k3s datastore; ship off-site (restic/rclone to object storage); run one restore test; use `/mnt/storage` as a second local copy.
4. **Then:** revive Prometheus with retention + alerts (disk, memory, pod restarts, cert expiry, backup age); set memory limits; commit configs and reconcile docs with reality.

---

## Appendix A — Handy commands for a future skill

```bash
ssh K3s-server                                   # key-only; sudo needs a password
kubectl get pods -A -o wide; kubectl top nodes; kubectl top pods -A --sort-by=memory
kubectl get pv,pvc,svc -A
systemctl status k3s caddy containerd
bash ~/dev-ops/caddy/caddy_deploy.sh             # deploy Caddyfile (reloads caddy)
~/dev-ops/k3s-deployment/scripts/backup-now.sh   # on-demand DB dump
~/scripts/k3s-graceful-stop.sh                   # before reboot/maintenance
docker images; docker system df                  # server is also the image build host
tailscale status
```

## Appendix B — NodePort map

30300/30301 cybernetics · 30310 twenty CRM · 30080 librechat · 30081 librechat admin · 30368 ghost · 30380 gitea web+registry · 30722 gitea SSH · 30587 main-website (off) · 30808 plane · 30820 vaultwarden · 30880 drawio · 30017 mongo · 30306 mysql · 30898 postgres · 30490 redis · 30672/31672 rabbitmq · 30900/30901 minio · 30333/30334 qdrant · 30770 meilisearch · 30990 prometheus (off)

## Appendix C — Verification gaps (need `sudo`)

`sudo nft list ruleset`, `sudo fail2ban-client status`, `sudo cat /etc/rancher/k3s/registries.yaml`, `sudo crictl images`, `sudo journalctl -p err -b`, `sudo du -sh /var/lib/rancher /var/lib/docker`, `sudo crontab -l`, `sudo smartctl -a /dev/nvme0n1 /dev/nvme1n1` (disk health), unattended-upgrades status.
