import subprocess
import pathlib
import xml.etree.ElementTree as ET

from gitlogfeed import Html, Feed, main, parse_git_log, iter_git_log


ASSETS = pathlib.Path(__file__).parent.joinpath("assets")
NAMESPACES = {"": "http://www.w3.org/2005/Atom"}


def test_html(tmpdir):
    commit = next(parse_git_log(ASSETS.joinpath("feed-git.log").open(encoding="ascii")))
    html = Html()
    html.parse_commit(commit)

    html_file = tmpdir.join("diff.html")
    html.write(str(html_file))

    test_asset = ASSETS.joinpath("patch.html")

    assert _canonicalize_xml(html_file) == _canonicalize_xml(test_asset)


def test_feed():
    feed_name = "feed.atom.xml"
    feed_title = "Feed title"
    base_url = "https://feed-example.com"
    feed = Feed(feed_title, base_url, feed_name)
    commits = list(
        parse_git_log(ASSETS.joinpath("feed-git.log").open(encoding="ascii"))
    )

    for commit in commits:
        entry = feed.add_entry(commit)
        feed.add_entry_link(entry, f"{commit['hash']}.html")

    assert feed.feed.find("title").text == feed_title
    assert feed.feed.find("id").text == base_url

    entries = feed.feed.findall("entry")

    assert len(entries) == len(commits)

    for entry, commit in zip(entries, commits):
        assert entry.find("title").text == commit["title"]
        assert entry.find("author/name").text == commit["name"]
        assert entry.find("author/email").text == commit["email"]
        assert entry.find("updated").text == commit["date"]
        assert entry.find("published").text == commit["date"]
        assert entry.find("summary/pre").text == "".join(commit["message"])
        assert entry.find("link").attrib["href"] == f"{base_url}/{commit['hash']}.html"


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


def test_parse():
    git_log_path = ASSETS.joinpath("git.log")
    commits = list(parse_git_log(git_log_path.open(encoding="ascii")))

    assert commits == [
        {
            "title": "setup.py: version 1.0.0",
            "hash": "17a5555072179a6c50c39979787921205e67e1a6",
            "date": "2022-03-19T22:38:46+01:00",
            "email": "gergo@nyiro.name",
            "name": "Gergo Nyiro",
            "message": [],
            "patch": _filter_lines(git_log_path.open(encoding="ascii"), 7, 19),
        },
        {
            "title": "gitlogfeed cli: use base_url as positional argument",
            "hash": "bda6a7e93152d5998d05ba8d512c2c4972bce889",
            "date": "2022-03-19T22:22:35+01:00",
            "email": "john@mail.com",
            "name": "John Doe",
            "message": ["Add help to the cli options.\n"],
            "patch": _filter_lines(git_log_path.open(encoding="ascii"), 29, 165),
        },
    ]


def test_parse_from_git(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "first commit\n\nFirst\n- message", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit\n\nSecond\n- message", {"foo.py": "print(24)"})

    git_log = iter_git_log(str(repo), 2, 3, None)
    commits = list(parse_git_log(git_log))

    log = [
        {
            "title": "second commit",
            "name": "Test User",
            "email": "test.user@github.com",
            "message": ["Second\n", "- message\n"],
        },
        {
            "title": "first commit",
            "name": "Test User",
            "email": "test.user@github.com",
            "message": ["First\n", "- message\n"],
        },
    ]

    assert _filter_commits(commits, {"title", "name", "email", "message"}) == log


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


def _filter_lines(file_desc, start, end):
    return [line for i, line in enumerate(file_desc, 1) if start <= i <= end]
