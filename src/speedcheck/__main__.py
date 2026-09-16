from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Final

import httpx

from speedcheck.checker import (
    REQUEST_COUNT,
    MeasurementSummary,
    RequestMeasurement,
    calculate_summary,
    measure_url,
)

ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


class CliArguments(argparse.Namespace):
    url: str


def parse_http_url(value: str) -> str:
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as exc:
        msg = f"invalid URL: {exc}"
        raise argparse.ArgumentTypeError(msg) from exc

    if url.scheme not in ALLOWED_SCHEMES:
        msg = "URL must use http or https"
        raise argparse.ArgumentTypeError(msg)

    if not url.host:
        msg = "URL must contain a host"
        raise argparse.ArgumentTypeError(msg)

    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speedcheck",
        description="Measure HTTP download speed using 10 sequential requests.",
    )
    parser.add_argument(
        "url",
        type=parse_http_url,
        help="URL of a file to download",
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> CliArguments:
    args = CliArguments()

    build_parser().parse_args(argv, namespace=args)

    return args


def format_measurement(index: int, measurement: RequestMeasurement) -> str:
    return (
        f"[{index:02d}/{REQUEST_COUNT:02d}]  "
        f"{measurement.downloaded_megabytes:.2f} MB  |  "
        f"{measurement.elapsed_seconds:.3f} s  |  "
        f"{measurement.speed_megabytes_per_second:.2f} MB/s"
    )


def format_summary(summary: MeasurementSummary) -> str:
    return (
        "\n"
        "Summary\n"
        "-------\n"
        f"Average request time: {summary.average_request_seconds:.3f} s\n"
        f"Total downloaded:     {summary.total_downloaded_megabytes:.2f} MB\n"
        f"Average speed:        "
        f"{summary.average_speed_megabytes_per_second:.2f} MB/s"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    print(f"Measuring: {args.url}")
    print(f"Requests: {REQUEST_COUNT}")
    print()

    measurements: list[RequestMeasurement] = []

    try:
        for index, measurement in enumerate(measure_url(args.url), start=1):
            measurements.append(measurement)
            print(format_measurement(index, measurement))

    except httpx.HTTPStatusError as exc:
        print(
            f"error: request failed with HTTP {exc.response.status_code}",
            file=sys.stderr,
        )
        return 1

    except httpx.TimeoutException:
        print(
            "error: request timed out",
            file=sys.stderr,
        )
        return 1

    except httpx.RequestError as exc:
        print(
            f"error: request failed: {exc}",
            file=sys.stderr,
        )
        return 1

    summary = calculate_summary(measurements)
    print(format_summary(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
