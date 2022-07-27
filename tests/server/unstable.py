import http.server
import os


class UnstableHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self) -> None:
        if "COUNT" not in os.environ:
            os.environ["COUNT"] = "1"

        if int(os.environ["COUNT"]) % 2 == 0:
            self.send_response(200)
        else:
            self.send_response(500)

        self.end_headers()

        os.environ["COUNT"] = str(int(os.environ["COUNT"]) + 1)

    def log_message(self, format, *args) -> None:  # type: ignore[no-untyped-def]
        pass


def main(port: int = None) -> None:
    port = port or 8000
    with http.server.HTTPServer(("", port), UnstableHTTPRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
