"""Local-only source secret scan; prints paths/line numbers, never matched values.

Covers tracked and untracked source and build output. This is
an intentionally small high-confidence scan plus explicit env-file checks,
not a guarantee that arbitrary secrets can be recognized.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache', '.idea'}
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'),
    'AWS access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'GitHub token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b'),
    'API key': re.compile(r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{32,}|sk_live_[A-Za-z0-9]{20,}|AIza[A-Za-z0-9_-]{30,})\b'),
    'Anthropic API key': re.compile(r'\bsk-ant-(?:api\d{2}-)?[A-Za-z0-9_-]{40,}\b'),
    'Render token': re.compile(r'\b(?:rnd_|rdr_)[A-Za-z0-9]{25,}\b'),
}
DATABASE = re.compile(r'postgres(?:ql)?(?:\+psycopg)?://[^\s/:]+:([^\s/@]+)@[^\s\"\']+')
PLACEHOLDERS = {'p', 'pw', 'password', 'placeholder', 'postgres', 'test', 'unused'}


def findings(content: str):
    for number, line in enumerate(content.splitlines(), 1):
        for kind, pattern in PATTERNS.items():
            if pattern.search(line):
                yield number, kind
        for match in DATABASE.finditer(line):
            if match.group(1).lower() not in PLACEHOLDERS:
                yield number, 'database credential'


def scan_history() -> int:
    """Inspect every reachable blob, including deleted files, without excerpts."""
    if subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=ROOT, text=True).strip() == 'true':
        print('History scan requires a full clone (fetch-depth: 0).')
        return 1
    objects = subprocess.check_output(['git', 'rev-list', '--objects', '--all'], cwd=ROOT).splitlines()
    found = scanned = 0
    with subprocess.Popen(['git', 'cat-file', '--batch'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as process:
        for item in objects:
            oid, _, name = item.partition(b' ')
            process.stdin.write(oid + b'\n')
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3:
                raise RuntimeError('Could not read a reachable Git object.')
            content = process.stdout.read(int(header[2]))
            process.stdout.read(1)
            if header[1] != b'blob':
                continue
            scanned += 1
            matches = list(findings(content.decode('utf-8', errors='ignore')))
            path = name.decode('utf-8', errors='replace')
            if Path(path).name.startswith('.env') and Path(path).name != '.env.example':
                matches.append((1, 'committed environment file'))
            if matches:
                # Report the introduction, not the later deletion of a secret.
                commits = subprocess.check_output(['git', 'log', '--all', '--reverse', '--format=%H', '--find-object=' + oid.decode()], cwd=ROOT, text=True).splitlines()
                commit = commits[0] if commits else 'unknown'
                for number, kind in matches:
                    print(f'{path!r}:{number}: {kind}; commit {commit} (value suppressed)')
                    found += 1
        process.stdin.close()
        process.wait()
    print(f'Scanned {scanned} reachable Git blobs; {found} findings.')
    return bool(found)


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
        try:
            # Also inspect printable content in SQLite, images and artifacts.
            content = path.read_bytes().decode('utf-8', errors='ignore')
        except (UnicodeError, OSError):
            continue
        scanned += 1
        found.extend((str(relative), number, kind) for number, kind in findings(content))
    for path, number, kind in found:
        print(f'{path}:{number}: review {kind} (value suppressed)')
    print(f'Scanned {scanned} source/config files; {len(found)} high-confidence findings; {len(local_env)} local real-env files.')
    return bool(found)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Scan all reachable Git history, including deleted content.')
    sys.exit(scan_history() if parser.parse_args().history else scan())
