import argparse
import logging
import os
from typing import List


def parse_args(args: List[str]) -> argparse.Namespace:
    default_values = {'document': 'query { FUZZ }'}

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v',
        '--verbose',
        default=0,
        action='count',
    )
    parser.add_argument(
        '-i',
        '--input-schema',
        metavar='<file>',
        type=argparse.FileType('r'),
        help='Input file containing JSON schema which will be supplemented with obtained information',
    )
    parser.add_argument(
        '-o',
        '--output',
        metavar='<file>',
        help='Output file containing JSON schema (default to stdout)',
    )
    parser.add_argument(
        '-d',
        '--document',
        metavar='<string>',
        default=default_values['document'],
        help=f'Start with this document (default {default_values["document"]})',
    )
    parser.add_argument(
        '-H',
        '--header',
        metavar='<header>',
        dest='headers',
        action='append',
        default=[],
    )
    parser.add_argument(
        '-c',
        '--concurrent-requests',
        metavar='<int>',
        type=int,
        default=None,
        help='Number of concurrent requests to send to the server',
    )
    parser.add_argument(
        '-w',
        '--wordlist',
        metavar='<file>',
        type=argparse.FileType('r'),
        help='This wordlist will be used for all brute force effots (fields, arguments and so on)',
    )
    parser.add_argument('url')

    return parser.parse_args(args)


def setup_logger(verbosity: int) -> None:
    fmt = os.getenv('LOG_FMT') or '%(asctime)s \t%(levelname)s\t| %(message)s'
    datefmt = os.getenv('LOG_DATEFMT') or '%Y-%m-%d %H:%M:%S'

    default_level = os.getenv('LOG_LEVEL') or 'INFO'
    level = 'DEBUG' if verbosity >= 1 else default_level.upper()

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
    )

    logging.getLogger('asyncio').setLevel(logging.ERROR)
