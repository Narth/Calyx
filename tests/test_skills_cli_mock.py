import subprocess
import sys

def test_skills_cli_list():
    result = subprocess.run([sys.executable, 'tools/skills_cli.py', 'list'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'sysadmin-toolbox' in result.stdout


def test_skills_cli_mock_run():
    result = subprocess.run([
        sys.executable,
        'tools/skills_cli.py',
        'run',
        'sysadmin-toolbox',
        '--args',
        '--help',
        '--mock'
    ], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'Mock run' in result.stdout
