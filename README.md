# 7taps-analytics
Importing xAPI data from 7taps and doing magical stuff with it

## Development

This project uses [pre-commit](https://pre-commit.com/) to enforce formatting with [Black](https://black.readthedocs.io/en/stable/) and import sorting with [isort](https://pycqa.github.io/isort/).

Install the hook:

```
pip install pre-commit
pre-commit install
```

Run the configured checks on any files you modify before committing:

```
pre-commit run --files <changed files>
```

Alternatively, rely on the Git hook by simply running `git commit` after installing pre-commit.
