import requests

import re
import logging
from typing import Any
from typing import Set
from typing import List
from typing import Dict
from typing import Optional

from clairvoyance import graphql


def get_valid_fields(error_message: str) -> Set:
    valid_fields = set()

    multiple_suggestions_re = 'Cannot query field "([_A-Za-z][_0-9A-Za-z]*)" on type "[_A-Za-z][_0-9A-Za-z]*". Did you mean (?P<multi>("[_A-Za-z][_0-9A-Za-z]*", )+)(or "(?P<last>[_A-Za-z][_0-9A-Za-z]*)")?\?'
    or_suggestion_re = 'Cannot query field "[_A-Za-z][_0-9A-Za-z]*" on type "[_A-Za-z][_0-9A-Za-z]*". Did you mean "(?P<one>[_A-Za-z][_0-9A-Za-z]*)" or "(?P<two>[_A-Za-z][_0-9A-Za-z]*)"\?'
    single_suggestion_re = 'Cannot query field "([_A-Za-z][_0-9A-Za-z]*)" on type "[_A-Za-z][_0-9A-Za-z]*". Did you mean "(?P<field>[_A-Za-z][_0-9A-Za-z]*)"\?'
    invalid_field_re = (
        'Cannot query field "[_A-Za-z][_0-9A-Za-z]*" on type "[_A-Za-z][_0-9A-Za-z]*".'
    )
    # TODO: this regex here more than one time, make it shared?
    valid_field_regexes = [
        'Field "(?P<field>[_A-Za-z][_0-9A-Za-z]*)" of type "(?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)" must have a selection of subfields. Did you mean "[_A-Za-z][_0-9A-Za-z]* \{ ... \}"\?',
    ]

    no_fields_regex = 'Field "[_A-Za-z][_0-9A-Za-z]*" must not have a selection since type "[0-9a-zA-Z\[\]!]+" has no subfields.'

    if re.fullmatch(no_fields_regex, error_message):
        return valid_fields

    if re.fullmatch(multiple_suggestions_re, error_message):
        match = re.fullmatch(multiple_suggestions_re, error_message)

        for m in match.group("multi").split(", "):
            if m:
                valid_fields.add(m.strip('"'))

        if match.group("last"):
            valid_fields.add(match.group("last"))
    elif re.fullmatch(or_suggestion_re, error_message):
        match = re.fullmatch(or_suggestion_re, error_message)

        valid_fields.add(match.group("one"))
        valid_fields.add(match.group("two"))
    elif re.fullmatch(single_suggestion_re, error_message):
        match = re.fullmatch(single_suggestion_re, error_message)

        valid_fields.add(match.group("field"))
    elif re.fullmatch(invalid_field_re, error_message):
        pass
    elif re.fullmatch(valid_field_regexes[0], error_message):
        match = re.fullmatch(valid_field_regexes[0], error_message)
        valid_fields.add(match.group("field"))
    else:
        logging.warning(f"Unknown error message: '{error_message}'")

    return valid_fields


def probe_valid_fields(
    wordlist: Set, config: graphql.Config, input_document: str
) -> Set[str]:
    # We're assuming all fields from wordlist are valid,
    # then remove fields that produce an error message
    valid_fields = set(wordlist)

    for i in range(0, len(wordlist), config.bucket_size):
        bucket = wordlist[i : i + config.bucket_size]

        document = input_document.replace("FUZZ", " ".join(bucket))

        response = graphql.post(
            config.url, headers=config.headers, json={"query": document}
        )
        errors = response.json()["errors"]
        logging.debug(
            f"Sent {len(bucket)} fields, recieved {len(errors)} errors in {response.elapsed.total_seconds()} seconds"
        )

        for error in errors:
            error_message = error["message"]

            if (
                "must not have a selection since type" in error_message
                and "has no subfields" in error_message
            ):
                return set()

            # First remove field if it produced an "Cannot query field" error
            match = re.search(
                'Cannot query field "(?P<invalid_field>[_A-Za-z][_0-9A-Za-z]*)"',
                error_message,
            )
            if match:
                valid_fields.discard(match.group("invalid_field"))

            # Second obtain field suggestions from error message
            valid_fields |= get_valid_fields(error_message)

    return valid_fields


