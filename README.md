# Thunderbird Maintenance Tool

A safe and advanced maintenance utility for Mozilla Thunderbird.

The tool focuses on:

- profile cleanup
- cache/index rebuilding
- responsiveness optimization
- profile diagnostics
- safe backup creation
- corruption detection
- oversized mailbox detection
- SQLite validation
- performance recommendations

The tool NEVER deletes actual email content.

---

# Features

## Safe Operations

The tool safely removes ONLY rebuildable cache/index files:

- `.msf`
- `global-messages-db.sqlite`
- `folderTree.json`
- `xulstore.json`
- `session.json`
- `cache2/`
- `startupCache/`

Optional advanced cleanup:

- `panacea.dat`
- `OfflineCache/`

with explicit user confirmation.

---

# Additional Diagnostics

- detects giant mbox files
- detects suspicious zero-byte indexes
- SQLite integrity checks
- Thunderbird process detection
- profile size analysis
- folder statistics
- health score generation
- orphaned cache detection
- antivirus recommendations

---

# Safety Design

The tool:

- NEVER deletes real mail containers
- NEVER deletes prefs.js
- NEVER deletes passwords/certificates
- automatically creates backups
- creates detailed logs
- supports dry-run mode

---

# Requirements

- Python 3.10+
- Windows recommended

Install dependencies:

```bash
pip install -r requirements.txt
````

---

# Usage

## Analyze only

```bash
python thunderbird_maintenance.py --dry-run
```

## Full maintenance

```bash
python thunderbird_maintenance.py
```

## Custom backup path

```bash
python thunderbird_maintenance.py --backup D:\\TBBackup
```

---

# Recommended Thunderbird Settings

For best performance:

1. Disable global indexing
2. Reduce offline synchronization
3. Compact folders regularly
4. Avoid huge Inbox folders
5. Exclude Thunderbird profile from antivirus scanning

---

# Important Notes

The first Thunderbird startup after maintenance may be slower.

Thunderbird rebuilds indexes automatically.

Subsequent startups are usually much faster.

After, Unified foldler may be gone (invisible). To show it again, go to Thunderbird settings --> View --> Folders --> Unified Folders. Then, move it up to the top of the folder list.