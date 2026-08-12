"""Aplicação de um design (dict {parâmetro: valor}) num documento OpenRocket.

Toda modificação passa pelos setters oficiais da API Java (nomes verificados
por reflexão — scripts/api_dump.txt), preservando um projeto sempre válido.

Atributos especiais:
- ``shape``          formato do cone/transição (CONICAL, OGIVE, ELLIPSOID, POWER,
                     PARABOLIC, HAACK) — Transition.setShapeType
- ``shape_parameter``  parâmetro do formato (Haack/Power) — setShapeParameter
- ``position``       deslocamento axial (setAxialOffset, mantendo o AxialMethod)
- ``position_bottom``/``position_top``/``position_absolute``  força o método axial
- ``cd``             coeficiente de arrasto de paraquedas (desliga o automático)
- ``deploy_delay`` / ``deploy_altitude`` / ``deploy_event``  configuração de ejeção
- ``override_mass``  massa forçada do componente
- ``motor``          designação do motor (tratado pelo runner, exige simulação)
- ``ejection_delay`` retardo da carga de ejeção do motor (idem)
- ``fin_count`` / demais numéricos: convertidos por snake_case -> setCamelCase
  (root_chord -> setRootChord, sweep -> setSweep, thickness -> setThickness...)
"""

from __future__ import annotations

from typing import Any

from ..bridge.orjava import J, OrBridge
from ..config.loader import ParameterConfig

# Atributos resolvidos fora deste módulo (precisam de simulação/config de voo).
MOTOR_ATTRIBUTES = {"motor", "ejection_delay"}

# Materiais construíveis (densidade em kg/m³) para o atributo bulk_material.
# Valores de referência de fabricantes; ajuste/acrescente conforme o estoque.
MATERIALS: dict[str, float] = {
    "pla": 1250.0,           # impressão 3D, 100% infill
    "petg": 1250.0,
    "poliestireno": 1050.0,  # chapa de PS
    "polietileno": 950.0,    # chapa de PE (HDPE 940-970); usado nas aletas do bit07_B
    "pet_garrafa": 1380.0,   # parede de garrafa PET
    "papel_cartao": 680.0,   # papel cartão/papelão prensado
    "balsa": 170.0,
}


def _snake_to_setter(attribute: str) -> str:
    return "set" + "".join(part.capitalize() for part in attribute.split("_"))


def _axial_method(name: str) -> Any:
    AxialMethod = J("info.openrocket.core.rocketcomponent.position.AxialMethod")
    return getattr(AxialMethod, name)


def _apply_freeform_planform(component: Any, dim: str, si_value: float) -> None:
    """Redefine o planform de um FreeformFinSet como trapézio, alterando UMA
    dimensão (root, tip, sweep ou height) e preservando as demais.

    Convenção de pontos (verificada no bit04.ork): (0,0) -> (sweep, height) ->
    (sweep+tip, height) -> (root, y_root), onde y_root acompanha a superfície
    cônica do componente-pai (slope = y_last/x_last dos pontos atuais).
    """
    pts = list(component.getFinPoints())
    xs = [float(p.x) for p in pts]
    ys = [float(p.y) for p in pts]
    top = max(ys)
    top_xs = [x for x, y in zip(xs, ys) if abs(y - top) < 1e-9]
    dims = {
        "root": xs[-1],
        "height": top,
        "sweep": min(top_xs),
        "tip": max(top_xs) - min(top_xs),
    }
    slope = (ys[-1] / xs[-1]) if abs(xs[-1]) > 1e-9 else 0.0
    dims[dim] = float(si_value)
    root, tip, sweep, height = dims["root"], dims["tip"], dims["sweep"], dims["height"]

    Coordinate = J("info.openrocket.core.util.Coordinate")
    new_pts = [
        Coordinate(0.0, 0.0, 0.0),
        Coordinate(sweep, height, 0.0),
        Coordinate(sweep + tip, height, 0.0),
        Coordinate(root, slope * root, 0.0),
    ]
    import jpype

    component.setPoints(jpype.JArray(Coordinate)(new_pts))


def _set_bulk_material(component: Any, name: str) -> None:
    name = name.lower()
    if name not in MATERIALS:
        raise ValueError(f"Material '{name}' desconhecido; opções: {sorted(MATERIALS)}")
    Material = J("info.openrocket.core.material.Material")
    MType = J("info.openrocket.core.material.Material$Type")
    component.setMaterial(Material.newMaterial(MType.BULK, f"orx_{name}", MATERIALS[name], True))


