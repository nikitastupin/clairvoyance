import http.server
import json
from typing import Optional


class UnstableHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # pylint: disable=invalid-name
        body = json.dumps(
            {
                "errors": [
                    {
                        "message": 'Cannot query field "IAmWrongField" on type "Mutation".',
                        "locations": [{"line": 1, "column": 12}],
                        "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"},
                    }
                ]
            }
        )

        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(body, "ascii"))

    def log_message(self, format, *args) -> None:  # type: ignore[no-untyped-def] # pylint: disable=redefined-builtin
        pass


def main(port: Optional[int] = None) -> None:
    port = port or 8081
    with http.server.HTTPServer(("", port), UnstableHTTPRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
