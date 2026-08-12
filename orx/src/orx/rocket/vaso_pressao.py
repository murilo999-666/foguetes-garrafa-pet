"""Corpo paramétrico: o vaso de pressão vira geometria livre (não mais a
garrafa PET de catálogo), e o motor é gerado proporcionalmente a ele.

O corpo de um foguete de vinagre É o vaso de pressão — então mudar o corpo
muda o motor. Aqui o corpo é definido por diâmetro, comprimento, parede e
material; disso saem o volume interno, a pressão que ele aguenta e, via
motor_parametrico, a curva de empuxo correspondente.

Parâmetros de design reconhecidos (todos opcionais):
  body_diameter (cm), body_length (cm), body_wall (mm), body_material,
  vinegar_fill (fração 0-0.92), nozzle_diameter (mm)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..config.loader import ParameterConfig, UNIT_TO_SI
from ..utils.logging import get_logger
from .parameters import _set_bulk_material

log = get_logger("rocket.vaso")

CHAVES = {"body_diameter", "body_length", "body_wall", "body_material",
          "vinegar_fill", "nozzle_diameter"}


def eh_parametrico(design: dict[str, Any]) -> bool:
    return bool(CHAVES & set(design))


def _valor(design: dict, specs: dict, nome: str, padrao: float) -> float:
    if nome not in design:
        return padrao
    spec = specs.get(nome)
    fator = UNIT_TO_SI[spec.unit] if spec and spec.unit else 1.0
    return float(design[nome]) * fator


def remodelar_corpo(bridge, doc, design: dict[str, Any],
                    specs: dict[str, ParameterConfig]) -> dict[str, float]:
    """Aplica a geometria do vaso ao documento. Devolve dados para o motor."""
    cilindro = None
    for c in bridge.iter_components(doc):
        if "cilindro" in str(c.getName()).lower():
            cilindro = c
            break
    if cilindro is None:
        raise ValueError("corpo (cilindro) não encontrado no modelo base")

    raio = _valor(design, specs, "body_diameter", float(cilindro.getOuterRadius()) * 2) / 2
    comp = _valor(design, specs, "body_length", float(cilindro.getLength()))
    parede = _valor(design, specs, "body_wall", float(cilindro.getThickness()))
    material = str(design.get("body_material", "pet_garrafa"))

    cilindro.setOuterRadius(raio)
    cilindro.setLength(comp)
    cilindro.setThickness(parede)
    _set_bulk_material(cilindro, material)

    # a ogiva e o ombro precisam casar com o novo diâmetro
    for c in bridge.iter_components(doc):
        nome, tipo = str(c.getName()).lower(), str(c.getComponentName()).lower()
        if "ogiva" in tipo or "nose" in tipo:
            c.setAftRadius(raio)
        elif "ombro" in nome or ("transi" in tipo and "superior" not in nome):
            c.setForeRadius(raio)          # entrada do ombro = diâmetro do corpo

    v_interno = math.pi * max(raio - parede, 1e-4) ** 2 * comp
    return {"raio": raio, "parede": parede, "material": material,
            "volume": v_interno, "comprimento": comp}


def preparar_motor(design: dict[str, Any], specs: dict[str, ParameterConfig],
                   geo: dict[str, float], pasta_cache: Path):
    """Gera o .eng proporcional ao vaso. Levanta PressaoExcessiva se estourar."""
    from ..simulation.motor_parametrico import gerar_motor

    fracao = float(design.get("vinegar_fill", 0.75))
    bocal = _valor(design, specs, "nozzle_diameter", 0.02174)   # padrão: bocal PCO
    return gerar_motor(
        v_total_m3=geo["volume"], fracao_vinagre=fracao, bocal_m=bocal,
        raio_vaso_m=geo["raio"], parede_m=geo["parede"], material=geo["material"],
        pasta_cache=pasta_cache,
        diametro_mm=geo["raio"] * 2000, comprimento_mm=geo["comprimento"] * 1000,
    )
