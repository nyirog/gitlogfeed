import subprocess
import tempfile
import datetime
import argparse
import sys
import enum

import xml.etree.ElementTree as ET


def main(argv=None):
    arg_parser = _create_arg_parser()
    args = arg_parser.parse_args(argv)

    git = Git(args.repo, args.filter_path, args.diff_context)
    feed = Feed(git, args.feed_title, args.base_url, args.feed_name, args.target_dir)
    commits = git.log(args.log_limit)

    try:
        update = commits[0]["date"]
    except IndexError:
        update = datetime.datetime.now().isformat()

    feed.update(update)

    for commit in commits:
        feed.add_entry(commit)

    feed.write()


def _create_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--filter-path")
    parser.add_argument("--log-limit", type=int, default=20)
    parser.add_argument("--diff-context", type=int, default=5000)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--target-dir", default=".")
    parser.add_argument("--feed-name", default="atom.xml")
    parser.add_argument("--feed-title", default="Git log feed")

    return parser


class App:
    def __init__(self, git, feed, log_limit):
        self._git = git
        self._feed = feed
        self._log_limit = log_limit

    def main(self):
        commits = self._git.log(self._log_limit)

        try:
            update = commits[0]["date"]
        except IndexError:
            update = datetime.datetime.now().isformat()

        self._feed.update(update)

        for commit in commits:
            self._feed.add_entry(commit)

        self._feed.write()


def _parse_commit_info(file_desc):
    return dict(line.strip().split(",", maxsplit=1) for line in file_desc)


class Git:
    def __init__(self, repo, filter_path, diff_context):
        self._repo = repo
        self._filter_path = filter_path
        self._diff_context = diff_context
        self._sub_process = SubProcess(cwd=repo, encoding="utf-8")

    def iter_patch_lines(self, commit):
        yield from self._sub_process.pipe(self._get_show_args(commit, ""))

    def log(self, max_count):
        args = [
            "git",
            "log",
            "--format=format:%H",
            f"--max-count={max_count}",
        ]

        if self._filter_path:
            args.extend(["--", self._filter_path])

        return [self._get_commit(line.strip()) for line in self._sub_process.pipe(args)]

    def _get_commit(self, commit):
        args = self._get_show_args(commit, "title,%s%ndate,%aI%nname,%an%nemail,%ae")
        info = dict(
            line.strip().split(",", maxsplit=1) for line in self._sub_process.pipe(args)
        )

        info["commit"] = commit
        info["message"] = self._sub_process.call(self._get_show_args(commit, "%b"))

        return info

    def _get_show_args(self, commit, commit_format):
        args = [
            "git",
            "show",
            f"--format=format:{commit_format}",
        ]

        if commit_format:
            args.append("--no-patch")
        else:
            args.append(f"--unified={self._diff_context}")

        args.append(commit)

        return args


class SubProcess:
    def __init__(self, cwd=None, encoding="utf-8"):
        self._cwd = cwd
        self._encoding = encoding

    def call(self, args):
        result = subprocess.run(args, check=True, capture_output=True, cwd=self._cwd)
        return result.stdout.decode("utf-8")

    def pipe(self, args):
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp:
            with subprocess.Popen(args, stdout=tmp, cwd=self._cwd) as proc:
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
    def __init__(self, title):
        self.doc = ET.Element("html")
        _add_child(self.doc, "head")
        _add_child(self.doc, "title", text=title)
        self.body = _add_child(self.doc, "body")

    def parse_diff(self, diff_lines):
        pre = _add_child(self.doc, "pre")
        diff_scope = DiffScope()

        for line in diff_lines:
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
    # pylint: disable=too-many-arguments
    def __init__(self, git, title, base_url, filename, target_dir):
        self.filename = filename
        self.base_url = base_url
        self.git = git
        self.target_dir = target_dir

        self.feed = ET.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})

        _add_child(self.feed, "link", href=f"{base_url}/{filename}", rel="self")
        _add_child(self.feed, "id", text=base_url)
        _add_child(self.feed, "title", text=title)

    def update(self, update):
        _add_child(self.feed, "updated", text=update)

    def add_entry(self, commit_info):
        entry = _add_child(self.feed, "entry")
        _add_child(entry, "id", text=f"urn:sha256:{commit_info['commit']}")
        _add_child(entry, "title", text=commit_info["title"])
        _add_child(entry, "updated", text=commit_info["date"])
        _add_child(entry, "published", text=commit_info["date"])

        summary = _add_child(entry, "summary", type="html")
        _add_child(summary, "pre", text=commit_info["message"])

        author = _add_child(entry, "author")
        _add_child(author, "name", text=commit_info["name"])
        _add_child(author, "email", text=commit_info["email"])

        filename = f"{commit_info['commit']}.html"
        html = Html(commit_info["title"])
        html.parse_diff(self.git.iter_patch_lines(commit_info["commit"]))
        html.write(f"{self.target_dir}/{filename}")

        _add_child(
            entry,
            "link",
            href=f"{self.base_url}/{filename}",
            rel="alternate",
        )

    def write(self):
        tree = ET.ElementTree(self.feed)
        tree.write(f"{self.target_dir}/{self.filename}", xml_declaration=True)


def _add_child(parent, tag, text=None, **attrib):
    child = parent.makeelement(tag, attrib)
    child.text = text
    parent.append(child)
    return child


if __name__ == "__main__":
    sys.exit(main())
