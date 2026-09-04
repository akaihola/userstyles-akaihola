# T3 Code user style — working notes

Goal: customize the thread appearance of the T3 Code web client **without modifying
T3 Code**, ending in a Firefox **Stylus** user style. We tune the CSS live in a Chromium
instance over CDP, then compile the result for Stylus.

This file is a local working note (untracked). Per `AGENTS.md` it should not be committed.

## Why Stylus, not a userscript

- Colors alone: T3 Code already has a theme editor (Settings → Theme, stored in
  `localStorage` key `t3code:themes:v1`) that drives the CSS variables. Use it first.
- Layout/typography/dimming/hiding: CSS-only, so a styling extension. Stylus applies
  before first paint, survives SPA navigation, scopes per origin.
- Userscripts would have to fight React re-renders of the virtualized timeline with a
  `MutationObserver`. Avoid unless the DOM itself must change.
- Firefox extensions do not load in the Electron desktop app; this targets the web client
  (`npx t3` / app.t3.codes) in Firefox.

## Live-tuning setup

Chromium runs on `akaihola@atom`, the agent on `agent@gogo`.

- Chromium's `--remote-debugging-port=9222` binds `127.0.0.1` only;
  `--remote-debugging-address=…` was not honored by the headful build, and
  `agent@gogo` has no SSH key for `akaihola@atom`.
- Working solution: reverse tunnel from atom: `ssh -N -R 9222:127.0.0.1:9222 agent@gogo`.
  The agent then talks to `http://127.0.0.1:9222` on gogo. (Sandboxed shell commands get
  "Bad Gateway" from the sandbox proxy; CDP calls run with the sandbox disabled.)
- Tab under test: `http://gogo:3773/<projectId>/<threadId>` (title "T3 Code (Alpha)").

Helper: `/tmp/claude/t3-style/cdp.py` (run with `uv run --with websocket-client cdp.py …`,
cwd `/tmp/claude/t3-style`). It finds the tab by title and:

| command              | effect                                                                 |
| -------------------- | ---------------------------------------------------------------------- |
| `push <file.css>`    | create/overwrite `<style id="t3-user-style">` in `<head>` (no reload) |
| `shot <out.png>`     | `Page.captureScreenshot` of the tab                                    |
| `eval '<js>'`        | `Runtime.evaluate`, JSON value back                                    |
| `clear`              | remove the injected style                                              |

Working stylesheet: `/tmp/claude/t3-style/t3-user-style.css` (current contents mirrored
below). Screenshots: `baseline.png`, `iterN.png` in the same directory.

Loop: edit CSS → `push` → `eval` computed colors on the rows in question → `shot` → the
user checks by eye in Chromium → adjust.

## What the DOM offers (stable hooks)

From `apps/web/src/components/chat/MessagesTimeline.tsx`:

```
[data-timeline-root]                      thread column (max-w-3xl)
[data-timeline-row-kind="message"]        + [data-message-role="user"|"assistant"], [data-message-id]
[data-timeline-row-kind="work"]           grouped tool calls
[data-timeline-row-kind="work-live"]      currently running tool
[data-timeline-row-kind="work-toggle"]    "+N previous tool calls" / "Show fewer tool calls"
[data-timeline-row-kind="working"]        "Working for Ns" spinner row
[data-timeline-row-kind="turn-fold"]      "Worked for Ns" fold
[data-timeline-row-kind="turn-plan"], [data-timeline-row-kind="proposed-plan"]
.chat-markdown                            markdown body of a message
```

Tailwind utility classes are not stable; prefer the `data-*` hooks and CSS variables.

## Cascade facts that matter

- The web app is Tailwind v4 (`@import "tailwindcss"`): utilities live in the `utilities`
  cascade layer, so unlayered injected CSS wins without `!important`.
- **Live build vs. source checkout differ.** The build served on `gogo:3773` compiles
  `text-foreground` to `color: var(--foreground)`, `text-message-foreground` to
  `var(--message-foreground)`, `text-destructive` to `var(--destructive)`, etc. The current
  source (`apps/web/src/index.css`, `@theme inline`) routes them through
  `var(--contrast-foreground)` / `var(--contrast-message-foreground)` computed on `:root`.
  The style sets **both** so it keeps working after an upgrade.
