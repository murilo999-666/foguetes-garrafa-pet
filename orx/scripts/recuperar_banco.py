"""Reconstrói um banco SQLite corrompido (corrupção de índice) num arquivo limpo.

Uso: python scripts/recuperar_banco.py <caminho.sqlite>
Cria <caminho>_limpo.sqlite, valida a integridade e compara as contagens.
O original NÃO é apagado (renomeie manualmente depois de conferir).
"""

import shutil
import sqlite3
import sys
from pathlib import Path


def contagens(con: sqlite3.Connection) -> dict:
    return {
        "runs": con.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
        "evaluations": con.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0],
    }


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1
               else r"D:\1-Competicoes\OBAFOG\foguetes\bit04 2L script\foguete_real\otimizacao\orx.sqlite")
    dst = src.with_name(src.stem + "_limpo.sqlite")
    backup = src.with_name(src.name + ".backup_corrompido")

    if not backup.exists():
        shutil.copy2(src, backup)
        print(f"backup: {backup}")

    con = sqlite3.connect(str(src))
    antes = contagens(con)
    print(f"original: {antes['runs']} runs, {antes['evaluations']} avaliações")

    if dst.exists():
        dst.unlink()
    # VACUUM INTO reconstrói tabelas e índices do zero num arquivo novo
    con.execute("VACUUM INTO ?", (str(dst),))
    con.close()

    novo = sqlite3.connect(str(dst))
    integridade = novo.execute("PRAGMA integrity_check").fetchone()[0]
    depois = contagens(novo)
    novo.close()

    print(f"limpo:    {depois['runs']} runs, {depois['evaluations']} avaliações")
    print(f"integridade: {integridade}")
    if integridade == "ok" and depois == antes:
        print(f"\nOK — banco recuperado sem perda: {dst}")
        print("Para adotar: renomeie o original e ponha o _limpo no lugar.")
        return 0
    print("\nATENÇÃO: divergência ou integridade falhou — mantenha o original.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
