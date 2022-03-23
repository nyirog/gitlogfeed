"""
Create an atom feed from git log.
"""

import subprocess
import tempfile
import datetime
import argparse
import sys
import enum
import re
import warnings

import xml.etree.ElementTree as ET


def main(argv=None):
    arg_parser = _create_arg_parser()
    args = arg_parser.parse_args(argv)

    if args.stdin:
        git_log = sys.stdin

    else:
        git_log = iter_git_log(
            args.repo, args.log_limit, args.diff_context, args.filter_path
        )

    commits = GitLogParser().parse(git_log)
    feed = Feed(args.feed_title, args.base_url, args.feed_name)

    try:
        commit = next(commits)

    except StopIteration:
        update = datetime.datetime.now().isformat()

    else:
        update = commit["date"]
        feed.add_commit(commit, args.target_dir)

    for commit in commits:
        feed.add_commit(commit, args.target_dir)

    feed.update(update)
    feed.write(f"{args.target_dir}/{args.feed_name}")


def _create_arg_parser():
    parser = argparse.ArgumentParser(
        description="Create an atom feed from git log.",
        epilog="""
        The title and summary of the feed entry will be created from the commit
        message. An html file will be created from every patch and the content of the
        feed entry will be linked to the html file.
        """,
    )
    parser.add_argument(
        "-i", "--stdin", action="store_true", help="Read git log from stdin"
    )

    group = parser.add_argument_group("git")
    group.add_argument(
        "--repo",
        default=".",
        help="Path of the git repository, default is the current directory.",
    )
    group.add_argument(
        "--filter-path",
        help="Narrow the commits which affects the specified FILTER_PATH.",
    )
    group.add_argument(
        "--log-limit",
        type=int,
        default=20,
        help="Limit the number of commits to process, default is %(default)s.",
    )
    group.add_argument(
        "--diff-context",
        type=int,
        default=3,
        help="Number of lines used in the diff, default is %(default)s.",
    )

    group = parser.add_argument_group("feed")
    group.add_argument(
        "base_url",
        help="The atom feed and the html diff files will be linked under this url. "
        "This url will be used as the id of the feed.",
    )
    group.add_argument(
        "--target-dir",
        default=".",
        help="gitlogfeed will generate the files into this directory, "
        "default is the current directory.",
    )
    group.add_argument(
        "--feed-name",
        default="atom.xml",
        help="Name of the feed file, default is '%(default)s'.",
    )
    group.add_argument(
        "--feed-title",
        default="Git log feed",
        help="Title of the feed, default is '%(default)s'.",
    )

    return parser


def iter_git_log(repo, max_count, diff_context, filter_path):
    args = [
        "git",
        "log",
        "--date=iso-strict",
        f"--unified={diff_context}",
        f"--max-count={max_count}",
    ]
    if filter_path:
        args.extend(["--", filter_path])

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp:
        with subprocess.Popen(args, stdout=tmp, cwd=repo) as proc:
            proc.communicate()
            tmp.seek(0)
            yield from tmp


class Color(str, enum.Enum):
    WHITE = "white"
    GREY = "lightgrey"
    BLUE = "lightblue"
    GREEN = "lightgreen"
    RED = "pink"


class DiffScope:
    def __init__(self):
        self._in_header = False

    def select_color(self, line) -> Color:
        if self._in_header:
            return Color.GREY

        if line.startswith("diff "):
            self._in_header = True
            return Color.BLUE

        if line.startswith("+"):
            return Color.GREEN

        if line.startswith("-"):
            return Color.RED

        return Color.WHITE

    def check_scope(self, line):
        if self._in_header and line.startswith("@@ "):
            self._in_header = False


class Html:
    def __init__(self):
        self.doc = ET.Element("html")
        _add_child(self.doc, "head")

    def parse_commit(self, commit):
        _add_child(self.doc, "title", text=commit["title"])
        body = _add_child(self.doc, "body")
        pre = _add_child(body, "pre")
        diff_scope = DiffScope()

        for line in commit["patch"]:
            bg_color = diff_scope.select_color(line)
            _add_child(pre, "span", text=line, style=f"background-color:{bg_color}")
            diff_scope.check_scope(line)

    def write(self, filename):
        tree = ET.ElementTree(self.doc)
        tree.write(
            filename,
            method="html",
        )


