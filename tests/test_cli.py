import pytest

from speedcheck.__main__ import (
    format_measurement,
    format_summary,
    parse_args,
)
from speedcheck.checker import (
    MeasurementSummary,
    RequestMeasurement,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/file.bin",
        "https://example.com/file.bin",
    ],
)
def test_parse_args_accepts_http_urls(url: str) -> None:
    args = parse_args((url,))

    assert args.url == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file.bin",
        "example.com/file.bin",
        "https:///file.bin",
    ],
)
def test_parse_args_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args((url,))

    assert exc_info.value.code == 2


def test_format_measurement() -> None:
    measurement = RequestMeasurement(
        elapsed_seconds=2.0,
        downloaded_bytes=10_000_000,
    )

    result = format_measurement(
        index=1,
        measurement=measurement,
    )

    assert result == "[01/10]  10.00 MB  |  2.000 s  |  5.00 MB/s"


def test_format_summary() -> None:
    summary = MeasurementSummary(
        average_request_seconds=1.25,
        total_downloaded_bytes=100_000_000,
        average_speed_bytes_per_second=8_000_000.0,
    )

    result = format_summary(summary)

    assert result == (
        "\n"
        "Summary\n"
        "-------\n"
        "Average request time: 1.250 s\n"
        "Total downloaded:     100.00 MB\n"
        "Average speed:        8.00 MB/s"
    )
