import unittest
import logging
import json

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


if __name__ == "__main__":
    unittest.main()
