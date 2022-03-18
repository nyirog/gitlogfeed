[![Makefile CI](https://github.com/nyirog/gitlogfeed/actions/workflows/makefile.yml/badge.svg)](https://github.com/nyirog/gitlogfeed/actions/workflows/makefile.yml)

# gitlogfeed

`gitlogfeed` creates an atom feed from your git log.

## Installation

```sh
pip install gitlogfeed
```

## When to use?

If your project has plain text documentation (reStrucutedText, markdown or
gherkin) you can setup an atom feed with `gitlogfeed` to notify your users
about the changes of your project:

```sh
gitlogfeed --repo /path/of/your/git/repo --base-url https://your.site --filter-path docs
```

The title and summary of the feed entry will be created from the commit
message. `gitlogfeed` creates an html file from the patch and the content of the
feed entry will link to the html file.

`gitlogfeed` uses quite high diff context limit (5000) so the feed entry will
contain the whole files not just the changes. You can change the context limit
with `--diff-limit` option:

```
gitlogfeed --base-url https://your.site --diff-context 10
```
