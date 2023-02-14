import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Optional

from clairvoyance import graphql, oracle
from clairvoyance.client import Client
from clairvoyance.config import Config
from clairvoyance.entities import GraphQLPrimitive
from clairvoyance.entities.context import client, logger_ctx
from clairvoyance.utils import parse_args, setup_logger


def setup_context(
    url: str,
    logger: logging.Logger,
    headers: Optional[Dict[str, str]] = None,
    concurrent_requests: Optional[int] = None,
    proxy: Optional[str] = None,
    max_retries: Optional[int] = None,
    backoff: Optional[int] = None,
) -> None:
    """Initialize objects and freeze them into the context."""

    Config()
    Client(
        url,
        headers=headers,
        concurrent_requests=concurrent_requests,
        proxy=proxy,
        max_retries=max_retries,
        backoff=backoff,
    )
    logger_ctx.set(logger)


def load_default_wordlist() -> List[str]:
    wl = os.path.join(os.path.dirname(__file__), 'wordlist.txt')
    with open(wl, 'r', encoding='utf-8') as f:
        return [w.strip() for w in f.readlines() if w.strip()]


async def blind_introspection(
    url: str,
    logger: logging.Logger,
    wordlist: List[str],
    concurrent_requests: Optional[int] = None,
    headers: Optional[Dict[str, str]] = None,
    input_document: Optional[str] = None,
    input_schema_path: Optional[str] = None,
    output_path: Optional[str] = None,
    proxy: Optional[str] = None,
    max_retries: Optional[int] = None,
    backoff: Optional[int] = None,
) -> str:
    wordlist = wordlist or load_default_wordlist()
    assert wordlist, 'No wordlist provided'

    setup_context(
        url,
        logger=logger,
        headers=headers,
        concurrent_requests=concurrent_requests,
        proxy=proxy,
        max_retries=max_retries,
        backoff=backoff,
    )

    logger.info(f'Starting blind introspection on {url}...')

    input_schema = None
    if input_schema_path:
        with open(input_schema_path, 'r', encoding='utf-8') as f:
            input_schema = json.load(f)

    input_document = input_document or 'query { FUZZ }'
    ignored = set(e.value for e in GraphQLPrimitive)
    while True:
        schema = await oracle.clairvoyance(
            wordlist,
            input_document=input_document,
            input_schema=input_schema,
        )

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(schema)

        input_schema = json.loads(schema)
        s = graphql.Schema(schema=input_schema)

        _next = s.get_type_without_fields(ignored)
        ignored.add(_next)

        if _next:
            input_document = s.convert_path_to_document(s.get_path_from_root(_next))
        else:
            break

    logger.info('Blind introspection complete.')
    await client().close()
    return schema


def cli(argv: Optional[List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    setup_logger(args.verbose)

    headers = {}
    for h in args.headers:
        key, value = h.split(': ', 1)
        headers[key] = value

    wordlist = []
    if args.wordlist:
        wordlist = [w.strip() for w in args.wordlist.readlines() if w.strip()]

    asyncio.run(
        blind_introspection(
            args.url,
            logger=logging.getLogger('clairvoyance'),
            concurrent_requests=args.concurrent_requests,
            headers=headers,
            input_document=args.document,
            input_schema_path=args.input_schema,
            output_path=args.output,
            wordlist=wordlist,
            proxy=args.proxy,
            max_retries=args.max_retries,
            backoff=args.backoff,
        )
    )
