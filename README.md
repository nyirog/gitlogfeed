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
gitlogfeed --repo /path/of/your/git/repo --filter-path docs https://your.site
```

The title and summary of the feed entry will be created from the commit
message. `gitlogfeed` creates html file from every patch and the content of the
feed entry will link to the html file.

The scope of the generated diff can be set with the `--diff-context` option.
You can show the entire file with a big enough limit:

```
gitlogfeed --diff-context 5000 https://your.site
```

`gitlogfeed` can read the git log from stdin:

```
git log --max-count 20 | gitlogfeed -i --target-dir docs/build https://your.site
```
