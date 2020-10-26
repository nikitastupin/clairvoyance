# clairvoyance

Some GraphQL APIs have disabled introspection. For example, [Apollo Server disables introspection automatically if the `NODE_ENV` environment variable is set to `production`](https://www.apollographql.com/docs/tutorial/schema/#explore-your-schema).

Clairvoyance allows us to get GraphQL API schema when introspection is disabled. It produces schema in JSON format suitable for other tools like [GraphQL Voyager](https://github.com/APIs-guru/graphql-voyager), [InQL](https://github.com/doyensec/inql) or [graphql-path-enum](https://gitlab.com/dee-see/graphql-path-enum).

## Installation

```
$ git clone https://github.com/nikitastupin/clairvoyance.git
$ cd clairvoyance
$ pip3 install -r requirements.txt
```

## Usage

```
$ python3 -m clairvoyance --help
```

```
$ python3 -m clairvoyance -vv -o /path/to/schema.json -w /path/to/wordlist.txt https://swapi-graphql.netlify.app/.netlify/functions/index
```

## Supported GraphQL libraries

* [apollo-server](https://github.com/apollographql/apollo-server)
* [graphql-js](https://github.com/graphql/graphql-js)

## Development

To run unit tests:

```
$ cd clairvoyance
$ python3 -m unittest tests/*_test.py
```

Documentation located at [Development](https://github.com/nikitastupin/clairvoyance/wiki/Development) wiki page.
