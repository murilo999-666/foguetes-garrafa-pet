"""Painel ao vivo do progresso das simulações — barra, números e ETA.

Lê o banco SQLite e o log em modo SOMENTE LEITURA: não interfere no processo.
Se o banco estiver corrompido, cai no snapshot orx_RESGATE.sqlite e no log.

Uso:
  python scripts/acompanhar.py            painel do LABORATÓRIO (500 mil)
  python scripts/acompanhar.py bit04      painel da reotimização do bit04
  python scripts/acompanhar.py lab --uma-vez    mostra uma vez e sai
"""

import io
import sqlite3
import sys
import time
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RAIZ = Path(__file__).parent.parent
OBAFOG = Path(r"D:\1-Competicoes\OBAFOG")

# preset -> (título, log, banco, meta_total, fases_ou_None)
PRESETS = {
    "lab": (
        "LABORATÓRIO — 500 mil simulações",
        RAIZ / "results/lab500k.log",
        OBAFOG / "_laboratorio testes livres/simulacoes/orx.sqlite",
        500_000,
        [("random", 150_000), ("adaptive", 175_000),
         ("genetic", 125_000), ("optuna", 50_000)],
    ),
    "bit04": (
        "BIT04 — caça 3 aletas SEM cant (alvo >380 m)",
        RAIZ / "results/bit04_3aletas.log",
        OBAFOG / "bit04 2L script/foguete_real/otimizacao_aletas/orx.sqlite",
        60_000,   # 5 blocos de 12 mil
        [("b1", 12_000), ("b2", 12_000), ("b3", 12_000),
         ("b4", 12_000), ("b5", 12_000)],
    ),
    "construivel": (
        "LABORATÓRIO CONSTRUÍVEL — corpo livre, limites reais (massa <=4kg)",
        RAIZ / "results/lab_construivel.log",
        OBAFOG / "_laboratorio construivel/simulacoes/orx.sqlite",
        105_000,
        [("random", 40_000), ("adaptive", 40_000), ("genetic", 25_000)],
    ),
    "fog2": (
        "FOGUETE 2 — garantia, motor fixo 1,2 L (o vinagre que sobra)",
        RAIZ / "results/foguete2.log",
        OBAFOG / "_foguete2_garantia/orx.sqlite",
        24_000,   # random 8k + adaptive 16k
        [("random", 8_000), ("adaptive", 16_000)],
    ),
}

VERDE, AMAR, CINZA, NEGRITO, FIM = "\033[92m", "\033[93m", "\033[90m", "\033[1m", "\033[0m"


def barra(fracao: float, largura: int = 44, cor: str = VERDE) -> str:
    cheio = int(round(max(0.0, min(fracao, 1.0)) * largura))
    return f"{cor}{'█' * cheio}{CINZA}{'░' * (largura - cheio)}{FIM}"


def ler_banco(banco: Path):
    """Total, viáveis e melhor — best-effort, com fallback ao resgate."""
    resgate = banco.with_name("orx_RESGATE.sqlite")
    for alvo in (banco, resgate):
        if not alvo.exists():
            continue
        try:
            con = sqlite3.connect(f"file:{alvo}?mode=ro", uri=True, timeout=5)
            try:
                total = con.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
                viaveis, melhor = con.execute(
                    "SELECT COUNT(*), MAX(score) FROM evaluations WHERE feasible=1").fetchone()
                runs = con.execute(
                    "SELECT name, status,"
                    " (SELECT COUNT(*) FROM evaluations e WHERE e.run_id=runs.id)"
                    " FROM runs ORDER BY id").fetchall()
                return total, viaveis or 0, melhor, runs, ("resgate" if alvo == resgate else "vivo")
            finally:
                con.close()
        except sqlite3.DatabaseError:
            continue
    return 0, 0, None, [], "log"


def _linhas_log(log: Path) -> list[str]:
    if not log.exists():
        return []
    with open(log, "rb") as f:
        f.seek(max(0, f.seek(0, 2) - 40000))
        return f.read().decode("utf-8", "ignore").splitlines()


def fase_atual(log: Path) -> tuple[str, int, int]:
    """(nome|'', feitas, total) — aceita '[N/total]' e '[tag N/total]'."""
    for ln in reversed(_linhas_log(log)):
        ln = ln.strip()
        if ln.startswith("[") and "/" in ln and "]" in ln:
            corpo = ln[1:ln.index("]")]
            try:
                if " " in corpo:
                    tag, resto = corpo.split(" ", 1)
                else:
                    tag, resto = "", corpo
                feitas, total = resto.split("/")
                return tag, int(feitas), int(total)
            except ValueError:
                continue
    return "", 0, 0


def melhor_do_log(log: Path) -> float | None:
    for ln in reversed(_linhas_log(log)):
        if "melhor=" in ln:
            try:
                return float(ln.split("melhor=")[1].split()[0])
            except (ValueError, IndexError):
                continue
    return None


def painel(preset: str) -> str:
    titulo, log, banco, meta, fases = PRESETS[preset]
    total, viaveis, melhor, runs, origem = ler_banco(banco)
    if melhor is None:
        melhor = melhor_do_log(log)
    nome, feitas, alvo = fase_atual(log)

    if fases:  # multi-fase: soma as fases concluídas + a atual
        concluidas = 0
        for f, orc in fases:
            if f == nome:
                break
            concluidas += orc
        global_feito = concluidas + feitas
    else:      # fase única
        global_feito = feitas
    frac = global_feito / meta if meta else 0

    linhas = [
        f"\n{NEGRITO}  {titulo}{FIM}   {time.strftime('%H:%M:%S')}",
        f"\n\n  GERAL   {barra(frac)} {frac*100:5.1f}%   "
        f"{global_feito:,} / {meta:,}".replace(",", "."),
    ]
    if nome:
        linhas.append(f"\n  {NEGRITO}fase {nome}{FIM}  "
                      f"{barra(feitas/alvo if alvo else 0, 30, AMAR)} "
                      f"{feitas:,}/{alvo:,}".replace(",", "."))
    linhas.append("\n")
    if total:
        linhas.append(f"\n  gravadas ({origem:>7}) : {total:,}".replace(",", "."))
        linhas.append(f"\n  viáveis           : {viaveis:,} "
                      f"({100*viaveis/total:.0f}%)".replace(",", "."))
    if melhor:
        linhas.append(f"\n  {NEGRITO}melhor alcance    : {melhor:.1f} m{FIM}")
    if runs:
        linhas.append("\n\n  fases:")
        for nm, st, n in runs:
            marca = "✓" if st == "done" else "▶"
            linhas.append(f"\n    {marca} {nm:<26} {n:>7,}".replace(",", "."))
    linhas.append(f"\n\n  {CINZA}Ctrl+C para sair — não interfere na simulação{FIM}\n")
    return "".join(linhas)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    preset = args[0] if args and args[0] in PRESETS else "lab"
    uma_vez = "--uma-vez" in sys.argv
    try:
        while True:
            print("\033[2J\033[H" + painel(preset), flush=True)
            if uma_vez:
                return
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n  encerrado (a simulação continua rodando)\n")


if __name__ == "__main__":
    main()
