# clairvoyance

Some GraphQL APIs have disabled introspection. For example, [Apollo Server disables introspection automatically if the `NODE_ENV` environment variable is set to `production`](https://www.apollographql.com/docs/tutorial/schema/#explore-your-schema).

Clairvoyance allows us to get GraphQL API schema when introspection is disabled. It produces schema in JSON format suitable for other tools like [GraphQL Voyager](https://github.com/APIs-guru/graphql-voyager), [InQL](https://github.com/doyensec/inql) or [graphql-path-enum](https://gitlab.com/dee-see/graphql-path-enum).

## Acknowledgments

Thanks to [Swan](https://github.com/c3b5aw) from [Escape-Technologies](https://github.com/Escape-Technologies) for 2.0 version.

## Usage

### From PyPI

```bash
pip install clairvoyance
```

### From Python interpreter

```bash
git clone https://github.com/nikitastupin/clairvoyance.git
cd clairvoyance
pip install poetry
poetry config virtualenvs.in-project true
poetry install --no-dev
source .venv/bin/activate
```

```bash
python3 -m clairvoyance --help
```

```bash
python3 -m clairvoyance -o /path/to/schema.json https://swapi-graphql.netlify.app/.netlify/functions/index
```

### From Docker Image

```bash
docker run --rm nikitastupin/clairvoyance --help
```

```bash
# Assuming the wordlist.txt file is found in $PWD
docker run --rm -v $(pwd):/tmp/ nikitastupin/clairvoyance -vv -o /tmp/schema.json -w /tmp/wordlist.txt https://swapi-graphql.netlify.app/.netlify/functions/index
```

You can refer to 2nd half of [GraphQL APIs from bug hunter's perspective by Nikita Stupin](https://youtu.be/nPB8o0cSnvM) talk for detailed description.

### From BlackArch Linux

```bash
pacman -S clairvoyance
```

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

In case of question or issue with clairvoyance please refer to [wiki](https://github.com/nikitastupin/clairvoyance/wiki) or [issues](https://github.com/nikitastupin/clairvoyance/issues). If this doesn't solve your problem feel free to open a [new issue](https://github.com/nikitastupin/clairvoyance/issues/new).

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. For more information about tests, internal project structure and so on refer to [Development](https://github.com/nikitastupin/clairvoyance/wiki/Development) wiki page.
