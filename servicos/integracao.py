"""Consulta integrada da Etapa 2: cliente (Árvore B) + destino (Tabela Hash).

Etapa 1 da consulta: busca o cliente pelo ID na Árvore B.
Etapa 2 da consulta: busca o país de destino pelo código na Tabela Hash.
Depois cruza os dois resultados com o pacote contratado (arquivos/pacotes.json)
e o estado operacional do país (diferencial da equipe).
"""

from __future__ import annotations

from .clientes_service import ClientesService, interpretar_id
from .paises_service import PaisesService, normalizar_codigo


def _pacotes_que_cobrem(clientes: ClientesService, regiao: str) -> list[dict]:
    return [p for p in clientes.pacotes if regiao in p["regioes"]]


def consulta_integrada(clientes: ClientesService, paises: PaisesService,
                       cliente_id_bruto: str, destino_bruto: str) -> dict:
    resultado = {
        "cliente_id": None, "cliente": None, "busca_cliente": None,
        "codigo": normalizar_codigo(destino_bruto), "pais": None, "busca_pais": None,
        "pacote": None, "sugestoes": [],
        "status": "", "mensagem": "", "nivel": "secondary",
    }

    cliente_id = interpretar_id(cliente_id_bruto)
    if cliente_id is None:
        resultado.update(status="id_invalido", nivel="warning",
                         mensagem="Informe o ID do cliente (número inteiro positivo).")
        return resultado
    resultado["cliente_id"] = cliente_id

    # ---- Etapa 1: Árvore B ----
    cliente = clientes.buscar(cliente_id)
    resultado["busca_cliente"] = clientes.arvore.ultima_busca
    resultado["cliente"] = cliente
    if cliente is None:
        resultado.update(status="cliente_nao_encontrado", nivel="danger",
                         mensagem=f"Cliente {cliente_id} não encontrado na Árvore B.")
        return resultado

    codigo = resultado["codigo"] or cliente["destino"]
    resultado["codigo"] = codigo
    if not codigo:
        resultado.update(status="sem_destino", nivel="warning",
                         mensagem="O cliente não tem destino cadastrado: informe o país de destino.")
        return resultado

    # ---- Etapa 2: Tabela Hash ----
    pais = paises.buscar(codigo)
    resultado["busca_pais"] = paises.tabela.ultima_operacao
    resultado["pais"] = pais
    if pais is None:
        resultado.update(status="pais_nao_atendido", nivel="danger",
                         mensagem=f"O destino {codigo} não é atendido (não está na Tabela Hash).")
        return resultado

    # ---- Cruzamento: estado do país, eSIM e pacote ----
    pacote = clientes.buscar_pacote(cliente["pacote"]) if cliente["pacote"] else None
    resultado["pacote"] = pacote

    if pais.get("estado") == "falha":
        resultado.update(status="pais_em_falha", nivel="danger",
                         mensagem=f"{pais['pais']} está em falha operacional: sem cobertura no momento.")
    elif not cliente["esim"]:
        resultado.update(status="sem_esim", nivel="warning",
                         mensagem="O cliente ainda não tem eSIM associado.")
    elif pacote is None:
        resultado.update(status="sem_pacote", nivel="warning",
                         mensagem="O cliente tem eSIM, mas nenhum pacote contratado.",
                         sugestoes=_pacotes_que_cobrem(clientes, pais["regiao"]))
    elif pais["regiao"] not in pacote["regioes"]:
        resultado.update(status="pacote_nao_cobre", nivel="warning",
                         mensagem=f"O pacote {pacote['nome']} não cobre a região {pais['regiao']}.",
                         sugestoes=_pacotes_que_cobrem(clientes, pais["regiao"]))
    else:
        resultado.update(status="ok", nivel="success",
                         mensagem=f"Cobertura confirmada em {pais['pais']} com o pacote {pacote['nome']}.")
    return resultado
