#!/usr/bin/env python3
"""
Claude Code hook to enforce TypeScript quality:
- no `any` type usage
- prefer named exports over default exports
- no console.log or debugger statements in production code
"""

import json
import re
import sys
from pathlib import Path

TS_EXTENSIONS = {'.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'}

TEST_PATTERNS = [
    r'\.test\.',
    r'\.spec\.',
    r'__tests__',
    r'\.stories\.',
    r'\.storybook',
]


def strip_strings_and_comments(code: str) -> str:
    out = list(code)
    i = 0
    n = len(code)
    state = None
    tmpl_depth = 0
    while i < n:
        ch = code[i]
        if state is None:
            if ch == '/' and i + 1 < n and code[i + 1] == '/':
                while i < n and code[i] != '\n':
                    out[i] = ' '
                    i += 1
                continue
            if ch == '/' and i + 1 < n and code[i + 1] == '*':
                out[i] = ' '
                out[i + 1] = ' '
                i += 2
                while i < n:
                    if code[i] == '*' and i + 1 < n and code[i + 1] == '/':
                        out[i] = ' '
                        out[i + 1] = ' '
                        i += 2
                        break
                    if code[i] != '\n':
                        out[i] = ' '
                    i += 1
                continue
            if ch == "'" or ch == '"':
                state = ch
                i += 1
                continue
            if ch == '`':
                state = '`'
                i += 1
                continue
            i += 1
            continue
        if state == "'" or state == '"':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == state:
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
        if state == '`':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == '$' and i + 1 < n and code[i + 1] == '{':
                i += 2
                depth = 1
                while i < n and depth > 0:
                    c2 = code[i]
                    if c2 == '{':
                        depth += 1
                    elif c2 == '}':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                continue
            if ch == '`':
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
    return ''.join(out)


def get_extension(file_path: str) -> str:
    return Path(file_path).suffix.lower()


def is_ts_file(file_path: str) -> bool:
    return get_extension(file_path) in TS_EXTENSIONS


def is_test_file(file_path: str) -> bool:
    return any(re.search(p, file_path) for p in TEST_PATTERNS)


def check_any_type(scrubbed: str, file_path: str) -> list[str]:
    """check for any type usage"""
    if get_extension(file_path) not in {'.ts', '.tsx'}:
        return []

    issues = []
    lines = scrubbed.split('\n')

    any_patterns = [
        (r':\s*any\b', 'explicit any type'),
        (r'<any>', 'any in generic'),
        (r'as\s+any\b', 'cast to any'),
        (r'\[\s*any\s*\]', 'any in array type'),
        (r'Record<[^>]*,\s*any>', 'any in Record'),
        (r'Promise<any>', 'any in Promise'),
    ]

    for line_num, line in enumerate(lines, 1):
        for pattern, description in any_patterns:
            if re.search(pattern, line):
                issues.append(f"line {line_num}: {description} - use a proper type instead")
                break

    return issues


def is_nextjs_special_file(file_path: str) -> bool:
    """check if file is a next.js file that requires default export"""
    path = Path(file_path)
    nextjs_files = {'page', 'layout', 'loading', 'error', 'not-found', 'template', 'default', 'middleware'}
    return path.stem in nextjs_files


def requires_default_export(file_path: str) -> bool:
    """check if file requires default export by convention"""
    path = Path(file_path)
    config_patterns = ['vite.config', 'vitest.config', 'tailwind.config', 'postcss.config']
    if path.name == 'vite-env.d.ts' or path.name == 'env.d.ts':
        return True
    return any(p in path.name for p in config_patterns)


def check_default_exports(content: str, file_path: str) -> list[str]:
    """check for default exports"""
    if not is_ts_file(file_path):
        return []

    if is_nextjs_special_file(file_path):
        return []

    if requires_default_export(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'\bexport\s+default\b', line):
            issues.append(
                f"line {line_num}: default export detected - prefer named exports for better refactoring"
            )

    return issues


def check_console_debugger(scrubbed: str, file_path: str) -> list[str]:
    """check for console.log and debugger statements"""
    if not is_ts_file(file_path):
        return []

    if is_test_file(file_path):
        return []

    issues = []
    lines = scrubbed.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'\bconsole\.(log|debug|info|warn|error|trace|dir|table)\b', line):
            if not re.search(r'\bconsole\.(error|warn)\b', line):
                issues.append(
                    f"line {line_num}: console statement detected - remove before production"
                )

        if re.search(r'\bdebugger\b', line):
            issues.append(f"line {line_num}: debugger statement detected - remove before production")

    return issues


def validate(file_path: str, content: str) -> list[str]:
    """run all typescript quality checks"""
    scrubbed = strip_strings_and_comments(content)
    all_issues = []
    all_issues.extend(check_any_type(scrubbed, file_path))
    all_issues.extend(check_default_exports(content, file_path))
    all_issues.extend(check_console_debugger(scrubbed, file_path))
    return all_issues


def extract_content(tool_input: dict) -> str:
    edits = tool_input.get('edits')
    if isinstance(edits, list) and edits:
        return '\n'.join(e.get('new_string', '') for e in edits)
    return tool_input.get('new_string', '') or tool_input.get('content', '')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = extract_content(tool_input)
    if not content:
        sys.exit(0)

    issues = validate(file_path, content)

    if issues:
        print("typescript quality issues:", file=sys.stderr)
        for issue in issues[:8]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 8:
            print(f"  ... and {len(issues) - 8} more issues", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
