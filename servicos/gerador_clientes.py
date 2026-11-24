"""Geração de clientes fictícios (Etapa 2).

Usado pelo script scripts/gerar_clientes.py e também pela aplicação, que gera
arquivos/clientes.json automaticamente na primeira execução se ele não existir.
A mesma semente sempre produz o mesmo arquivo.
"""

from __future__ import annotations

import json
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NOMES = ["Ana", "Bruno", "Carla", "Daniel", "Elisa", "Fábio", "Gabriela", "Hugo",
         "Isabela", "João", "Karen", "Lucas", "Marina", "Nicolas", "Olívia",
         "Pedro", "Quitéria", "Rafael", "Sofia", "Thiago", "Valentina", "Wagner",
         "Yasmin", "Zeca", "Amanda", "Caio", "Débora", "Eduardo", "Fernanda", "Gustavo"]
SOBRENOMES = ["Almeida", "Barbosa", "Cardoso", "Dias", "Esteves", "Ferreira", "Gomes",
              "Henrique", "Ibrahim", "Jesus", "Lima", "Machado", "Nascimento",
              "Oliveira", "Pereira", "Queiroz", "Ribeiro", "Santos", "Teixeira",
              "Uchoa", "Vieira", "Xavier", "Zanetti", "Carvalho", "Moreira"]

_SEM_ACENTO = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeioooucAAAAEEIOOOUC")


def gerar_clientes(caminho_saida: str, caminho_paises: str, caminho_pacotes: str,
                   quantidade: int = 1000, semente: int = 2026) -> int:
    """Grava ${quantidade} clientes em caminho_saida; devolve quantos gravou."""
    rnd = random.Random(semente)
    with open(caminho_paises, encoding="utf-8") as f:
        codigos = [p["codigo"] for p in json.load(f)]
    with open(caminho_pacotes, encoding="utf-8") as f:
        pacotes = [p["id"] for p in json.load(f)]

    ids = rnd.sample(range(1000, 10000), quantidade)  # IDs únicos, já embaralhados
    linhas = []
    for cid in ids:
        nome = f"{rnd.choice(NOMES)} {rnd.choice(SOBRENOMES)}"
        email = f"{nome.translate(_SEM_ACENTO).lower().replace(' ', '.')}{cid}@exemplo.com"
        tem_esim = rnd.random() < 0.6
        linhas.append(json.dumps({
            "id": cid,
            "nome": nome,
            "email": email,
            "pais_origem": rnd.choice(codigos),
            "destino": rnd.choice(codigos) if rnd.random() < 0.7 else "",
            "esim": f"ESIM-{cid:06d}" if tem_esim else "",
            "pacote": rnd.choice(pacotes) if tem_esim else "",
        }, ensure_ascii=False))

    os.makedirs(os.path.dirname(caminho_saida) or ".", exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("[\n  " + ",\n  ".join(linhas) + "\n]\n")
    return len(linhas)
