# TODO

Top-priority item first; the rest are the design ideas and follow-ups gathered so far,
kept so nothing is lost when a session ends.

## 1. CI: GitHub action to run tests and quality checks (DONE)
`.github/workflows/ci.yml`: a `lint` job (`ruff format --check`, `ruff check`, `mypy`)
and a `test` job (`pytest`). The tools are real runtime dependencies, not mocked:
- reference `metamath` v0.198 (latest tag): built in the action with the README gcc
  command line `gcc m*.c -o metamath -O3 -funroll-loops -finline-functions
  -fomit-frame-pointer -Wall -pedantic -DINLINE=inline`.
- `metamath-knife` v0.3.9 (latest tag): built in the action on the latest stable Rust
  via `cargo install --git https://github.com/metamath/metamath-knife --tag v0.3.9`.
- Both binaries are cached under `.ci/tools/bin` (actions/cache) so they are not
  rebuilt every run; `set.mm` is fetched from GitHub and cached keyed on its HEAD commit.

## 2. Current slice: 2-step `<->` chain (in progress)
Implement the forward two-step `<->` chain via one join rule (bitri-style), on the
self-contained mini-DB fixture (no set.mm). Tests first (RED), then implementation (GREEN),
commit both.

- RED: parser tests — trailing refs after `{ by ... }` are `join_refs`, not `rule_refs`;
  also strip plain trailing `(ref)` (not just `(-1:ref)`) from the step expression.
  Update `test_parse_step_with_indexed_rule` accordingly.
- RED: engine test — 2-step chain on the mini-DB fixture derives the exact tokens
  `vx cA wcel vx cB wcel vx cC wcel vx cA cB r1 vx cB cC r2 bitri` and `disjoint == []`.
- GREEN: parser — add `join_refs` (with optional per-ref index) to `Justification`.
- GREEN: `rule_info` — extend to `$a` (and `$p`) statements; collect mandatory `$f`/`$e`
  hypotheses in RPN order with typecodes and statement text.
- GREEN: engine — derive the chain: WFF cells (TOPLEVEL parse of `<typecode> <expr>`
  via settings, minus the trailing TOP.* label) + step proofs (rule's mandatory hyps +
  label) + join rule; pass `settings` into `derive_calc_proof`.
- Verify the generated `.mm` passes `verify proof *` (metamath) for the mini-DB chain.
- Update `design.md` (chaining slice) once GREEN lands.

## 3. N-step chain accumulation (ac9s-goal)
Generalize from 2 steps to N-step chains that *fold* intermediate results with the join
rule, matching the `myac9s`/`ac6s4` example in `examples/ac9s.mmcalc`.
Also handle multiple join refs positioned on successive relational steps
(`(bitri)`, then `(sylib)`, then `(-1:impbii)` in ac9s).

## 4. `<-` backward steps / symmetry
Support backward relational steps via symmetry rules (`bicomi`, `impbii`); the engine
needs a window/symmetry story. Deferred by the chosen slice-2 scope.

## 5. Indexed join references
Define semantics for `(-1:impbii)`: combine with the result of the step `-1` back
(i.e. the current chain so far). Currently only parsed, not interpreted.

## 6. Step-rule "/join" verification in the engine
Ideally the engine checks that each step rule's conclusion is an instance of the
join rule's `$e` hypothesis (substitution-aware), not just that the calc expressions
appear verbatim in the theorem statement. Decide how far to go; the definitive check is
the reference tool's own `verify proof *` on the generated file.

## Maintenance / infrastructure
- Keep long-lived scratch artifacts out of `/tmp` (transient): persisted development
  mini-DBs live under `devonly/` (git-ignored). Verified mini-DB: `devonly/minichain.mm`.
- Test fixtures that should be committed (self-contained, no set.mm) live under
  `tests/fixtures/` (`minichain.mm`, `minichain.settings`).
- `metamath` and `metamath-knife` are real runtime dependencies, both invoked by bare
  name from PATH (`MM_TOOL` env allows overriding `metamath`). Do not hard-code paths.