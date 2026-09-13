"""Local-only source secret scan; prints paths/line numbers, never matched values.

Covers tracked and untracked source, excluding generated artifacts. This is
an intentionally small high-confidence scan plus explicit env-file checks,
not a guarantee that arbitrary secrets can be recognized.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {'.git', '.venv', 'venv', 'node_modules', 'dist', '__pycache__', '.pytest_cache', '.idea', 'test-results', 'playwright-report'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'API key': re.compile(r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|sk_live_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,})\b'),
}
DATABASE = re.compile(r'postgres(?:ql)?(?:\+psycopg)?://[^\s/:]+:([^\s/@]+)@[^\s\"\']+')
PLACEHOLDERS = {'p', 'pw', 'password', 'placeholder', 'postgres', 'test', 'unused'}


def scan() -> int:
    tracked = set(subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines())
    found = []
    scanned = 0
    local_env = []
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDE for part in relative.parts) or not path.is_file() or path.is_symlink():
            continue
        if path.name.startswith('.env') and path.name != '.env.example':
            local_env.append(str(relative))
            if str(relative) in tracked:
                found.append((str(relative), 1, 'tracked environment file'))
        # Expanded reference assets are source inputs too. Do not silently
        # omit a film/song catalog just because it exceeds the old text limit.
        limit = 30_000_000 if relative.parts[:4] == ('backend', 'app', 'data', 'knowledge') else 2_000_000
        if path.stat().st_size > limit:
            continue
        try:
            content = path.read_text()
        except (UnicodeError, OSError):
            continue
        scanned += 1
        for number, line in enumerate(content.splitlines(), 1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    found.append((str(relative), number, kind))
            for match in DATABASE.finditer(line):
                if match.group(1).lower() not in PLACEHOLDERS:
                    found.append((str(relative), number, 'database credential'))
    for path, number, kind in found:
        print(f'{path}:{number}: review {kind} (value suppressed)')
    print(f'Scanned {scanned} source/config files; {len(found)} high-confidence findings; {len(local_env)} local real-env files.')
    return bool(found)


if __name__ == '__main__':
    sys.exit(scan())
