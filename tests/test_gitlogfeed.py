import subprocess

from gitlogfeed import Git


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


def _git_init():
    subprocess.check_call(["git", "init"])


def _git_commit(repo, message, files):
    for filename, content in files.items():
        repo.join(filename).write_text(content, "ascii")
        subprocess.check_call(["git", "add", filename])

    subprocess.check_call(["git", "commit", "-m", message])
