"""Interface de linha de comando.

    python optimize.py <comando> [--config config/default.yaml] [...]

Comandos: info, params, motors, simulate, optimize, best, compare, plot, export,
save-best.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .utils.logging import setup_logging


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optimize.py",
        description="Plataforma de otimização automática para OpenRocket",
    )
    parser.add_argument("--config", default="config/default.yaml", help="arquivo YAML")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="componentes do foguete e parâmetros configurados")
    sub.add_parser("params", help="parâmetros otimizáveis e valores atuais (baseline)")

    p = sub.add_parser("motors", help="busca motores no banco do OpenRocket")
    p.add_argument("text", help="designação ou fabricante (ex.: C6, Estes)")

    p = sub.add_parser("simulate", help="simula o baseline ou um design JSON")
    p.add_argument("--design", default="{}", help='ex.: {"fin_root_chord": 9.0}')

    p = sub.add_parser("optimize", help="roda a otimização configurada no YAML")
    p.add_argument("--algorithm", default=None, help="sobrescreve o algoritmo")
    p.add_argument("--evaluations", type=int, default=None, help="sobrescreve o orçamento")
    p.add_argument("--name", default=None, help="nome da run")

    p = sub.add_parser("best", help="melhor design de uma run")
    p.add_argument("--run", type=int, default=None)

    p = sub.add_parser("compare", help="resumo automático de uma run (ou várias)")
    p.add_argument("--run", type=int, default=None)
    p.add_argument("--runs", default=None, help="ids separados por vírgula: compara algoritmos")

    p = sub.add_parser("plot", help="gera os gráficos de uma run")
    p.add_argument("--run", type=int, default=None)

    p = sub.add_parser("export", help="exporta avaliações de uma run")
    p.add_argument("--run", type=int, default=None)
    p.add_argument("--format", default="csv", choices=["csv", "json"])

    p = sub.add_parser("save-best", help="salva .ork com o melhor design de uma run")
    p.add_argument("--run", type=int, default=None)
    p.add_argument("--out", required=True, help="caminho do .ork de saída")
    return parser


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    from .mcp.tools import Session

    if args.command == "optimize":
        # otimização usa engine direto (suporta paralelo) sem precisar de Session/JVM local
        import dataclasses

        from .config import load_config
        from .config.loader import OptimizerConfig
        from .optimizer.engine import run_optimization

        cfg = load_config(args.config)
        opt = cfg.optimizer
        if args.algorithm or args.evaluations:
            opt = OptimizerConfig(
                algorithm=args.algorithm or opt.algorithm,
                max_evaluations=args.evaluations or opt.max_evaluations,
                seed=opt.seed, profile=opt.profile,
                infeasible_penalty=opt.infeasible_penalty, options=opt.options,
            )
            cfg = dataclasses.replace(cfg, optimizer=opt)

        def progress(i: int, total: int, value: float | None, best: float | None) -> None:
            if i % max(1, total // 50) == 0 or i == total:
                shown = "erro/inviável" if value is None else f"{value:.4g}"
                best_s = f"{best:.4g}" if best is not None and best > -1e8 else "n/a"
                print(f"[{i}/{total}] valor={shown} | melhor={best_s}", flush=True)

        run_id = run_optimization(cfg, run_name=args.name, progress=progress)
        from .analysis.compare import summarize_run
        from .results.db import ResultsDB

        with ResultsDB(cfg.db_path) as db:
            print()
            print(summarize_run(db, run_id))
        print(f"\nrun_id: {run_id}")
        return 0

    session = Session(args.config)
    if args.command == "info":
        _print_json({"components": session.components(), "parameters": session.parameters()})
    elif args.command == "params":
        _print_json({"parameters": session.parameters(), "baseline": session.baseline()})
    elif args.command == "motors":
        _print_json(session.search_motors(args.text))
    elif args.command == "simulate":
        _print_json(session.simulate(json.loads(args.design)))
    elif args.command == "best":
        _print_json(session.best_design(args.run))
    elif args.command == "compare":
        if args.runs:
            print(session.compare_algorithms([int(x) for x in args.runs.split(",")]))
        else:
            print(session.compare(args.run))
    elif args.command == "plot":
        for path in session.plot(args.run):
            print(path)
    elif args.command == "export":
        print(session.export_results(args.run, args.format))
    elif args.command == "save-best":
        best = session.best_design(args.run)
        if best is None:
            print("Nenhuma run/avaliação viável no banco.", file=sys.stderr)
            return 1
        print(session.save_design(args.out, best["params"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