def probe_valid_args(
    field: str, wordlist: Set, config: graphql.Config, input_document: str
) -> Set[str]:
    valid_args = set(wordlist)

    document = input_document.replace(
        "FUZZ", f"{field}({', '.join([w + ': 7' for w in wordlist])})"
    )

    response = graphql.post(
        config.url, headers=config.headers, json={"query": document}
    )
    errors = response.json()["errors"]

    for error in errors:
        error_message = error["message"]

        if (
            "must not have a selection since type" in error_message
            and "has no subfields" in error_message
        ):
            return set()

        # First remove arg if it produced an "Unknown argument" error
        match = re.search(
            'Unknown argument "(?P<invalid_arg>[_A-Za-z][_0-9A-Za-z]*)" on field "[_A-Za-z][_0-9A-Za-z.]*"',
            error_message,
        )
        if match:
            valid_args.discard(match.group("invalid_arg"))

        # Second obtain args suggestions from error message
        valid_args |= get_valid_args(error_message)

    return valid_args


def probe_args(
    field: str, wordlist: Set, config: graphql.Config, input_document: str
) -> Set[str]:
    valid_args = set()

    for i in range(0, len(wordlist), config.bucket_size):
        bucket = wordlist[i : i + config.bucket_size]
        valid_args |= probe_valid_args(field, bucket, config, input_document)

    return valid_args


def get_valid_args(error_message: str) -> Set[str]:
    return grep(error_message, "InputValue", "name")


def grep(error_message: str, context: str, what: str) -> Optional[Set[str]]:
    NAME = "[_A-Za-z][_0-9A-Za-z]*"
    TYPEREF = "\[?[_A-Za-z][_0-9A-Za-z]*!?\]?!?"

    SKIP_REGEXES = [
        f'Unknown argument "{NAME}" on field "{NAME}\.{NAME}"\.',
        f"Cannot return null for non-nullable field {NAME}\.{NAME}\.",
    ]

    FREGEXES = [
        f'Field "{NAME}" of type "(?P<typeref>{TYPEREF})" must have a selection of subfields\. Did you mean "{NAME} {{ \.\.\. }}"\?',
        f'Field "{NAME}" must not have a selection since type "(?P<typeref>{TYPEREF})" has no subfields\.',
        f'Cannot query field "{NAME}" on type "(?P<typeref>{TYPEREF})"\.',
        f'Unknown argument "{NAME}" on field "{NAME}" of type "(?P<typeref>{TYPEREF})"\.',
    ]

    IVREGEXES = [
        f'Field "{NAME}" argument "(?P<arg>{NAME})" of type "(?P<typeref>{TYPEREF})" is required, but it was not provided\.',
        f"Expected type (?P<typeref>{TYPEREF}), found .+\.",
        f"(?P<typeref>{TYPEREF}) cannot represent .+",
        f"Field {NAME}\.(?P<arg>{NAME}) of required type (?P<typeref>{TYPEREF}) was not provided\.",
        f'Field "{NAME}\.{NAME}" of required type "(?P<typeref>{TYPEREF})" was not provided\.',
        f'Unknown argument "{NAME}" on field "{NAME}" of type "{TYPEREF}"\. Did you mean "(?P<arg>{NAME})"\?',
        f'Unknown argument "{NAME}" on field "{NAME}\.{NAME}"\. Did you mean "(?P<arg>{NAME})"\?',
        f'Unknown argument "{NAME}" on field "{NAME}" of type "{TYPEREF}"\. Did you mean "(?P<first_arg>{NAME})" or "(?P<second_arg>{NAME})"\?',
    ]

    ret = set()
    regexes = None
    skip_regexes = SKIP_REGEXES
    is_unknown_error_message = True

    if context == "Field":
        regexes = FREGEXES
        skip_regexes += IVREGEXES
    elif context == "InputValue":
        regexes = IVREGEXES
        skip_regexes += FREGEXES
    else:
        raise Exception(f"Unknown context: {context}")

    for r in skip_regexes:
        if re.fullmatch(r, error_message):
            return set()

    if what == "typeref":
        for r in regexes:
            match = re.fullmatch(r, error_message)
            if match:
                is_unknown_error_message = False
                if "typeref" in match.groupdict():
                    ret.add(match.group("typeref"))
                break
    elif what == "name":
        for r in regexes:
            match = re.fullmatch(r, error_message)
            if match:
                is_unknown_error_message = False
                if "arg" in match.groupdict():
                    ret.add(match.group("arg"))
                elif (
                    "first_arg" in match.groupdict()
                    and "second_arg" in match.groupdict()
                ):
                    ret.add(match.group("first_arg"))
                    ret.add(match.group("second_arg"))
    else:
        raise Exception(f"Unknown what: {what}")

    if is_unknown_error_message:
        logging.warning(f"Unknown error ({context}, {what}): {error_message}")

    return ret


