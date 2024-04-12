# pylint: disable=anomalous-backslash-in-string, line-too-long

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from clairvoyance import graphql
from clairvoyance.entities import GraphQLPrimitive
from clairvoyance.entities.errors import EndpointError
from clairvoyance.entities.context import client, config, log
from clairvoyance.entities.oracle import FuzzingContext
from clairvoyance.utils import track

# yapf: disable

MAIN_REGEX = r"""[_0-9A-Za-z\.\[\]!]+"""
REQUIRED_BUT_NOT_PROVIDED = r"""required(, but it was not provided| but not provided)?\."""

_FIELD_REGEXES = {
    'SKIP': [
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] must not have a selection since type ['"]""" + MAIN_REGEX + r"""['"] has no subfields\.""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] argument ['"]""" + MAIN_REGEX + r"""['"] of type ['"]""" + MAIN_REGEX + r"""['"] is """ + REQUIRED_BUT_NOT_PROVIDED,
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"]""" + MAIN_REGEX + r"""['"]\.""",
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"](""" + MAIN_REGEX + r""")['"]\. Did you mean to use an inline fragment on ['"]""" + MAIN_REGEX + r"""['"]\?""",
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"](""" + MAIN_REGEX + r""")['"]\. Did you mean to use an inline fragment on ['"]""" + MAIN_REGEX + r"""['"] or ['"]""" + MAIN_REGEX + r"""['"]\?""",
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"](""" + MAIN_REGEX + r""")['"]\. Did you mean to use an inline fragment on (['"]""" + MAIN_REGEX + r"""['"], )+(or ['"]""" + MAIN_REGEX + r"""['"])?\?"""
    ],
    'VALID_FIELD': [
        r"""Field ['"](?P<field>""" + MAIN_REGEX + r""")['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] must have a selection of subfields\. Did you mean ['"]""" + MAIN_REGEX + r"""( \{ \.\.\. \})?['"]\?""",
        r"""Field ['"](?P<field>""" + MAIN_REGEX + r""")['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] must have a sub selection\."""
    ],
    'SINGLE_SUGGESTION': [
        r"""Cannot query field ['"](""" + MAIN_REGEX + r""")['"] on type ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean ['"](?P<field>""" + MAIN_REGEX + r""")['"]\?"""
    ],
    'DOUBLE_SUGGESTION': [
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean ['"](?P<one>""" + MAIN_REGEX + r""")['"] or ['"](?P<two>""" + MAIN_REGEX + r""")['"]\?"""
    ],
    'MULTI_SUGGESTION': [
        r"""Cannot query field ['"](""" + MAIN_REGEX + r""")['"] on type ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean (?P<multi>(['"]""" + MAIN_REGEX + r"""['"], )+)(or ['"](?P<last>""" + MAIN_REGEX + r""")['"])?\?"""
    ],
}

_ARG_REGEXES = {
    'SKIP': [
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"]\.""",
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"] of type ['"]""" + MAIN_REGEX + r"""['"]\.""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] of type ['"]""" + MAIN_REGEX + r"""['"] must have a selection of subfields\. Did you mean ['"]""" + MAIN_REGEX + r"""( \{ \.\.\. \})?['"]\?""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] argument ['"]""" + MAIN_REGEX + r"""['"] of type ['"]""" + MAIN_REGEX + r"""['"] is """ + REQUIRED_BUT_NOT_PROVIDED,
    ],
    'SINGLE_SUGGESTION': [
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"] of type ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean ['"](?P<arg>""" + MAIN_REGEX + r""")['"]\?""",
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean ['"](?P<arg>""" + MAIN_REGEX + r""")['"]\?"""
    ],
    'DOUBLE_SUGGESTION': [
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"]( of type ['"]""" + MAIN_REGEX + r"""['"])?\. Did you mean ['"](?P<first>""" + MAIN_REGEX + r""")['"] or ['"](?P<second>""" + MAIN_REGEX + r""")['"]\?"""
    ],
    'MULTI_SUGGESTION': [
        r"""Unknown argument ['"]""" + MAIN_REGEX + r"""['"] on field ['"]""" + MAIN_REGEX + r"""['"]\. Did you mean (?P<multi>(['"]""" + MAIN_REGEX + r"""['"], )+)(or ['"](?P<last>""" + MAIN_REGEX + r""")['"])?\?"""
    ],
}

_TYPEREF_REGEXES = {
    'FIELD': [
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] must have a selection of subfields\. Did you mean ['"]""" + MAIN_REGEX + r"""( \{ \.\.\. \})?['"]\?""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] must not have a selection since type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] has no subfields\.""",
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"]\.""",
        r"""Cannot query field ['"]""" + MAIN_REGEX + r"""['"] on type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"]\. Did you mean [^\?]+\?""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] must not have a sub selection\.""",
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] must have a sub selection\.""",

    ],
    'ARG': [
        r"""Field ['"]""" + MAIN_REGEX + r"""['"] argument ['"]""" + MAIN_REGEX + r"""['"] of type ['"](?P<typeref>""" + MAIN_REGEX + r""")['"] is """ + REQUIRED_BUT_NOT_PROVIDED,
        r"""Expected type (?P<typeref>""" + MAIN_REGEX + r"""), found .+\.""",
    ],
}

WRONG_FIELD_EXAMPLE = 'IAmWrongField'

_WRONG_TYPENAME = [
    r"""Cannot query field ['"]""" + WRONG_FIELD_EXAMPLE + r"""['"] on type ['"](?P<typename>""" + MAIN_REGEX + r""")['"].""",
    r"""Field ['"]""" + MAIN_REGEX + r"""['"] must not have a selection since type ['"](?P<typename>""" + MAIN_REGEX + r""")['"] has no subfields.""",
    r"""Field ['"]""" + MAIN_REGEX + r"""['"] of type ['"](?P<typename>""" + MAIN_REGEX + r""")['"] must not have a sub selection.""",
]

_GENERAL_SKIP = [
    r"""String cannot represent a non string value: .+""",
    r"""Float cannot represent a non numeric value: .+""",
    r"""ID cannot represent a non-string and non-integer value: .+""",
    r"""Enum ['"]""" + MAIN_REGEX + r"""['"] cannot represent non-enum value: .+"""
    r"""Int cannot represent non-integer value: .+""",
    r"""Not authorized""",
]

# yapf: enable

# Compiling all regexes for performance
FIELD_REGEXES = {k: [re.compile(r) for r in v] for k, v in _FIELD_REGEXES.items()}
ARG_REGEXES = {k: [re.compile(r) for r in v] for k, v in _ARG_REGEXES.items()}
TYPEREF_REGEXES = {k: [re.compile(r) for r in v] for k, v in _TYPEREF_REGEXES.items()}
WRONG_TYPENAME = [re.compile(r) for r in _WRONG_TYPENAME]
GENERAL_SKIP = [re.compile(r) for r in _GENERAL_SKIP]


# pylint: disable=too-many-branches
def get_valid_fields(error_message: str) -> Set[str]:
    """Fetching valid fields using regex heuristics."""

    valid_fields: Set[str] = set()

    for regex in FIELD_REGEXES['SKIP'] + GENERAL_SKIP:
        if regex.fullmatch(error_message):
            return valid_fields

    for regex in FIELD_REGEXES['VALID_FIELD']:
        match = regex.fullmatch(error_message)
        if match:
            valid_fields.add(match.group('field'))
            return valid_fields

    for regex in FIELD_REGEXES['SINGLE_SUGGESTION']:
        match = regex.fullmatch(error_message)
        if match:
            valid_fields.add(match.group('field'))
            return valid_fields

    for regex in FIELD_REGEXES['DOUBLE_SUGGESTION']:
        match = regex.fullmatch(error_message)
        if match:
            valid_fields.add(match.group('one'))
            valid_fields.add(match.group('two'))
            return valid_fields

    for regex in FIELD_REGEXES['MULTI_SUGGESTION']:
        match = regex.fullmatch(error_message)
        if match:

            for m in match.group('multi').split(', '):
                if m:
                    valid_fields.add(m.strip('"').strip('\''))
            if match.group('last'):
                valid_fields.add(match.group('last'))

            return valid_fields

    log().debug(f'Unknown error message for `valid_field`: \'{error_message}\'')

    return valid_fields


async def probe_valid_fields(
    wordlist: List[str],
    input_document: str,
) -> Set[str]:
    """Sending a wordlist to check for valid fields.

    Args:
        wordlist: The words that would leads to discovery.
        config: The config for the graphql client.
        input_document: The base document.

    Returns:
        A set of discovered valid fields.
    """

    async def __probation(i: int) -> Set[str]:
        bucket = wordlist[i:i + config().bucket_size]
        valid_fields = set(bucket)
        document = input_document.replace('FUZZ', ' '.join(bucket))

        start_time = time.time()
        response = await client().post(document)
        total_time = time.time() - start_time

        errors = response['errors']

        log().debug(f'Sent {len(bucket)} fields, received {len(errors)} errors in {round(total_time, 2)} seconds')

        for error in errors:
            error_message = error['message']

            if ('must not have a selection since type' in error_message and \
                'has no subfields' in error_message):
                return set()

            # ! LEGACY CODE please keep
            # First remove field if it produced an 'Cannot query field' error
            match = re.search(
                r"""Cannot query field [\'"](?P<invalid_field>[_A-Za-z][_0-9A-Za-z]*)[\'"]""",
                error_message,
            )
            if match:
                valid_fields.discard(match.group('invalid_field'))

            # Second obtain field suggestions from error message
            valid_fields |= get_valid_fields(error_message)

        return valid_fields

    # Create task list
    tasks: List[asyncio.Task] = []
    for i in range(0, len(wordlist), config().bucket_size):
        tasks.append(asyncio.create_task(__probation(i)))

    # Process results
    valid_fields = set()
    for task in track(asyncio.as_completed(tasks), description=f'Sending {len(tasks)} fields', total=len(tasks)):
        result = await task
        valid_fields.update(result)

    return valid_fields


async def probe_valid_args(
    field: str,
    wordlist: List[str],
    input_document: str,
) -> Set[str]:
    """Sends the wordlist as arguments and deduces its type from the error msgs received."""

    valid_args = set(wordlist)

    document = input_document.replace('FUZZ', f'{field}({", ".join([w + ": 7" for w in wordlist])})')

    response = await client().post(document=document)

    if 'errors' not in response:
        return valid_args

    errors = response['errors']
    for error in errors:
        error_message = error['message']

        if ('must not have a selection since type' in error_message and 'has no subfields' in error_message):
            return set()

        # First remove arg if it produced an 'Unknown argument' error
        match = re.search(
            r"""Unknown argument ['"](?P<invalid_arg>[_A-Za-z][_0-9A-Za-z]*)['"] on field ['"][_A-Za-z][_0-9A-Za-z\.]*['"]""",
            error_message,
        )
        if match:
            valid_args.discard(match.group('invalid_arg'))

        duplicate_arg_regex = r"""There can be only one argument named ["'](?P<arg>[_0-9a-zA-Z\.\[\]!]*)["']\.?"""
        if re.fullmatch(duplicate_arg_regex, error_message):
            match = re.fullmatch(duplicate_arg_regex, error_message)
            valid_args.discard(match.group('arg'))  # type: ignore
            continue

        # Second obtain args suggestions from error message
        valid_args |= get_valid_args(error_message)

    return valid_args


async def probe_args(
    field: str,
    wordlist: List[str],
    input_document: str,
) -> Set[str]:
    """Wrapper function for deducing the arg types."""

    tasks: List[asyncio.Task] = []
    for i in range(0, len(wordlist), config().bucket_size):
        bucket = wordlist[i:i + config().bucket_size]
        tasks.append(asyncio.create_task(probe_valid_args(field, bucket, input_document)))

    valid_args: Set[str] = set()

    results = await asyncio.gather(*tasks)
    for result in results:
        valid_args |= result

    return valid_args


def get_valid_args(error_message: str) -> Set[str]:
    """Get the type of an arg using regex."""

    valid_args = set()

    for regex in ARG_REGEXES['SKIP'] + GENERAL_SKIP:
        if re.fullmatch(regex, error_message):
            return set()

    for regex in ARG_REGEXES['SINGLE_SUGGESTION']:
        if re.fullmatch(regex, error_message):
            match = re.fullmatch(regex, error_message)
            if match:
                valid_args.add(match.group('arg'))

    for regex in ARG_REGEXES['DOUBLE_SUGGESTION']:
        match = re.fullmatch(regex, error_message)
        if match:
            valid_args.add(match.group('first'))
            valid_args.add(match.group('second'))

    for regex in ARG_REGEXES['MULTI_SUGGESTION']:
        if re.fullmatch(regex, error_message):
            match = re.fullmatch(regex, error_message)
            if match:
                for m in match.group('multi').split(', '):
                    if m:
                        valid_args.add(m.strip('"').strip('\''))

                if match.group('last'):
                    valid_args.add(match.group('last'))

    if not valid_args:
        log().debug(f'Unknown error message for `valid_args`: \'{error_message}\'')

    return valid_args


def get_typeref(
    error_message: str,
    context: FuzzingContext,
) -> Optional[graphql.TypeRef]:
    """Using predefined regex deduce the type of a field."""

    def __extract_matching_fields(
        error_message: str,
        context: FuzzingContext,
    ) -> Optional[re.Match]:

        if context == FuzzingContext.FIELD:
            # in the case of a field
            for regex in TYPEREF_REGEXES['ARG'] + GENERAL_SKIP:
                if re.fullmatch(regex, error_message):
                    return None

            for regex in TYPEREF_REGEXES['FIELD']:
                match = re.fullmatch(regex, error_message)
                if match:
                    return match

        elif context == FuzzingContext.ARGUMENT:
            # in the case of an argument
            # we drop the following messages
            for regex in TYPEREF_REGEXES['FIELD'] + GENERAL_SKIP:
                if re.fullmatch(regex, error_message):
                    return None
            # if not dropped, we try to extract the type
            for regex in TYPEREF_REGEXES['ARG']:
                match = re.fullmatch(regex, error_message)
                if match:
                    return match

        log().debug(f'Unknown error message for `typeref` with context `{context.value}`: \'{error_message}\'')
        return None

    match = __extract_matching_fields(error_message, context)

    if match:
        tk = match.group('typeref')

        name = tk.replace('!', '').replace('[', '').replace(']', '')
        kind = ''
        if name in GraphQLPrimitive:
            kind = 'SCALAR'
        elif context == FuzzingContext.FIELD:
            kind = 'OBJECT'
        elif context == FuzzingContext.ARGUMENT:
            kind = 'INPUT_OBJECT'
            name = name.rstrip('Input') + 'Input'  # Make sure `Input` is always once at the end
        else:
            log().debug(f'Unknown kind for `typeref`: \'{error_message}\'')
            return None

        is_list = bool('[' in tk and ']' in tk)
        non_null_item = bool(is_list and '!]' in tk)
        non_null = tk.endswith('!')

        return graphql.TypeRef(
            name=name,
            kind=kind,
            is_list=is_list,
            non_null_item=non_null_item,
            non_null=non_null,
        )

    return None


async def probe_typeref(
    documents: List[str],
    context: FuzzingContext,
) -> Optional[graphql.TypeRef]:
    """Sending a document to attain errors in order to deduce the type of fields."""

    async def __probation(document: str) -> Optional[graphql.TypeRef]:
        """Send a document to attempt discovering a typeref."""

        response = await client().post(document)
        for error in response.get('errors', []):
            if isinstance(error, str):
                continue

            if not isinstance(error['message'], dict):
                typeref = get_typeref(
                    error['message'],
                    context,
                )

            log().debug(f'get_typeref("{error["message"]}", "{context}") -> {typeref}')
            if typeref:
                return typeref

        return None

    tasks: List[asyncio.Task] = []
    for document in documents:
        tasks.append(asyncio.create_task(__probation(document)))

    typeref: Optional[graphql.TypeRef] = None
    results = await asyncio.gather(*tasks)
    for result in results:
        if result:
            typeref = result

    if not typeref and context != FuzzingContext.ARGUMENT:
        error_message = f'Unable to get TypeRef for {documents} in context {context}. '
        error_message += 'It is very likely that Field Suggestion is not fully enabled on this endpoint.'
        raise EndpointError(error_message)

    return typeref


async def probe_field_type(
    field: str,
    input_document: str,
) -> Optional[graphql.TypeRef]:
    """Wrapper function for sending the queries to deduce the field type."""

    documents = [
        input_document.replace('FUZZ', f'{field}'),
        input_document.replace('FUZZ', f'{field} {{ lol }}'),
    ]

    return await probe_typeref(documents, FuzzingContext.FIELD)


async def probe_arg_typeref(
    field: str,
    arg: str,
    input_document: str,
) -> Optional[graphql.TypeRef]:
    """Wrapper function to deduce the type of an arg."""

    documents = [
        input_document.replace('FUZZ', f'{field}({arg}: 42)'),
        input_document.replace('FUZZ', f'{field}({arg}: {{}})'),
        input_document.replace('FUZZ', f'{field}({arg[:-1]}: 42)'),
        input_document.replace('FUZZ', f'{field}({arg}: \"42\")'),
        input_document.replace('FUZZ', f'{field}({arg}: false)'),
    ]

    return await probe_typeref(documents, FuzzingContext.ARGUMENT)


async def probe_typename(input_document: str) -> str:

    document = input_document.replace('FUZZ', WRONG_FIELD_EXAMPLE)

    response = await client().post(document=document)
    if 'errors' not in response:
        log().warning(f"""Unable to get typename from {document}.
                      Field Suggestion might not be enabled on this endpoint. Using default "Query""")
        return 'Query'

    errors = response['errors']

    match = None
    for regex in WRONG_TYPENAME:
        for error in errors:
            match = re.fullmatch(regex, error['message'])
            if match:
                break
        if match:
            break

    if not match:
        log().debug(f"""Unkwon error in `probe_typename`: "{errors}" does not match any known regexes.
                    Field Suggestion might not be enabled on this endpoint. Using default "Query""")
        return 'Query'

    return (match.group('typename').replace('[', '').replace(']', '').replace('!', ''))


async def fetch_root_typenames() -> Dict[str, Optional[str]]:
    documents: Dict[str, str] = {
        'queryType': 'query { __typename }',
        'mutationType': 'mutation { __typename }',
        'subscriptionType': 'subscription { __typename }',
    }
    typenames: Dict[str, Optional[str]] = {
        'queryType': None,
        'mutationType': None,
        'subscriptionType': None,
    }

    for name, document in track(documents.items(), description='Fetching root typenames'):
        response = await client().post(document=document)

        data = response.get('data', {})
        if data:
            typenames[name] = data['__typename']

    log().debug(f'Root typenames are: {typenames}')
    return typenames


async def explore_field(
    field_name: str,
    input_document: str,
    wordlist: List[str],
    typename: str,
) -> Tuple[graphql.Field, List[graphql.InputValue]]:
    """Perform exploration on a field."""

    typeref = await probe_field_type(
        field_name,
        input_document,
    )

    args = []
    field = graphql.Field(field_name, typeref)
    if field.type.name in GraphQLPrimitive:
        log().debug(f'Skip probe_args() for "{field.name}" of type "{field.type.name}"')
    else:
        arg_names = await probe_args(
            field.name,
            wordlist,
            input_document,
        )

        log().debug(f'{typename}.{field_name}.args = {arg_names}')
        for arg_name in arg_names:
            arg_typeref = await probe_arg_typeref(field.name, arg_name, input_document)

            if not arg_typeref:
                log().debug(f'Skip argument {arg_name} because TypeRef equals {arg_typeref}')
                continue

            arg = graphql.InputValue(arg_name, arg_typeref)

            field.args.append(arg)
            args.append(arg)

    return field, args


async def clairvoyance(
    wordlist: List[str],
    input_document: str,
    input_schema: Dict[str, Any] = None,
) -> str:

    log().debug(f'input_document = {input_document}')

    if not input_schema:
        root_typenames = await fetch_root_typenames()
        schema = graphql.Schema(
            query_type=root_typenames['queryType'],
            mutation_type=root_typenames['mutationType'],
            subscription_type=root_typenames['subscriptionType'],
        )
    else:
        schema = graphql.Schema(schema=input_schema)

    typename = await probe_typename(input_document)
    log().debug(f'__typename = {typename}')

    valid_fields = await probe_valid_fields(
        wordlist,
        input_document,
    )
    log().debug(f'{typename}.fields = {valid_fields}')

    tasks: List[asyncio.Task] = []
    for field_name in valid_fields:
        tasks.append(asyncio.create_task(explore_field(
            field_name,
            input_document,
            wordlist,
            typename,
        )))

    for task in track(asyncio.as_completed(tasks), description=f'Processing {len(tasks)} responses', total=len(tasks)):
        field, args = await task
        for arg in args:
            schema.add_type(arg.type.name, 'INPUT_OBJECT')
        schema.types[typename].fields.append(field)
        schema.add_type(field.type.name, 'OBJECT')

    return repr(schema)
