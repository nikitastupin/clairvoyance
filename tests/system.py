import os
import json
import unittest
import subprocess
import time


class TestClairvoyance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cwd = "/tmp/swapi-graphql"
        cls.port = "1337"

        env = os.environ
        env["PORT"] = cls.port

        cls.swapi = subprocess.Popen(["npm", "start"], env=env, cwd=cls.cwd)
        time.sleep(5)

        output_file = "/tmp/t.json"
        cls.p = subprocess.run(
            [
                "python3",
                "-m",
                "clairvoyance",
                "-o",
                output_file,
                "-w",
                "tests/data/swapi/wordlist.txt",
                f"http://localhost:{cls.port}",
            ],
            capture_output=True,
        )

        cls.swapi.terminate()
        cls.swapi.wait()

        with open(output_file) as f:
            cls.schema = json.load(f)

        cls._schema = cls.schema["data"]["__schema"]

    @unittest.skip("Clairvoyance produces false positive warnings")
    def test_no_warnings(self):
        self.assertFalse(p.stderr)

    def test_found_valid_root_types(self):
        self.assertEqual(self._schema["queryType"], {"name": "Root"})
        self.assertIsNone(self._schema["mutationType"])
        self.assertIsNone(self._schema["subscriptionType"])

    def test_found_valid_field(self):
        self.assertIn("Vehicle", [t["name"] for t in self._schema["types"]])

    @classmethod
    def tearDownClass(cls):
        if cls.p.stdout:
            print(cls.p.stdout)
        if cls.p.stderr:
            print(cls.p.stderr)


if __name__ == "__main__":
    unittest.main()
