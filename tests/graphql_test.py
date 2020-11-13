import unittest
import logging
import json
import time
import subprocess

logging.basicConfig(level=logging.ERROR)

from clairvoyance import graphql


class TestSchema(unittest.TestCase):
    def setUp(self):
        with open("tests/data/schema.json", "r") as f:
            schema_json = json.load(f)
            self.schema = graphql.Schema(schema=schema_json)

    def test_get_path_from_root(self):
        want = ["Query", "homes", "paymentSubscriptions"]
        got = self.schema.get_path_from_root("PaymentSubscriptionsForHome")
        self.assertEqual(got, want)

    def test_get_type_without_fields(self):
        want = "Mutation"
        got = self.schema.get_type_without_fields()
        self.assertEqual(got, want)

    def test_convert_path_to_document(self):
        path = ["Query", "homes", "paymentSubscriptions"]
        want = "query { homes { paymentSubscriptions { FUZZ } } }"
        got = self.schema.convert_path_to_document(path)
        self.assertEqual(got, want)

    def test_raise_exception_on_unknown_operation_type(self):
        input = ["UnknownType"]

        with self.assertRaises(Exception) as cm:
            self.schema.convert_path_to_document(input)

        exception_msg = str(cm.exception)
        self.assertEqual(exception_msg, "Unknown operation type")

    def test_convert_path_to_document_handling_subscription(self):
        path = ["Subscription"]
        want = "subscription { FUZZ }"
        got = self.schema.convert_path_to_document(path)
        self.assertEqual(got, want)


class TestPost(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._unstable = subprocess.Popen(["python3", "tests/server/unstable.py"])
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls._unstable.terminate()
        cls._unstable.wait()

    def test_retries_on_500(self):
        response = graphql.post("http://localhost:8000")
        self.assertEqual(response.status_code, 200)


class TestToJson(unittest.TestCase):
    def test_typeref_to_json(self):
        want = {
            "name": None,
            "kind": "NON_NULL",
            "ofType": {
                "name": None,
                "kind": "LIST",
                "ofType": {"name": "String", "kind": "SCALAR", "ofType": None},
            },
        }

        typeref = graphql.TypeRef(
            name="String",
            kind="SCALAR",
            is_list=True,
            non_null_item=False,
            non_null=True,
        )
        got = typeref.to_json()

        # https://github.com/nikitastupin/clairvoyance/issues/9
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
