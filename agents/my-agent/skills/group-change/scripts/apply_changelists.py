#!/usr/bin/env python3
"""
Apply an IntelliJ IDEA changelist grouping by surgically rewriting the
<component name="ChangeListManager"> block inside .idea/workspace.xml.

Why a script: parsing `git status`, turning each change into the exact
<change beforePath/afterPath ...> element IDEA expects, creating changelists
without duplicating ones that already exist, and backing up workspace.xml are
deterministic and identical on every run. The *classification* of each file
into a changelist is the judgment part and is done by the caller, who passes
the result in as a {changelist_name: [paths]} mapping.

The rest of workspace.xml is left byte-for-byte untouched: only the
ChangeListManager block is replaced (or inserted if absent). This avoids losing
comments / other components that a full XML rewrite would clobber.

Usage:
    python apply_changelists.py --repo <repo_root> --mapping <mapping.json> [--dry-run]
    cat mapping.json | python apply_changelists.py --repo <repo_root> --mapping -

mapping.json looks like:
    {
      "数据结构": ["src/main/java/.../FooPO.java", "src/main/java/.../FooVO.java"],
      "枚举":     ["src/main/java/.../StatusEnum.java"],
      "其他":     []
    }
Paths are relative to the git root (exactly as `git status` prints them).
Any changed file not present in the mapping is placed in the "其他" changelist.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape, quoteattr

OTHER_LIST = "其他"
IDEA_DEFAULT_NAME = "Changes"  # IDEA's built-in default changelist name


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=True).stdout


def git_root(repo):
    try:
        out = run(["git", "rev-parse", "--show-toplevel"], repo).strip()
        return out
    except subprocess.CalledProcessError:
        sys.exit(f"ERROR: {repo} is not inside a git repository.")


def find_idea_dir(start):
    """Walk upward from start looking for a .idea directory."""
    cur = os.path.abspath(start)
    while True:
        cand = os.path.join(cur, ".idea")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def parse_git_status(groot):
    """Return list of dicts: {status, path, old_path}. Uses -z for safety."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=all"],
        cwd=groot, capture_output=True, check=True,
    ).stdout
    tokens = out.split(b"\0")
    changes = []
    i = 0
    while i < len(tokens):
        rec = tokens[i]
        if not rec:
            i += 1
            continue
        xy = rec[:2].decode("utf-8", "replace")
        path = rec[3:].decode("utf-8", "replace")
        old_path = None
        if xy and (xy[0] in ("R", "C")):
            # rename/copy: next token is the old path; current path is the new one
            if i + 1 < len(tokens):
                old_path = tokens[i + 1].decode("utf-8", "replace")
            i += 2
        else:
            i += 1
        changes.append({"status": xy, "path": path, "old_path": old_path})
    return changes


def change_kind(xy):
    """Collapse a porcelain XY code into added/deleted/renamed/modified."""
    if xy == "??":
        return "added"
    if "R" in xy or "C" in xy:
        return "renamed"
    if "D" in xy:
        return "deleted"
    if "A" in xy:
        return "added"
    return "modified"


def project_relpath(groot, project_dir, git_relpath):
    """Convert a git-root-relative path into a $PROJECT_DIR$-relative path.

    Both roots are realpath'd first: on macOS `git rev-parse --show-toplevel`
    resolves symlinks (e.g. /var -> /private/var) while the .idea path may not,
    which would otherwise produce bogus ../../private/var/... relative paths.
    """
    abs_path = os.path.realpath(os.path.join(groot, git_relpath))
    rel = os.path.relpath(abs_path, os.path.realpath(project_dir))
    return rel.replace(os.sep, "/")


def pd(rel):
    return "$PROJECT_DIR$/" + rel


def build_change_element(ch, groot, project_dir):
    kind = change_kind(ch["status"])
    new_rel = project_relpath(groot, project_dir, ch["path"])
    if kind == "added":
        attrs = f'afterPath={quoteattr(pd(new_rel))} afterDir="false"'
    elif kind == "deleted":
        attrs = f'beforePath={quoteattr(pd(new_rel))} beforeDir="false"'
    elif kind == "renamed":
        old_rel = project_relpath(groot, project_dir, ch["old_path"] or ch["path"])
        attrs = (f'beforePath={quoteattr(pd(old_rel))} beforeDir="false" '
                 f'afterPath={quoteattr(pd(new_rel))} afterDir="false"')
    else:  # modified
        attrs = (f'beforePath={quoteattr(pd(new_rel))} beforeDir="false" '
                 f'afterPath={quoteattr(pd(new_rel))} afterDir="false"')
    return f'      <change {attrs} />'


