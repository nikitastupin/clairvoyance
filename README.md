# Clairvoyance

Obtain GraphQL API Schema even if the introspection is disabled.

[![PyPI](https://img.shields.io/pypi/v/clairvoyance)](https://pypi.org/project/clairvoyance/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/clairvoyance)](https://pypi.org/project/clairvoyance/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/clairvoyance)](https://pypi.org/project/clairvoyance/)
[![GitHub](https://img.shields.io/github/license/nikitastupin/clairvoyance)](https://github.com/nikitastupin/clairvoyance/blob/main/LICENSE)

## Introduction

Some GraphQL APIs have disabled introspection. For example, [Apollo Server disables introspection automatically if the `NODE_ENV` environment variable is set to `production`](https://www.apollographql.com/docs/tutorial/schema/#explore-your-schema).

Clairvoyance allows us to get GraphQL API schema when introspection is disabled. It produces schema in JSON format suitable for other tools like [GraphQL Voyager](https://github.com/APIs-guru/graphql-voyager), [InQL](https://github.com/doyensec/inql) or [graphql-path-enum](https://gitlab.com/dee-see/graphql-path-enum).

## Contributors

Thanks to the [contributers](#contributors) for their work.

- [nikitastupin](https://github.com/nikitastupin)
- [Escape](https://escape.tech) team :
  - [iCarossio](https://github.com/iCarossio)
  - [Swan](https://github.com/c3b5aw)
  - [QuentinN42](https://github.com/QuentinN42)
  - [Nohehf](https://github.com/Nohehf)
- [i-tsaturov](https://github.com/i-tsaturov)
- [EONRaider](https://github.com/EONRaider)
- [noraj](https://github.com/noraj)
- [belane](https://github.com/belane)

## Getting started

```bash
pip install clairvoyance
clairvoyance https://rickandmortyapi.com/graphql -o schema.json
# should take about 2 minute
```

## Docker Image

```bash
docker run --rm nikitastupin/clairvoyance --help
```

## Advanced Usage

### Which wordlist should I use?

There are at least two approaches:

- Use general English words (e.g. [google-10000-english](https://github.com/first20hours/google-10000-english)).
- Create target specific wordlist by extracting all valid GraphQL names from application HTTP traffic, from mobile application static files, etc. Regex for GraphQL name is [`[_A-Za-z][_0-9A-Za-z]*`](http://spec.graphql.org/June2018/#sec-Names).

### Environment Variables

```bash
LOG_FMT=`%(asctime)s \t%(levelname)s\t| %(message)s` # A string format for logging.
LOG_DATEFMT=`%Y-%m-%d %H:%M:%S` # A string format for logging date.
LOG_LEVEL=`INFO` # A string level for logging.
```

## Support

> Due to time constraints @nikitastupin won't be able to answer all the issues for some time but he'll do his best to review & merge PRs

In case of question or issue with clairvoyance please refer to [wiki](https://github.com/nikitastupin/clairvoyance/wiki) or [issues](https://github.com/nikitastupin/clairvoyance/issues). If this doesn't solve your problem feel free to open a [new issue](https://github.com/nikitastupin/clairvoyance/issues/new).

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. For more information about tests, internal project structure and so on refer to [Development](https://github.com/nikitastupin/clairvoyance/wiki/Development) wiki page.

## Documentation

- You may find more details on how the tool works in the second half of the [GraphQL APIs from bug hunter's perspective by Nikita Stupin](https://youtu.be/nPB8o0cSnvM) talk.
