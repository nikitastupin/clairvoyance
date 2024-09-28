# Troubleshooting Guide

At first, determine the case: whether the Clairvoyance doesn't work at all, with particular website or stops working during its executing. After this, refer to appropriate section for guidance.

## The Clairvoyance doesn't work at all
 - Installation: make sure that there were no errors during installation and that you are using correct version of dependencies.
 - Internet: make sure that you have a stable connection and that the Clairvoyance has rights to access your target.
 - Usage: refer to the [README](README.md) for usage instructions.

## The Clairvoyance doesn't work with particular website
 - Scope: make sure that there is no general issue: try `clairvoyance https://rickandmortyapi.com/graphql -o schema.json` or known working target.
 - URI: check endpoint URI validity (it might be a typo, an erroneous copy or other issue).
 - Authorization issue: ensure usage of correct headers, cookies and other authorization pieces.
 - WAF: ensure that the program imitates browser/web client at sufficient level, e.g. check that user agent matches modern browser/app-specific web client.

## The Clairvoyance worked, but stopped working
 - Does the program work when you restart it? If the answer is yes, check "Rate Limits", if not, then check "Server-related issue"
 - Rate Limits: server might rate limit requests from the same IP/user. Lower amount of threads or try to run the program in a slow mode
 - Server-related issue: server might be temporary unavailable, check the endpoint manually using browser or other previously used tools. Alternatively, your IP/user might have been banned.
