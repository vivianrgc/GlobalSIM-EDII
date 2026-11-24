"""Gera arquivos/clientes.json com clientes fictícios (Etapa 2).

Uso (a partir da pasta do projeto):
    python scripts/gerar_clientes.py              # 1000 clientes, semente 2026
    python scripts/gerar_clientes.py 1500 7       # quantidade e semente

IDs únicos (sorteados sem repetição entre 1000 e 9999), registros em ordem
embaralhada. Países e pacotes vêm de arquivos/paises.json e pacotes.json.
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from servicos.gerador_clientes import gerar_clientes  # noqa: E402

if __name__ == "__main__":
    quantidade = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    semente = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
    arq = os.path.join(BASE, "arquivos")
    total = gerar_clientes(os.path.join(arq, "clientes.json"),
                           os.path.join(arq, "paises.json"),
                           os.path.join(arq, "pacotes.json"), quantidade, semente)
    print(f"{total} clientes gravados em arquivos/clientes.json")
