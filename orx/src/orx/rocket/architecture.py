"""Arquitetura livre do corpo: ADICIONAR um segmento de garrafa PET à frente
do corpo fixo, sem alterar nada do que já existe.

"Tubo do corpo" e "Transição" (o bico/ombro da garrafa) NÃO são tocados —
eles SÃO a garrafa PET 2L retornável real, usada como vaso de pressão/motor
(reprodutível por definição: é a garrafa física que a equipe já usa). A
única liberdade é adicionar um segmento adicional de garrafa (com seu
próprio acoplador impresso) à frente desse corpo fixo — nunca modificá-lo.

Catálogo de tamanhos para o segmento ADICIONADO (medidas típicas de mercado
brasileiro — "reprodutível" numa garrafa significa "existe pra comprar", não
uma dimensão contínua qualquer):
"""

from __future__ import annotations

from typing import Any

from ..config.loader import ParameterConfig, UNIT_TO_SI
from ..utils.logging import get_logger
from .parameters import MATERIALS, _set_bulk_material

log = get_logger("rocket.architecture")

PET_BOTTLES: dict[str, dict[str, float]] = {
    "500ml": {"outer_diameter_m": 0.060, "length_m": 0.220, "wall_thickness_m": 0.00025},
    "600ml": {"outer_diameter_m": 0.0695, "length_m": 0.2366, "wall_thickness_m": 0.00025},
    "1.5L": {"outer_diameter_m": 0.089, "length_m": 0.338, "wall_thickness_m": 0.00025},
    "2L": {"outer_diameter_m": 0.090, "length_m": 0.330, "wall_thickness_m": 0.00025},
}

FWD_TUBE_NAME = "Tubo do corpo 2"
COUPLER_NAME = "Transição superior"


def apply_architecture(
    bridge: Any, doc: Any, design: dict[str, Any], specs: dict[str, ParameterConfig]
) -> None:
    """Restrutura a árvore ANTES do apply_design normal rodar.

    Lê (se presentes no design): extra_bottle (0|1), bottle_fwd (chave de
    PET_BOTTLES, só usada se extra_bottle==1), coupler_length, coupler_material.

    "Tubo do corpo" e "Transição" nunca são modificados — apenas lidos (para
    casar o raio do acoplador com o corpo fixo existente). Se extra_bottle==1,
    adiciona "Tubo do corpo 2" (novo segmento) + "Transição superior"
    (acoplador impresso) à frente do corpo fixo; caso contrário, remove-os
    se existirem (nunca deveria, já que o documento é recarregado do disco a
    cada avaliação — defensivo mesmo assim).
    """
    if "extra_bottle" not in design:
        return  # config sem arquitetura livre (ex.: bit03.yaml antigo)

    from ..bridge.orjava import J

    nose = bridge.find_component(doc, "Ogiva")
    stage = nose.getParent()
    tube_aft = bridge.find_component(doc, "Tubo do corpo")  # FIXO — nunca alterado

    existing_fwd = [c for c in bridge.iter_components(doc) if str(c.getName()) == FWD_TUBE_NAME]
    existing_coupler = [c for c in bridge.iter_components(doc) if str(c.getName()) == COUPLER_NAME]

    if int(design["extra_bottle"]) == 1:
        aft_radius = float(tube_aft.getOuterRadius())  # lido, não escrito
        fwd = PET_BOTTLES[str(design["bottle_fwd"])]
        coupler_spec = specs.get("coupler_length")
        coupler_len = (
            float(design.get("coupler_length", 3.0)) * UNIT_TO_SI[coupler_spec.unit]
            if coupler_spec
            else 0.03
        )
        coupler_mat = str(design.get("coupler_material", "pla"))
        AxialMethod = J("info.openrocket.core.rocketcomponent.position.AxialMethod")

        if existing_fwd:
            tube_fwd = existing_fwd[0]
        else:
            BodyTube = J("info.openrocket.core.rocketcomponent.BodyTube")
            tube_fwd = BodyTube()
            tube_fwd.setName(FWD_TUBE_NAME)
            stage.addChild(tube_fwd, stage.getChildPosition(tube_aft))

        if existing_coupler:
            coupler = existing_coupler[0]
        else:
            Transition = J("info.openrocket.core.rocketcomponent.Transition")
            coupler = Transition()
            coupler.setName(COUPLER_NAME)
            stage.addChild(coupler, stage.getChildPosition(tube_aft))

        tube_fwd.setAxialMethod(AxialMethod.AFTER)
        tube_fwd.setOuterRadius(fwd["outer_diameter_m"] / 2)
        tube_fwd.setLength(fwd["length_m"])
        tube_fwd.setThickness(fwd["wall_thickness_m"])
        _set_bulk_material(tube_fwd, "pet_garrafa")

        coupler.setAxialMethod(AxialMethod.AFTER)
        coupler.setForeRadius(fwd["outer_diameter_m"] / 2)
        coupler.setAftRadius(aft_radius)  # casa com o corpo fixo, sem alterá-lo
        coupler.setLength(max(coupler_len, 0.005))
        _set_bulk_material(coupler, coupler_mat if coupler_mat in MATERIALS else "pla")
    else:
        for extra in existing_fwd + existing_coupler:
            stage.removeChild(stage.getChildPosition(extra))
