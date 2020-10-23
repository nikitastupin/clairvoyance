import os
import json
import http.server


class GraphqlHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.dumps(
            {
                "errors": [
                    {
                        "message": 'Cannot query field "imwrongfield" on type "Mutation".',
                        "locations": [{"line": 1, "column": 12}],
                        "extensions": {"code": "GRAPHQL_VALIDATION_FAILED"},
                    }
                ]
            }
        )

        self.send_response(200)
        self.end_headers()
        self.wfile.write(bytes(body, "ascii"))

    def log_message(self, format, *args):
        pass


def main(port=8001):
    with http.server.HTTPServer(("", port), GraphqlHTTPRequestHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
