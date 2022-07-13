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

    multiple_suggestions_re = 'Cannot query field [\'"]([_A-Za-z][_0-9A-Za-z]*)[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean (?P<multi>([\'"][_A-Za-z][_0-9A-Za-z]*[\'"], )+)(or [\'"](?P<last>[_A-Za-z][_0-9A-Za-z]*)[\'"])?\?'
    or_suggestion_re = 'Cannot query field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean [\'"](?P<one>[_A-Za-z][_0-9A-Za-z]*)[\'"] or [\'"](?P<two>[_A-Za-z][_0-9A-Za-z]*)[\'"]\?'
    single_suggestion_re = 'Cannot query field [\'"]([_A-Za-z][_0-9A-Za-z]*)[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean [\'"](?P<field>[_A-Za-z][_0-9A-Za-z]*)[\'"]\?'
    invalid_field_re = (
        'Cannot query field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"].'
    )
    # TODO: this regex here more than one time, make it shared?
    valid_field_regexes = [
        'Field [\'"](?P<field>[_A-Za-z][_0-9A-Za-z]*)[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a selection of subfields. Did you mean [\'"][_A-Za-z][_0-9A-Za-z]* \{ ... \}[\'"]\?',
    ]

    no_fields_regex = 'Field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] must not have a selection since type [\'"][0-9a-zA-Z\[\]!]+[\'"] has no subfields.'

    if re.fullmatch(no_fields_regex, error_message):
        return valid_fields

    if re.fullmatch(multiple_suggestions_re, error_message):
        match = re.fullmatch(multiple_suggestions_re, error_message)

        for m in match.group("multi").split(", "):
            if m:
                valid_fields.add(m.strip('"').strip("'"))

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
        bucket = wordlist[i: i + config.bucket_size]

        document = input_document.replace("FUZZ", " ".join(bucket))

        response = graphql.post(
            config.url,
            headers=config.headers,
            json={"query": document},
            verify=config.verify,
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
                'Cannot query field [\'"](?P<invalid_field>[_A-Za-z][_0-9A-Za-z]*)[\'"]',
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
        config.url,
        headers=config.headers,
        json={"query": document},
        verify=config.verify,
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
            'Unknown argument [\'"](?P<invalid_arg>[_A-Za-z][_0-9A-Za-z]*)[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z.]*[\'"]',
            error_message,
        )
        if match:
            valid_args.discard(match.group("invalid_arg"))

        duplicate_arg_regex = 'There can be only one argument named [\"](?P<arg>[_0-9a-zA-Z\[\]!]*)[\"]\.?'
        if re.fullmatch(duplicate_arg_regex, error_message):
            match = re.fullmatch(duplicate_arg_regex, error_message)
            valid_args.discard(match.group("arg"))
            continue

        # Second obtain args suggestions from error message
        valid_args |= get_valid_args(error_message)

    return valid_args


def probe_args(
    field: str, wordlist: Set, config: graphql.Config, input_document: str
) -> Set[str]:
    valid_args = set()

    for i in range(0, len(wordlist), config.bucket_size):
        bucket = wordlist[i: i + config.bucket_size]
        valid_args |= probe_valid_args(field, bucket, config, input_document)

    return valid_args


def get_valid_args(error_message: str) -> Set[str]:
    valid_args = set()

    skip_regexes = [
        'Unknown argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] of type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"].',
        'Field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] of type [\'"][_A-Za-z\[\]!][a-zA-Z\[\]!]*[\'"] must have a selection of subfields. Did you mean [\'"][_A-Za-z][_0-9A-Za-z]* \{ ... \}[\'"]\?',
        'Field [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"] is required, but it was not provided.',
        'Unknown argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z.]*[\'"]\.',
    ]

    single_suggestion_regexes = [
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"][_0-9a-zA-Z\[\]!]*[\'"]. Did you mean [\'"](?P<arg>[_0-9a-zA-Z\[\]!]*)[\'"]\?'
    ]

    double_suggestion_regexes = [
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"]. Did you mean [\'"](?P<first>[_0-9a-zA-Z\[\]!]*)[\'"] or [\'"](?P<second>[_0-9a-zA-Z\[\]!]*)[\'"]\?'
    ]


    for regex in skip_regexes:
        if re.fullmatch(regex, error_message):
            return set()

    for regex in single_suggestion_regexes:
        if re.fullmatch(regex, error_message):
            match = re.fullmatch(regex, error_message)
            valid_args.add(match.group("arg"))

    for regex in double_suggestion_regexes:
        match = re.fullmatch(regex, error_message)
        if match:
            valid_args.add(match.group("first"))
            valid_args.add(match.group("second"))

    if not valid_args:
        logging.warning(f"Unknown error message: {error_message}")

    return valid_args


def get_valid_input_fields(error_message: str) -> Set:
    valid_fields = set()

    single_suggestion_re = "Field [_0-9a-zA-Z\[\]!]*.(?P<field>[_0-9a-zA-Z\[\]!]*) of required type [_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]* was not provided."

    if re.fullmatch(single_suggestion_re, error_message):
        match = re.fullmatch(single_suggestion_re, error_message)
        if match.group("field"):
            valid_fields.add(match.group("field"))
        else:
            logging.warning(f"Unknown error message: '{error_message}'")

    return valid_fields


