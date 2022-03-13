import subprocess
import tempfile
import datetime
import argparse
import sys

import xml.etree.ElementTree as ET


def main():
    args = _parse_args()
    git = Git(args.repo, args.filter_path, args.diff_context)
    feed = Feed(git, args.feed_title, args.base_url, args.feed_name)
    app = App(git, feed, args.log_limit)

    return app.main()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--filter-path")
    parser.add_argument("--log-limit", type=int, default=20)
    parser.add_argument("--diff-context", type=int, default=5000)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--feed-name", default="atom.xml")
    parser.add_argument("--feed-title", default="Git log feed")

    return parser.parse_args()


class App:
    def __init__(self, git, feed, log_limit):
        self._git = git
        self._feed = feed
        self._log_limit = log_limit

    def main(self):
        commits = self._git.log(self._log_limit, "%H", self._list_commits)

        try:
            update = commits[0]["date"]
        except IndexError:
            update = datetime.datetime.now().isformat()

        self._feed.update(update)

        for commit in commits:
            self._feed.add_entry(commit)

        self._feed.write()

    def _list_commits(self, file_desc):
        return [self._get_commit(line.strip()) for line in file_desc]

    def _get_commit(self, commit):
        info = self._git.show(
            commit, "title,%s%ndate,%aI%nname,%an%nemail,%ae", _parse_commit_info
        )
        info["commit"] = commit
        info["message"] = self._git.show(commit, "%b")

        return info


def _parse_commit_info(file_desc):
    return dict(line.strip().split(",", maxsplit=1) for line in file_desc)


class Git:
    def __init__(self, repo, filter_path, diff_context):
        self._repo = repo
        self._filter_path = filter_path
        self._diff_context = diff_context

    def log(self, max_count, commit_format, processor=None):
        args = [
            "git",
            "log",
            f"--max-count={max_count}",
            f"--format=format:{commit_format}",
        ]

        if self._filter_path:
            args.extend(["--", self._filter_path])

        if callable(processor):
            return self._pipe(args, processor)

        return self._run(args)

    def show(self, commit, commit_format, processor=None):
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

        if self._filter_path:
            args.extend(["--", self._filter_path])

        if callable(processor):
            return self._pipe(args, processor)

        return self._run(args)

    def _pipe(self, args, processor):
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as tmp:
            with subprocess.Popen(args, stdout=tmp, cwd=self._repo) as proc:
                proc.communicate()
                tmp.seek(0)
                return processor(tmp)

    def _run(self, args):
        result = subprocess.run(args, check=True, capture_output=True, cwd=self._repo)
        return result.stdout.decode("utf-8")


class Html:
    def __init__(self, title):
        self.doc = ET.Element("html")
        _add_child(self.doc, "head")
        _add_child(self.doc, "title", text=title)
        self.body = _add_child(self.doc, "body")

    def parse_diff(self, file_desc):
        div = _add_child(self.doc, "pre")
        for line in file_desc:
            span = _add_child(div, "span", **self._select_attrs(line))
            span.text = line

    @staticmethod
    def _select_attrs(line):
        if line.startswith("+ "):
            return {"style": "background-color:lightgreen"}

        if line.startswith("- "):
            return {"style": "background-color:pink"}

        if line.startswith("diff "):
            return {"style": "background-color:lightblue"}

        if (
            line.startswith("index ")
            or line.startswith("+++ ")
            or line.startswith("--- ")
            or line.startswith("@@ ")
        ):
            return {"style": "background-color:lightgrey"}

        return {}

    def write(self, filename):
        tree = ET.ElementTree(self.doc)
        tree.write(
            filename,
            method="html",
        )


class Feed:
    def __init__(self, git, title, base_url, filename):
        self.filename = filename
        self.base_url = base_url
        self.git = git

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
        self.git.show(commit_info["commit"], "", html.parse_diff)
        html.write(filename)

        _add_child(
            entry,
            "link",
            href=f"{self.base_url}/{filename}",
            type="alternate",
        )

    def write(self):
        tree = ET.ElementTree(self.feed)
        tree.write(self.filename, xml_declaration=True)


def _add_child(parent, tag, text=None, **attrib):
    child = parent.makeelement(tag, attrib)
    child.text = text
    parent.append(child)
    return child


if __name__ == "__main__":
    sys.exit(main())
