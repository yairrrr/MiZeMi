"""The audit scanner must inspect deleted history and generated build output."""
import importlib.util
from pathlib import Path
import subprocess

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts' / 'check_secrets.py'
spec = importlib.util.spec_from_file_location('audit_secrets', SCRIPT)
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


def repository(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=tmp_path, stderr=subprocess.DEVNULL, text=True)
    git('init', '-q')
    git('config', 'user.email', 'audit@example.invalid')
    git('config', 'user.name', 'Synthetic audit fixture')
    monkeypatch.setattr(scanner, 'ROOT', tmp_path)
    return git


def test_deleted_synthetic_token_is_reported_without_value(tmp_path, monkeypatch, capsys):
    git = repository(tmp_path, monkeypatch)
    synthetic = 'gh' + 'p_' + 'A' * 36
    file = tmp_path / 'removed.txt'
    file.write_text(synthetic)
    git('add', 'removed.txt')
    git('commit', '-qm', 'Synthetic scanner fixture')
    commit = git('rev-parse', 'HEAD').strip()
    git('rm', 'removed.txt')
    git('commit', '-qm', 'Remove fixture')
    assert scanner.scan_history() == 1
    output = capsys.readouterr().out
    assert commit in output
    assert 'removed.txt' in output and 'GitHub token' in output
    assert synthetic not in output


def test_generated_bundle_is_scanned(tmp_path, monkeypatch, capsys):
    repository(tmp_path, monkeypatch)
    (tmp_path / 'frontend' / 'dist').mkdir(parents=True)
    synthetic = 'gh' + 'p_' + 'B' * 36
    (tmp_path / 'frontend' / 'dist' / 'app.js').write_text(synthetic)
    assert scanner.scan() == 1
    output = capsys.readouterr().out
    assert 'frontend/dist/app.js' in output
    assert synthetic not in output
