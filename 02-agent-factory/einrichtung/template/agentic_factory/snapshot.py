"""Spec checksums and local copies, to find what a developer edited by hand since the last spec or build run. The
checksum goes into the [KI] comment; the copy under ~/.factory-local/ is the base for the diff. Never inside the project.
"""
import difflib
import hashlib
import re
import shutil
from pathlib import Path

from . import config, ticket

HEADER_RE = re.compile(r"(?:\A|(?<=\n\n))=== (.+?) ===$", re.M)  # the headers of fetch.spec_result's text
LINE_RE = re.compile(r"[^\n]*\n|[^\n]+")  # lines split on \n only, so \r stays part of the line
NO_NEWLINE = "\\ No newline at end of file\n"


def spec_files(repo, F, change, known):
    """Sorted repo-relative files of the change: those matching spec_change_re with this change as group 1, and all files
    under the folder of any known path in the spec area that doesn't belong to another change (BMad PRD folders)."""
    rx = re.compile(F["spec_change_re"])
    area = re.compile(F["spec_any_under"]) if F.get("spec_any_under") else None
    files = [p for p in ticket.repo_files(repo) if (repo / p).is_file()]
    folders = []
    for k in known:
        m = rx.match(k)
        if area and area.match(k) and (m is None or m.group(1) in (None, change)):
            folders.append(k.rpartition("/")[0] + "/")
    return sorted({p for p in files
                   if ((m := rx.match(p)) and m.group(1) == change) or any(p.startswith(f) for f in folders)})


def paths_in_spec_text(text):
    """The paths of the `=== path ===` headers of a spec text, in order."""
    return HEADER_RE.findall(text)


def checksum(repo, paths):
    """sha256 over path + NUL + bytes + NUL of the files, sorted by path. Bytes as they are, so line endings count."""
    h = hashlib.sha256()
    for p in sorted(set(paths)):
        try:
            data = (repo / p).read_bytes()
        except OSError as e:
            raise config.Stop(f"can't read the spec file {p}: {e.strerror or e}")
        h.update(p.encode("utf-8") + b"\0" + data + b"\0")
    return h.hexdigest()


def local_root():
    return Path.home() / ".factory-local"


def _part(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value) or ".." in value:
        raise config.Stop(f"{value!r} can't be a folder name of the local spec copy")
    return value


def copy_dir(repo, key, change, mode, n):
    """~/.factory-local/<repo>/specs/<key>/<change>/<mode>-<n>/. Not created here."""
    return local_root() / _part(repo.name) / "specs" / _part(key) / _part(change) / f"{_part(mode)}-{int(n)}"


def save(repo, paths, dest):
    """Replaces dest with a byte-for-byte copy of the files. Only below ~/.factory-local/."""
    try:
        dest.resolve().relative_to(local_root().resolve())
    except ValueError:
        raise config.Stop(f"the spec copy goes below {local_root()}, not to {dest}")
    if dest.resolve() == local_root().resolve():
        raise config.Stop(f"the spec copy goes below {local_root()}, not to {dest}")
    for p in paths:
        if Path(p).is_absolute() or ".." in Path(p).parts:
            raise config.Stop(f"not a path inside the repository: {p}")
    try:
        if dest.exists():
            shutil.rmtree(dest)
        for p in paths:
            target = dest / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repo / p).read_bytes())
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise config.Stop(f"can't save the spec copy to {dest}: {e.strerror or e}")


def _lines(data):
    """The text of the bytes as lines; None (missing file) is no lines. The last line always ends in a newline."""
    if data is None:
        return []
    lines = LINE_RE.findall(data.decode("utf-8", errors="replace"))
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n" + NO_NEWLINE
    return lines


def _read(path):
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError as e:
        raise config.Stop(f"can't read {path}: {e.strerror or e}")


def diff(dest, repo, paths):
    """Unified diff of the copy in dest against the files now, repo-relative paths in the headers. Files only in paths
    count as added, files only in the copy as removed. "" when nothing differs."""
    try:
        saved = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} if dest.is_dir() else set()
    except OSError as e:
        raise config.Stop(f"can't read the spec copy {dest}: {e.strerror or e}")
    out = []
    for p in sorted(saved | set(paths)):
        old = _read(dest / p) if p in saved else None
        new = _read(repo / p) if p in paths else None
        if old == new:
            continue
        out.extend(difflib.unified_diff(_lines(old), _lines(new), f"a/{p}", f"b/{p}"))
    return "".join(out)
