# MacBook Pro — Local PostgreSQL, pgvector & Redis via MacPorts

- **Checked:** 2026-11-07 on the local MacBook Pro (macOS 13.7.8 Ventura, Darwin 22.6.0, Apple Silicon `arm64`)
- **Package manager:** MacPorts 2.12.6 at `/opt/local/bin/port`. The port index is more than two weeks old (`sudo port selfupdate` recommended), so the versions below may lag slightly.
- **Scope:** whether PostgreSQL, Redis and pgvector can be installed with MacPorts, how pgvector was built, verification results, and the setup steps still outstanding.

---

## 1. Summary

| Component | MacPorts? | Status on this Mac |
|---|---|---|
| PostgreSQL 18 | ✅ `postgresql18` + `postgresql18-server` @18.6 | **Installed**, but the database cluster is **not initialised** and the server is **not running** |
| pgvector | ❌ no port exists | **Built from source** against MacPorts PG18 → v**0.8.7**, verified working |
| Redis 7.4 | ✅ `redis7` @7.4.11 (also `redis` @8.8.0, `valkey` @9.1.2) | **Installed and running** (v7.4.11, `localhost:6379`, starts at boot), `redis-cli ping` → `PONG` |

Outstanding work: initialise and start PostgreSQL (§4), set `port select` (§4), and decide whether to keep Postgres.app (§6). Redis is done (§5).

---

## 2. MacPorts availability

### PostgreSQL
PostgreSQL comes as two ports: `postgresqlNN` (client and libraries) and `postgresqlNN-server` (server and launchd job).

| Version | Port |
|---|---|
| 18.6 (latest stable) | `postgresql18`, `postgresql18-server` |
| 17.11 | `postgresql17`, `postgresql17-server` |
| 16.15 | `postgresql16`, `postgresql16-server` |
| 10 – 15 | `postgresql10…15-server` (older, still available) |
| 19beta3 | `postgresql19-devel-server` (pre-release, not for production) |

The only PostgreSQL extension ports MacPorts has are PostGIS (`postgis` @3.6.4, `postgis2`, `postgis3`).

### Redis
| Port | Version | Notes |
|---|---|---|
| `redis` | 8.8.0 | Upstream Redis, current major |
| `redis7` | 7.4.11 | Redis 7.4 line, a sub-port of `redis` (**installed**) |
| `valkey` | 9.1.2 | Linux Foundation open-source fork of Redis, protocol-compatible |

All support `darwin` (Ventura OK). `redis` and `redis7` conflict, so only one can be installed at a time.

