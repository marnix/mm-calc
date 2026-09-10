# mmcalc Design Document

## Overview

mmcalc implements calculational proofs for Metamath, based on the idea described in:

**Source:** https://groups.google.com/g/metamath/c/aNki7h6G50A/m/-hsjesajGAAJ

**Author:** Marnix Klooster

## Original Proposal

The calculational proof format is a favorite of mine. My vision is to have something like mmj2, but using such a calculational proof / structured derivation format:

1. A text file format for writing down calculational proofs for Metamath statements, with all "essential" information for a valid Metamath proof;
2. A tool that can read such a file, and extract the Metamath proofs from them (without built-in knowledge about set.mm or parentheses or such);
3. Interactive support for building up such calculations, by slowly growing such a file, much the same way Idris does, perhaps using LSP, so that it is relatively easy to support multiple editors.

### Example: ac9s

```
* (Ac9.1) |- A e. _V $==>
*  |- $...
    X_ x e. A B =/= (/)
        <->   { by (n0) using (bicomi) } (bitri)
        E. f f e. X_ x e. A B
        <->   { by (elixp) and (vex)
                    using (bitcomi) and (exbii) } (sylib)
        E. f ( f Fn A /\ A. x e. A ( f ` x ) e. B )
        <-    { by (ac6s4) and (Ac9.1) } (-1:impbii)
    A. x e. A B =/= (/)
        <-    { by (ixpn0) }
            X_ x e. A B =/= (/) .
```

This can automatically be expanded into a proof requiring only proof searches involving very specific named statements.

### Additional Information Needed

To make all this work without requiring arbitrary searches, some additional information about set.mm would need to be provided, e.g.:

```metamath
$( which mathematical context are we working in: $)
$[ set.mm $]
$( parsing rules: to parse ` x y z ` we construct the
   unique proof tree of ` $TOP x y z ` . $)
