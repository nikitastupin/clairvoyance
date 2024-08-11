import json
import os
import subprocess
import unittest
from typing import Any, Dict, Optional


class TestClairvoyance(unittest.TestCase):
    port: str
    clairvoyance: subprocess.CompletedProcess
    schema: Any

    @classmethod
    def setUpClass(cls) -> None:
        cls.port = "4000"
        output_file = "/tmp/t.json"

        try:
            os.remove(output_file)
        except FileNotFoundError:
            pass

        cls.clairvoyance = subprocess.run(
            [
                "python3",
                "-m",
                "clairvoyance",
                "-o",
                output_file,
                "-wv",
                "-w",
                "tests/data/wordlist-for-apollo-server.txt",
                f"http://localhost:{cls.port}",
            ],
            capture_output=True,
            check=True,
        )

        with open(output_file, "r", encoding="utf-8") as f:
            j = json.load(f)

        cls.schema = j["data"]["__schema"]

    @property
    def query_type(self) -> Any:
        query_type = self.get_type(self.schema["queryType"]["name"])
        if not query_type:
            raise RuntimeError("Schema don't contain query type")

        return query_type

    def get_type(self, name: str) -> Optional[Dict[str, Any]]:
        for t in self.schema["types"]:
            if t["name"] == name:
                return t

        return None

    def test_validate_wordlist(self) -> None:
        self.assertIn(b"Removed 1 items from wordlist", self.clairvoyance.stderr)

    def test_found_root_type_names(self) -> None:
        self.assertEqual(self.schema["queryType"], {"name": "Query"})
        self.assertEqual(self.schema["mutationType"], {"name": "Mutation"})
        self.assertIsNone(self.schema["subscriptionType"])

    def test_type_names(self) -> None:
        type_names = [t["name"] for t in self.schema["types"]]

        self.assertIn("Query", type_names)
        self.assertIn("Mutation", type_names)
        self.assertIn("Launch", type_names)
        self.assertIn("Rocket", type_names)
        self.assertIn("User", type_names)
        self.assertIn("Mission", type_names)
        self.assertIn("TripUpdateResponse", type_names)

    def test_query_basics(self) -> None:
        query_type = self.query_type

        self.assertEqual(query_type["name"], "Query")
        self.assertEqual(query_type["kind"], "OBJECT")

    def test_query_field_names(self) -> None:
        query_fields = self.query_type["fields"]
        field_names = [f["name"] for f in query_fields]

        self.assertEqual(len(field_names), 3)
        self.assertIn("launches", field_names)
        self.assertIn("launch", field_names)
        self.assertIn("me", field_names)

    def test_query_field_types(self) -> None:
        query_fields = self.query_type["fields"]

        for f in query_fields:
            if f["name"] == "launches":
                want = {
                    "kind": "OBJECT",
                    "name": "Launch",
                    "ofType": None,
                }
                self.assertEqual(f["type"], want)
            elif f["name"] == "launch":
                want = {"kind": "OBJECT", "name": "Launch", "ofType": None}
                self.assertEqual(f["type"], want)
            elif f["name"] == "me":
                want = {"kind": "OBJECT", "name": "User", "ofType": None}
                self.assertEqual(f["type"], want)
            else:
                self.fail(f'Unexpected field {f["name"]} on query type')

    def test_scalar_arguments(self) -> None:
        query_fields = self.query_type["fields"]

        for f in query_fields:
            if f["name"] == "launch":
                self.assertEqual(len(f["args"]), 1)
                self.assertEqual(f["args"][0]["name"], "id")

                want = {
                    "kind": "NON_NULL",
                    "name": None,
                    "ofType": {"kind": "SCALAR", "name": "ID", "ofType": None},
                }

                self.assertEqual(f["args"][0]["type"], want)

    def test_nonroot_type_field_names(self) -> None:
        nonroot_type = self.get_type("User")

        self.assertIsNotNone(nonroot_type)

        if not nonroot_type:
            return

        field_names = [f["name"] for f in nonroot_type["fields"]]

        # self.assertEqual(len(field_names), 3)
        self.assertIn("id", field_names)
        self.assertIn("email", field_names)
        self.assertIn("trips", field_names)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.clairvoyance.stdout:
            with open("/tmp/clairvoyance-tests.stdout", "wb") as f:
                f.write(cls.clairvoyance.stdout)

        if cls.clairvoyance.stderr:
            with open("/tmp/clairvoyance-tests.stderr", "wb") as f:
                f.write(cls.clairvoyance.stderr)


if __name__ == "__main__":
    unittest.main()
