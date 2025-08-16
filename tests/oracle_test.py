import asyncio
import logging
import subprocess
import time
import unittest

import aiounittest

from clairvoyance import graphql, oracle
from clairvoyance.client import Client
from clairvoyance.entities.context import client
from clairvoyance.entities.oracle import FuzzingContext


class TestGetValidFields(unittest.TestCase):
    # pylint: disable=line-too-long
    def test_multiple_suggestions(self) -> None:
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

        want_3 = {"pastes", "users", "audits"}
        got_3 = oracle.get_valid_fields(
            'Cannot query field "assets" on type "Query". Did you mean "pastes", "users" or "audits"?'
        )
        self.assertEqual(got_3, want_3)

    def test_single_suggestion(self) -> None:
        want = {"homes"}
        got = oracle.get_valid_fields(
            'Cannot query field "home" on type "Query". Did you mean "homes"?'
        )
        self.assertEqual(got, want)

    def test_valid_field(self) -> None:
        want = {"address"}
        got = oracle.get_valid_fields(
            'Field "address" of type "HomeAddress" must have a selection of subfields. Did you mean "address { ... }"?'
        )
        self.assertEqual(got, want)

    def test_or_suggestion(self) -> None:
        want = {"devices", "unassigned"}
        got = oracle.get_valid_fields(
            'Cannot query field "designer" on type "Query". Did you mean "devices" or "unassigned"?'
        )
        self.assertEqual(got, want)


class TestGetValidArgs(unittest.TestCase):
    def test_single_suggestion(self) -> None:
        want = {"input"}
        got = oracle.get_valid_args(
            'Unknown argument "inpu" on field "setNameForHome" of type "Mutation". Did you mean "input"?'
        )
        self.assertEqual(got, want)

    def test_double_suggestion(self) -> None:
        want = {"after", "last"}
        got = oracle.get_valid_args(
            'Unknown argument "fasten" on field "filmConnection" of type "Vehicle". Did you mean "after" or "last"?'
        )
        self.assertEqual(got, want)

    def test_multiple_suggestions(self) -> None:
        want_3 = {"after", "first", "types"}
        got_3 = oracle.get_valid_args(
            'Unknown argument "fares" on field "Organization.vulnerabilities". Did you mean "after", "first", or "types"?'
        )
        self.assertEqual(got_3, want_3)

        want = {"port", "host", "path"}
        got = oracle.get_valid_args(
            'Unknown argument "pot" on field "importPaste" of type "Mutations". Did you mean "port", "host" or "path"?'
        )
        self.assertEqual(got, want)


class TestGetTypeRef(unittest.TestCase):
    def test_non_nullable_object(self) -> None:
        want = graphql.TypeRef(
            name="SetArmedStateForHomeInput",
            kind="INPUT_OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "setArmedStateForHome" argument "input" of type "SetArmedStateForHomeInput!" is required, but it was not provided.',
            FuzzingContext.ARGUMENT,
        )
        self.assertEqual(got, want)

    def test_input_suffix(self) -> None:
        want = graphql.TypeRef(
            name="OrganizationInput",
            kind="INPUT_OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "Organization" argument "input" of type "OrganizationInput!" is required, but it was not provided.',
            FuzzingContext.ARGUMENT,
        )
        self.assertEqual(got, want)

    def test_inputfield_object_non_nullable(self) -> None:
        want = graphql.TypeRef(
            name="SetArmedStateForHomeInput",
            kind="INPUT_OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            "Expected type SetArmedStateForHomeInput!, found 7.",
            FuzzingContext.ARGUMENT,
        )
        self.assertEqual(got, want)

    # pylint: disable=line-too-long
    def test_object_field(self) -> None:
        want = graphql.TypeRef(
            name="SetArmedStateForHomePayload",
            kind="OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Field "setArmedStateForHome" of type "SetArmedStateForHomePayload" must have a selection of subfields. Did you mean "setArmedStateForHome { ... }"?',
            FuzzingContext.FIELD,
        )
        self.assertEqual(got, want)

    def test_via_wrong_field(self) -> None:
        want = graphql.TypeRef(
            name="Boolean",
            kind="SCALAR",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "isMfaEnabled" must not have a selection since type "Boolean!" has no subfields.',
            FuzzingContext.FIELD,
        )
        self.assertEqual(got, want)

    def test_field_regex_3(self) -> None:
        want = graphql.TypeRef(
            name="HomeSettings",
            kind="OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Cannot query field "IAmWrongField" on type "HomeSettings".',
            FuzzingContext.FIELD,
        )
        self.assertEqual(got, want)

    def test_field_regex_4(self) -> None:
        want = graphql.TypeRef(
            name="InitDomainActionPayload",
            kind="OBJECT",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Cannot query field "message" on type "InitDomainActionPayload". Did you mean to use an inline fragment on "UserError" or "BaseUserError"?',
            FuzzingContext.FIELD,
        )
        self.assertEqual(got, want)

    def test_skip_error_message(self) -> None:
        want = None
        with self.assertLogs() as cm:
            got = oracle.get_typeref(
                'Field "species" of type "Species" must have a selection of subfields. Did you mean "species { ... }"?',
                FuzzingContext.ARGUMENT,
            )
            # https://stackoverflow.com/a/61381576
            logging.warning("Dummy warning")
        self.assertEqual(want, got)
        self.assertCountEqual(["WARNING:root:Dummy warning"], cm.output)

    def test_issue_16(self) -> None:
        want = graphql.TypeRef(
            name="ID",
            kind="SCALAR",
            is_list=False,
            non_null_item=False,
            non_null=True,
        )
        got = oracle.get_typeref(
            'Field "node" argument "id" of type "ID!" is required but not provided.',
            FuzzingContext.ARGUMENT,
        )
        self.assertIsNotNone(got)

        if not got:
            return

        self.assertEqual(got.name, want.name)
        self.assertEqual(got.kind, want.kind)
        self.assertEqual(got.is_list, want.is_list)
        self.assertEqual(got.non_null_item, want.non_null_item)
        self.assertEqual(got.non_null, want.non_null)

    def test_dvga(self) -> None:
        want = graphql.TypeRef(
            name="String",
            kind="SCALAR",
            is_list=False,
            non_null_item=False,
            non_null=False,
        )
        got = oracle.get_typeref(
            'Field "systemHealth" of type "String" must not have a sub selection.',
            FuzzingContext.FIELD,
        )

        self.assertIsNotNone(got)
        if not got:
            return

        self.assertEqual(got.name, want.name)
        self.assertEqual(got.kind, want.kind)
        self.assertEqual(got.is_list, want.is_list)
        self.assertEqual(got.non_null_item, want.non_null_item)
        self.assertEqual(got.non_null, want.non_null)


class TestTypeRef(unittest.TestCase):
    def test_to_json(self) -> None:
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
    def test_field_or_arg_type_from_json(self) -> None:
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


class TestProbeTypename(aiounittest.AsyncTestCase):
    _unstable: subprocess.Popen[bytes]

    @classmethod
    def setUpClass(cls) -> None:
        Client("http://localhost:8081/graphql")

        cls._unstable = subprocess.Popen(  # pylint: disable=consider-using-with
            ["python3", "tests/server/graphql.py"]
        )
        time.sleep(1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._unstable.terminate()
        cls._unstable.wait()

        asyncio.run(client().close())

    async def test_probe_typename(self) -> None:
        typename = await oracle.probe_typename("123")

        self.assertEqual(typename, "Mutation")


if __name__ == "__main__":
    unittest.main()
