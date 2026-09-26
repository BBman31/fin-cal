"""Import an existing budget workbook into data/settings.yaml + data/spending_log.xlsx.

Usage:
    uv run python scripts/import_template.py path/to/workbook.xlsx [--out data] [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fincal import storage
from fincal.importer import read_log, read_settings, write_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--out", type=Path, default=storage.PROJECT_ROOT / "data")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args(argv)

    settings_file = storage.settings_path(args.out)
    log_file = storage.log_path(args.out)
    existing = [p for p in (settings_file, log_file) if p.exists()]
    if existing and not args.force:
        print(f"Refusing to overwrite {', '.join(map(str, existing))} (use --force)")
        return 1

    settings, warnings = read_settings(args.workbook)
    for w in warnings:
        print(f"warning: {w}")
    try:
        storage.save_settings(settings, settings_file)
    except storage.SettingsError as e:
        print(f"error: settings are invalid, nothing written: {e}")
        return 1
    log = read_log(args.workbook, settings)
    write_log(log, log_file)

    print(f"Wrote {settings_file}")
    print(f"  income={settings.income:g}  weights={settings.bucket_weights}")
    print(
        f"  {len(settings.fixed_costs)} fixed costs, "
        f"{len(settings.flexible_categories)} flexible categories, "
        f"{len(settings.item_categories)} item mappings, "
        f"{len(settings.category_buckets)} category mappings, "
        f"{len(settings.open_close)} open/close months"
    )
    overrides = int(log["Category"].notna().sum()) if len(log) else 0
    print(f"Wrote {log_file}: {len(log)} rows ({overrides} with a category override)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
