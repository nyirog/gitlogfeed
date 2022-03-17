import subprocess
import pathlib
import xml.etree.ElementTree as ET

from gitlogfeed import Git, Html


ASSETS = pathlib.Path(__file__).parent.joinpath("assets")


def test_git_show(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        _git_init()
        _git_commit(repo, "commit title\n\ncommit message", {"foo.py": "print(42)"})

    git = Git(str(repo), None, 20)

    assert git.show("HEAD", "%s") == "commit title"
    assert git.show("HEAD", "%b") == "commit message\n"


def test_git_log(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)

    assert git.log(2, "%s", list) == ["second commit\n", "first commit"]


def test_git_log_filter(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        _git_init()
        _git_commit(repo, "python commit", {"foo.py": "print(42)"})
        _git_commit(repo, "php commit", {"foo.php": "echo 42;"})

    git = Git(str(repo), "*.py", 20)

    assert git.log(2, "%s", list) == ["python commit"]


def test_git_log_limit(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    git = Git(str(repo), None, 20)

    assert git.log(1, "%s", list) == ["second commit"]


def test_html(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        _git_init()
        _git_commit(repo, "first commit", {"foo.py": "print(42)"})
        _git_commit(repo, "second commit", {"foo.py": "print(24)"})

    html = Html("Test title")
    git = Git(str(repo), None, 20)
    git.show("HEAD", "", html.parse_diff)

    html_file = tmpdir.join("diff.html")
    html.write(str(html_file))

    test_asset = ASSETS.joinpath("diff.html")

    assert _canonicalize_xml(html_file) == _canonicalize_xml(test_asset)


def _git_init():
    subprocess.check_call(["git", "init"])
    subprocess.check_call(["git", "config", "--local", "user.name", "test"])
    subprocess.check_call(["git", "config", "--local", "user.email", "test@github.com"])


def _git_commit(repo, message, files):
    for filename, content in files.items():
        repo.join(filename).write_text(content, "ascii")
        subprocess.check_call(["git", "add", filename])

    subprocess.check_call(["git", "commit", "-m", message])


def _canonicalize_xml(from_file):
    return ET.canonicalize(from_file=str(from_file))
