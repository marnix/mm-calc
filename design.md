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
TOP.wff $a $TOP wff ph $.
TOP.turnstile $a $TOP |- ph $.
TOP.set $a $TOP set x $.
TOP.class $a $TOP class x $.
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
- An expression
- A justification: `{ by (rule) using (other rules) }`
- Optional indexed references: `(-1:impbii)`

### Proof Generation Strategy

For each calculational step:
1. Parse the expression into Metamath tokens using the grammar
2. Look up the referenced theorem via metamath-knife
3. Determine substitutions by matching hypothesis expressions
4. Build the proof tree by chaining applications
5. Output compressed proof tokens

## Related

- [mmj2](https://github.com/metamath/mmj2) - Java-based Metamath GUI with proof assistant
- [metamath-knife](https://github.com/metamath/metamath-knife) - Rust-based Metamath verifier
- [Metamath Proof Explorer](https://us.metamath.org/mpeuni/mmset.html)
