#!/usr/bin/env python3
"""
fix_addresses.py - Automatically fix off-by-one address errors in source files

Finds addresses that start with RET (0x22) and increments them by 1.
"""

import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FW_BIN = PROJECT_ROOT / "fw.bin"
SRC_DIR = PROJECT_ROOT / "src"

BANK1_FILE_BASE = 0xFF6B
BANK1_CODE_BASE = 0x8000

def calc_file_offset(code_addr, is_bank1):
    if is_bank1:
        return BANK1_FILE_BASE + (code_addr - BANK1_CODE_BASE)
    return code_addr

def get_byte_at(file_offset):
    try:
        with open(FW_BIN, 'rb') as f:
            f.seek(file_offset)
            return f.read(1)[0]
    except:
        return None

def fix_file(filepath, dry_run=True):
    """Fix address errors in a file. Returns number of fixes."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return 0

    fixes = 0
    new_lines = []

    for lineno, line in enumerate(lines, 1):
        new_line = line

        # Check for Bank 1 marker
        is_bank1 = 'bank 1' in line.lower() or 'bank1' in line.lower()

        # Find address ranges: 0xABCD-0xEFGH
        # Also capture optional size like "(N bytes)"
        pattern = r'(0x[0-9a-fA-F]{4,5})\s*-\s*(0x[0-9a-fA-F]{4,5})(\s*\((\d+)\s*bytes?\))?'

        for match in re.finditer(pattern, line):
            start_str = match.group(1)
            end_str = match.group(2)
            size_part = match.group(3) or ""
            old_size = int(match.group(4)) if match.group(4) else None

            start = int(start_str, 16)
            end = int(end_str, 16)

            # Check if start address points to RET
            file_offset = calc_file_offset(start, is_bank1)
            byte_at_start = get_byte_at(file_offset)

            if byte_at_start == 0x22:  # RET instruction
                # Fix: increment start by 1
                new_start = start + 1
                new_size = end - new_start + 1

                # Build replacement string
                new_start_str = f"0x{new_start:04x}" if len(start_str) == 6 else f"0x{new_start:05x}"

                if old_size is not None:
                    old_full = f"{start_str}-{end_str} ({old_size} bytes)"
                    new_full = f"{new_start_str}-{end_str} ({new_size} bytes)"
                else:
                    old_full = f"{start_str}-{end_str}"
                    new_full = f"{new_start_str}-{end_str}"

                if old_full in new_line:
                    new_line = new_line.replace(old_full, new_full)
                    fixes += 1
                    rel_path = filepath.relative_to(PROJECT_ROOT)
                    print(f"  {rel_path}:{lineno}: {start_str} -> {new_start_str}")

        new_lines.append(new_line)

    if fixes > 0 and not dry_run:
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))

    return fixes

def main():
    if not FW_BIN.exists():
        print(f"Error: {FW_BIN} not found")
        sys.exit(1)

    dry_run = '--fix' not in sys.argv

    if dry_run:
        print("DRY RUN - no changes will be made. Use --fix to apply changes.")
    else:
        print("APPLYING FIXES...")
    print("=" * 60)

    total_fixes = 0

    for ext in ['*.h', '*.c']:
        for filepath in SRC_DIR.rglob(ext):
            fixes = fix_file(filepath, dry_run)
            total_fixes += fixes

    print("=" * 60)
    print(f"Total fixes: {total_fixes}")

    if dry_run and total_fixes > 0:
        print("\nRun with --fix to apply these changes")

if __name__ == '__main__':
    main()
