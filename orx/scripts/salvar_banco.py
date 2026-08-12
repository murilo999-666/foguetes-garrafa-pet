"""Salva/recupera um banco orx com índice corrompido, preservando o máximo.

Lê o banco de ORIGEM em modo SOMENTE LEITURA por varredura de tabela (evita o
índice corrompido) e grava tudo num banco novo, íntegro, com os índices
reconstruídos. Não modifica a origem nem interfere num processo que esteja
escrevendo nela.

Se uma página estiver corrompida, o intervalo de rowid afetado é isolado e
pulado (perde-se só as poucas linhas daquela página, não o banco todo).

Uso: python scripts/salvar_banco.py <origem.sqlite> <destino.sqlite>
"""

import sqlite3
import sys
from pathlib import Path

CHUNK = 5000


def colunas(con, tabela):
    return [d[1] for d in con.execute(f"PRAGMA table_info({tabela})")]


def salvar_tabela(orig, novo, tabela) -> tuple[int, int]:
    cols = colunas(orig, tabela)
    lista = ",".join(cols)
    phold = ",".join("?" * len(cols))
    max_rowid = orig.execute(f"SELECT MAX(rowid) FROM {tabela}").fetchone()[0] or 0
    ok = perdidas = 0
    lo = 1
    while lo <= max_rowid:
        hi = lo + CHUNK - 1
        try:
            linhas = orig.execute(
                f"SELECT {lista} FROM {tabela} WHERE rowid BETWEEN ? AND ?", (lo, hi)
            ).fetchall()
            novo.executemany(f"INSERT INTO {tabela} ({lista}) VALUES ({phold})", linhas)
            ok += len(linhas)
            lo = hi + 1
        except sqlite3.DatabaseError:
            # há uma página ruim neste intervalo: refina linha a linha p/ salvar
            # o que der e pular só as corrompidas
            for rid in range(lo, hi + 1):
                try:
                    linha = orig.execute(
                        f"SELECT {lista} FROM {tabela} WHERE rowid=?", (rid,)
                    ).fetchone()
                    if linha:
                        novo.execute(
                            f"INSERT INTO {tabela} ({lista}) VALUES ({phold})", linha)
                        ok += 1
                except sqlite3.DatabaseError:
                    perdidas += 1
            lo = hi + 1
    novo.commit()
    return ok, perdidas


def main() -> int:
    origem = Path(sys.argv[1])
    destino = Path(sys.argv[2])
    if destino.exists():
        destino.unlink()

    orig = sqlite3.connect(f"file:{origem}?mode=ro", uri=True, timeout=30)
    novo = sqlite3.connect(str(destino))

    # esquema (o CREATE das tabelas costuma sobreviver; se não, recria manual)
    try:
        for (sql,) in orig.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND sql NOT NULL"):
            novo.execute(sql)
    except sqlite3.DatabaseError:
        from orx.results.db import _SCHEMA  # fallback: esquema conhecido
        novo.executescript(_SCHEMA)
    novo.commit()

    total = {}
    for tabela in ("runs", "evaluations"):
        ok, perdidas = salvar_tabela(orig, novo, tabela)
        total[tabela] = (ok, perdidas)
        print(f"  {tabela}: {ok:,} salvas".replace(",", ".")
              + (f" | {perdidas} perdidas (paginas corrompidas)" if perdidas else " | 0 perdidas"))

    # recria os índices a partir dos dados já íntegros
    try:
        for (sql,) in orig.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND sql NOT NULL"):
            try:
                novo.execute(sql)
            except sqlite3.DatabaseError:
                pass
    except sqlite3.DatabaseError:
        pass
    novo.commit()

    integridade = novo.execute("PRAGMA integrity_check").fetchone()[0]
    print(f"  integridade do banco recuperado: {integridade}")
    orig.close()
    novo.close()
    print(f"\n  recuperado em: {destino}")
    return 0 if integridade == "ok" else 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    sys.exit(main())