def _apply_durepox_fill(component: Any, depth_m: float, spec: ParameterConfig) -> None:
    """Lastro reprodutível: preenchimento do bico da ogiva com massa epóxi.

    O componente de massa deve ser filho da ogiva. O valor do parâmetro é a
    profundidade de preenchimento a partir da ponta; a massa é DERIVADA de
    densidade × volume interno real (perfil r(x) do próprio OpenRocket,
    descontada a espessura da parede), garantindo um lastro construível:
    "encha X cm do bico com Durepoxi".

    Modelado como uma pilha de discos finos (não um único cilindro): um
    MassComponent assume massa uniformemente distribuída ao longo do seu
    comprimento (CG no meio), o que erra a posição real do centro de massa
    de um preenchimento CÔNICO (mais massa perto da base, mais larga, do que
    perto da ponta). Com N discos, cada um no raio local da ogiva, a massa
    total e o centro de massa físico ficam corretos (verificado: erro de CG
    de ~1,5 cm com 1 cilindro vs. <0,01 cm com N=8 discos, para o bit03).

    options do parâmetro: density_g_cm3 (default 1.7).
    """
    import math

    nose = component.getParent()
    if nose is None or not hasattr(nose, "getShapeType"):
        raise ValueError(
            f"durepox_fill exige componente de massa dentro da ogiva "
            f"(pai atual: {nose.getName() if nose else None})"
        )
    density = float(spec.options.get("density_g_cm3", 1.7)) * 1000.0  # kg/m³
    wall = float(nose.getThickness())
    depth = min(float(depth_m), float(nose.getLength()) * 0.95)

    N_DISCS = 8
    AxialMethod = J("info.openrocket.core.rocketcomponent.position.AxialMethod")
    disc_len = depth / N_DISCS

    discs = [component]
    while len(discs) < N_DISCS:
        clone = component.copy()
        nose.addChild(clone)
        discs.append(clone)
    # se um design anterior deixou discos extras (nunca deveria, já que o
    # documento é recarregado do disco a cada avaliação — defensivo mesmo assim)
    for extra in discs[N_DISCS:]:
        nose.removeChild(nose.getChildPosition(extra))
    discs = discs[:N_DISCS]

    for i, disc in enumerate(discs):
        x_lo = i * disc_len
        x_mid = x_lo + disc_len / 2
        r_inner = max(float(nose.getRadius(x_mid)) - wall, 0.0)
        disc_volume = math.pi * r_inner * r_inner * disc_len
        disc.setAxialMethod(AxialMethod.TOP)
        disc.setAxialOffset(x_lo)
        disc.setLength(max(disc_len, 1e-5))
        disc.setRadius(max(r_inner, 1e-4))
        disc.setComponentMass(density * disc_volume)


def _apply_special(
    component: Any, attribute: str, si_value: Any, spec: ParameterConfig
) -> bool:
    """Aplica atributos com tratamento especial. True se tratado."""
    if attribute == "durepox_fill":
        _apply_durepox_fill(component, float(si_value), spec)
        return True
    if attribute == "bulk_material":
        _set_bulk_material(component, str(si_value))
        return True
    if attribute == "architecture_noop":
        return True  # tratado por rocket/architecture.py antes deste loop rodar
    if attribute.startswith("ff_"):
        _apply_freeform_planform(component, attribute[3:], float(si_value))
        return True
    if attribute == "shape":
        Shape = J("info.openrocket.core.rocketcomponent.Transition$Shape")
        component.setShapeType(Shape.valueOf(str(si_value).upper()))
        return True
    if attribute == "position":
        component.setAxialOffset(float(si_value))
        return True
    if attribute in ("position_bottom", "position_top", "position_absolute"):
        component.setAxialMethod(_axial_method(attribute.split("_")[1].upper()))
        component.setAxialOffset(float(si_value))
        return True
    if attribute == "cd":
        component.setCDAutomatic(False)
        component.setCD(float(si_value))
        return True
    if attribute in ("deploy_delay", "deploy_altitude", "deploy_event"):
        deploy = component.getDeploymentConfigurations().getDefault()
        if attribute == "deploy_delay":
            deploy.setDeployDelay(float(si_value))
        elif attribute == "deploy_altitude":
            deploy.setDeployAltitude(float(si_value))
        else:
            DeployEvent = J(
                "info.openrocket.core.rocketcomponent.DeploymentConfiguration$DeployEvent"
            )
            deploy.setDeployEvent(DeployEvent.valueOf(str(si_value).upper()))
        return True
    if attribute == "override_mass":
        component.setMassOverridden(True)
        component.setOverrideMass(float(si_value))
        return True
    return False


def apply_design(
    bridge: OrBridge,
    doc: Any,
    design: dict[str, Any],
    specs: dict[str, ParameterConfig],
) -> dict[str, Any]:
    """Aplica os valores do design no documento. Devolve atributos de motor
    pendentes ({param_name: (spec, valor)}) para o runner resolver com a
    simulação em mãos."""
    pending_motor: dict[str, Any] = {}
    for name, value in design.items():
        spec = specs.get(name)
        if spec is None:
            raise KeyError(f"Design contém parâmetro sem spec: {name}")
        if spec.attribute in MOTOR_ATTRIBUTES:
            pending_motor[name] = (spec, value)
            continue
        if spec.attribute.startswith("sim_"):
            continue  # opção de simulação; o runner injeta nos overrides
        si_value = spec.to_si(value)
        # glob no nome do componente aplica o valor a TODOS os que casarem
        # (ex.: as 4 aletas idênticas do bit04)
        for component in bridge.find_components(doc, spec.component):
            if _apply_special(component, spec.attribute, si_value, spec):
                continue
            setter_name = _snake_to_setter(spec.attribute)
            setter = getattr(component, setter_name, None)
            if setter is None:
                raise AttributeError(
                    f"Componente '{spec.component}' ({component.getComponentName()}) "
                    f"não tem {setter_name}(); atributo '{spec.attribute}' inválido"
                )
            if spec.integer:
                setter(int(round(float(si_value))))
            else:
                setter(float(si_value))
    return pending_motor


def read_current_values(
    bridge: OrBridge, doc: Any, specs: dict[str, ParameterConfig]
) -> dict[str, Any]:
    """Lê os valores atuais dos parâmetros (na unidade da spec) — útil como
    design de referência (baseline)."""
    from ..config.loader import UNIT_TO_SI

    out: dict[str, Any] = {}
    for name, spec in specs.items():
        if spec.attribute in MOTOR_ATTRIBUTES or spec.is_categorical and spec.attribute == "shape":
            continue
        component = bridge.find_component(doc, spec.component)
        getter_name = "get" + _snake_to_setter(spec.attribute)[3:]
        getter = getattr(component, getter_name, None)
        if getter is None:
            continue
        try:
            value = getter()
        except Exception:
            continue
        try:
            out[name] = float(value) / UNIT_TO_SI[spec.unit]
        except (TypeError, ValueError):
            out[name] = str(value)
    return out
