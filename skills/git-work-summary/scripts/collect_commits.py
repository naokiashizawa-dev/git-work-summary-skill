"""Collect read-only Git evidence for a calendar day. Python 3.10+, Git 2.37+."""
import argparse
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


def git(repo, *args, allowed_returncodes=(0,)):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), "-c", "core.quotepath=false",
         "-c", "i18n.logOutputEncoding=utf-8", *args],
        capture_output=True,
    )
    if result.returncode not in allowed_returncodes:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout.decode("utf-8", errors="replace")


def collect(args):
    offset = None
    if args.utc_offset:
        match = re.fullmatch(r"([+-])(\d{2}):(\d{2})", args.utc_offset)
        if not match:
            raise ValueError("--utc-offset must be +/-HH:MM, e.g. +09:00")
        sign, hours, minutes = match.groups()
        if int(hours) > 23 or int(minutes) > 59:
            raise ValueError("Invalid UTC offset")
        offset = timezone(timedelta(hours=int(hours), minutes=int(minutes)) *
                          (1 if sign == "+" else -1))
    day = date.fromisoformat(args.date) if args.date else datetime.now(offset).date()
    start = datetime.combine(day, time.min, offset)
    end = datetime.combine(day + timedelta(days=1), time.min, offset)
    # Convert each boundary separately so the system timezone can cross DST.
    if offset is None:
        start, end = start.astimezone(), end.astimezone()
    root = Path(git(args.repo, "rev-parse", "--show-toplevel").strip())
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD", allowed_returncodes=(0, 1))
    ref = args.ref or "HEAD"
    try:
        resolved = git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    except RuntimeError:
        # An unborn branch has no commits; invalid user-supplied refs are errors.
        if args.ref or git(root, "rev-parse", "--is-shallow-repository").strip() == "true":
            raise
        if git(root, "show-ref", "--head", allowed_returncodes=(0, 1)):
            raise
        resolved = ""
    records = ""
    if resolved:
        records = git(root, "log", "--no-decorate", "--encoding=utf-8",
                      "--since-as-filter=" + start.isoformat(), "--until=" + end.isoformat(),
                      "--format=%H%x00%ct%x00%aI%x00%cI%x00%an%x00%s", resolved, "--")
    commits = []
    for line in filter(None, records.split("\n")):
        sha, timestamp, authored, committed, author, subject = line.split("\0", 5)
        if not start.timestamp() <= int(timestamp) < end.timestamp():
            continue
        files = git(root, "diff-tree", "--root", "--no-commit-id", "--name-only",
                    "--no-renames", "--first-parent", "-m", "-r", "-z", sha, "--")
        commits.append(dict(hash=sha, author=author, author_date=authored,
                            commit_date=committed, subject=subject,
                            changed_files=list(dict.fromkeys(filter(None, files.split("\0"))))))
    result = dict(repository=str(root), branch=branch.strip() or "detached HEAD",
                  ref=ref, resolved_ref=resolved or None, date=day.isoformat(),
                  start_inclusive=start.isoformat(), end_exclusive=end.isoformat(),
                  shallow=git(root, "rev-parse", "--is-shallow-repository").strip() == "true",
                  commit_count=len(commits), commits=commits)
    if args.include_working_tree:
        result["working_tree"] = {
            "staged": list(filter(None, git(root, "diff", "--cached", "--name-only", "-z", "--").split("\0"))),
            "unstaged": list(filter(None, git(root, "diff", "--name-only", "-z", "--").split("\0"))),
            "untracked": list(filter(None, git(root, "ls-files", "--others", "--exclude-standard", "-z", "--").split("\0"))),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today in the selected timezone")
    parser.add_argument("--utc-offset", help="Fixed offset, e.g. +09:00; defaults to system local timezone")
    parser.add_argument("--ref", help="Branch or revision; defaults to current HEAD")
    parser.add_argument("--include-working-tree", action="store_true")
    args = parser.parse_args()
    try:
        result = collect(args)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(2, str(error) + "\n")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
