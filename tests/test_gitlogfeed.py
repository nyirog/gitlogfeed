import subprocess
import pathlib
import xml.etree.ElementTree as ET

from gitlogfeed import Git, Html, Feed, main


ASSETS = pathlib.Path(__file__).parent.joinpath("assets")
NAMESPACES = {"": "http://www.w3.org/2005/Atom"}


def test_git_iter_patch_lines(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "commit title\n\ncommit message", {"foo.py": "print(42)"})

    git = Git(str(repo), None, 20)
    test_asset = ASSETS.joinpath("patch.diff").read_text(encoding="ascii")

    assert "".join(git.iter_patch_lines("HEAD")) == test_asset


def test_git_log(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)
    log = [
        {
            "title": "second commit",
            "name": "Test User",
            "email": "test.user@github.com",
            "message": "",
        },
        {
            "title": "first commit",
            "name": "Test User",
            "email": "test.user@github.com",
            "message": "",
        },
    ]

    assert _filter_commits(git.log(2), {"title", "name", "email", "message"}) == log


def test_git_log_filter(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "python commit", {"foo.py": "print(42)"})
        _git_commit(repo, "php commit", {"foo.php": "echo 42;"})

    git = Git(str(repo), "*.py", 20)
    log = [
        {"title": "python commit"},
    ]

    assert _filter_commits(git.log(2), {"title"}) == log


def test_git_log_limit(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)
    log = [
        {"title": "second commit"},
    ]

    assert _filter_commits(git.log(1), {"title"}) == log


def test_html(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)
    html = Html("Test title")
    html.parse_diff(git.iter_patch_lines("HEAD"))

    html_file = tmpdir.join("diff.html")
    html.write(str(html_file))

    test_asset = ASSETS.joinpath("diff.html")

    assert _canonicalize_xml(html_file) == _canonicalize_xml(test_asset)


def test_filtered_diff_html(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "python commit", {"foo.py": "print(42)"})
        _git_commit(repo, "php commit", {"foo.php": "echo 42;", "foo.py": "print(24)"})

    git = Git(str(repo), "*.py", 20)
    html = Html("Test title")
    html.parse_diff(git.iter_patch_lines("HEAD"))

    html_file = tmpdir.join("diff.html")
    html.write(str(html_file))

    test_asset = ASSETS.joinpath("diff.html")

    assert _canonicalize_xml(html_file) == _canonicalize_xml(test_asset)


def test_feed(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first-commit\n\nFirst message", {"foo.py": "print(42)"})
        _git_commit(repo, "second-commit\n\nSecond message", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)
    feed_name = "feed.atom.xml"
    feed_title = "Feed title"
    base_url = "https://feed-example.com"
    feed = Feed(git, feed_title, base_url, feed_name, str(tmpdir))
    commits = git.log(2)

    for commit in commits:
        feed.add_entry(commit)

    feed.write()

    feed_xml = ET.parse(str(tmpdir.join(feed_name)))

    assert _find_text(feed_xml, "title") == feed_title
    assert _find_text(feed_xml, "id") == base_url

    entries = feed_xml.findall("entry", NAMESPACES)

    assert len(entries) == len(commits)

    for entry, commit in zip(entries, commits):
        assert _find_text(entry, "title") == commit["title"]
        assert _find_text(entry, "author/name") == commit["name"]
        assert _find_text(entry, "author/email") == commit["email"]
        assert _find_text(entry, "updated") == commit["date"]
        assert _find_text(entry, "published") == commit["date"]
        assert _find_text(entry, "summary/pre") == commit["message"]

        link = entry.find("link", NAMESPACES).attrib["href"]
        url, resource = link.rsplit("/", maxsplit=1)

        assert url == base_url
        assert resource == f"{commit['commit']}.html"

        _assert_text_files(
            ASSETS.joinpath(f"{commit['title']}.html"), tmpdir.join(resource)
        )


def test_main(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})

    feed_name = "feed.atom.xml"
    feed_title = "Feed title"
    base_url = "https://feed-example.com"

    main(
        [
            "--target-dir",
            str(tmpdir),
            "--repo",
            str(repo),
            "--feed-name",
            feed_name,
            "--feed-title",
            feed_title,
            base_url,
        ]
    )

    feed_xml = ET.parse(str(tmpdir.join(feed_name)))

    assert _find_text(feed_xml, "title") == feed_title
    assert _find_text(feed_xml, "id") == base_url
    assert _find_all_text(feed_xml, "entry/title") == ["first commit"]
    assert _find_all_text(feed_xml, "entry/author/name") == ["Test User"]


def _git_init():
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "config", "--local", "user.name", "Test User"])
    subprocess.check_call(
        ["git", "config", "--local", "user.email", "test.user@github.com"]
    )


def _git_commit(repo, message, files):
    for filename, content in files.items():
        repo.join(filename).write_text(content, "ascii")
        subprocess.check_call(["git", "add", filename])

    subprocess.check_call(["git", "commit", "-m", message])


def _canonicalize_xml(from_file):
    return ET.canonicalize(from_file=str(from_file))


def _filter_commits(commits, required):
    return [
        {key: value for key, value in commit.items() if key in required}
        for commit in commits
    ]


def _find_text(root, tag):
    return root.find(tag, NAMESPACES).text


def _find_all_text(root, tag):
    return [node.text for node in root.findall(tag, NAMESPACES)]


def _assert_text_files(path_a, path_b, encoding="ascii"):
    assert path_a.read_text(encoding) == path_b.read_text(encoding)
