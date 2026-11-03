"""Use compact mathematical identifiers in all distributed example notebooks."""
import re
from backend.syntax import TOKEN, parse
from backend.units import unit_text, parse_unit

SUBSCRIPTS = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
WORDS = '''acceleration angular angularMomentum atRest axial axis best balls bottom bound bounds branches candidate center certificates charge closest coefficient coils com contributions coords critical criticalFourth crossSection current delta densities dipoleField discriminant distance duration effective emf energy energySpatial eps epsilon equations eta f8 field flux force freeFall functions gap gaps gravity h1 h2 heights induced initial initialAcceleration ionField kineticSpatial kummer levels length ll magnetic mass momentum momentumSpatial motion motions nextBottom nn normalized normalizedClosest normalization nr pairs parameter phi planar planarMasses planarStart planarVelocity poly positions potential potentialSpatial principal quadratic quadraticPosition quantization radial radialForce radialHyper radius radius3 rec regular relative res residual residuals residues rest rho rn row rules scores sign signs singleField small solid spatial spatialMasses spatialStart spatialVelocity speedDrifts speeds2 spherical spring spring1 spring2 square start starts state states stiffness sweptArea tau theta timeScale total toFunctions turning turningEquation u1 u2 uniform ux uy values velocities vx vy winners x1 x2 x3 y1 y2 y3 y4 y5 a1 a2 a3 a4 a5 b0 c4 t0 v0 alpha ell mu angle1 angle2'''.split()
OVERRIDES = {
    'mass': 'm', 'gravity': 'g', 'length': 'l', 'spring': 'k',
    'alpha': 'α', 'delta': 'δ', 'eps': 'ε', 'epsilon': 'ε', 'eta': 'η',
    'theta': 'θ', 'phi': 'φ', 'rho': 'ρ', 'tau': 'τ', 'ell': 'ℓ', 'mu': 'μ',
    'energy': 'H', 'energySpatial': 'H₁', 'potential': 'U', 'potentialSpatial': 'U₁',
    'sweptArea': 'S₁', 'flux': 'Φ', 'emf': 'ε₁', 'current': 'j₀', 'force': 'F', 'res': 'R', 'values': 'q₀',
    'coords': 'q₁', 'functions': 'q₂', 'equations': 'e₁', 'initial': 'c₀',
    'rest': 'r₀', 'stiffness': 'K', 'small': 'u₀', 'start': 'x₀',
    'positions': 'p₀', 'velocities': 'v₄', 'momentum': 'p₁', 'momentumSpatial': 'p₂', 'angular': 'L',
    'relative': 'r₃', 'heights': 'h₀', 'spring1': 'k₁', 'spring2': 'k₂',
    'timeScale': 'τ₀', 'coefficient': 'c', 'spherical': 'Y', 'regular': 'u₀',
    'quantization': 'n₀', 'principal': 'n₁', 'radius3': 'r₀', 'rn': 'R₁', 'densities': 'p₁',
    'motion': 'r₁', 'quadratic': 'v₃', 'quadraticPosition': 'r₂',
    'vx': 'v₁', 'vy': 'v₂', 'ux': 'u₁', 'uy': 'u₂',
    'field': 'B₁', 'b0': 'B₀', 'c4': 'C₄', 'angle1': 'θ₁', 'angle2': 'θ₂',
}
SYMBOLS = dict(OVERRIDES)
used = set(SYMBOLS.values())
for word in sorted(set(WORDS)):
    if word in SYMBOLS:
        continue
    if re.fullmatch(r'[a-z]\d+', word):
        candidate = word[0]+word[1:].translate(SUBSCRIPTS)
    else:
        index = 1
        while word[0]+str(index).translate(SUBSCRIPTS) in used:
            index += 1
        candidate = word[0]+str(index).translate(SUBSCRIPTS)
    if candidate in used:
        index = 1
        while word[0]+str(index).translate(SUBSCRIPTS) in used:
            index += 1
        candidate = word[0]+str(index).translate(SUBSCRIPTS)
    SYMBOLS[word] = candidate
    used.add(candidate)


def compact_source(source):
    def replace(match):
        token = match.group()
        if token.startswith('"'):
            return re.sub(r'\b(?:[A-Za-z]\d+|theta|phi|rho|eta|ell|eps|nr)\b', lambda m: SYMBOLS.get(m.group(), m.group()), token)
        return SYMBOLS.get(token, token)
    return TOKEN.sub(replace, source)


def compact_notebook(notebook):
    originals = set()
    def collect(node):
        if node.kind == 'symbol':
            originals.add(node.value)
        if node.kind == 'call' and len(node.args) == 2 and node.args[0].kind in ('number', 'group', 'call'):
            try:
                parse_unit(unit_text(node.args[1]))
            except Exception:
                pass
            else:
                collect(node.args[0])
                return
        for child in node.args:
            collect(child)
    for cell in notebook['cells']:
        if cell['mode'] != 'markdown':
            collect(parse(cell['code']))
    renamed = {}
    for original in originals:
        target = SYMBOLS.get(original, original)
        if target in renamed and renamed[target] != original:
            raise ValueError(f"Duplicate example symbol {target}: {renamed[target]}, {original} in {notebook['title']}")
        renamed[target] = original
    for cell in notebook['cells']:
        if cell['mode'] == 'markdown':
            cell['code'] = re.sub(r'\b[A-Za-z][A-Za-z0-9]*\b', lambda m: SYMBOLS.get(m.group(), m.group()), cell['code'])
        else:
            cell['code'] = compact_source(cell['code'])
    return notebook
