#!/usr/bin/env python3
"""
verify_addresses.py - Verify function addresses in source comments against fw.bin

Parses .h and .c files for address comments and checks them against the firmware.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FW_BIN = PROJECT_ROOT / "fw.bin"
SRC_DIR = PROJECT_ROOT / "src"

# Bank 1 offset calculation: file_offset = 0xFF6B + (code_addr - 0x8000)
BANK1_FILE_BASE = 0xFF6B
BANK1_CODE_BASE = 0x8000

def calc_file_offset(code_addr, is_bank1):
    """Calculate file offset from code address."""
    if is_bank1:
        return BANK1_FILE_BASE + (code_addr - BANK1_CODE_BASE)
    return code_addr

def disassemble_at(file_offset, num_instructions=5):
    """Disassemble at a file offset using r2."""
    try:
        cmd = f"r2 -a 8051 -q -c 'pd {num_instructions} @ 0x{file_offset:x}' {FW_BIN}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        # Strip ANSI color codes
        output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        return output.strip()
    except Exception as e:
        return f"ERROR: {e}"

def get_bytes_at(file_offset, count=8):
    """Get raw bytes at file offset."""
    try:
        with open(FW_BIN, 'rb') as f:
            f.seek(file_offset)
            data = f.read(count)
            return ' '.join(f'{b:02x}' for b in data)
    except Exception as e:
        return f"ERROR: {e}"

def parse_address_comment(line, prev_lines=None):
    """
    Parse address from comment line.
    Returns (start_addr, end_addr, is_bank1, func_name) or None
    """
    # Skip lines that describe memory mappings or regions rather than functions
    skip_patterns = [
        r'Physical\s+0x',           # Memory mapping descriptions
        r'→\s*Logical',             # Arrow mappings
        r':\s*Bank\s+[01]\s+dispatch',  # Dispatch region descriptions
        r'dispatch\s+stubs',        # Dispatch stub descriptions
        r'BANK\s+MAPPING',          # Bank mapping header
        r'mapped\s+at\s+0x',        # "mapped at" descriptions
        r'Dispatch\s+Functions\s*\(',  # "Bank 1 Dispatch Functions (" section headers
        r'dispatches\s+to\s+bank',  # "dispatches to bank 1" descriptions
        r'->\s*dispatches',         # "-> dispatches" comments
    ]
    for pattern in skip_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return None

    # Patterns to match:
    # /* 0x1234-0x5678 */
    # /* Address: 0x1234-0x5678 */
    # /* Bank 1 Address: 0x1234-0x5678 */
    # void func(void);  /* 0x1234-0x5678 */

    is_bank1 = 'bank 1' in line.lower() or 'bank1' in line.lower()

    # Match address ranges like 0xABCD-0xEFGH
    range_match = re.search(r'0x([0-9a-fA-F]{4,5})\s*-\s*0x([0-9a-fA-F]{4,5})', line)
    if range_match:
        start = int(range_match.group(1), 16)
        end = int(range_match.group(2), 16)

        # Skip very large ranges (likely memory region descriptions)
        if end - start > 0x1000:
            return None

        # Try to extract function name
        func_name = None
        # Check for function declaration pattern
        func_match = re.search(r'(\w+)\s*\([^)]*\)\s*;?\s*/\*', line)
        if func_match:
            func_name = func_match.group(1)
        # Check previous lines for function name in comment header
        if not func_name and prev_lines:
            for prev in prev_lines[-5:]:
                name_match = re.search(r'\*\s+(\w+)\s+-', prev)
                if name_match:
                    func_name = name_match.group(1)
                    break

        return (start, end, is_bank1, func_name)

    return None

def scan_file(filepath):
    """Scan a file for address comments and return list of findings."""
    findings = []

    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return findings

    prev_lines = []
    for lineno, line in enumerate(lines, 1):
        result = parse_address_comment(line, prev_lines)
        if result:
            start, end, is_bank1, func_name = result
            findings.append({
                'file': filepath,
                'line': lineno,
                'start': start,
                'end': end,
                'is_bank1': is_bank1,
                'func_name': func_name or 'unknown',
                'source_line': line.strip()
            })
        prev_lines.append(line)
        if len(prev_lines) > 10:
            prev_lines.pop(0)

    return findings

def verify_address(finding):
    """Verify an address against fw.bin and return verification info."""
    start = finding['start']
    end = finding['end']
    is_bank1 = finding['is_bank1']

    file_offset = calc_file_offset(start, is_bank1)
    size = end - start + 1

    # Get disassembly
    disasm = disassemble_at(file_offset, min(10, max(5, size // 3)))

    # Get raw bytes
    raw_bytes = get_bytes_at(file_offset, 8)

    # Check for potential issues
    issues = []

    # Check if it starts with ret (0x22) - probably wrong address
    if raw_bytes.startswith('22 '):
        issues.append("STARTS WITH RET - likely wrong address")

    # Check if address seems unreasonable
    # Bank 1 addresses must be >= 0x8000 (that's where Bank 1 is mapped)
    if is_bank1 and start < 0x8000:
        issues.append("Bank 1 but address < 0x8000 - invalid")

    # Check file offset bounds
    fw_size = os.path.getsize(FW_BIN)
    if file_offset >= fw_size:
        issues.append(f"File offset 0x{file_offset:x} beyond file size 0x{fw_size:x}")

    # Check for invalid opcodes in disasm
    if 'invalid' in disasm.lower():
        issues.append("Contains invalid opcodes")

    # Check if function appears to start mid-instruction (heuristic)
    # Look for common function prologues
    first_bytes = raw_bytes.split()[:2]
    if len(first_bytes) >= 1:
        first_byte = int(first_bytes[0], 16)
        # Suspicious if starts with operand-like values in certain ranges
        # 0x22 = ret, should not start function
        # But many valid opcodes exist, so be conservative

    return {
        'file_offset': file_offset,
        'size': size,
        'disasm': disasm,
        'raw_bytes': raw_bytes,
        'issues': issues
    }

def main():
    if not FW_BIN.exists():
        print(f"Error: {FW_BIN} not found")
        sys.exit(1)

    print(f"Scanning source files in {SRC_DIR}")
    print(f"Verifying against {FW_BIN}")
    print("=" * 80)

    # Find all .h and .c files
    all_findings = []
    for ext in ['*.h', '*.c']:
        for filepath in SRC_DIR.rglob(ext):
            findings = scan_file(filepath)
            all_findings.extend(findings)

    print(f"\nFound {len(all_findings)} address comments\n")

    # Verify each finding
    issues_found = 0
    issue_types = {}
    files_with_issues = set()

    summary_mode = '--summary' in sys.argv
    show_all = '--all' in sys.argv

    for finding in sorted(all_findings, key=lambda x: (str(x['file']), x['line'])):
        rel_path = finding['file'].relative_to(PROJECT_ROOT)
        verification = verify_address(finding)

        has_issues = len(verification['issues']) > 0
        if has_issues:
            issues_found += 1
            files_with_issues.add(str(rel_path))
            for issue in verification['issues']:
                issue_type = issue.split(' - ')[0] if ' - ' in issue else issue.split()[0]
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

        # Print based on verbosity
        if not summary_mode and (has_issues or show_all):
            bank_str = "Bank1 " if finding['is_bank1'] else ""
            print(f"{rel_path}:{finding['line']}")
            print(f"  Function: {finding['func_name']}")
            print(f"  Claimed: {bank_str}0x{finding['start']:04x}-0x{finding['end']:04x} ({verification['size']} bytes)")
            print(f"  File offset: 0x{verification['file_offset']:05x}")
            print(f"  Raw bytes: {verification['raw_bytes']}")

            if verification['issues']:
                print(f"  ISSUES:")
                for issue in verification['issues']:
                    print(f"    - {issue}")

            if show_all or has_issues:
                print(f"  Disassembly:")
                for line in verification['disasm'].split('\n')[:8]:
                    print(f"    {line}")
            print()

    print("=" * 80)
    print(f"Total: {len(all_findings)} addresses checked, {issues_found} with potential issues")

    if issue_types:
        print(f"\nIssue breakdown:")
        for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
            print(f"  {count:4d}  {issue_type}")

    if files_with_issues:
        print(f"\nFiles with issues ({len(files_with_issues)}):")
        for f in sorted(files_with_issues):
            print(f"  {f}")

    if issues_found > 0 and '--all' not in sys.argv and not summary_mode:
        print("\nRun with --all to see all addresses")
        print("Run with --summary for just counts")

    return 0 if issues_found == 0 else 1

if __name__ == '__main__':
    main()
