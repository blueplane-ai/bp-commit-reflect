# ADR-003: Multiple Storage Backends

## Status

Accepted

## Context

Commit reflections need to be persisted for various use cases:

1. **Personal analytics**: Developers want to query their own patterns over time
2. **Team sharing**: Teams may want to share insights and aggregate data
3. **Version control**: Reflections tied to specific commits should travel with code
4. **Portability**: Data should be easy to export, backup, and migrate
5. **Querying**: Some use cases need structured queries, others need simple logs

Different storage mechanisms have different trade-offs:

- **Git commit messages**: Keep reflection with code history, visible in `git log`
- **JSONL files**: Simple, portable, version-controllable, human-readable
- **SQLite database**: Rich querying, analytics, full-text search
- **Cloud storage**: Team aggregation, centralized analytics (future)

We need to decide how many storage backends to support and how to configure them.

## Decision

We will support **three storage backends** that can be used simultaneously or individually:

### 1. JSONL (JSON Lines) - Default, Always Enabled

Append-only log file where each line is a complete JSON object representing one reflection.

**Default path:** `.commit-reflections.jsonl` (project root)

**Format:**
```json
{"timestamp":"2025-11-22T10:30:00Z","project":"my-app","commit_hash":"a1b2c3d","reflections":{...}}
```

**Use cases:**
- Version control (check in with repo)
- Team sharing (everyone sees same file)
- Simple querying with `grep`, `jq`, etc.
- Easy backup and export
- Human-readable logs

### 2. SQLite Database - Optional

Structured database for rich querying and analytics.

**Default path:** `~/.commit-reflect/reflections.db` (user home)

**Schema:**
```sql
CREATE TABLE reflections (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp DATETIME NOT NULL,
  project TEXT NOT NULL,
  branch TEXT NOT NULL,
  commit_hash TEXT NOT NULL UNIQUE,
  commit_message TEXT,
  files_changed TEXT, -- JSON array
  ai_synergy INTEGER CHECK(ai_synergy BETWEEN 1 AND 5),
  confidence INTEGER CHECK(confidence BETWEEN 1 AND 5),
  experience TEXT CHECK(LENGTH(experience) <= 512),
  blockers TEXT,
  learning TEXT,
  metadata TEXT -- JSON
);
```

**Use cases:**
- Cross-project analytics
- Time-series queries
- Pattern detection
- Aggregation and reporting
- Full-text search

### 3. Amended Git Commit Messages - Optional

Append structured reflection to the commit message body.

**Format:**
```
Add JWT authentication middleware

Initial commit message here.

---
Commit Reflection:
AI Synergy: 4/5
Confidence: 5/5
Experience: Felt smooth once I got into it...
Blockers: Unclear documentation on refresh token storage
Learning: Learned about HttpOnly cookies
```

**Use cases:**
- Keep reflection with code forever
- No separate files to manage
- Visible in `git log`, GitHub UI
- Reflection tied to specific commit

**Configuration:**

All backends are configured via `.commit-reflect.json`:

```json
{
  "storage": ["jsonl", "database", "git"],
  "jsonl_path": ".commit-reflections.jsonl",
  "db_path": "~/.commit-reflect/reflections.db",
  "amend_commit": false  // dangerous, opt-in only
}
```

**Default behavior:** JSONL only (safest, most portable)

## Consequences

### Positive

- **Flexibility**: Users choose storage that fits their workflow
- **Data portability**: JSONL provides simple export format
- **Rich querying**: SQLite enables complex analytics
- **Git integration**: Amended commits keep reflection with code history
- **Incremental adoption**: Start with JSONL, add SQLite later for analytics
- **Team collaboration**: JSONL in repo enables shared team insights
- **No vendor lock-in**: All formats are open and portable

### Negative

- **Complexity**: Three backends to implement, test, and maintain
- **Potential inconsistency**: If one backend fails, data may be incomplete
- **Git amend risks**: Amending commits can cause issues with pushed commits
- **Storage duplication**: Same data stored multiple times if multiple backends enabled
- **Configuration complexity**: Users must understand trade-offs of each option

### Neutral

- **Disk usage**: Multiple backends use more space (minimal impact for text data)
- **Performance**: Writing to multiple backends adds latency (acceptable for post-commit)
- **Sync responsibility**: Users must manage keeping JSONL and SQLite in sync if both used

## Alternatives Considered

### Single Storage Backend (JSONL Only)

Only support JSONL files, no database or git integration.

**Pros:**
- Simple implementation
- Easy to understand
- Portable and version-controllable

**Cons:**
- No rich querying without external tools
- Cross-project analytics requires parsing all JSONL files
- No structured schema enforcement
- Hard to build analytics tools

**Why rejected:** Too limiting for analytics use cases, which are core to value proposition.

### Single Storage Backend (SQLite Only)

Only support SQLite database.

**Pros:**
- Rich querying built-in
- Strong schema enforcement
- Excellent analytics capabilities
- Battle-tested reliability

**Cons:**
- Binary format, not human-readable
- Hard to version control
- Difficult to share with team
- Merge conflicts impossible to resolve
- Not portable across systems

**Why rejected:** Poor team collaboration story, not version-controllable.

### Cloud Storage Only

Store all reflections in cloud service (S3, Firebase, etc.).

**Pros:**
- Centralized team data
- Easy aggregation
- Built-in backup
- Could enable web dashboard

**Cons:**
- Requires network connectivity
- Privacy and security concerns
- Vendor lock-in
- Cost for storage
- Overkill for single developer
- Can't work offline

**Why rejected:** Too complex for MVP, defeats "simple journaling" goal.

### PostgreSQL/MySQL Support

Support full relational databases in addition to SQLite.

**Pros:**
- Multi-user support
- Better concurrency
- Larger data capacity

**Cons:**
- Requires running database server
- Complex setup for simple tool
- Overkill for personal reflections
- Deployment and maintenance burden

**Why rejected:** SQLite sufficient for personal use, can add PostgreSQL later if team features needed.

### Filesystem Hierarchy (Individual JSON Files)

Store each reflection as separate JSON file in directory structure like `.reflections/2025/11/22/a1b2c3d.json`.

**Pros:**
- Easy to find individual reflections
- Good for version control (smaller diffs)
- Simple file-per-reflection model

**Cons:**
- Many small files create clutter
- Slower to query (must read many files)
- File system overhead
- Harder to aggregate

**Why rejected:** JSONL provides better performance and simpler aggregation.

## Implementation Notes

### Write Strategy

1. Validate reflection data against schema
2. Write to all configured backends in parallel
3. If any backend fails, log warning but continue (best-effort)
4. Return success if at least one backend succeeded
5. Include backend status in completion response

### Read Strategy (for `get_recent_reflections`)

1. Prefer SQLite if available (fastest queries)
2. Fall back to JSONL parsing if no database
3. Git commit messages are write-only (not queried)

### Error Handling

- **JSONL write fail**: Log error, continue (likely permissions issue)
- **SQLite write fail**: Log error, continue (database may not exist)
- **Git amend fail**: Log error, continue (may be dangerous amend scenario)
- **All backends fail**: Return error to user, suggest checking permissions

### Migration Path

Provide CLI command to migrate data between backends:

```bash
commit-reflect migrate --from jsonl --to database
commit-reflect export --format csv --output reflections.csv
```

## References

- [JSONL Specification](https://jsonlines.org/)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Git Commit Message Best Practices](https://chris.beams.io/posts/git-commit/)
- ADR-001: CLI-First Architecture
