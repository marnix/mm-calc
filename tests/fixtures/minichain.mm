$( Mini database for mmcalc tests: minimal class/membership fragment.
   r1, r2 and bitri are AXIOMS so tests need no logic proof. $)

$c TOPLEVEL wff setvar class |- e. <-> ( ) $.

$v x A B C ph ps ch $.
vx    $f setvar x $.
cA    $f class A $.
cB    $f class B $.
cC    $f class C $.
wph   $f wff ph $.
wps   $f wff ps $.
wch   $f wff ch $.

wcel $a wff x e. A $.
wbi  $a wff ph <-> ps $.

r1 $a |- ( x e. A <-> x e. B ) $.
r2 $a |- ( x e. B <-> x e. C ) $.

${
  bitri.1 $e |- ( ph <-> ps ) $.
  bitri.2 $e |- ( ps <-> ch ) $.
  bitri $a |- ( ph <-> ch ) $.
$}

${
  $d x A $. $d x B $. $d x C $.
  xch $p |- ( x e. A <-> x e. C ) $=
    vx cA wcel vx cB wcel vx cC wcel vx cA cB r1 vx cB cC r2 bitri $.
$}