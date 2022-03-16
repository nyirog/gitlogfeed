import subprocess

from gitlogfeed import Git

def test_git_show(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        repo.join("foo.py").write_text("print(42)", "ascii")
        subprocess.check_call(["git", "add", "."])
        subprocess.check_call(["git", "commit", "-m", "commit title\n\ncommit message"])

    git = Git(str(repo), None, 20)

    assert git.show("HEAD", "%s") == "commit title"
    assert git.show("HEAD", "%b") == "commit message\n"


def test_git_log(tmpdir):
    repo = tmpdir.mkdir("repo")

    with repo.as_cwd():
        subprocess.check_call(["git", "init"])
        repo.join("foo.py").write_text("print(42)", "ascii")
        subprocess.check_call(["git", "add", "."])
        subprocess.check_call(["git", "commit", "-m", "first commit"])
        repo.join("foo.py").write_text("print(24)", "ascii")
        subprocess.check_call(["git", "commit", "-a", "-m", "second commit"])

    git = Git(str(repo), None, 20)

    assert git.log(2, "%s", list) == ["second commit\n", "first commit"]
