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
### From Python interpreter
```
$ python3 -m clairvoyance --help
```

```
$ python3 -m clairvoyance -vv -o /path/to/schema.json -w /path/to/wordlist.txt https://swapi-graphql.netlify.app/.netlify/functions/index
```
### From Docker Image
```
$ docker run --rm nikitastupin/clairvoyance --help
```
```
# Assuming the wordlist.txt file is found in $PWD
$ docker run --rm -v $(pwd):/tmp/ nikitastupin/clairvoyance -vv -o /tmp/schema.json -w /tmp/wordlist.txt https://swapi-graphql.netlify.app/.netlify/functions/index
```

You can refer to 2nd half of [GraphQL APIs from bug hunter's perspective by Nikita Stupin](https://youtu.be/nPB8o0cSnvM) talk for detailed description.

### Which wordlist should I use?

There are at least two approaches:

- Use general English words (e.g. [google-10000-english](https://github.com/first20hours/google-10000-english)).
- Create target specific wordlist by extracting all valid GraphQL names from application HTTP traffic, from mobile application static files, etc. Regex for GraphQL name is [`[_A-Za-z][_0-9A-Za-z]*`](http://spec.graphql.org/June2018/#sec-Names).

## Support

In case of question or issue with clairvoyance please refer to [wiki](https://github.com/nikitastupin/clairvoyance/wiki) or [issues](https://github.com/nikitastupin/clairvoyance/issues). If this doesn't solve your problem feel free to open a [new issue](https://github.com/nikitastupin/clairvoyance/issues/new).

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. For more information about tests, internal project structure and so on refer to [Development](https://github.com/nikitastupin/clairvoyance/wiki/Development) wiki page.
