import pytest

from orx.config.loader import ConstraintConfig, ObjectiveConfig
from orx.objectives.objective import Constraints, Objective
from orx.results.db import ResultsDB

METRICS = {"apogee": 100.0, "max_velocity": 50.0, "stability_static": 1.5,
           "horizontal_distance": 30.0, "broken": None}


def test_objective_metric_name():
    obj = Objective(ObjectiveConfig(metric="horizontal_distance", direction="maximize"))
    assert obj.value(METRICS) == 30.0
    assert obj.signed(30.0) == 30.0


def test_objective_expression_and_minimize():
    obj = Objective(ObjectiveConfig(metric="apogee - 2*max_velocity", direction="minimize"))
    assert obj.value(METRICS) == 0.0
    assert obj.signed(10.0) == -10.0


def test_objective_missing_metric():
    obj = Objective(ObjectiveConfig(metric="broken"))
    assert obj.value(METRICS) is None


def test_constraints():
    cons = Constraints((
        ConstraintConfig(metric="stability_static", min=1.0, max=3.0),
        ConstraintConfig(metric="apogee", min=200.0),
        ConstraintConfig(metric="broken", min=0.0),
    ))
    v = cons.violations(METRICS)
    assert len(v) == 2  # apogee < 200 e broken ausente
    assert not Constraints(()).violations(METRICS)


def test_db_roundtrip(tmp_path):
    db = ResultsDB(str(tmp_path / "t.sqlite"))
    run = db.create_run("teste", "random", "apogee", "maximize", "base.ork", {"k": 1})
    db.add_evaluation(run, 1, {"x": 1.0}, {"apogee": 10.0}, 10.0, True, [])
    db.add_evaluation(run, 2, {"x": 2.0}, {"apogee": 30.0}, 30.0, True, [])
    db.add_evaluation(run, 3, {"x": 3.0}, {"apogee": 99.0}, 99.0, False, ["estab"])
    db.add_evaluation(run, 4, {"x": 4.0}, None, None, False, error="boom")

    best = db.best_evaluation(run, "maximize")
    assert best is not None and best["score"] == 30.0  # inviável não conta
    assert db.count_evaluations(run) == 4

    df = db.evaluations_df(run)
    assert list(df["p_x"]) == [1.0, 2.0, 3.0, 4.0]
    assert "m_apogee" in df.columns
    db.finish_run(run)
    assert db.runs_df().iloc[-1]["status"] == "done"
    db.close()
