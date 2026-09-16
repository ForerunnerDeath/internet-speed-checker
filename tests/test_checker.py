import httpx
import pytest

from speedcheck.checker import (
    REQUEST_COUNT,
    RequestMeasurement,
    calculate_summary,
    download_once,
    measure_downloads,
)


def test_download_once_counts_downloaded_bytes() -> None:
    payload = b"x" * 150_000

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            stream=httpx.ByteStream(payload),
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        measurement = download_once(
            client=client,
            url="https://example.com/file.bin",
        )

    assert measurement.downloaded_bytes == len(payload)
    assert measurement.elapsed_seconds > 0


@pytest.mark.parametrize("status_code", [404, 500])
def test_download_once_raises_for_http_error(status_code: int) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            stream=httpx.ByteStream(b"error"),
        )

    transport = httpx.MockTransport(handler)

    with (
        httpx.Client(transport=transport) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        download_once(
            client=client,
            url="https://example.com/file.bin",
        )


def test_measure_downloads_performs_expected_number_of_requests() -> None:
    payload = b"x" * 1_000
    request_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1

        return httpx.Response(
            status_code=200,
            stream=httpx.ByteStream(payload),
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as client:
        measurements = list(
            measure_downloads(
                client=client,
                url="https://example.com/file.bin",
            )
        )

    assert request_count == REQUEST_COUNT
    assert len(measurements) == REQUEST_COUNT
    assert all(measurement.downloaded_bytes == len(payload) for measurement in measurements)


def test_calculate_summary_aggregates_measurements() -> None:
    measurements = (
        RequestMeasurement(
            elapsed_seconds=1.0,
            downloaded_bytes=1_000_000,
        ),
        RequestMeasurement(
            elapsed_seconds=3.0,
            downloaded_bytes=9_000_000,
        ),
    )

    summary = calculate_summary(measurements)

    assert summary.average_request_seconds == 2.0
    assert summary.total_downloaded_bytes == 10_000_000
    assert summary.average_speed_bytes_per_second == 2_500_000.0

    assert summary.total_downloaded_megabytes == 10.0
    assert summary.average_speed_megabytes_per_second == 2.5


def test_calculate_summary_rejects_empty_measurements() -> None:
    with pytest.raises(
        ValueError,
        match="At least one measurement is required",
    ):
        calculate_summary(())


@pytest.mark.parametrize(
    "elapsed_seconds",
    [0.0, -1.0],
)
def test_request_measurement_rejects_non_positive_elapsed_time(elapsed_seconds: float) -> None:
    with pytest.raises(
        ValueError,
        match="Elapsed time must be greater than zero",
    ):
        RequestMeasurement(
            elapsed_seconds=elapsed_seconds,
            downloaded_bytes=1_000,
        )


def test_request_measurement_rejects_negative_downloaded_bytes() -> None:
    with pytest.raises(
        ValueError,
        match="Downloaded bytes cannot be negative",
    ):
        RequestMeasurement(
            elapsed_seconds=1.0,
            downloaded_bytes=-1,
        )


def test_request_measurement_allows_zero_downloaded_bytes() -> None:
    measurement = RequestMeasurement(
        elapsed_seconds=1.0,
        downloaded_bytes=0,
    )

    assert measurement.downloaded_bytes == 0
    assert measurement.speed_bytes_per_second == 0.0
