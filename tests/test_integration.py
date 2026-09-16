import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import ClassVar

from speedcheck.checker import REQUEST_COUNT, measure_url

_STREAM_CHUNKS: tuple[bytes, ...] = (
    b"a" * 4_000,
    b"b" * 4_000,
    b"c" * 4_000,
)
_CHUNK_DELAY_SECONDS = 0.03


class _SlowStreamingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    request_count: ClassVar[int] = 0

    def do_GET(self) -> None:
        type(self).request_count += 1

        content_length = sum(len(chunk) for chunk in _STREAM_CHUNKS)

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(content_length))
        self.end_headers()

        for index, chunk in enumerate(_STREAM_CHUNKS):
            if index > 0:
                time.sleep(_CHUNK_DELAY_SECONDS)

            self.wfile.write(chunk)
            self.wfile.flush()

    def log_message(self, format: str, *args: object) -> None:
        pass


def test_measure_url_includes_response_body_download_time() -> None:
    _SlowStreamingHandler.request_count = 0

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _SlowStreamingHandler,
    )
    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    try:
        url = f"http://127.0.0.1:{server.server_port}/file.bin"
        measurements = list(measure_url(url))
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=1.0)

    expected_bytes = sum(len(chunk) for chunk in _STREAM_CHUNKS)

    # Two pauses occur after the first chunk. Use a tolerance so that
    # the test verifies the timing semantics without depending on exact
    # scheduler precision.
    minimum_expected_elapsed = _CHUNK_DELAY_SECONDS * 1.5

    assert _SlowStreamingHandler.request_count == REQUEST_COUNT
    assert len(measurements) == REQUEST_COUNT

    assert all(measurement.downloaded_bytes == expected_bytes for measurement in measurements)
    assert all(
        measurement.elapsed_seconds >= minimum_expected_elapsed for measurement in measurements
    )
