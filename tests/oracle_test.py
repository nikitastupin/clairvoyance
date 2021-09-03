import time
import logging
import unittest
import subprocess

from clairvoyance import graphql
from clairvoyance import oracle


class TestGetValidFields(unittest.TestCase):
    def test_multiple_suggestions(self):
        want = {
            "setNameForHome",
            "setNameForCamera",
            "setAddressForHome",
            "setNameForHomeSensor",
            "setArmedStateForHome",
        }
        got = oracle.get_valid_fields(
            'Cannot query field "NameForHome" on type "Mutation". Did you mean "setNameForHome", "setNameForCamera", "setAddressForHome", "setNameForHomeSensor", or "setArmedStateForHome"?'
        )
        self.assertEqual(got, want)

        want_2 = {"homeId", "name", "role"}
        got_2 = oracle.get_valid_fields(
            'Cannot query field "home" on type "Home". Did you mean "homeId", "name", or "role"?'
        )
        self.assertEqual(got_2, want_2)

    def test_single_suggestion(self):
        want = {"homes"}
        got = oracle.get_valid_fields(
            'Cannot query field "home" on type "Query". Did you mean "homes"?'
        )
        self.assertEqual(got, want)

    def test_valid_field(self):
        want = {"address"}
        got = oracle.get_valid_fields(
            'Field "address" of type "HomeAddress" must have a selection of subfields. Did you mean "address { ... }"?'
        )
        self.assertEqual(got, want)

    def test_or_suggestion(self):
        want = {"devices", "unassigned"}
        got = oracle.get_valid_fields(
            'Cannot query field "designer" on type "Query". Did you mean "devices" or "unassigned"?'
        )
        self.assertEqual(got, want)


class TestGetValidArgs(unittest.TestCase):
    def test_single_suggestion(self):
        want = {"input"}
        got = oracle.get_valid_args(
            'Unknown argument "inpu" on field "setNameForHome" of type "Mutation". Did you mean "input"?'
        )
        self.assertEqual(got, want)

    def test_double_suggestion(self):
        want = {"after", "last"}
        got = oracle.get_valid_args(
            'Unknown argument "fasten" on field "filmConnection" of type "Vehicle". Did you mean "after" or "last"?'
        )
        self.assertEqual(got, want)


class TestGetValidInputFields(unittest.TestCase):
    def test_single_suggestion(self):
        want = {"name"}
        got = oracle.get_valid_input_fields(
            "Field SetNameForHomeInput.name of required type String! was not provided."
        )
        self.assertEqual(got, want)


class TestGetTypeRef(unittest.TestCase):
    def test_non_nullable_object(self):
        want = graphql.TypeRef(
            name="SetArmedStateForHomeInput",
            kind="INPUT_OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "setArmedStateForHome" argument "input" of type "SetArmedStateForHomeInput!" is required, but it was not provided.',
            "InputValue",
        )
        self.assertEqual(got, want)

    def test_inputfield_object_non_nullable(self):
        want = graphql.TypeRef(
            name="SetArmedStateForHomeInput",
            kind="INPUT_OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            "Expected type SetArmedStateForHomeInput!, found 7.", "InputValue"
        )
        self.assertEqual(got, want)

    def test_object_field(self):
        want = graphql.TypeRef(
            name="SetArmedStateForHomePayload",
            kind="OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Field "setArmedStateForHome" of type "SetArmedStateForHomePayload" must have a selection of subfields. Did you mean "setArmedStateForHome { ... }"?',
            "Field",
        )
        self.assertEqual(got, want)

    def test_via_wrong_field(self):
        want = graphql.TypeRef(
            name="Boolean",
            kind="SCALAR",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "isMfaEnabled" must not have a selection since type "Boolean!" has no subfields.',
            "Field",
        )
        self.assertEqual(got, want)

    def test_field_regex_3(self):
        want = graphql.TypeRef(
            name="HomeSettings",
            kind="OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Cannot query field "imwrongfield" on type "HomeSettings".', "Field"
        )
        self.assertEqual(got, want)

    def test_skip_error_message(self):
        want = None
        with self.assertLogs() as cm:
            got = oracle.get_typeref(
                'Field "species" of type "Species" must have a selection of subfields. Did you mean "species { ... }"?',
                "InputValue",
            )
            # https://stackoverflow.com/a/61381576
            logging.warning("Dummy warning")
        self.assertEqual(want, got)
        self.assertCountEqual(["WARNING:root:Dummy warning"], cm.output)

    def test_issue_16(self):
        want = graphql.TypeRef(
            name="ID",
            kind="SCALAR",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "node" argument "id" of type "ID!" is required but not provided.', "InputValue"
        )
        self.assertEqual(got.name, want.name)
        self.assertEqual(got.kind, want.kind)
        self.assertEqual(got.is_list, want.is_list)
        self.assertEqual(got.non_null_item, want.non_null_item)
        self.assertEqual(got.non_null, want.non_null)


class TestTypeRef(unittest.TestCase):
    def test_to_json(self):
        name = "TestObject"
        kind = "OBJECT"

        want = {
            "kind": "NON_NULL",
            "name": None,
            "ofType": {
                "kind": "LIST",
                "name": None,
                "ofType": {
                    "kind": "NON_NULL",
                    "name": None,
                    "ofType": {"kind": kind, "name": name, "ofType": None},
                },
            },
        }
        got = graphql.TypeRef(
            name=name,
            kind=kind,
            is_list=True,
            non_null_item=True,
            non_null=True,
        ).to_json()
        self.assertEqual(got, want)


class TestGraphql(unittest.TestCase):
    def test_field_or_arg_type_from_json(self):
        name = "TestObject"
        kind = "OBJECT"
        want = graphql.TypeRef(
            name=name,
            kind=kind,
            is_list=True,
            non_null_item=True,
            non_null=True,
        )
        got = graphql.field_or_arg_type_from_json(
            {
                "kind": "NON_NULL",
                "name": None,
                "ofType": {
                    "kind": "LIST",
                    "name": None,
                    "ofType": {
                        "kind": "NON_NULL",
                        "name": None,
                        "ofType": {"kind": kind, "name": name, "ofType": None},
                    },
                },
            }
        )
        self.assertEqual(got, want)


class TestProbeTypename(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._unstable = subprocess.Popen(["python3", "tests/server/graphql.py"])
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        cls._unstable.terminate()
        cls._unstable.wait()

    def test_probe_typename(self):
        config = graphql.Config()
        config.url = "http://localhost:8001"
        typename = oracle.probe_typename("123", config)
        self.assertEqual(typename, "Mutation")


if __name__ == "__main__":
    unittest.main()
