import json
import logging
import subprocess
import time
import unittest

logging.basicConfig(level=logging.ERROR)

from clairvoyance import graphql


class TestSchema(unittest.TestCase):

    def setUp(self) -> None:
        with open("tests/data/schema.json", "r") as f:
            schema_json = json.load(f)
            self.schema = graphql.Schema(schema=schema_json)

    def test_get_path_from_root(self) -> None:
        want = ["Query", "homes", "paymentSubscriptions"]
        got = self.schema.get_path_from_root("PaymentSubscriptionsForHome")
        self.assertEqual(got, want)

    def test_get_type_without_fields(self) -> None:
        want = "Mutation"
        got = self.schema.get_type_without_fields()
        self.assertEqual(got, want)

    def test_convert_path_to_document(self) -> None:
        path = ["Query", "homes", "paymentSubscriptions"]
        want = "query { homes { paymentSubscriptions { FUZZ } } }"
        got = self.schema.convert_path_to_document(path)
        self.assertEqual(got, want)

    def test_raise_exception_on_unknown_operation_type(self) -> None:
        input = ["UnknownType"]

        with self.assertRaises(Exception) as cm:
            self.schema.convert_path_to_document(input)

        exception_msg = str(cm.exception)
        self.assertEqual(exception_msg, "Unknown operation type")

    def test_convert_path_to_document_handling_subscription(self) -> None:
        path = ["Subscription"]
        want = "subscription { FUZZ }"
        got = self.schema.convert_path_to_document(path)
        self.assertEqual(got, want)


class TestPost(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls._unstable = subprocess.Popen(["python3", "tests/server/unstable.py"])
        time.sleep(1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._unstable.terminate()
        cls._unstable.wait()

    def test_retries_on_500(self) -> None:
        response = graphql.post("http://localhost:8000")
        self.assertEqual(response.status_code, 200)


class TestToJson(unittest.TestCase):

    def test_typeref_to_json(self) -> None:
        want = {
            "name": None,
            "kind": "NON_NULL",
            "ofType": {
                "name": None,
                "kind": "LIST",
                "ofType": {
                    "name": "String",
                    "kind": "SCALAR",
                    "ofType": None
                },
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


class TestFromJson(unittest.TestCase):

    def test_typeref_from_json(self) -> None:
        want = graphql.TypeRef("Launch", "OBJECT", True, False, True)

        typeref = {
            "kind": "NON_NULL",
            "name": None,
            "ofType": {
                "kind": "LIST",
                "name": None,
                "ofType": {
                    "kind": "OBJECT",
                    "name": "Launch",
                    "ofType": None
                },
            },
        }

        got = graphql.field_or_arg_type_from_json(typeref)

        self.assertEqual(got.to_json(), want.to_json())


if __name__ == "__main__":
    unittest.main()
