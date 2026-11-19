"""The modules changed since their version was last set (the version in __manifest__.py).

    python3 tools/versions.py          list every module and what changed since its version
    python3 tools/versions.py --check  the same, and fail when a changed module kept its version
    python3 tools/versions.py --db BASE [--conf odoo.conf]
                                       on a server: the modules of BASE older than this code, and
                                       the command that updates them

Run with --check before each commit: a module changed keeps the version of the code it had, and
a server cannot tell which modules to update (`-u`). Each commit that changes a module raises its
version: 20.0.X.Y.0 for a new feature or screen, 20.0.X.Y.Z for a fix.

With --db, the versions installed in the base (`ir_module_module`) are read with psycopg2 (the Python
of Odoo) or psql, connected as the server: the db_host, db_port, db_user and db_password of the
configuration file (--conf, else $ODOO_RC), else the PG* variables. Nothing is written."""
import ast
import configparser
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


# === ON A SERVER: THE BASE AGAINST THIS CODE === #

def code_modules():
    """{name: (version, manifest, of the project)} of the modules in this repository: the project at its
    root, the other authors under marketplace/ (loaded when their folder is on the addons path)."""
    found = {}
    folders = [(ROOT, True)]
    market = os.path.join(ROOT, "marketplace")
    if os.path.isdir(market):
        folders += [(os.path.join(market, name), False) for name in sorted(os.listdir(market))]
    for folder, project in folders:
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name, "__manifest__.py")
            if name in OTHER_AUTHORS or not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as file:
                manifest = ast.literal_eval(file.read())
            found.setdefault(name, (manifest.get("version", ""), manifest, project))
    return found


def full_version(version, series):
    """The version as Odoo writes it in the base: the series first (« 1.0 » becomes « 20.0.1.0 »)."""
    if not version:
        return series
    if version.startswith(series + ".") or version == series:
        return version
    return f"{series}.{version}" if version.count(".") <= 2 else version


def version_key(version):
    return tuple(int(part) if part.isdigit() else 0 for part in (version or "").split("."))


def plan(code, rows):
    """What to do so that the base runs this code. `code`: {name: (version, manifest, of the project)};
    `rows`: [(name, state, installed version)] of the base. Returns the lists:
    update [(name, installed, code)], install [names], new [(name, version, note)], older [(name,
    installed, code)], half [(name, state)]."""
    base = {name: (state, version or "") for name, state, version in rows}
    series = ".".join((base.get("base", ("", "20.0"))[1] or "20.0").split(".")[:2])
    installed = {name for name, (state, _version) in base.items() if state in ("installed", "to upgrade")}
    update, install, new, older, half = [], [], [], [], []
    for name, (version, manifest, project) in sorted(code.items()):
        state, in_base = base.get(name, ("absent", ""))
        version = full_version(version, series)
        if state in ("installed", "to upgrade"):
            if state == "to upgrade":
                half.append((name, state))
            if state == "to upgrade" or version_key(version) > version_key(in_base):
                update.append((name, in_base, version))
            elif version_key(version) < version_key(in_base):
                older.append((name, in_base, version))
        elif state == "to install":
            half.append((name, state))
            install.append(name)
        elif project:
            depends = manifest.get("depends", [])
            if manifest.get("auto_install") and depends and all(dep in installed for dep in depends):
                # Every module it needs is there: Odoo would have installed it with them
                install.append(name)
                new.append((name, version, "installs itself with " + ", ".join(depends)))
            elif manifest.get("auto_install"):
                new.append((name, version, "comes with " + ", ".join(dep for dep in depends if dep not in installed)))
            elif "_demo" in name:
                new.append((name, version, "demo data: never on a real server"))
            else:
                new.append((name, version, manifest.get("summary") or manifest.get("name") or ""))
    return {"update": update, "install": install, "new": new, "older": older, "half": half}


def read_conf(path):
    """The connection of the Odoo server to PostgreSQL, from its configuration file."""
    if not path:
        return {}
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(path):
        sys.exit(f"Configuration file not found: {path}")
    options = parser["options"] if parser.has_section("options") else {}
    found = {}
    for key, name in (("db_host", "host"), ("db_port", "port"), ("db_user", "user"), ("db_password", "password")):
        value = (options.get(key) or "").strip()
        if value and value != "False":
            found[name] = value
    return found


def base_rows(db, connection):
    query = "SELECT name, state, latest_version FROM ir_module_module"
    try:
        import psycopg2
    except ImportError:
        psycopg2 = None
    if psycopg2:
        try:
            with psycopg2.connect(dbname=db, **connection) as conn, conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except psycopg2.Error as error:
            sys.exit(f"Cannot read the base {db}: {str(error).strip()}")
    env = dict(os.environ)
    for name, variable in (("host", "PGHOST"), ("port", "PGPORT"), ("user", "PGUSER"), ("password", "PGPASSWORD")):
        if name in connection:
            env[variable] = connection[name]
    try:
        result = subprocess.run(["psql", "-d", db, "-AtF", "\t", "-c", query], env=env,
                                capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("Neither psycopg2 nor psql: run this with the Python of Odoo, or install psql.")
    if result.returncode:
        sys.exit(f"Cannot read the base {db}: {result.stderr.strip()}")
    return [tuple(line.split("\t")) for line in result.stdout.splitlines() if line]


def server(db, conf):
    todo = plan(code_modules(), base_rows(db, read_conf(conf)))
    width = max([len(name) for name, *_rest in todo["update"] + todo["older"] + todo["new"]] + [10])
    if todo["half"]:
        print("Left half done by a command that stopped (run the command below again):")
        for name, state in todo["half"]:
            print(f"  {name:<{width}}  {state}")
    if todo["older"]:
        print("Older in this code than in the base (check the branch deployed):")
        for name, in_base, version in todo["older"]:
            print(f"  {name:<{width}}  {in_base} in the base, {version} here")
    if todo["update"]:
        print(f"To update ({len(todo['update'])}), installed -> this code:")
        for name, in_base, version in todo["update"]:
            print(f"  {name:<{width}}  {in_base or '?'} -> {version}")
    if todo["new"]:
        print("Not installed (add to -i the ones wanted):")
        for name, version, note in todo["new"]:
            print(f"  {name:<{width}}  {version}  {note}")
    if not todo["update"] and not todo["install"]:
        print(f"The base {db} runs this code: nothing to update.")
        return
    parts = ["odoo", "-c", conf or "odoo.conf", "-d", db]
    if todo["install"]:
        parts += ["-i", ",".join(todo["install"])]
    if todo["update"]:
        parts += ["-u", ",".join(name for name, *_rest in todo["update"])]
    print("Command:")
    print("  " + " ".join(parts + ["--stop-after-init"]))


def main():
    args = sys.argv[1:]
    if "--db" in args:
        position = args.index("--db")
        if position + 1 >= len(args):
            sys.exit("--db needs the name of the base")
        conf = args[args.index("--conf") + 1] if "--conf" in args[:-1] else os.environ.get("ODOO_RC")
        server(args[position + 1], conf)
        return
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
