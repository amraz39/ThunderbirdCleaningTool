"""
===========================================================
Thunderbird Maintenance Tool
===========================================================

Safe advanced maintenance utility for Mozilla Thunderbird.

MAIN GOALS:
- improve responsiveness
- clean rebuildable cache/index structures
- detect corruption risks
- analyze profile health
- preserve all actual emails

THIS TOOL NEVER DELETES:
- actual mail containers
- prefs.js
- passwords
- certificates
- address books

IMPORTANT:
Close Thunderbird before running.

===========================================================
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import psutil

# ===========================================================
# CONFIGURATION
# ===========================================================

DEFAULT_BACKUP_ROOT = Path(r"E:\ThunderbirdBackup")
REPORTS_DIR = Path("reports")

SAFE_DELETE_FILES = {
    "global-messages-db.sqlite",
    "folderTree.json",
    "xulstore.json",
    "session.json",
}

SAFE_DELETE_DIRS = {
    "cache2",
    "startupCache",
}

OPTIONAL_DELETE_FILES = {
    "panacea.dat",
}

OPTIONAL_DELETE_DIRS = {
    "OfflineCache",
}

NEVER_DELETE = {
    "prefs.js",
    "key4.db",
    "cert9.db",
    "logins.json",
    "abook.sqlite",
}

# ===========================================================
# LOGGING
# ===========================================================

logger = logging.getLogger("tbmaint")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(message)s",
    "%H:%M:%S"
))

logger.addHandler(console_handler)

# ===========================================================
# UTILITIES
# ===========================================================


def human_size(size: int) -> str:
    """Convert bytes to human-readable string."""

    units = ["B", "KB", "MB", "GB", "TB"]

    size = float(size)

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"



def sha256sum(path: Path) -> str:
    """Generate SHA256 checksum for integrity tracking."""

    sha = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)

    return sha.hexdigest()


# ===========================================================
# THUNDERBIRD DETECTION
# ===========================================================


def thunderbird_running() -> bool:
    """
    Detect whether Thunderbird is currently running.

    Maintenance should never run against live profile data.
    """

    for proc in psutil.process_iter(["name"]):

        try:
            name = proc.info["name"]

            if name and "thunderbird" in name.lower():
                return True

        except Exception:
            continue

    return False


# ===========================================================
# PROFILE DISCOVERY
# ===========================================================


def get_profile_root() -> Path:
    """Locate Thunderbird profile directory."""

    appdata = os.getenv("APPDATA")

    if not appdata:
        raise RuntimeError("APPDATA environment variable missing")

    path = Path(appdata) / "Thunderbird" / "Profiles"

    if not path.exists():
        raise RuntimeError(f"Thunderbird profiles not found: {path}")

    return path



def discover_profiles() -> list[Path]:
    """Return all Thunderbird profiles."""

    root = get_profile_root()

    return [p for p in root.iterdir() if p.is_dir()]


# ===========================================================
# ANALYSIS
# ===========================================================


def analyze_profile(profile: Path) -> dict:
    """
    Analyze Thunderbird profile structure.

    Collect:
    - total size
    - largest files
    - mbox statistics
    - SQLite statistics
    - suspicious files
    """

    stats = {
        "profile": profile.name,
        "size": 0,
        "msf_count": 0,
        "sqlite_count": 0,
        "mail_containers": 0,
        "large_mbox": [],
        "largest_files": [],
        "zero_byte_indexes": [],
        "health_score": 100,
    }

    all_files = []

    for path in profile.rglob("*"):

        if not path.is_file():
            continue

        try:
            size = path.stat().st_size
        except Exception:
            continue

        stats["size"] += size
        all_files.append((size, path))

        suffix = path.suffix.lower()

        if suffix == ".msf":
            stats["msf_count"] += 1

            if size == 0:
                stats["zero_byte_indexes"].append(str(path))
                stats["health_score"] -= 5

        if suffix == ".sqlite":
            stats["sqlite_count"] += 1

        # mbox detection
        if suffix == "":
            stats["mail_containers"] += 1

            if size > 1 * 1024 * 1024 * 1024:
                stats["large_mbox"].append({
                    "file": str(path),
                    "size": size,
                })
                stats["health_score"] -= 10

    all_files.sort(reverse=True)

    stats["largest_files"] = [
        {
            "file": str(path),
            "size": size,
        }
        for size, path in all_files[:20]
    ]

    if stats["size"] > 10 * 1024 * 1024 * 1024:
        stats["health_score"] -= 15

    return stats


# ===========================================================
# SQLITE VALIDATION
# ===========================================================


def validate_sqlite(profile: Path):
    """Run SQLite integrity checks."""

    logger.info("Checking SQLite integrity...")

    for db in profile.rglob("*.sqlite"):

        try:
            conn = sqlite3.connect(db)
            cur = conn.cursor()

            cur.execute("PRAGMA integrity_check;")
            result = cur.fetchone()

            if result and result[0] == "ok":
                logger.info(f"OK SQLite: {db.name}")
            else:
                logger.warning(f"SQLite integrity warning: {db}")

            conn.close()

        except Exception as e:
            logger.warning(f"SQLite check failed: {db} -> {e}")


# ===========================================================
# BACKUP
# ===========================================================


def backup_profile(profile: Path, backup_root: Path) -> Path:
    """
    Create full profile backup.

    Uses timestamped backup directories.
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_target = backup_root / f"{profile.name}_{timestamp}"

    logger.info(f"Creating backup: {backup_target}")

    shutil.copytree(profile, backup_target)

    logger.info("Backup completed")

    return backup_target


