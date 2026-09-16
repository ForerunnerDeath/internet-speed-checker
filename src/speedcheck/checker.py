from __future__ import annotations

import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Final

import httpx

BYTES_PER_MEGABYTE: Final[int] = 1_000_000
CHUNK_SIZE_BYTES: Final[int] = 64 * 1024
REQUEST_COUNT: Final[int] = 10
REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0


@dataclass(frozen=True, slots=True)
class RequestMeasurement:
    elapsed_seconds: float
    downloaded_bytes: int

    def __post_init__(self) -> None:
        if self.elapsed_seconds <= 0:
            msg = "Elapsed time must be greater than zero."
            raise ValueError(msg)

        if self.downloaded_bytes < 0:
            msg = "Downloaded bytes cannot be negative."
            raise ValueError(msg)

    @property
    def speed_bytes_per_second(self) -> float:
        return self.downloaded_bytes / self.elapsed_seconds

    @property
    def downloaded_megabytes(self) -> float:
        return self.downloaded_bytes / BYTES_PER_MEGABYTE

    @property
    def speed_megabytes_per_second(self) -> float:
        return self.speed_bytes_per_second / BYTES_PER_MEGABYTE


@dataclass(frozen=True, slots=True)
class MeasurementSummary:
    average_request_seconds: float
    total_downloaded_bytes: int
    average_speed_bytes_per_second: float

    @property
    def total_downloaded_megabytes(self) -> float:
        return self.total_downloaded_bytes / BYTES_PER_MEGABYTE

    @property
    def average_speed_megabytes_per_second(self) -> float:
        return self.average_speed_bytes_per_second / BYTES_PER_MEGABYTE


def calculate_summary(measurements: Sequence[RequestMeasurement]) -> MeasurementSummary:
    if not measurements:
        msg = "At least one measurement is required."
        raise ValueError(msg)

    total_elapsed_seconds = sum(measurement.elapsed_seconds for measurement in measurements)
    total_downloaded_bytes = sum(measurement.downloaded_bytes for measurement in measurements)

    return MeasurementSummary(
        average_request_seconds=total_elapsed_seconds / len(measurements),
        total_downloaded_bytes=total_downloaded_bytes,
        average_speed_bytes_per_second=(total_downloaded_bytes / total_elapsed_seconds),
    )


def download_once(client: httpx.Client, url: str) -> RequestMeasurement:
    started_at = time.perf_counter()
    downloaded_bytes = 0

    with client.stream("GET", url) as response:
        response.raise_for_status()

        for chunk in response.iter_raw(chunk_size=CHUNK_SIZE_BYTES):
            downloaded_bytes += len(chunk)

        elapsed_seconds = time.perf_counter() - started_at

    return RequestMeasurement(
        elapsed_seconds=elapsed_seconds,
        downloaded_bytes=downloaded_bytes,
    )


def measure_downloads(client: httpx.Client, url: str) -> Iterator[RequestMeasurement]:
    for _ in range(REQUEST_COUNT):
        yield download_once(
            client=client,
            url=url,
        )


def measure_url(url: str) -> Iterator[RequestMeasurement]:
    with httpx.Client(
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
    ) as client:
        yield from measure_downloads(
            client=client,
            url=url,
        )
