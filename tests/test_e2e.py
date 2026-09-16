import os

import pytest

from speedcheck.__main__ import main
from speedcheck.checker import REQUEST_COUNT

NETWORK_TEST_URL = "https://speed.cloudflare.com/__down?bytes=100000"


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_E2E_TESTS") != "1",
    reason="E2E tests require external network access",
)
def test_speedcheck_against_real_http_endpoint(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main((NETWORK_TEST_URL,))

    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"Requests: {REQUEST_COUNT}" in captured.out
    assert captured.out.count("/10]") == REQUEST_COUNT
    assert "Summary" in captured.out
    assert "Average request time:" in captured.out
    assert "Total downloaded:" in captured.out
    assert "Average speed:" in captured.out
    assert captured.err == ""