class Feed:
    def __init__(self, title, base_url, feed_name):
        self.base_url = base_url

        self.feed = ET.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})

        _add_child(self.feed, "link", href=f"{base_url}/{feed_name}", rel="self")
        _add_child(self.feed, "id", text=base_url)
        _add_child(self.feed, "title", text=title)

    def update(self, update):
        _add_child(self.feed, "updated", text=update)

    def add_commit(self, commit, target_dir):
        diff_file = f"{commit['hash']}.html"
        entry = self.add_entry(commit)
        self.add_entry_link(entry, diff_file)
        html = Html()
        html.parse_commit(commit)
        html.write(f"{target_dir}/{diff_file}")

    def add_entry(self, commit_info):
        entry = _add_child(self.feed, "entry")
        _add_child(entry, "id", text=f"urn:sha256:{commit_info['hash']}")
        _add_child(entry, "title", text=commit_info["title"])
        _add_child(entry, "updated", text=commit_info["date"])
        _add_child(entry, "published", text=commit_info["date"])

        summary = _add_child(entry, "summary", type="html")
        _add_child(summary, "pre", text="".join(commit_info["message"]))

        author = _add_child(entry, "author")
        _add_child(author, "name", text=commit_info["name"])
        _add_child(author, "email", text=commit_info["email"])

        return entry

    def add_entry_link(self, entry, filename):
        _add_child(
            entry,
            "link",
            href=f"{self.base_url}/{filename}",
            rel="alternate",
        )

    def write(self, filename):
        tree = ET.ElementTree(self.feed)
        tree.write(filename, xml_declaration=True)


def _add_child(parent, tag, text=None, **attrib):
    child = parent.makeelement(tag, attrib)
    child.text = text
    parent.append(child)
    return child


COMMIT_PATTERN = re.compile(r"^commit\s+([a-f0-9]{40})")
AUTHOR_PATTERN = re.compile(r"^Author:\s+(.+)\s+<(.+)>")
DATE_PATTERN = re.compile(r"^Date:\s+(.+)$")
HEADER_PATTERN = re.compile(r"^\w+:\s+\S+")
MESSAGE_PATTERN = re.compile(r"^[ ]{4}(.*)")
PATCH_PATTERN = re.compile(r"diff --git ")


class GitLogParser:
    def __init__(self):
        self._commit = {}
        self._parse_line = self._parse_init

    def parse(self, lines):
        for line in lines:
            if commit := self._parse_line(line):
                yield commit

        if self._commit:
            yield self._commit

    def _parse_init(self, line):
        if result := COMMIT_PATTERN.search(line):
            commit, self._commit = self._commit, Commit(result.group(1))
            self._parse_line = self._parse_header
            return commit

        if result := PATCH_PATTERN.search(line):
            self._parse_line = self._parse_patch
            self._commit["patch"].append(line)
            return {}

        warnings.warn(f"Unprocessed git log line: {line}")
        return {}

    def _parse_header(self, line):
        if result := AUTHOR_PATTERN.search(line):
            self._commit["name"] = result.group(1)
            self._commit["email"] = result.group(2)

        elif result := DATE_PATTERN.search(line):
            self._commit["date"] = _parse_date(result.group(1))

        elif line == "\n":
            self._parse_line = self._parse_title

        elif not HEADER_PATTERN.search(line):
            warnings.warn(f"Unprocessed git log line in header: {line}")

    def _parse_title(self, line):
        if result := line.strip():
            self._commit["title"] = result

        else:
            self._parse_line = self._parse_message

    def _parse_message(self, line):
        if MESSAGE_PATTERN.search(line):
            self._commit["message"].append(line[4:])

        elif PATCH_PATTERN.search(line):
            self._parse_line = self._parse_patch
            self._commit["patch"].append(line)

        elif line == "\n":
            self._parse_line = self._parse_init

        else:
            warnings.warn(f"Unprocessed git log line in message: {line}")

    def _parse_patch(self, line):
        if result := COMMIT_PATTERN.search(line):
            commit, self._commit = self._commit, Commit(result.group(1))
            self._parse_line = self._parse_header
            return commit

        if line == "\n":
            self._parse_line = self._parse_init
            return {}

        self._commit["patch"].append(line)
        return {}


def _parse_date(date_str):
    try:
        date = datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")

    except ValueError:
        return date_str

    return date.isoformat()


class Commit(dict):
    def __init__(self, commit_hash):
        super().__init__(hash=commit_hash, message=[], patch=[])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