def probe_input_fields(
    field: str, argument: str, wordlist: Set, config: graphql.Config
) -> Set[str]:
    valid_input_fields = set(wordlist)

    document = f"mutation {{ {field}({argument}: {{ {', '.join([w + ': 7' for w in wordlist])} }}) }}"

    response = graphql.post(
        config.url,
        headers=config.headers,
        json={"query": document},
        verify=config.verify,
    )
    errors = response.json()["errors"]

    for error in errors:
        error_message = error["message"]

        # First remove field if it produced an error
        match = re.search(
            'Field [\'"](?P<invalid_field>[_0-9a-zA-Z\[\]!]*)[\'"] is not defined by type [_0-9a-zA-Z\[\]!]*.',
            error_message,
        )
        if match:
            valid_input_fields.discard(match.group("invalid_field"))

        # Second obtain field suggestions from error message
        valid_input_fields |= get_valid_input_fields(error_message)

    return valid_input_fields


def get_typeref(error_message: str, context: str) -> Optional[graphql.TypeRef]:
    typeref = None

    field_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a selection of subfields. Did you mean [\'"][_0-9a-zA-Z\[\]!]* \{ ... \}[\'"]\?',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] must not have a selection since type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] has no subfields.',
        'Cannot query field [\'"][_0-9a-zA-Z\[\]!]*[\'"] on type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"].',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must not have a sub selection\.',
    ]
    arg_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] is required.+\.',
        "Expected type (?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*), found .+\."
    ]
    arg_skip_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"] must have a selection of subfields\. Did you mean [\'"][_0-9a-zA-Z\[\]!]* \{ \.\.\. \}[\'"]\?'
    ]

    match = None

    if context == "Field":
        for regex in field_regexes:
            if re.fullmatch(regex, error_message):
                match = re.fullmatch(regex, error_message)
                break
    elif context == "InputValue":
        for regex in arg_skip_regexes:
            if re.fullmatch(regex, error_message):
                return None

        for regex in arg_regexes:
            if re.fullmatch(regex, error_message):
                match = re.fullmatch(regex, error_message)
                break

    if match:
        tk = match.group("typeref")

        name = tk.replace("!", "").replace("[", "").replace("]", "")
        kind = ""
        if name.endswith("Input"):
            kind = "INPUT_OBJECT"
        elif name in ["Int", "Float", "String", "Boolean", "ID"]:
            kind = "SCALAR"
        else:
            kind = "OBJECT"
        is_list = True if "[" and "]" in tk else False
        non_null_item = True if is_list and "!]" in tk else False
        non_null = True if tk.endswith("!") else False

        typeref = graphql.TypeRef(
            name=name,
            kind=kind,
            is_list=is_list,
            non_null_item=non_null_item,
            non_null=non_null,
        )
    else:
        logging.warning(f"Unknown error message: '{error_message}'")

    return typeref


def probe_typeref(
    documents: List[str], context: str, config: graphql.Config
) -> Optional[graphql.TypeRef]:
    typeref = None

    for document in documents:
        response = graphql.post(
            config.url,
            headers=config.headers,
            json={"query": document},
            verify=config.verify,
        )
        errors = response.json().get("errors", [])

        for error in errors:
            typeref = get_typeref(error["message"], context)
            logging.debug(f"get_typeref('{error['message']}', '{context}') -> {typeref}")
            if typeref:
                return typeref

    if not typeref and context != 'InputValue':
        raise Exception(f"Unable to get TypeRef for {documents} in context {context}")

    return None


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
        input_document.replace("FUZZ", f"{field}({arg}: 7)"),
        input_document.replace("FUZZ", f"{field}({arg}: {{}})"),
        input_document.replace("FUZZ", f"{field}({arg[:-1]}: 7)"),
        input_document.replace("FUZZ", f"{field}({arg}: \"7\")"),
        input_document.replace("FUZZ", f"{field}({arg}: false)"),
    ]

    typeref = probe_typeref(documents, "InputValue", config)
    return typeref


def probe_typename(input_document: str, config: graphql.Config) -> str:
    typename = ""
    wrong_field = "imwrongfield"
    document = input_document.replace("FUZZ", wrong_field)

    response = graphql.post(
        config.url,
        headers=config.headers,
        json={"query": document},
        verify=config.verify,
    )
    errors = response.json()["errors"]

    wrong_field_regexes = [
        f'Cannot query field [\'"]{wrong_field}[\'"] on type [\'"](?P<typename>[_0-9a-zA-Z\[\]!]*)[\'"].',
        f'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] must not have a selection since type [\'"](?P<typename>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] has no subfields.',
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
            config.url,
            headers=config.headers,
            json={"query": document},
            verify=config.verify,
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
    logging.debug(f"__typename = {typename}")

    valid_mutation_fields = probe_valid_fields(wordlist, config, input_document)
    logging.debug(f"{typename}.fields = {valid_mutation_fields}")

    for field_name in valid_mutation_fields:
        typeref = probe_field_type(field_name, config, input_document)
        field = graphql.Field(field_name, typeref)

        if field.type.name not in ["Int", "Float", "String", "Boolean", "ID"]:
            arg_names = probe_args(field.name, wordlist, config, input_document)
            logging.debug(f"{typename}.{field_name}.args = {arg_names}")
            for arg_name in arg_names:
                arg_typeref = probe_arg_typeref(
                    field.name, arg_name, config, input_document
                )
                if not arg_typeref:
                    logging.warning(f'Skip argument {arg_name} because TypeRef equals {arg_typeref}')
                    continue
                arg = graphql.InputValue(arg_name, arg_typeref)

                field.args.append(arg)
                schema.add_type(arg.type.name, "INPUT_OBJECT")
        else:
            logging.debug(
                f"Skip probe_args() for '{field.name}' of type '{field.type.name}'"
            )

        schema.types[typename].fields.append(field)
        schema.add_type(field.type.name, "OBJECT")

    return schema.to_json()