def get_typeref(error_message: str, context: str) -> Optional[graphql.TypeRef]:
    typeref = None

    match = grep(error_message, context, "typeref")

    if match:
        if len(match) != 1:
            raise Exception(f"grep for TypeRef returned {match} matches")

        typeref_string = match.pop()

        name = typeref_string.replace("!", "").replace("[", "").replace("]", "")
        kind = None

        if name in ["Int", "Float", "String", "Boolean", "ID"]:
            kind = "SCALAR"
        else:
            if context == "Field":
                kind = "OBJECT"
            elif context == "InputValue":
                kind = "INPUT_OBJECT"
            else:
                raise Exception(f"Unexpected context: {context}")

        is_list = True if "[" and "]" in typeref_string else False
        non_null_item = True if "!]" in typeref_string else False
        non_null = True if typeref_string.endswith("!") else False

        typeref = graphql.TypeRef(
            name,
            kind,
            is_list=is_list,
            non_null_item=non_null_item,
            non_null=non_null,
        )

    return typeref


def probe_typeref(
    documents: List[str], context: str, config: graphql.Config
) -> Optional[graphql.TypeRef]:
    typeref = None
    errors = []

    for document in documents:
        response = graphql.post(
            config.url, headers=config.headers, json={"query": document}
        )
        errors += response.json().get("errors", [])

    for error in errors:
        typeref = get_typeref(error["message"], context)
        if typeref:
            break

    if not typeref:
        raise Exception(f"Unable to get TypeRef for {documents}")

    return typeref


def probe_field_type(
    field: str, config: graphql.Config, input_document: str
) -> graphql.TypeRef:
    documents = [
        input_document.replace("FUZZ", f"{field}"),
        input_document.replace("FUZZ", f"{field} {{ lol }}"),
    ]

    typeref = probe_typeref(documents, "Field", config)
    return typeref


def probe_arg_typeref(
    field: str, arg: str, config: graphql.Config, input_document: str
) -> graphql.TypeRef:
    documents = [
        input_document.replace("FUZZ", f"{field}({arg[:-1]}: 7)"),
        input_document.replace("FUZZ", f"{field}({arg}: {{}})"),
        input_document.replace("FUZZ", f"{field}({arg}: 7)"),
    ]

    typeref = probe_typeref(documents, "InputValue", config)
    return typeref


def probe_typename(input_document: str, config: graphql.Config) -> str:
    typename = ""
    wrong_field = "imwrongfield"
    document = input_document.replace("FUZZ", wrong_field)

    response = graphql.post(
        config.url, headers=config.headers, json={"query": document}
    )
    errors = response.json()["errors"]

    wrong_field_regexes = [
        f'Cannot query field "{wrong_field}" on type "(?P<typename>[_0-9a-zA-Z\[\]!]*)".',
        f'Field "[_0-9a-zA-Z\[\]!]*" must not have a selection since type "(?P<typename>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)" has no subfields.',
    ]

    match = None

    for regex in wrong_field_regexes:
        for error in errors:
            match = re.fullmatch(regex, error["message"])
            if match:
                break
        if match:
            break

    if not match:
        raise Exception(f"Expected '{errors}' to match any of '{wrong_field_regexes}'.")

    typename = (
        match.group("typename").replace("[", "").replace("]", "").replace("!", "")
    )

    return typename


