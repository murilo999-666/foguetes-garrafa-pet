"""Constrói o .ork fiel à garrafa PET retornável REDUZIDA do bit05.

Especificações reais medidas pelo Murilo (garrafa 2L retornável reduzida):
  - diâmetro externo 9,585 cm  (raio 4,7925 cm)
  - altura total 33 cm
  - MESMO peso de uma retornável comum (~105 g)  -> parede efetiva maior
  - capacidade útil ~1,8 L
  - por ter raio menor, aguenta MAIS pressão (tensão de aro sigma = P*r/t;
    r menor -> P de ruptura maior p/ mesma parede)

Mantém o acabamento de bocal PCO-1810 (furo 21,74 mm = bocal do motor) idêntico
ao da 2L, pois o gargalo é padrão independente do corpo.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import jpype

from orx.bridge.orjava import J, OrBridge
from orx.rocket.parameters import _set_bulk_material

DONOR = r"D:\1-Competicoes\OBAFOG\foguetes\bit03 2L real\foguete_novo.ork"
OUT = r"D:\1-Competicoes\OBAFOG\foguetes\bit06 1,8L script\garrafa_bit06_base.ork"

R_OUT = 0.047925   # raio externo (Ø 9,585 cm)
WALL = 0.00072     # parede efetiva maior (mesmo peso, garrafa "encolhida")


def _get_or_add(b, doc, stage, name, cls_name, after):
    ex = [c for c in b.iter_components(doc) if str(c.getName()) == name]
    if ex:
        return ex[0]
    comp = J(cls_name)()
    comp.setName(name)
    stage.addChild(comp, jpype.JInt(int(stage.getChildPosition(after)) + 1))
    return comp


def main() -> None:
    b = OrBridge()
    doc = b.load_document(DONOR)
    doc.getRocket().setName("bit06 - Garrafa PET retornavel reduzida (~1,8L)")

    AxialMethod = J("info.openrocket.core.rocketcomponent.position.AxialMethod")
    Shape = J("info.openrocket.core.rocketcomponent.Transition$Shape")
    BT = "info.openrocket.core.rocketcomponent.BodyTube"
    MC = "info.openrocket.core.rocketcomponent.MassComponent"

    # ogiva impressa: diâmetro cheio, cobre a base (como o Murilo monta)
    nose = b.find_component(doc, "Ogiva")
    nose.setLength(0.11)
    nose.setShapeType(Shape.PARABOLIC)
    nose.setThickness(0.0012)
    nose.setAftRadius(R_OUT)
    _set_bulk_material(nose, "pla")
    stage = nose.getParent()

    # cilindro (33 cm total: cilindro ~21 + ombro 5,5 + gargalo ~2 + base sob a ogiva)
    tube = b.find_component(doc, "Tubo do corpo")
    tube.setName("Garrafa reduzida - cilindro")
    tube.setAxialMethod(AxialMethod.AFTER)
    tube.setOuterRadius(R_OUT)
    tube.setLength(0.210)
    tube.setThickness(WALL)
    _set_bulk_material(tube, "pet_garrafa")

    # base petaloide interna (sob a ogiva, dentro do cilindro): só massa
    ex_base = [c for c in b.iter_components(doc)
               if str(c.getName()) == "Garrafa reduzida - base petaloide (interna)"]
    base = ex_base[0] if ex_base else J(MC)()
    if not ex_base:
        base.setName("Garrafa reduzida - base petaloide (interna)")
        tube.addChild(base)
    base.setAxialMethod(AxialMethod.TOP)
    base.setAxialOffset(0.0)
    base.setLength(0.035)
    base.setRadius(0.042)
    base.setComponentMass(0.010)

    # ombro (aletas montam aqui)
    shoulder = b.find_component(doc, "Transição")
    shoulder.setName("Garrafa reduzida - ombro")
    shoulder.setAxialMethod(AxialMethod.AFTER)
    shoulder.setShapeType(Shape.OGIVE)
    shoulder.setForeRadius(R_OUT)
    shoulder.setAftRadius(0.01245)
    shoulder.setLength(0.052)
    shoulder.setThickness(0.0008)
    _set_bulk_material(shoulder, "pet_garrafa")

    # acabamento PCO-1810 (padrão, idêntico à 2L): pescoço-anel-rosca-lábio
    prev = shoulder
    for name, r_out, length, wall, mass in [
        ("Garrafa reduzida - pescoco", 0.01245, 0.004, 0.0016, 0.003),
        ("Garrafa reduzida - anel de suporte", 0.0165, 0.0025, 0.0057, 0.005),
        ("Garrafa reduzida - rosca", 0.0137, 0.012, 0.0028, 0.007),
        ("Garrafa reduzida - labio do bocal", 0.0125, 0.0025, 0.0016, 0.002),
    ]:
        comp = _get_or_add(b, doc, stage, name, BT, prev)
        comp.setAxialMethod(AxialMethod.AFTER)
        comp.setOuterRadius(r_out)
        comp.setLength(length)
        comp.setThickness(wall)
        _set_bulk_material(comp, "pet_garrafa")
        comp.setMassOverridden(True)
        comp.setOverrideMass(mass)
        prev = comp

    # aletas iniciais no ombro
    fins = b.find_component(doc, "Conjunto de aletas de formato livre")
    Coordinate = J("info.openrocket.core.util.Coordinate")
    pts = [Coordinate(0.0, 0.0, 0.0), Coordinate(0.06, 0.05, 0.0),
           Coordinate(0.10, 0.05, 0.0), Coordinate(0.045, -0.03, 0.0)]
    fins.setPoints(jpype.JArray(Coordinate)(pts))
    fins.setAxialMethod(AxialMethod.BOTTOM)
    fins.setAxialOffset(-0.002)
    fins.setThickness(0.0008)
    _set_bulk_material(fins, "poliestireno")

    ballast = b.find_component(doc, "Componente de massa")
    ballast.setComponentMass(0.050)

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    b.save_document(doc, OUT)
    print(f"salvo: {OUT}")

    doc2 = b.load_document(OUT)
    total = 0.0
    for c in b.iter_components(doc2):
        n = str(c.getName())
        if "Garrafa" in n:
            total += float(c.getMass())
        print(f"  {n:38s} {float(c.getMass())*1000:6.1f} g")
    print(f"  >>> garrafa reduzida vazia: {total*1000:.1f} g (alvo ~105 g)")


if __name__ == "__main__":
    main()
