import argparse
import logging

from typing import List


def parse_args(args: List[str]) -> argparse.Namespace:
    default_values = {'document': 'query { FUZZ }'}

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v',
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
        '-w',
        '--wordlist',
        metavar='<file>',
        type=argparse.FileType('r'),
        help='This wordlist will be used for all brute force effots (fields, arguments and so on)',
    )
    parser.add_argument('url')

    return parser.parse_args(args)


def setup_logger(verbosity: int) -> None:
    format = '%(asctime)s \t%(levelname)s\t| %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'

    if verbosity == 1:
        level = logging.INFO
    elif verbosity > 1:
        level = logging.DEBUG
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format=format,
        datefmt=datefmt,
    )

    logging.getLogger('asyncio').setLevel(logging.ERROR)
