"""The modules changed since their version was last set (the version in __manifest__.py).

    python3 tools/versions.py          list every module and what changed since its version
    python3 tools/versions.py --check  the same, and fail when a changed module kept its version

Run with --check before each commit: a module changed keeps the version of the code it had, and
a server cannot tell which modules to update (`-u`). Each commit that changes a module raises its
version: 20.0.X.Y.0 for a new feature or screen, 20.0.X.Y.Z for a fix."""
import ast
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
# Modules of other authors, kept as they are published
OTHER_AUTHORS = {"marketplace"}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def modules():
    for name in sorted(os.listdir(ROOT)):
        manifest = os.path.join(ROOT, name, "__manifest__.py")
        if name not in OTHER_AUTHORS and os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as file:
                yield name, ast.literal_eval(file.read()).get("version", "")


def changes_since_version(name, version):
    """(commit where the version was set, commits that changed the module since, files changed
    and not committed yet)."""
    since = git("log", "-1", "--format=%h", f"-S\"version\": \"{version}\"", "--", f"{name}/__manifest__.py")
    commits = git("log", "--format=%h %s", f"{since}..HEAD", "--", name).splitlines() if since else []
    pending = git("status", "--porcelain", "--", name).splitlines()
    # A version raised and not committed yet covers the changes waiting with it
    manifest_pending = any(line.endswith("__manifest__.py") for line in pending)
    committed = git("show", f"HEAD:{name}/__manifest__.py") if since else ""
    raised = manifest_pending and f'"version": "{version}"' not in committed
    return since, commits, pending, raised


def main():
    check = "--check" in sys.argv[1:]
    late = []
    for name, version in modules():
        since, commits, pending, raised = changes_since_version(name, version)
        if raised:
            print(f"{name} {version}: version raised, to commit with its changes")
            continue
        if not commits and not pending:
            continue
        print(f"{name} {version} (set in {since or '?'}): {len(commits)} commit(s) and {len(pending)} file(s) changed since")
        for line in commits[:10]:
            print(f"    {line}")
        late.append(name)
    if not late:
        print("Every changed module has a new version.")
    if check and late:
        print("Raise the version of: " + ", ".join(late))
        sys.exit(1)


if __name__ == "__main__":
    main()