Licensing: Redis 7.4 is RSALv2/SSPLv1 (`port notes redis7` says so; the port's `License:` field says AGPL-3, which only applies to Redis 8+). Redis 8 is tri-licensed and includes AGPLv3. Valkey is BSD-3 (`port install valkey +redis_compat` gives drop-in `redis-*` binaries).

### pgvector
No port exists: `port search pgvector` and description searches turn up nothing, and there is no `postgresqlNN-pgvector`. The alternatives are building from source (the chosen route), Homebrew `pgvector` (which brings its own PostgreSQL), or the `pgvector/pgvector:pg18` Docker image.

---

## 3. pgvector — build & verification

### Build (from source, against MacPorts PG18)
```sh
git clone https://github.com/pgvector/pgvector.git
cd pgvector
git checkout $(git describe --tags --abbrev=0)   # latest release tag

make PG_CONFIG=/opt/local/lib/postgresql18/bin/pg_config
sudo make install PG_CONFIG=/opt/local/lib/postgresql18/bin/pg_config
```

> Rebuild after every **major** PostgreSQL upgrade (e.g. 18 → 19). Minor updates (18.x) don't need it.

### Installed files
| Item | Path |
|---|---|
| Shared library | `/opt/local/lib/postgresql18/vector.dylib` (Mach-O 64-bit bundle, arm64) |
| Control file | `/opt/local/share/postgresql18/extension/vector.control` (`default_version = '0.8.7'`) |
| SQL scripts | `/opt/local/share/postgresql18/extension/vector--*.sql` |
| `pg_config` | `/opt/local/lib/postgresql18/bin/pg_config` (`--pkglibdir` = `/opt/local/lib/postgresql18`, `--sharedir` = `/opt/local/share/postgresql18`) |

### Verification (2026-11-07)
These tests ran on a throwaway cluster (`initdb` in a temp directory, TCP `localhost:54329`), which was stopped and deleted afterwards. The real system was not changed.

| Test | Result |
|---|---|
| `CREATE EXTENSION vector` | ✅ `extversion = 0.8.7` |
| `vector(3)` column, insert, nearest-neighbour `ORDER BY embedding <-> …` | ✅ correct ordering |
| L2 `<->` and cosine `<=>` distance operators | ✅ correct values |
| HNSW index (`vector_l2_ops`) | ✅ builds; planner uses `Index Scan` |
| IVFFlat index (`vector_cosine_ops`) | ✅ builds |
| `halfvec`, `sparsevec`, `bit` Hamming `<~>` | ✅ |

Smoke test you can re-run in any database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT extversion FROM pg_extension WHERE extname = 'vector';
SELECT '[1,2,3]'::vector <-> '[3,1,2]'::vector AS l2_distance;   -- 2.449…
```

> Gotcha: Unix-socket paths are limited to ~103 characters on macOS. A cluster started with `-k <long path>` will fail to start, so use a short socket directory or TCP (`-k '' -c listen_addresses=localhost`).

---

## 4. PostgreSQL 18 — remaining setup

Current state:
- Ports `postgresql18 @18.6_0`, `postgresql18-server @18.6_0`, `postgresql_select-18` are active.
- `/opt/local/var/db/postgresql18/` does **not exist**, so there is no cluster yet.
- The launchd plist is linked at `/Library/LaunchDaemons/org.macports.postgresql18-server.plist`, but with no data directory the server isn't running.
- `port select --show postgresql` is `none`, so `psql` etc. aren't on `PATH` (use the full path `/opt/local/lib/postgresql18/bin/`).

Steps:
```sh
# 1. initialise the cluster
sudo mkdir -p /opt/local/var/db/postgresql18/defaultdb
sudo chown postgres:postgres /opt/local/var/db/postgresql18/defaultdb
sudo -u postgres /opt/local/lib/postgresql18/bin/initdb -D /opt/local/var/db/postgresql18/defaultdb

# 2. start now and at boot
sudo port reload postgresql18-server      # or: sudo port load postgresql18-server

# 3. put psql/pg_dump/etc. on PATH
sudo port select --set postgresql postgresql18

# 4. enable pgvector per database
psql -U postgres -c 'CREATE EXTENSION vector;'
```

Run `port notes postgresql18-server` for the port's own notes on paths.

Useful commands:
| Task | Command |
|---|---|
| Stop / disable at boot | `sudo port unload postgresql18-server` |
| Start / enable at boot | `sudo port load postgresql18-server` |
| Server log | under the data dir / see `port notes postgresql18-server` |
| Status | `sudo -u postgres /opt/local/lib/postgresql18/bin/pg_ctl -D /opt/local/var/db/postgresql18/defaultdb status` |

---

## 5. Redis 7.4 — installed

Installed and verified 2026-11-07:
```sh
sudo port install redis7
redis-server --version        # Redis server v=7.4.11 … malloc=jemalloc-5.3.0 bits=64
sudo port load redis7         # start now and at boot (launchd)
redis-cli ping                # PONG
```

| Item | Path / value |
|---|---|
| Binaries | `/opt/local/bin/redis-server`, `redis-cli`, `redis-sentinel`, `redis-benchmark`, `redis-check-aof`, `redis-check-rdb` |
| Config | `/opt/local/etc/redis.conf` (a copy of `redis.conf.sample`; `sentinel.conf.sample` is there too) |
| Data dir | `/opt/local/var/db/redis` |
| Log | `/opt/local/var/log/redis.log` |
| launchd plist | `/Library/LaunchDaemons/org.macports.redis7.plist` |
| Listening | `127.0.0.1` and `::1`, port `6379`, `protected-mode yes`, no password |

Useful commands:
| Task | Command |
|---|---|
| Stop / disable at boot | `sudo port unload redis7` |
| Start / enable at boot | `sudo port load redis7` |
| Restart after editing `redis.conf` | `sudo port reload redis7` |
| Run in the foreground instead of launchd | `redis-server /opt/local/etc/redis.conf` |
| Server info | `redis-cli info server` |

> Moving to Redis 8 later: `sudo port unload redis7 && sudo port uninstall redis7 && sudo port install redis && sudo port load redis`. The data dir is shared, but back up `dump.rdb` first.

---

## 6. Notes & risks

- **Postgres.app is also present.** Its login helper `com.postgresapp.Postgres2LoginHelper` is registered with launchd. It wasn't running during the check, but if it starts it will compete with MacPorts PostgreSQL for port **5432**. Either remove it or move one server to another port.
- **Stale port index.** Run `sudo port selfupdate && sudo port upgrade outdated` to pick up newer patch releases (e.g. of `redis7` or `postgresql18`).
- **pgvector is outside MacPorts.** `port upgrade` won't update it. Track pgvector releases yourself and rebuild with the `make` commands in §3. A PostgreSQL *major* upgrade requires a rebuild before `CREATE EXTENSION`/`ALTER EXTENSION vector UPDATE` will work.
- **Upgrading pgvector** in existing databases after a rebuild: `ALTER EXTENSION vector UPDATE;`
