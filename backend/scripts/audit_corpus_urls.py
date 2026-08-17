"""Check the bundled corpus citations against their live documentation URLs."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from e3sm_assist.ingest import load_corpus


def main() -> int:
    """Print failing corpus URLs and return a nonzero exit status when any are unreachable."""
    failures: list[str] = []
    checked: set[str] = set()
    for entry in load_corpus():
        url = str(entry.url)
        if url in checked:
            continue
        checked.add(url)
        request = Request(url, headers={"User-Agent": "e3sm-assist-link-audit"})
        try:
            with urlopen(request, timeout=20) as response:  # noqa: S310
                if 200 <= response.status < 400:
                    continue
                failures.append(f"{response.status} {url}")
        except HTTPError as error:
            failures.append(f"{error.code} {url}")
        except URLError as error:
            failures.append(f"unreachable {url}: {error.reason}")

    if failures:
        print("Broken corpus URLs:")
        print("\n".join(failures))
        return 1

    print(f"All {len(checked)} corpus URLs are reachable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
