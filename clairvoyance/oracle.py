# pylint: disable=anomalous-backslash-in-string, line-too-long

import asyncio
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from clairvoyance import graphql
from clairvoyance.entities import GraphQLPrimitive
from clairvoyance.entities.context import client, config, log
from clairvoyance.entities.oracle import FuzzingContext


# pylint: disable=too-many-branches
def get_valid_fields(error_message: str) -> Set[str]:
    """Fetching valid fields using regex heuristics."""

    valid_fields: Set[str] = set()

    multiple_suggestion_regex = 'Cannot query field [\'"]([_A-Za-z][_0-9A-Za-z]*)[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean (?P<multi>([\'"][_A-Za-z][_0-9A-Za-z]*[\'"], )+)(or [\'"](?P<last>[_A-Za-z][_0-9A-Za-z]*)[\'"])?\?'
    or_suggestion_regex = 'Cannot query field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean [\'"](?P<one>[_A-Za-z][_0-9A-Za-z]*)[\'"] or [\'"](?P<two>[_A-Za-z][_0-9A-Za-z]*)[\'"]\?'
    single_suggestion_regex = 'Cannot query field [\'"]([_A-Za-z][_0-9A-Za-z]*)[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"]. Did you mean [\'"](?P<field>[_A-Za-z][_0-9A-Za-z]*)[\'"]\?'
    invalid_field_regex = ('Cannot query field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] on type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"].')
    # TODO: this regex here more than one time, make it shared?
    valid_field_regex = [
        'Field [\'"](?P<field>[_A-Za-z][_0-9A-Za-z]*)[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a selection of subfields. Did you mean [\'"][_A-Za-z][_0-9A-Za-z\.]*( \{ \.\.\. \})?[\'"]\?',
        'Field [\'"](?P<field>[_A-Za-z][_0-9A-Za-z]*)[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a sub selection\.'
    ]

    no_field_regexs = [
        'Field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] must not have a selection since type [\'"][0-9a-zA-Z\[\]!]+[\'"] has no subfields.',
        'Field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"] is required(, but it was not provided| but not provided)?\.',
    ]

    for regex in no_field_regexs:
        if re.fullmatch(regex, error_message):
            return valid_fields

    if re.fullmatch(multiple_suggestion_regex, error_message):
        match = re.fullmatch(multiple_suggestion_regex, error_message)
        if match:
            for m in match.group('multi').split(', '):
                if m:
                    valid_fields.add(m.strip('"').strip('\''))

            if match.group('last'):
                valid_fields.add(match.group('last'))

    elif re.fullmatch(or_suggestion_regex, error_message):
        match = re.fullmatch(or_suggestion_regex, error_message)
        if match:
            valid_fields.add(match.group('one'))
            valid_fields.add(match.group('two'))

    elif re.fullmatch(single_suggestion_regex, error_message):
        match = re.fullmatch(single_suggestion_regex, error_message)
        if match:
            valid_fields.add(match.group('field'))

    elif re.fullmatch(invalid_field_regex, error_message):
        pass

    elif re.fullmatch(valid_field_regex[0], error_message):
        match = re.fullmatch(valid_field_regex[0], error_message)
        if match:
            valid_fields.add(match.group('field'))

    elif re.fullmatch(valid_field_regex[1], error_message):
        match = re.fullmatch(valid_field_regex[1], error_message)
        if match:
            valid_fields.add(match.group('field'))

    else:
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
                'Cannot query field [\'"](?P<invalid_field>[_A-Za-z][_0-9A-Za-z]*)[\'"]',
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
    results = await asyncio.gather(*tasks)
    for result in results:
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
            'Unknown argument [\'"](?P<invalid_arg>[_A-Za-z][_0-9A-Za-z]*)[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"]',
            error_message,
        )
        if match:
            valid_args.discard(match.group('invalid_arg'))

        duplicate_arg_regex = 'There can be only one argument named [\"](?P<arg>[_0-9a-zA-Z\.\[\]!]*)[\"]\.?'
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

    skip_regexes = [
        'Unknown argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] of type [\'"][_A-Za-z][_0-9A-Za-z]*[\'"].',
        'Field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] of type [\'"][_A-Za-z\[\]!][a-zA-Z\[\]!]*[\'"] must have a selection of subfields. Did you mean [\'"][_A-Za-z][_0-9A-Za-z]*( \{ \.\.\. \})?[\'"]\?',
        'Field [\'"][_A-Za-z][_0-9A-Za-z\.]*[\'"] argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"] is required(, but it was not provided| but not provided)?\.',
        'Unknown argument [\'"][_A-Za-z][_0-9A-Za-z]*[\'"] on field [\'"][_A-Za-z][_0-9A-Za-z.]*[\'"]\.',
    ]
    single_suggestion_regex = [
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"][_0-9a-zA-Z\[\]!]*[\'"]. Did you mean [\'"](?P<arg>[_0-9a-zA-Z\.\[\]!]*)[\'"]\?',
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_.0-9a-zA-Z\[\]!]*[\'"]. Did you mean [\'\"](?P<arg>[_0-9a-zA-Z\[\]!]*)[\'\"]\?'
    ]
    double_suggestion_regexes = [
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_.0-9a-zA-Z\[\]!]*[\'"]( of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"])?. Did you mean [\'"](?P<first>[_0-9a-zA-Z\.\[\]!]*)[\'"] or [\'"](?P<second>[_0-9a-zA-Z\.\[\]!]*)[\'"]\?'
    ]

    for regex in skip_regexes:
        if re.fullmatch(regex, error_message):
            return set()

    for regex in single_suggestion_regex:
        if re.fullmatch(regex, error_message):
            match = re.fullmatch(regex, error_message)
            if match:
                valid_args.add(match.group('arg'))

    for regex in double_suggestion_regexes:
        match = re.fullmatch(regex, error_message)
        if match:
            valid_args.add(match.group('first'))
            valid_args.add(match.group('second'))

    if not valid_args:
        log().debug(f'Unknown error message for `valid_args`: \'{error_message}\'')

    return valid_args


