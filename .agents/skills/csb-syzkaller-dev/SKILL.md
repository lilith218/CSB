---
name: csb-syzkaller-dev
description: "Use when developing or debugging CSB's deps/syzkaller fork or bm-generator internals: trace parsing, syzlang serialization/extraction, prog2c CSB header generation, generated benchmark metadata, Go tooling/tests, or generator templates. For operating the generation pipeline without changing internals, use the generator docs or csb-syzkaller when available."
---

# CSB Syzkaller Development

Use this skill for implementation work in `deps/syzkaller` and CSB
`bm-generator/`. Keep stable architecture, workflow, and command details in the
project docs instead of repeating them here.

## Compose With

- Project docs first: `doc/bm-generator.md` for generator workflow, CSB
  syzkaller fork areas, build commands, focused Go tests, selection, and
  excluded syscalls; `doc/development.md` for repository discipline, common
  syzkaller change patterns, and style.
- `csb-syzkaller` for operating the generator pipeline or refreshing generated
  headers/configs without changing internals, when that skill is available.
- `csb-dev` for CSB runner/framework changes outside `bm-generator/` and
  `deps/syzkaller`, when that skill is available.
- `csb` or `csb-remote` for benchmark runtime validation, monitor setup, and
  host-dependent reproduction.

## First Checks

From the CSB root:

```bash
git status --short
git -C deps/syzkaller status --short
sed -n '1,260p' doc/bm-generator.md
sed -n '88,118p' doc/development.md
```

Then inspect only task-relevant generator or syzkaller code:

```bash
rg '<term>' bm-generator deps/syzkaller/tools/syz-trace2syz deps/syzkaller/tools/syz-extraction deps/syzkaller/tools/syz-prog2c deps/syzkaller/prog deps/syzkaller/pkg/csource
```

Treat `deps/syzkaller` as its own repository/submodule: check status, history,
diffs, tests, and generated binaries inside it with `git -C deps/syzkaller ...`.
Do not mix its changes with the CSB root repository.

## Development Guardrails

- Follow the syzkaller-specific change patterns in `doc/development.md` and the
  fork map in `doc/bm-generator.md`.
- Parser/proggen changes need Go tests and regenerated parser artifacts when the
  grammar requires it.
- Extraction changes should preserve deterministic ordering, dependency
  preservation, poll filtering, minimum-size behavior, and network split
  behavior.
- `prog2c`/`csource` changes need generated-header inspection for sanitized
  paths, sockets, buffers, file descriptor cleanup/leak handling, metadata, and
  trace output.
- Template or metadata changes should regenerate the smallest affected
  generated set and validate JSON/header name alignment.
- Do not delete or regenerate generated outputs unless the user asks, or unless
  regeneration is the explicit validation for the change. Generated artifacts
  are often untracked in this checkout.

## Validation

Use the build and focused Go test commands in `doc/bm-generator.md`. If Go,
tool caches, generated parser files, syzkaller tool builds, or host permissions
fail, report the exact requirement. For generated benchmark runtime failures,
separate parser, extraction, header generation, config generation, and CSB
runner layers before changing code.
