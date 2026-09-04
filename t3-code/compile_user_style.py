#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Compile a plain CSS file into a Stylus-importable user style.

Default output is UserCSS (``*.user.css``): a ``==UserStyle==`` metadata block
followed by the CSS wrapped in ``@-moz-document url-prefix(...)``.  This is the
format Stylus installs from a URL / the editor and the one userstyles.world
accepts.  ``--format json`` emits a Stylus backup file for Manage → Import.

Example::

    uv run compile_user_style.py t3-user-style.css -o t3-user-style.user.css
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from textwrap import dedent

DEFAULTS = {
    "name": "T3 Code – boxed responses & muted work rows",
    "namespace": "github.com/akaihola",
    "version": "1.0.1",
    "description": (
        "T3 Code web client: boxed assistant responses with sectioned code blocks, "
        "one muted colour for tool-call work sequences, dimmed monospace tool "
        "parameters, no divider on folded turns."
    ),
    "author": "Antti Kaihola",
    "license": "MIT",
    "url_prefix": [
        "http://gogo:3773/",
        "http://gogo.crane-boa.ts.net:3773/",
        "https://app.t3.codes/",
    ],
}
WEBKIT_RE = re.compile(r"::?-webkit-\w+")
# Comments and strings, so braces inside them are not counted.
OPAQUE_RE = re.compile(
    r"/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'", re.DOTALL
)


def check_css(css: str, source: str) -> None:
    """Abort on unbalanced braces (they would break the @-moz-document wrapper);
    warn about WebKit-only selectors that Firefox ignores."""
    stripped = OPAQUE_RE.sub("", css)
    depth = 0
    for lineno, line in enumerate(stripped.splitlines(), 1):
        for char in line:
            depth += {"{": 1, "}": -1}.get(char, 0)
            if depth < 0:
                sys.exit(f"{source}:{lineno}: unexpected '}}'")
    if depth:
        sys.exit(f"{source}: {depth} unclosed '{{'")
    if "/*" in stripped:
        sys.exit(f"{source}: unterminated comment")
    for lineno, line in enumerate(css.splitlines(), 1):
        if WEBKIT_RE.search(line):
            print(
                f"{source}:{lineno}: warning: WebKit-only selector, ignored by Firefox",
                file=sys.stderr,
            )


def usercss(css: str, opts: argparse.Namespace) -> str:
    meta = [
        ("name", opts.name),
        ("namespace", opts.namespace),
        ("version", opts.version),
        ("description", opts.description),
        ("author", opts.author),
        ("license", opts.license),
        ("homepageURL", opts.homepage),
        ("supportURL", opts.support),
        ("updateURL", opts.update_url),
    ]
    header = "\n".join(f"@{key:<15}{value}" for key, value in meta if value)
    scope = ", ".join(f'url-prefix("{prefix}")' for prefix in opts.url_prefix)
    body = "\n".join(f"  {line}" if line else "" for line in css.rstrip().splitlines())
    return dedent(
        """\
        /* ==UserStyle==
        {header}
        ==/UserStyle== */

        @-moz-document {scope} {{
        {body}
        }}
        """
    ).format(header=header, scope=scope, body=body)


def stylus_json(css: str, opts: argparse.Namespace) -> str:
    style = {
        "enabled": True,
        "name": opts.name,
        "sections": [{"code": css, "urlPrefixes": opts.url_prefix}],
    }
    return json.dumps([style], indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("css", type=Path, help="plain CSS input file")
    parser.add_argument(
        "-o", "--output", type=Path, help="output file (default: stdout)"
    )
    parser.add_argument("--format", choices=["usercss", "json"], default="usercss")
    for key in ("name", "namespace", "version", "description", "author", "license"):
        parser.add_argument(f"--{key}", default=DEFAULTS[key])
    parser.add_argument("--homepage", help="@homepageURL")
    parser.add_argument("--support", help="@supportURL")
    parser.add_argument(
        "--update-url", help="@updateURL (raw URL of the published .user.css)"
    )
    parser.add_argument(
        "--url-prefix",
        action="append",
        help=f"origin the style applies to; repeatable (default: {' '.join(DEFAULTS['url_prefix'])})",
    )
    opts = parser.parse_args()
    opts.url_prefix = opts.url_prefix or DEFAULTS["url_prefix"]

    css = opts.css.read_text(encoding="utf-8")
    check_css(css, str(opts.css))
    out = (usercss if opts.format == "usercss" else stylus_json)(css, opts)
    if opts.output:
        opts.output.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
