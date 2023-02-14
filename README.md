# clairvoyance

Some GraphQL APIs have disabled introspection. For example, [Apollo Server disables introspection automatically if the `NODE_ENV` environment variable is set to `production`](https://www.apollographql.com/docs/tutorial/schema/#explore-your-schema).

Clairvoyance allows us to get GraphQL API schema when introspection is disabled. It produces schema in JSON format suitable for other tools like [GraphQL Voyager](https://github.com/APIs-guru/graphql-voyager), [InQL](https://github.com/doyensec/inql) or [graphql-path-enum](https://gitlab.com/dee-see/graphql-path-enum).

## Acknowledgments

Thanks to [Swan](https://github.com/c3b5aw) from [Escape-Technologies](https://github.com/Escape-Technologies) for 2.0 version.

## Usage

```bash
clairvoyance -h
usage: clairvoyance [-h] [-v] [-i <file>] [-o <file>] [-d <string>] [-H <header>] [-c <int>] [-w <file>] [-x <string>] [-m <int>] [-b <int>] [-p {slow,fast}] url

positional arguments:
  url

options:
  -h, --help            show this help message and exit
  -v, --verbose
  -i <file>, --input-schema <file>
                        Input file containing JSON schema which will be supplemented with obtained information
  -o <file>, --output <file>
                        Output file containing JSON schema (default to stdout)
  -d <string>, --document <string>
                        Start with this document (default query { FUZZ })
  -H <header>, --header <header>
  -c <int>, --concurrent-requests <int>
                        Number of concurrent requests to send to the server
  -w <file>, --wordlist <file>
                        This wordlist will be used for all brute force effots (fields, arguments and so on)
  -x <string>, --proxy <string>
                        Define a proxy to use for all requests. For more info, read https://docs.aiohttp.org/en/stable/client_advanced.html?highlight=proxy
  -m <int>, --max-retries <int>
                        How many retries should be made when a request fails
  -b <int>, --backoff <int>
                        Exponential backoff factor. Delay will be calculated as: `0.5 * backoff**retries` seconds.
  -p {slow,fast}, --profile {slow,fast}
                        Select a speed profile. fast mod will set lot of workers to provide you quick result but if the server as some rate limit you may wnat to use slow mod.
```

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

### From BlackArch Linux

> NOTE: this distribution is supported by a third-party (i.e. not by the mainainters of clairvoyance)

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

> Due to time constraints @nikitastupin won't be able to answer all the issues for some time but he'll do his best to review & merge PRs

In case of question or issue with clairvoyance please refer to [wiki](https://github.com/nikitastupin/clairvoyance/wiki) or [issues](https://github.com/nikitastupin/clairvoyance/issues). If this doesn't solve your problem feel free to open a [new issue](https://github.com/nikitastupin/clairvoyance/issues/new).

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. For more information about tests, internal project structure and so on refer to [Development](https://github.com/nikitastupin/clairvoyance/wiki/Development) wiki page.

## Documentation

- You may find more details on how the tool works in the second half of the [GraphQL APIs from bug hunter's perspective by Nikita Stupin](https://youtu.be/nPB8o0cSnvM) talk.