def fetch_root_typenames(config: graphql.Config) -> Dict[str, Optional[str]]:
    documents = {
        "queryType": "query { __typename }",
        "mutationType": "mutation { __typename }",
        "subscriptionType": "subscription { __typename }",
    }
    typenames = {
        "queryType": None,
        "mutationType": None,
        "subscriptionType": None,
    }

    for name, document in documents.items():
        response = graphql.post(
            config.url, headers=config.headers, json={"query": document}
        )
        data = response.json().get("data", {})

        if data:
            typenames[name] = data["__typename"]

    logging.debug(f"Root typenames are: {typenames}")

    return typenames


def clairvoyance(
    wordlist: List[str],
    config: graphql.Config,
    input_schema: Dict[str, Any] = None,
    input_document: str = None,
) -> Dict[str, Any]:
    if not input_schema:
        root_typenames = fetch_root_typenames(config)
        schema = graphql.Schema(
            queryType=root_typenames["queryType"],
            mutationType=root_typenames["mutationType"],
            subscriptionType=root_typenames["subscriptionType"],
        )
    else:
        schema = graphql.Schema(schema=input_schema)

    typename = probe_typename(input_document, config)
    field_names = probe_valid_fields(wordlist, config, input_document)

    logging.debug(f"{typename}.fields = {field_names}")

    for field_name in field_names:
        typeref = probe_field_type(field_name, config, input_document)
        field = graphql.Field(field_name, typeref)

        arg_names = probe_args(field.name, wordlist, config, input_document)
        logging.debug(f"{typename}.{field_name}.args = {arg_names}")
        for arg_name in arg_names:
            arg_typeref = probe_arg_typeref(
                field.name, arg_name, config, input_document
            )
            arg = graphql.InputValue(arg_name, arg_typeref)

            field.args.append(arg)
            schema.add_type(arg.type.name, arg.type.kind)

        schema.types[typename].fields.append(field)
        schema.add_type(field.type.name, "OBJECT")

    return schema.to_json()


def probe_input_value_typeref(
    input_value: str, input_document: str, config: graphql.Config
) -> graphql.TypeRef:
    documents = [
        input_document.replace("FUZZ", f"{input_value}: 7"),
        input_document.replace("FUZZ", f"{input_value}: {{}}"),
    ]

    typeref = probe_typeref(documents, "InputValue", config)
    return typeref


def probe_input_values(
    wordlist: Set, input_document: str, config: graphql.Config
) -> List[str]:
    errors = []

    for i in range(0, len(wordlist), config.bucket_size):
        bucket = wordlist[i : i + config.bucket_size]

        document = input_document.replace(
            "FUZZ", ", ".join([w + ": 7" for w in wordlist])
        )

        response = graphql.post(
            config.url, headers=config.headers, json={"query": document}
        )

        errors += [e["message"] for e in response.json()["errors"]]

    return errors


def grep_valid_input_values(error_message: str) -> Set[str]:
    return grep(error_message, "InputValue", "name")


def obtain_valid_input_values(wordlist: Set[str], errors: List[str]) -> Set[str]:
    valid_input_values = set(wordlist.copy())

    for error_message in errors:
        # Frist remove entity if it produced an error
        match = re.search(
            'Field "(?P<field>[_A-Za-z][_0-9A-Za-z]*)" is not defined by type "?[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*"?\.',
            error_message,
        )
        if match:
            valid_input_values.discard(match.group("field"))

        # Second obtain suggestions from error message
        valid_input_values |= grep_valid_input_values(error_message)

    return valid_input_values


# clairvoyance() for INPUT_OBJECT
def clairvoyance_io(
    wordlist: List[str],
    config: graphql.Config,
    input_schema: Dict[str, Any],
    input_document: str,
    name: str,
) -> Dict[str, Any]:
    schema = graphql.Schema(schema=input_schema)

    errors = probe_input_values(wordlist, input_document, config)
    input_values = obtain_valid_input_values(wordlist, errors)

    for input_value in input_values:
        typeref = probe_input_value_typeref(input_value, input_document, config)
        logging.info(
            f"{input_value}.TypeRef.kind = {typeref.kind}\t{input_value}.TypeRef.name = {typeref.name}"
        )

        schema.types[name].fields.append(graphql.Field(input_value, typeref))

    return schema.to_json()
