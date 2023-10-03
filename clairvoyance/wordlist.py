# Wordlists are from https://github.com/Escape-Technologies/graphql-wordlist

import os
from typing import List
import requests


field_wordlist_path = "https://raw.githubusercontent.com/Escape-Technologies/graphql-wordlist/main/wordlists/10k/operationFieldWordlist-10k.txt"
argument_wordlist_path = "https://raw.githubusercontent.com/Escape-Technologies/graphql-wordlist/main/wordlists/10k/argumentWordlist-10k.txt"

field_wordlist_local_path = "~/.clairvoyance/fieldWordlist.txt"
argument_wordlist_local_path = "~/.clairvoyance/argumentWordlist.txt"


def fetch_wordlist(path: str, local_path: str) -> List[str]:
  if os.path.exists(local_path):
    with open(local_path, "r") as f:
      content = f.read()
      if content:
        return content.split("\n")
      
  req = requests.get(path)
  content = req.text
  if req.status_code != 200 or not content:
    raise Exception(f'Error fetching wordlist from {path}: {content}')
  
  try:
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "w") as f:
      f.write(content)
  except Exception as e:
    print(f'Error saving wordlist at {local_path}: {e}')
  
  return content.split("\n")
  
load_field_wordlist = lambda: fetch_wordlist(field_wordlist_path, field_wordlist_local_path)
load_argument_wordlist = lambda: fetch_wordlist(argument_wordlist_path, argument_wordlist_local_path)