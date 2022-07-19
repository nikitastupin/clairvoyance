import sys
import json
import asyncio
import logging

from typing import Dict, List, Optional

from clairvoyance import graphql, oracle
from clairvoyance.entities import GraphQLPrimitive
from clairvoyance.config import Config
from clairvoyance.utils import parse_args, setup_logger


async def blind_introspection(
    url: str,
    logger: logging.Logger,
    wordlist_path: str,
    input_schema_path: Optional[str] = None,
    input_document: Optional[str] = None,
    output_path: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    config = Config(
        url,
        headers=headers,
        logger=logger,
    )

    with open(wordlist_path, 'r', encoding='utf-8') as f:
        wordlist = [w.strip() for w in f.readlines() if w.strip()]

    input_schema = None
    if input_schema_path:
        with open(input_schema_path, 'r', encoding='utf-8') as f:
            input_schema = json.load(f)

    input_document = input_document or 'query { FUZZ }'
    ignore = set(GraphQLPrimitive.__members__.keys())
    while True:
        schema = await oracle.clairvoyance(
            wordlist,
            input_document=input_document,
            config=config,
            input_schema=input_schema,
        )

        if output_path:
            with open(output_path, 'w') as f:
                f.write(schema)

        input_schema = json.loads(schema)
        s = graphql.Schema(schema=input_schema)

        _next = s.get_type_without_fields(ignore)
        ignore.add(_next)

        if _next:
            input_document = s.convert_path_to_document(s.get_path_from_root(_next))
        else:
            break

    return schema


def cli(argv: Optional[List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    setup_logger(args.v)

    headers = {}
    for h in args.headers:
        key, value = h.split(': ', 1)
        headers[key] = value

    asyncio.run(
        blind_introspection(
            args.url,
            logger=logging.getLogger('clairvoyance'),
            wordlist_path=args.wordlist,
            input_schema_path=args.input_schema,
            input_document=args.document,
            output_path=args.output,
            headers=headers,
        )
    )


if __name__ == '__main__':
    cli()
