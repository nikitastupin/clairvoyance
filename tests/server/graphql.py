import http.server
import json


class GraphqlHTTPRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_POST(self) -> None:
        body = json.dumps({
            "errors": [{
                "message": 'Cannot query field "imwrongfield" on type "Mutation".',
                "locations": [{
                    "line": 1,
                    "column": 12
                }],
                "extensions": {
                    "code": "GRAPHQL_VALIDATION_FAILED"
                },
            }]
        })

        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(body, "ascii"))

    def log_message(self, format, *args) -> None:  # type: ignore[no-untyped-def]
        pass


def main(port: int = None) -> None:
    port = port or 8081
    with http.server.HTTPServer(("", port), GraphqlHTTPRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