# --- existing ChangeListManager parsing (to preserve ids / default / comments) ---

LIST_OPEN_RE = re.compile(r"<list\b([^>]*)>", re.S)
ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


LIST_BLOCK_RE = re.compile(r"<list\b([^>]*)>(.*?)</list>|<list\b([^>]*)/>", re.S)
CHANGE_PATH_RE = re.compile(r'(?:after|before)Path="\$PROJECT_DIR\$/([^"]*)"')


def parse_existing_lists(block):
    """Return {name: {id, default, comment}} from an existing CLM block."""
    existing = {}
    if not block:
        return existing
    for m in LIST_OPEN_RE.finditer(block):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        name = attrs.get("name")
        if name is None:
            continue
        existing[name] = {
            "id": attrs.get("id") or str(uuid.uuid4()),
            "default": attrs.get("default", "false") == "true",
            "comment": attrs.get("comment", ""),
        }
    return existing


def parse_existing_list_files(block):
    """Return {listname: set(project_dir_relative_paths)} of files currently
    assigned to each changelist. Used by --preserve to keep manual placements
    (e.g. a 'reviewed' changelist) intact across re-runs."""
    result = {}
    if not block:
        return result
    for m in LIST_BLOCK_RE.finditer(block):
        attrs = dict(ATTR_RE.findall(m.group(1) or m.group(3) or ""))
        name = attrs.get("name")
        body = m.group(2) or ""
        if name is None:
            continue
        result.setdefault(name, set()).update(CHANGE_PATH_RE.findall(body))
    return result


