import json
import logging
import argparse
import re
from typing import Dict

from clairvoyance import graphql
from clairvoyance import oracle


def parse_args():
    parser = argparse.ArgumentParser()

    defaults = {"document": "query { FUZZ }"}

    parser.add_argument("-v", default=0, action="count")
    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="Disable server's certificate verification",
    )
    parser.add_argument(
        "-i",
        "--input",
        metavar="<file>",
        type=argparse.FileType("r"),
        help="Input file containing JSON schema which will be supplemented with obtained information",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="<file>",
        help="Output file containing JSON schema (default to stdout)",
    )
    parser.add_argument(
        "-d",
        "--document",
        metavar="<string>",
        default=defaults["document"],
        help=f"Start with this document (default {defaults['document']})",
    )
    parser.add_argument(
        "-H",
        "--header",
        metavar="<header>",
        dest="headers",
        action="append",
        default=[],
    )
    parser.add_argument(
        "-w",
        "--wordlist",
        metavar="<file>",
        required=True,
        type=argparse.FileType("r"),
        help="This wordlist will be used for all brute force effots (fields, arguments and so on)",
    )
    parser.add_argument(
        "-wv",
        "--validate",
        action="store_true",
        help="Validate the wordlist items match name Regex",
    )
    parser.add_argument("url")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    format = "[%(levelname)s][%(asctime)s %(filename)s:%(lineno)d]\t%(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    if args.v == 1:
        level = logging.INFO
    elif args.v > 1:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format=format, datefmt=datefmt)

    config = graphql.Config()
    config.url = args.url
    config.verify = not args.insecure
    for h in args.headers:
        key, value = h.split(": ", 1)
        config.headers[key] = value

    with args.wordlist as f:
        wordlist = [w.strip() for w in f.readlines() if w.strip()]
        # de-dupe the wordlist.
        wordlist = list(set(wordlist))

    # remove wordlist items that don't conform to graphQL regex github-issue #11
    if args.validate:
        wordlist_parsed = [w for w in wordlist if re.match(r'[_A-Za-z][_0-9A-Za-z]*', w)]
        logging.info(f'Removed {len(wordlist) - len(wordlist_parsed)} items from Wordlist, to conform to name regex. '
                     f'https://spec.graphql.org/June2018/#sec-Names')
        wordlist = wordlist_parsed

    input_schema = None
    if args.input:
        with args.input as f:
            input_schema = json.load(f)

    input_document = args.document if args.document else None

    ignore = {"Int", "Float", "String", "Boolean", "ID"}
    while True:
        schema = oracle.clairvoyance(
            wordlist, config, input_schema=input_schema, input_document=input_document
        )

        if args.output:
            with open(args.output, "w") as f:
                f.write(schema)
        else:
            print(schema)

        input_schema = json.loads(schema)
        s = graphql.Schema(schema=input_schema)
        next = s.get_type_without_fields(ignore)
        ignore.add(next)
        if next:
            input_document = s.convert_path_to_document(s.get_path_from_root(next))
        else:
            break
