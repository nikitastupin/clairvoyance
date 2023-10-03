# Wordlists are from https://github.com/Escape-Technologies/graphql-wordlist

import os
from typing import List

import requests

field_wordlist_path = 'https://raw.githubusercontent.com/Escape-Technologies/graphql-wordlist/main/wordlists/10k/operationFieldWordlist-10k.txt'
argument_wordlist_path = 'https://raw.githubusercontent.com/Escape-Technologies/graphql-wordlist/main/wordlists/10k/argumentWordlist-10k.txt'

field_wordlist_local_path = os.path.expanduser('~/.clairvoyance/fieldWordlist.txt')
argument_wordlist_local_path = os.path.expanduser('~/.clairvoyance/argumentWordlist.txt')


def fetch_wordlist(path: str, local_path: str) -> List[str]:
    if os.path.exists(local_path):
        with open(local_path, 'r') as f:
            content = f.read()
            if content:
                return content.split('\n')

    req = requests.get(path)
    content = req.text
    if req.status_code != 200 or not content:
        raise RuntimeError(f'Error fetching wordlist from {path}: {content}')

    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'w') as f:
            f.write(content)
            print(f'Saved wordlist to {local_path}')
    except Exception as e:
        print(f'Error saving wordlist at {local_path}: {e}')

    return content.split('\n')


def load_field_wordlist() -> List[str]:
    return fetch_wordlist(field_wordlist_path, field_wordlist_local_path)


def load_argument_wordlist() -> List[str]:
    return fetch_wordlist(argument_wordlist_path, argument_wordlist_local_path)