# ===========================================================
# CLEANUP
# ===========================================================


def delete_path(path: Path, dry_run=False):
    """Delete file or directory safely."""

    if dry_run:
        logger.info(f"[DRY RUN] Would delete: {path}")
        return

    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)



def cleanup_profile(profile: Path, dry_run=False):
    """
    Perform safe cleanup.

    ONLY removes rebuildable caches/indexes.
    """

    logger.info("Starting cleanup...")

    deleted = 0

    # Delete MSF indexes
    for msf in profile.rglob("*.msf"):

        try:
            logger.info(f"Deleting MSF: {msf}")
            delete_path(msf, dry_run)
            deleted += 1

        except Exception as e:
            logger.warning(f"Failed deleting {msf}: {e}")

    # Safe file cleanup
    for path in profile.rglob("*"):

        name = path.name

        if name in NEVER_DELETE:
            continue

        if name in SAFE_DELETE_FILES:
            logger.info(f"Deleting safe file: {path}")
            delete_path(path, dry_run)
            deleted += 1

        if name in SAFE_DELETE_DIRS:
            logger.info(f"Deleting cache dir: {path}")
            delete_path(path, dry_run)
            deleted += 1

    return deleted


# ===========================================================
# OPTIONAL ADVANCED CLEANUP
# ===========================================================


def optional_cleanup(profile: Path, dry_run=False):
    """
    Perform optional cleanup requiring confirmation.
    """

    logger.info("Optional cleanup phase")

    answer = input(
        "Delete optional rebuildable caches like panacea.dat? (yes/no): "
    ).strip().lower()

    if answer != "yes":
        logger.info("Optional cleanup skipped")
        return

    for path in profile.rglob("*"):

        name = path.name

        if name in OPTIONAL_DELETE_FILES:
            logger.info(f"Deleting optional file: {path}")
            delete_path(path, dry_run)

        if name in OPTIONAL_DELETE_DIRS:
            logger.info(f"Deleting optional dir: {path}")
            delete_path(path, dry_run)


# ===========================================================
# REPORTING
# ===========================================================


def save_report(report: dict):
    """Save JSON maintenance report."""

    REPORTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report_file = REPORTS_DIR / f"report_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Report saved: {report_file}")


# ===========================================================
# MAIN
# ===========================================================


def main():

    parser = argparse.ArgumentParser(
        description="Thunderbird Maintenance Tool"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Analyze only, do not delete anything"
    )

    parser.add_argument(
        "--backup",
        type=str,
        default=str(DEFAULT_BACKUP_ROOT),
        help="Backup directory"
    )

    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)

    log_file = REPORTS_DIR / (
        f"maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s %(message)s"
    ))

    logger.addHandler(file_handler)

    logger.info("Thunderbird Maintenance Tool")

    if thunderbird_running():
        logger.error("Thunderbird is currently running")
        logger.error("Close Thunderbird before maintenance")
        sys.exit(1)

    profiles = discover_profiles()

    if not profiles:
        logger.error("No Thunderbird profiles found")
        sys.exit(1)

    logger.info(f"Found {len(profiles)} profile(s)")

    report = {
        "timestamp": datetime.now().isoformat(),
        "profiles": [],
    }

    backup_root = Path(args.backup)
    backup_root.mkdir(parents=True, exist_ok=True)

    for profile in profiles:

        logger.info("=" * 70)
        logger.info(f"PROFILE: {profile.name}")
        logger.info("=" * 70)

        before = analyze_profile(profile)

        logger.info(
            f"Profile size: {human_size(before['size'])}"
        )

        logger.info(
            f"Health score: {before['health_score']}/100"
        )

        validate_sqlite(profile)

        if before["large_mbox"]:
            logger.warning("Large mailbox files detected")

            for item in before["large_mbox"]:
                logger.warning(
                    f"{human_size(item['size'])} -> {item['file']}"
                )

        answer = input(
            f"Proceed with maintenance for {profile.name}? (yes/no): "
        ).strip().lower()

        if answer != "yes":
            logger.info("Skipped profile")
            continue

        backup_profile(profile, backup_root)

        deleted = cleanup_profile(profile, args.dry_run)

        optional_cleanup(profile, args.dry_run)

        after = analyze_profile(profile)

        profile_report = {
            "profile": profile.name,
            "before": before,
            "after": after,
            "deleted_items": deleted,
        }

        report["profiles"].append(profile_report)

        logger.info("Maintenance completed")

    save_report(report)

    logger.info("DONE")
    logger.info(f"Detailed log: {log_file}")


if __name__ == "__main__":
    main()
