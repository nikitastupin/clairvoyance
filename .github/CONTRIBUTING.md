# Contributing to Clairvoyance

**Clairvoyance** is an open-source project. We appreciate your contributions!

## Issues

If you have encountered an bug or want to propose your idea, you can open a new issue on the github.

### Best practices
1. Check for existing issues before opening a new one. If you find a similar one, add more details to it instead of creating a duplicate.
2. Use relevant template and follow it.
3. Add relevant details, it helps us in triaging and further steps.

## Code contribution
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

### Developer Environment Setup
We recommend to use [VSCodium](https://vscodium.com/#install)/VSCode IDE with recommended extensions (automatically suggested).

To resolve dependencies, execute the following commands in your terminal:
```shell
python -m pip install pipx
pipx ensurepath
pipx install poetry
poetry install
```

### Git Branches
Always use dedicated git branches for fixes or features instead of working directly on the master branch.

### Further information
Please refer to our [Development guide](https://github.com/nikitastupin/clairvoyance/wiki/Development) for guidance on testing, code style and more.