CLM_RE = re.compile(
    r'[ \t]*<component name="ChangeListManager">.*?</component>\n?',
    re.S,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="path inside the target git repo")
    ap.add_argument("--mapping", required=True, help="path to mapping JSON, or - for stdin")
    ap.add_argument("--dry-run", action="store_true", help="print result, do not write")
    ap.add_argument("--preserve", default="", help="comma-separated changelist names whose "
                    "current file assignments must be kept as-is (e.g. 'reviewed'), "
                    "overriding the mapping. Protects manual sorting on re-runs.")
    args = ap.parse_args()
    preserve_names = [n.strip() for n in args.preserve.split(",") if n.strip()]

    repo = os.path.abspath(args.repo)
    groot = git_root(repo)

    idea_dir = find_idea_dir(repo)
    if not idea_dir:
        sys.exit("ERROR: no .idea directory found at or above the repo. Is this an IntelliJ project?")
    project_dir = os.path.dirname(idea_dir)
    ws_path = os.path.join(idea_dir, "workspace.xml")

    # Load mapping
    raw = sys.stdin.read() if args.mapping == "-" else open(args.mapping, encoding="utf-8").read()
    mapping = json.loads(raw)

    # Invert mapping -> path -> listname
    path_to_list = {}
    for listname, paths in mapping.items():
        for p in paths:
            path_to_list[p.replace(os.sep, "/")] = listname

    changes = parse_git_status(groot)
    if not changes:
        print("No changed files reported by git status — nothing to group.")
        return

    # Read existing workspace.xml (or start fresh)
    if os.path.exists(ws_path):
        ws_text = open(ws_path, encoding="utf-8").read()
    else:
        ws_text = '<?xml version="1.0" encoding="UTF-8"?>\n<project version="4">\n</project>\n'

    m = CLM_RE.search(ws_text)
    existing_block = m.group(0) if m else ""
    existing = parse_existing_lists(existing_block)

    # --preserve: files currently sitting in these lists stay there, no matter
    # what the mapping says (protects manual sorting like a 'reviewed' list).
    existing_files = parse_existing_list_files(existing_block) if preserve_names else {}
    preserved = {}  # project_dir-relative path -> listname
    for lname in preserve_names:
        for relp in existing_files.get(lname, set()):
            preserved[relp] = lname

    # Bucket every changed file into a changelist (unmapped -> 其他)
    buckets = {}
    unmapped = []
    preserved_hits = []
    for ch in changes:
        key = ch["path"].replace(os.sep, "/")
        proj_rel = project_relpath(groot, project_dir, ch["path"])
        if proj_rel in preserved:
            listname = preserved[proj_rel]
            preserved_hits.append((key, listname))
        else:
            listname = path_to_list.get(key)
            if listname is None:
                listname = OTHER_LIST
                unmapped.append(key)
        buckets.setdefault(listname, []).append(ch)

    # Final set of lists = all existing lists (kept, possibly empty) + every list we need
    all_names = list(dict.fromkeys(list(existing.keys()) + list(buckets.keys())))

    # Decide which list is default: keep the existing default if any, else "Changes", else first.
    default_name = next((n for n, meta in existing.items() if meta["default"]), None)
    if default_name is None:
        default_name = IDEA_DEFAULT_NAME if IDEA_DEFAULT_NAME in all_names else (all_names[0] if all_names else IDEA_DEFAULT_NAME)
        if default_name not in all_names:
            all_names.insert(0, default_name)

    # Build the new ChangeListManager block
    lines = ['  <component name="ChangeListManager">']
    for name in all_names:
        meta = existing.get(name, {"id": str(uuid.uuid4()), "comment": ""})
        is_default = (name == default_name)
        comment = meta.get("comment", "")
        open_tag = (f'    <list default="true" ' if is_default else '    <list ') + \
                   f'id={quoteattr(meta["id"])} name={quoteattr(name)} comment={quoteattr(comment)}>'
        # normalize: ensure default attr only on default
        if is_default:
            open_tag = f'    <list default="true" id={quoteattr(meta["id"])} name={quoteattr(name)} comment={quoteattr(comment)}>'
        else:
            open_tag = f'    <list id={quoteattr(meta["id"])} name={quoteattr(name)} comment={quoteattr(comment)}>'
        change_lines = [build_change_element(ch, groot, project_dir) for ch in buckets.get(name, [])]
        if change_lines:
            lines.append(open_tag)
            lines.extend(change_lines)
            lines.append("    </list>")
        else:
            # keep empty changelists self-closed (IDEA does this)
            self_close = open_tag[:-1] + " />"  # turn '...>' into '... />'
            lines.append(self_close)
    lines.append("  </component>")
    new_block = "\n".join(lines) + "\n"

    # Splice into workspace.xml
    if m:
        new_ws = ws_text[:m.start()] + new_block + ws_text[m.end():]
    else:
        # insert right after the opening <project ...> tag
        pm = re.search(r"<project\b[^>]*>\n?", ws_text)
        if not pm:
            sys.exit("ERROR: workspace.xml has no <project> root element.")
        new_ws = ws_text[:pm.end()] + new_block + ws_text[pm.end():]

    # Report
    print("Changelist grouping to apply:")
    for name in all_names:
        cnt = len(buckets.get(name, []))
        flag = "  (default)" if name == default_name else ""
        print(f"  • {name}: {cnt} file(s){flag}")
    if preserved_hits:
        print(f"\nPreserved {len(preserved_hits)} file(s) in their existing changelist (--preserve):")
        for path, lname in preserved_hits:
            print(f"    - {path}  → {lname}")
    if unmapped:
        print(f"\n{len(unmapped)} changed file(s) were not in the mapping → placed in '{OTHER_LIST}':")
        for u in unmapped:
            print(f"    - {u}")

    if args.dry_run:
        print("\n--- DRY RUN: ChangeListManager block that would be written ---")
        print(new_block)
        return

    # Backup then write
    if os.path.exists(ws_path):
        backup = ws_path + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(backup, "w", encoding="utf-8") as f:
            f.write(ws_text)
        print(f"\nBacked up original workspace.xml → {backup}")
    with open(ws_path, "w", encoding="utf-8") as f:
        f.write(new_ws)
    print(f"Wrote changelists to {ws_path}")
    print("\nNow switch to IDEA: it should show a 'Project components changed externally' "
          "notification — click Reload. (If not, do File → Reload All from Disk, or reopen the project.)")


if __name__ == "__main__":
    main()
