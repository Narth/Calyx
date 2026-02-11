import subprocess
import sys


def test_firecrawl_mock_search():
    result = subprocess.run(
        [
            sys.executable,
            'tools/firecrawl_mcp.py',
            '--tool',
            'search',
            '--args',
            '{"query":"Station Calyx"}',
            '--mock'
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'Mocked response' in result.stdout
