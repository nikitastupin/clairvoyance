# Contributing to Clairvoyance

**Clairvoyance** is an open-source project. We appreciate your contributions!

## Issues

If you have encountered a bug or want to propose an idea, you can open [a new issue on GitHub](https://github.com/nikitastupin/clairvoyance/issues/new).

### Best Practices

1. Check for existing issues before opening a new one. If you find a similar one, add more details to it instead of creating a duplicate.
2. Use relevant template and follow it.
3. Add relevant details, it helps us in triaging and further steps.

## Code Contribution

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

### Developer Environment Setup

To resolve dependencies, execute the following commands in your terminal:

```shell
python -m pip install pipx
pipx ensurepath
pipx install poetry
poetry config virtualenvs.in-project true
poetry install
```

We use [VSCodium](https://vscodium.com/#install) and VSCode IDEs with extension in the [`.vscode/extensions.json` file](../.vscode/extensions.json). Having said that, you might use other tools as long as the outcome follows the guidelines of this project.

### Git Branches

Always use dedicated git branches for fixes or features instead of working directly on the main branch.

### Further Information

Please refer to our [Development guide](https://github.com/nikitastupin/clairvoyance/wiki/Development) for guidance on testing, code style and more.