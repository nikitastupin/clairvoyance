import json
import logging
import argparse
from typing import Dict

from clairvoyance import graphql
from clairvoyance import oracle


def parse_args():
    parser = argparse.ArgumentParser()

    defaults = {"document": "query { FUZZ }"}

    parser.add_argument("-v", default=0, action="count")
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
    for h in args.headers:
        key, value = h.split(": ", 1)
        config.headers[key] = value

    with args.wordlist as f:
        wordlist = [w.strip() for w in f.readlines() if w.strip()]

    input_schema = None
    if args.input:
        with args.input as f:
            input_schema = json.load(f)

    input_document = args.document if args.document else None

    mode = "OBJECT"  # OBJECT or INPUT_OBJECT
    ignore = {"Int", "Float", "String", "Boolean", "ID"}
    while True:
        if mode == "OBJECT":
            schema = oracle.clairvoyance(
                wordlist,
                config,
                input_schema=input_schema,
                input_document=input_document,
            )
        elif mode == "INPUT_OBJECT":
            schema = oracle.clairvoyance_io(
                wordlist,
                config,
                input_schema=input_schema,
                input_document=input_document,
            )
        else:
            raise Exception(f"Unknown mode {mode}")

        if args.output:
            with open(args.output, "w") as f:
                f.write(schema)
        else:
            print(schema)

        input_schema = json.loads(schema)
        s = graphql.Schema(schema=input_schema)
        next = s.get_type_without_fields(ignore)

        if next:
            if next.kind == "OBJECT":
                mode = "OBJECT"
            elif next.kind == "INPUT_OBJECT":
                mode = "INPUT_OBJECT"
            else:
                raise Exception(f"Don't have mode for {next.kind} kind")

            next = next.name
            ignore.add(next)

            if mode == "OBJECT":
                input_document = s.convert_path_to_document(s.get_path_from_root(next))
            elif mode == "INPUT_OBJECT":
                fpath, apath = s.get_path_from_root_ex(next)
                input_document = s.convert_path_to_document_ex(fpath, apath)
            else:
                raise Exception(f"Unknown mode {mode}")
        else:
            break