$c $TOP $.
```

Together with declarations that say things like:
- `<-` abbreviates `( $below -> $above )`
- `bitri`, `impbii`, `eqtrd`, etc. are transitivity rules
- `bicomi` etc. are symmetry rules
- `exbii` etc. are "windowing" (or "focusing") rules
- `3adant3` etc. are "context windowing" rules
- `simp1l` etc. are "context extraction" rules

### Background

Two background references with motivation:
- [EWD1300](https://www.cs.utexas.edu/users/EWD/transcriptions/EWD13xx/EWD1300.html)
- Back et al.'s [Teaching mathematics in high school](http://users.abo.fi/backrj/index.php?page=Teaching%20mathematics%20in%20high%20school.html) project's [Structured derivations](https://en.wikipedia.org/wiki/Structured_derivations)

## Implementation Approach

### Pipeline

```
.mmcalc file → Parser → Proof Engine → Generator → .mm file → metamath-knife verify
```

### Key Components

1. **Config** (`config.py`): Read settings files containing `$[ set.mm $]` includes
2. **Parser** (`parser.py`): Parse `.mmcalc` calculational proof format
3. **Proof Engine** (`engine.py`): Build Metamath proof trees from calculational steps
4. **Generator** (`generator.py`): Output valid `.mm` files with proof tokens
5. **Knife Wrapper** (`knife.py`): Interface to metamath-knife for verification

### Format Specification

A `.mmcalc` file contains:
- Settings references (database includes)
- Context/hypotheses
- Calculational proof steps with justifications

Each step has:
- An expression (opaque Metamath token text; no token is interpreted)
- A justification: `{ by (rule) using (other rules) }`
- Optional indexed references: `(-1:impbii)`

Nothing in the parser or engine interprets any *mathematical* token
(`|-`, `<->`, `->`, parentheses, ...): only file-syntax markers are
recognized (`$[`, `$d`, `$e`, `$p`, `$=`, `$.`, `$(`, `$}`, `${`, `$c`,
`$a`).  Expression structure is recovered exclusively through TOPLEVEL
parsing (below), using the rules in the `.settings` file.

### TOPLEVEL Parsing (Implemented)

A top-level *expression* is a statement: a typecode prefix followed by a
formula, e.g. `|- x e. A`, `wff ...`, `class ...`, `setvar x`.  Its parse
tree is the (essentially unique) proof tree of `TOPLEVEL <statement>`:
the `TOP.*` axiom for that typecode is the last step, and the formula's
grammar tree is proved underneath.

The `.settings` file therefore declares the TOPLEVEL token and one axiom
per statement type, e.g. (`examples/ac9s.settings`):

```metamath
$[ set.mm $]
$c TOPLEVEL $.
TOP.wff $a TOPLEVEL wff ph $.
TOP.set $a TOPLEVEL setvar x $.
TOP.class $a TOPLEVEL class A $.
TOP.turnstile $a TOPLEVEL |- ph $.
```

So `|- x e. A` parses (via the reference tool) to
`vx cv cA wcel TOP.turnstile`, and that label sequence is the proof of
`TOPLEVEL |- x e. A` — the parse tree, proved from `wff x e. A` (which is
proved from `class x` via `cv`, `class A`, `wcel`).

### Proof Generation Strategy

For each calculational step:
1. Parse the expression into Metamath tokens using the grammar
2. Look up the referenced theorem via metamath-knife
3. Determine substitutions by matching hypothesis expressions
4. Build the proof tree by chaining applications
5. Output uncompressed proof tokens

**Implemented (slice 1):** a calc with one relational step, where the
relation is stated by applying exactly one rule.  For a calc

```
A = B
<-> { by (dfcleq) }
A. x ( x e. A <-> x e. B )
.
```

the engine (`derive_calc_proof`) looks up `dfcleq` via the reference
tool's `show statement dfcleq /full`, which lists that statement's
mandatory hypotheses in RPN order (`vx cA cB`) and its mandatory
disjoint-variable pairs (`<x,A>`, `<x,B>`).  It verifies that the theorem
statement is a verbatim instance of the rule's conclusion, and emits the
proof tokens `vx cA cB dfcleq` plus the `$d` declarations.  The theorem
block is then generated and verified with both the reference Metamath tool
(`verify proof *`) and metamath-knife (`--verify`).

The `mmcalc generate` command derives these proof tokens automatically
when a theorem has none yet (or only a `?` placeholder).

**Implemented (slice 2):** a two-step `<->` chain joined by one
transitivity rule, e.g. for the mini-DB

```
x e. A
<-> { by (r1) } (bitri)
x e. B
<-> { by (r2) }
x e. C
.
```

with theorem `|- ( x e. A <-> x e. C )`.  The trailing `(bitri)` on a
relational step is a *join reference*: it names the rule that combines
the relational steps.  The engine looks up `bitri`'s metadata, which
lists (in RPN order) its `$f` well-formedness hypotheses (`wph wps wch`)
and its `$e` step hypotheses (`bitri.1 |- ( ph <-> ps )`,
`bitri.2 |- ( ps <-> ch )`).  It substitutes the `$f` variables by the
calc expressions in order and checks that the join rule's conclusion
matches the theorem statement and each `$e` hypothesis matches the
corresponding step rule's conclusion.  It then emits, for every `$f`
hypothesis, a well-formedness cell for the matching expression (the
TOPLEVEL parse of `typecode expr` minus the trailing `TOP.*` step), then
one step proof per relational step, then the join rule:

```
vx cA wcel vx cB wcel vx cC wcel vx cA cB r1 vx cB cC r2 bitri
```

Parser-wise, trailing `(rule)` after a `{ by ... }` block is stored as a
`join_refs` entry (with an optional numeric index for `(-1:impbii)` and
similar) and stripped from the step's expression.

**Not yet implemented:** relation chaining across more than two steps,
indexed joins, `bicomi` symmetry for backward `<-` steps, `exbii`
windowing, and generalized `using` hints — see the "Additional
Information Needed" section and the ac9s example.

## Related

- [mmj2](https://github.com/metamath/mmj2) - Java-based Metamath GUI with proof assistant
- [metamath-knife](https://github.com/metamath/metamath-knife) - Rust-based Metamath verifier
- [Metamath Proof Explorer](https://us.metamath.org/mpeuni/mmset.html)