def get_typeref(
    error_message: str,
    context: FuzzingContext,
) -> Optional[graphql.TypeRef]:
    """Using predefined regex deduce the type of a field."""

    field_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a selection of subfields. Did you mean [\'"][_0-9a-zA-Z\.\[\]!]*( \{ \.\.\. \})?[\'"]\?',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] must not have a selection since type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] has no subfields.',
        'Cannot query field [\'"][_0-9a-zA-Z\[\]!]*[\'"] on type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"].',
        'Cannot query field [\'"][_0-9a-zA-Z\[\]!]*[\'"] on type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"]. Did you mean [\'"][_0-9a-zA-Z\.\[\]!]*( \{ \.\.\. \})?[\'"]\?',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must not have a sub selection\.',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must have a sub selection\.'
    ]
    arg_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] is required(, but it was not provided| but not provided)?\.',
        'Expected type (?P<typeref>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*), found .+\.',
    ]
    arg_skip_regexes = [
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"][_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*[\'"] must have a selection of subfields\. Did you mean [\'"][_0-9a-zA-Z\.\[\]!]*( \{ \.\.\. \})?[\'"]\?'
        'Unknown argument [\'"][_0-9a-zA-Z\[\]!]*[\'"] on field [\'"][_0-9a-zA-Z\.\[\]!]*[\'"]. Did you mean [\'"](?P<typeref>[_0-9a-zA-Z\[\]!]*)[\'"]\?',
    ]

    match = None
    if context == FuzzingContext.FIELD:
        for regex in field_regexes:
            if re.fullmatch(regex, error_message):
                match = re.fullmatch(regex, error_message)
                break
    elif context == FuzzingContext.ARGUMENT:
        for regex in arg_skip_regexes:
            if re.fullmatch(regex, error_message):
                return None

        for regex in arg_regexes:
            if re.fullmatch(regex, error_message):
                match = re.fullmatch(regex, error_message)
                break

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

    log().debug(f'Unknown error message for `typeref`: \'{error_message}\'')
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
        try:
            raise Exception(f'Unable to get TypeRef for {documents} in context {context}')
        except Exception as e:
            raise Exception(e) from e

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
    wrong_field = 'imwrongfield'
    document = input_document.replace('FUZZ', wrong_field)

    response = await client().post(document=document)
    if 'errors' not in response:
        raise Exception(f'Unable to get typename from {document}')

    errors = response['errors']

    wrong_field_regexes = [
        f'Cannot query field [\'"]{wrong_field}[\'"] on type [\'"](?P<typename>[_0-9a-zA-Z\[\]!]*)[\'"].',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] must not have a selection since type [\'"](?P<typename>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] has no subfields.',
        'Field [\'"][_0-9a-zA-Z\[\]!]*[\'"] of type [\'"](?P<typename>[_A-Za-z\[\]!][_0-9a-zA-Z\[\]!]*)[\'"] must not have a sub selection.'
    ]

    match = None
    for regex in wrong_field_regexes:
        for error in errors:
            match = re.fullmatch(regex, error['message'])
            if match:
                break
        if match:
            break

    if not match:
        raise Exception(f'Expected "{errors}" to match any of "{wrong_field_regexes}".')

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

    for name, document in documents.items():
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

    results = await asyncio.gather(*tasks)
    for (field, args) in results:
        for arg in args:
            schema.add_type(arg.type.name, 'INPUT_OBJECT')
        schema.types[typename].fields.append(field)
        schema.add_type(field.type.name, 'OBJECT')

    return repr(schema)
