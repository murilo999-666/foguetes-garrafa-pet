"""Constrói o .ork FIEL à garrafa PET 2L retornável (REF-PET) invertida,
incluindo as curvas reais: base petaloide, ombro, pescoço, ANEL de suporte,
ROSCA e lábio do bocal (acabamento PCO-1810).

Geometria (REF-PET 2L, pesquisa + norma PCO-1810):
  - diâmetro máximo 104 mm, altura total 342 mm, vazia ~100-105 g
  - base petaloide: centro plano ~Ø56 curvando até Ø104 em ~38 mm (a ogiva
    impressa assenta no CENTRO da base; a curva da garrafa fica exposta ao ar,
    como no foguete real do Murilo)
  - cilindro ~218 mm (parede 0,62 mm)
  - ombro ogival 104 -> 24,9 mm em ~55 mm (aletas montam aqui)
  - acabamento PCO-1810: assento Ø24,9×4, ANEL de suporte Ø33×2,5,
    ROSCA Ø27,4×12, lábio Ø25×2,5 — furo interno 21,74 mm (o bocal do motor)

Voo: garrafa invertida (bocal = tubeira, atrás; base petaloide na frente).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import jpype

from orx.bridge.orjava import J, OrBridge
from orx.rocket.parameters import _set_bulk_material

DONOR = r"D:\1-Competicoes\OBAFOG\foguetes\bit03 2L real\foguete_novo.ork"
OUT = r"D:\1-Competicoes\OBAFOG\foguetes\bit04 2L script\foguete_real\garrafa2L_base.ork"


def _get_or_add(b, doc, stage, name, cls_name, after_component):
    existing = [c for c in b.iter_components(doc) if str(c.getName()) == name]
    if existing:
        return existing[0]
    comp = J(cls_name)()
    comp.setName(name)
    stage.addChild(comp, jpype.JInt(int(stage.getChildPosition(after_component)) + 1))
    return comp


def main() -> None:
    b = OrBridge()
    doc = b.load_document(DONOR)
    rocket = doc.getRocket()
    rocket.setName("Foguete Garrafa PET 2L retornavel (fiel)")

    AxialMethod = J("info.openrocket.core.rocketcomponent.position.AxialMethod")
    Shape = J("info.openrocket.core.rocketcomponent.Transition$Shape")
    BT = "info.openrocket.core.rocketcomponent.BodyTube"
    TR = "info.openrocket.core.rocketcomponent.Transition"

    # ---------- ogiva impressa: diâmetro cheio, cobre a base (como no real) ----------
    nose = b.find_component(doc, "Ogiva")
    nose.setLength(0.12)
    nose.setShapeType(Shape.PARABOLIC)
    nose.setThickness(0.0012)
    nose.setAftRadius(0.052)
    _set_bulk_material(nose, "pla")

    stage = nose.getParent()

    # ---------- cilindro ----------
    tube = b.find_component(doc, "Tubo do corpo")
    tube.setName("Garrafa 2L - cilindro")
    tube.setAxialMethod(AxialMethod.AFTER)
    tube.setOuterRadius(0.052)
    tube.setLength(0.218)
    tube.setThickness(0.00062)         # PET 0,62 mm -> ~61 g via material
    _set_bulk_material(tube, "pet_garrafa")

    # base petaloide fica DEBAIXO da coifa (interna): só massa, sem aerodinâmica
    MassComponent = "info.openrocket.core.rocketcomponent.MassComponent"
    base_existing = [c for c in b.iter_components(doc)
                     if str(c.getName()) == "Garrafa 2L - base petaloide (interna)"]
    if base_existing:
        base = base_existing[0]
    else:
        base = J(MassComponent)()
        base.setName("Garrafa 2L - base petaloide (interna)")
        tube.addChild(base)
    base.setAxialMethod(AxialMethod.TOP)
    base.setAxialOffset(0.0)
    base.setLength(0.038)
    base.setRadius(0.045)
    base.setComponentMass(0.010)

    # ---------- ombro (aletas montam aqui) ----------
    shoulder = b.find_component(doc, "Transição")
    shoulder.setName("Garrafa 2L - ombro")
    shoulder.setAxialMethod(AxialMethod.AFTER)
    shoulder.setShapeType(Shape.OGIVE)
    shoulder.setForeRadius(0.052)
    shoulder.setAftRadius(0.01245)
    shoulder.setLength(0.055)
    shoulder.setThickness(0.0008)
    _set_bulk_material(shoulder, "pet_garrafa")

    # ---------- acabamento PCO-1810: assento -> ANEL -> ROSCA -> lábio ----------
    seat = _get_or_add(b, doc, stage, "Garrafa 2L - pescoco", BT, shoulder)
    seat.setAxialMethod(AxialMethod.AFTER)
    seat.setOuterRadius(0.01245)       # Ø24,9
    seat.setLength(0.004)
    seat.setThickness(0.0016)
    _set_bulk_material(seat, "pet_garrafa")
    seat.setMassOverridden(True)
    seat.setOverrideMass(0.003)

    ring = _get_or_add(b, doc, stage, "Garrafa 2L - anel de suporte", BT, seat)
    ring.setAxialMethod(AxialMethod.AFTER)
    ring.setOuterRadius(0.0165)        # Ø33 — o "anel" da garrafa
    ring.setLength(0.0025)
    ring.setThickness(0.0057)
    _set_bulk_material(ring, "pet_garrafa")
    ring.setMassOverridden(True)
    ring.setOverrideMass(0.005)

    thread = _get_or_add(b, doc, stage, "Garrafa 2L - rosca", BT, ring)
    thread.setAxialMethod(AxialMethod.AFTER)
    thread.setOuterRadius(0.0137)      # Ø27,4 (crista da rosca PCO-1810)
    thread.setLength(0.012)
    thread.setThickness(0.0028)
    _set_bulk_material(thread, "pet_garrafa")
    thread.setMassOverridden(True)
    thread.setOverrideMass(0.007)

    lip = _get_or_add(b, doc, stage, "Garrafa 2L - labio do bocal", BT, thread)
    lip.setAxialMethod(AxialMethod.AFTER)
    lip.setOuterRadius(0.0125)         # Ø25; furo interno 21,74
    lip.setLength(0.0025)
    lip.setThickness(0.0016)
    _set_bulk_material(lip, "pet_garrafa")
    lip.setMassOverridden(True)
    lip.setOverrideMass(0.002)

    # ---------- aletas no ombro ----------
    fins = b.find_component(doc, "Conjunto de aletas de formato livre")
    Coordinate = J("info.openrocket.core.util.Coordinate")
    pts = [
        Coordinate(0.0, 0.0, 0.0),
        Coordinate(0.06, 0.05, 0.0),
        Coordinate(0.10, 0.05, 0.0),
        Coordinate(0.045, -0.03, 0.0),
    ]
    fins.setPoints(jpype.JArray(Coordinate)(pts))
    fins.setAxialMethod(AxialMethod.BOTTOM)
    fins.setAxialOffset(-0.002)
    fins.setThickness(0.0008)
    _set_bulk_material(fins, "poliestireno")

    # ---------- lastro Durepoxi (parametrizado depois) ----------
    ballast = b.find_component(doc, "Componente de massa")
    ballast.setComponentMass(0.050)

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    b.save_document(doc, OUT)
    print(f"salvo: {OUT}")

    doc2 = b.load_document(OUT)
    total = 0.0
    comp_len = 0.0
    for c in b.iter_components(doc2):
        name = str(c.getName())
        mass = float(c.getMass())
        if "Garrafa" in name:
            total += mass
            comp_len += float(c.getLength())
        print(f"  {name:34s} {mass*1000:6.1f} g")
    print(f"  >>> garrafa: {total*1000:.1f} g | comprimento {comp_len*100:.1f} cm "
          f"(real: ~100-105 g, 34,2 cm menos a base coberta)")


if __name__ == "__main__":
    main()
