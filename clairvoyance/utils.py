import argparse
import logging
from os import getenv
from typing import Any, Iterable, List

from rich.progress import track as rich_track


class Tracker:
    __enabled = False

    @classmethod
    def enable(cls) -> None:
        cls.__enabled = True

    @classmethod
    def disable(cls) -> None:
        cls.__enabled = False

    @classmethod
    def track(cls, it: Iterable, description: str, **kwargs) -> Iterable:  # type: ignore[no-untyped-def]
        if not cls.__enabled:
            return it
        description = f"{description: <32}"
        return rich_track(it, description, **kwargs)


track = Tracker.track


def default(arg: Any, default_value: Any) -> Any:
    return arg if arg is not None else default_value


def set_slow_config(args: argparse.Namespace) -> None:
    args.concurrent_requests = default(args.concurrent_requests, 1)
    args.max_retries = default(args.max_retries, 50)
    args.backoff = default(args.backoff, 2)


def parse_args(args: List[str]) -> argparse.Namespace:
    default_values = {"document": "query { FUZZ }"}

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v",
        "--verbose",
        default=0,
        action="count",
    )
    parser.add_argument(
        "-i",
        "--input-schema",
        metavar="<file>",
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
        default=default_values["document"],
        help=f'Start with this document (default {default_values["document"]})',
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
        "-c",
        "--concurrent-requests",
        metavar="<int>",
        type=int,
        default=None,
        help="Number of concurrent requests to send to the server",
    )
    parser.add_argument(
        "-w",
        "--wordlist",
        metavar="<file>",
        type=argparse.FileType("r"),
        help="This wordlist will be used for all brute force effots (fields, arguments and so on)",
    )
    parser.add_argument(
        "-wv",
        "--validate",
        action="store_true",
        help="Validate the wordlist items match name Regex",
    )
    parser.add_argument(
        "-x",
        "--proxy",
        metavar="<string>",
        type=str,
        help="Define a proxy to use for all requests. For more info, read https://docs.aiohttp.org/en/stable/client_advanced.html?highlight=proxy",
    )
    parser.add_argument(
        "-k",
        "--no-ssl",
        action="store_true",
        help="Disable SSL verification",
    )
    parser.add_argument(
        "-m",
        "--max-retries",
        metavar="<int>",
        type=int,
        help="How many retries should be made when a request fails",
    )
    parser.add_argument(
        "-b",
        "--backoff",
        metavar="<int>",
        type=int,
        help="Exponential backoff factor. Delay will be calculated as: `0.5 * backoff**retries` seconds.",
    )
    parser.add_argument(
        "-p",
        "--profile",
        choices=["slow", "fast"],
        default="fast",
        help="Select a speed profile. fast mod will set lot of workers to provide you quick result"
        + " but if the server as some rate limit you may want to use slow mod.",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Enable progress bar",
    )
    parser.add_argument("url")

    parsed_args = parser.parse_args(args)
    if parsed_args.profile == "slow":
        set_slow_config(parsed_args)

    if parsed_args.progress:
        Tracker.enable()

    return parsed_args


def setup_logger(verbosity: int) -> None:
    fmt = getenv("LOG_FMT") or "%(asctime)s \t%(levelname)s\t| %(message)s"
    datefmt = getenv("LOG_DATEFMT") or "%Y-%m-%d %H:%M:%S"

    default_level = getenv("LOG_LEVEL") or "INFO"
    level = "DEBUG" if verbosity >= 1 else default_level.upper()

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
    )

    logging.getLogger("asyncio").setLevel(logging.ERROR)
