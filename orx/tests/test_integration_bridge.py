"""Testes de integração: exigem OpenRocket instalado + JVM (lentos).

Rodar com: pytest -m integration
"""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

CONFIG = Path(__file__).parent.parent / "config" / "default.yaml"


@pytest.fixture(scope="module")
def runner():
    from orx.config import load_config
    from orx.simulation.runner import Runner

    return Runner(load_config(CONFIG))


def test_baseline_simulation(runner):
    result = runner.evaluate({})
    assert result.ok, result.error
    assert result.metrics["apogee"] > 10
    assert result.metrics["horizontal_distance"] is not None
    assert result.metrics["stability_static"] is not None


def test_design_changes_physics(runner):
    base = runner.evaluate({})
    heavy = runner.evaluate({"ballast_mass": 50.0})
    assert heavy.ok, heavy.error
    assert heavy.metrics["liftoff_mass"] > base.metrics["liftoff_mass"] + 0.04
    assert heavy.metrics["apogee"] < base.metrics["apogee"]


def test_invalid_component_errors(runner):
    from orx.config.loader import ParameterConfig

    runner.specs["bogus"] = ParameterConfig(
        name="bogus", component="Não Existe", attribute="length", unit="m", low=0, high=1
    )
    result = runner.evaluate({"bogus": 0.5})
    assert not result.ok and "não encontrado" in result.error
    del runner.specs["bogus"]


def test_save_design_roundtrip(runner, tmp_path):
    out = tmp_path / "saved.ork"
    runner.save_design({"nose_length": 15.0}, str(out))
    doc = runner.bridge.load_document(str(out))
    nose = runner.bridge.find_component(doc, "Nose cone")
    assert abs(float(nose.getLength()) - 0.15) < 1e-9