- Overriding a variable with a `color-mix()` of itself on the same element is a cycle
  (invalid). Compute the mixed values on an ancestor (`[data-timeline-root]`) into
  `--tweak-*` variables, then assign those on the rows.
- Measured dark-theme values: `--foreground #fffaff`, `--muted-foreground #8d8f97`,
  `--destructive #fb414a`, `--error-foreground #ff6467`, `--warning #fe9a00`. Assistant
  markdown renders as `oklab(0.99 … / 0.8)` (white at 80 % alpha).

## Tweaks so far

### 1. Work sequences use one muted color

Request: the assistant response immediately leading into a tool call and everything in
the work rows should use the same muted color as command summaries and "Worked for Ns".

Finding: command summaries and "Worked for Ns" already use `#8d8f97`. Virtualization
wraps every timeline row twice, so the leading assistant response must be matched through
the adjacent outer row wrappers rather than direct `message + work` sibling selection.

Current rule:

```css
[data-timeline-row-kind="work"],
[data-timeline-row-kind="work-live"],
[data-timeline-row-kind="work-toggle"],
[data-timeline-row-kind="working"] {
  --foreground: var(--muted-foreground);
  --message-foreground: var(--muted-foreground);
  --code-foreground: var(--muted-foreground);
  --destructive: var(--muted-foreground);
  --error-foreground: var(--muted-foreground);
  --warning: var(--muted-foreground);
  --contrast-foreground: var(--muted-foreground);
  --contrast-message-foreground: var(--muted-foreground);
}

/* Direct color rules make every text tier equal, including the adjacent
   assistant response and elements with their own color utility. */
:is([data-timeline-row-kind="work"], [data-timeline-row-kind="work-live"], [data-timeline-row-kind="work-toggle"], [data-timeline-row-kind="working"]),
:is([data-timeline-row-kind="work"], [data-timeline-row-kind="work-live"], [data-timeline-row-kind="work-toggle"], [data-timeline-row-kind="working"]) *,
*:has(> [data-timeline-root] > [data-timeline-row-kind="message"][data-message-role="assistant"]):has(+ * > [data-timeline-root] > [data-timeline-row-kind^="work"]) [data-timeline-row-kind="message"][data-message-role="assistant"],
*:has(> [data-timeline-root] > [data-timeline-row-kind="message"][data-message-role="assistant"]):has(+ * > [data-timeline-root] > [data-timeline-row-kind^="work"]) [data-timeline-row-kind="message"][data-message-role="assistant"] * {
  color: var(--muted-foreground);
}
```

Status: unified muted-color rule injected; awaiting visual verdict.

## Stylus packaging (done)

- `t3-user-style.user.css` — UserCSS: `==UserStyle==` metadata block + the CSS wrapped in
  `@-moz-document` for `http://gogo:3773/`, `http://gogo.crane-boa.ts.net:3773/`, and
  `https://app.t3.codes/`.
  Install: Stylus → Manage → tick "as UserCSS" → "Write new style" → paste → Ctrl+S, or
  open the file's `file://` / raw-GitHub URL and click "Install style".
- `compile_user_style.py` — stdlib-only `uv run` script regenerating the above from
  `t3-user-style.css` (`--format json` gives a Manage → Import backup; `--url-prefix`,
  `--version`, `--license`, `--update-url` … override the metadata). Checks brace balance
  and warns on `::-webkit-*` selectors. Output is byte-identical to the hand conversion.
- Scope lives in `@-moz-document`, not in Stylus's "Applies to" UI; add origins with
  `--url-prefix` (for publishing, drop the private `gogo` origin).
- Firefox checks: no `::-webkit-*` selectors, standard `scrollbar-*` only; needs Firefox
  ≥ 121 (`:has()`, `color-mix()`). Verify light and dark themes.
