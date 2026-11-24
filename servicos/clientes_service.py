"""Serviço de clientes: Árvore B + persistência em JSON (Etapa 2).

Mesmo fluxo da Etapa 1, agora com a Árvore B:
    JSON --carregar--> Árvore B --operações--> Árvore B --persistir--> JSON
Toda busca e alteração passa pela Árvore B; o JSON é só persistência.
A chave da árvore é o ID inteiro do cliente.
"""

from __future__ import annotations

import itertools
import json
import os
import re
import tempfile

from estruturas import ArvoreB

CAMPOS = ("nome", "email", "pais_origem", "destino")
_REGEX_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REGEX_PAIS = re.compile(r"^[A-Z]{2}$")


def ler_pacotes(caminho: str) -> list[dict]:
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def interpretar_id(valor) -> int | None:
    """Converte o ID digitado para inteiro positivo; None se for inválido."""
    texto = str(valor or "").strip()
    return int(texto) if texto.isdigit() and int(texto) > 0 else None


class ClientesService:
    def __init__(self, caminho_json: str, caminho_pacotes: str, paises=None,
                 grau_minimo: int = 3):
        self.caminho_json = caminho_json
        self.pacotes = ler_pacotes(caminho_pacotes)
        self.paises = paises  # PaisesService (valida origem/destino na Tabela Hash)
        self.arvore = ArvoreB(grau_minimo)
        self.carregar()

    # -------------------- persistência --------------------
    def carregar(self) -> int:
        """Lê o JSON e insere cada cliente na Árvore B."""
        if not os.path.exists(self.caminho_json):
            return 0
        with open(self.caminho_json, encoding="utf-8") as arquivo:
            registros = json.load(arquivo)
        for bruto in registros:
            cliente = {
                "id": int(bruto["id"]),
                "nome": str(bruto.get("nome", "")).strip(),
                "email": str(bruto.get("email", "")).strip(),
                "pais_origem": str(bruto.get("pais_origem", "")).strip().upper(),
                "destino": str(bruto.get("destino", "")).strip().upper(),
                "esim": str(bruto.get("esim", "")).strip(),
                "pacote": str(bruto.get("pacote", "")).strip(),
            }
            self.arvore.inserir(cliente["id"], cliente)
        return len(self.arvore)

    def salvar(self) -> None:
        """Grava a Árvore B no JSON, em ordem de ID (escrita atômica)."""
        linhas = [json.dumps(c, ensure_ascii=False) for _, c in self.arvore.em_ordem()]
        pasta = os.path.dirname(self.caminho_json) or "."
        os.makedirs(pasta, exist_ok=True)
        fd, caminho_tmp = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
                arquivo.write("[\n  " + ",\n  ".join(linhas) + "\n]\n" if linhas else "[]\n")
            os.replace(caminho_tmp, self.caminho_json)
        except Exception:
            if os.path.exists(caminho_tmp):
                os.remove(caminho_tmp)
            raise

    # -------------------- pacotes --------------------
    def buscar_pacote(self, pacote_id: str) -> dict | None:
        for pacote in self.pacotes:
            if pacote["id"] == pacote_id:
                return pacote
        return None

    # -------------------- validação --------------------
    def _pais_existe(self, codigo: str) -> bool:
        return self.paises is None or self.paises.contem(codigo)

    def validar(self, dados: dict) -> dict:
        erros = {}
        if not dados.get("nome"):
            erros["nome"] = "Informe o nome do cliente."
        if not _REGEX_EMAIL.match(dados.get("email", "")):
            erros["email"] = "Informe um e-mail válido."
        origem = dados.get("pais_origem", "")
        if not _REGEX_PAIS.match(origem):
            erros["pais_origem"] = "Informe o código de 2 letras do país de origem."
        elif not self._pais_existe(origem):
            erros["pais_origem"] = f"O país {origem} não está cadastrado na Tabela Hash."
        destino = dados.get("destino", "")
        if destino:  # destino é opcional
            if not _REGEX_PAIS.match(destino):
                erros["destino"] = "Informe o código de 2 letras do destino (ou deixe em branco)."
            elif not self._pais_existe(destino):
                erros["destino"] = f"O país {destino} não está cadastrado na Tabela Hash."
        return erros

    @staticmethod
    def _limpar(form) -> dict:
        dados = {campo: (form.get(campo) or "").strip() for campo in CAMPOS}
        dados["pais_origem"] = dados["pais_origem"].upper()
        dados["destino"] = dados["destino"].upper()
        return dados

    # -------------------- operações --------------------
    def __len__(self) -> int:
        return len(self.arvore)

    def buscar(self, cliente_id: int) -> dict | None:
        return self.arvore.buscar(cliente_id)

    def proximo_id(self) -> int:
        maior = self.arvore.maior_chave()
        return (maior or 0) + 1

    def listar_pagina(self, pagina: int = 1, por_pagina: int = 25) -> tuple[list[dict], int]:
        """Clientes da página (percurso em ordem da Árvore B) e total de páginas."""
        por_pagina = max(1, por_pagina)
        total_paginas = max(1, -(-len(self.arvore) // por_pagina))
        pagina = min(max(1, pagina), total_paginas)
        inicio = (pagina - 1) * por_pagina
        itens = itertools.islice(self.arvore.em_ordem(), inicio, inicio + por_pagina)
        return [cliente for _, cliente in itens], total_paginas

    def cadastrar(self, form) -> tuple[dict | None, dict, dict]:
        """Retorna (cliente cadastrado | None, erros, dados limpos). ID automático."""
        dados = self._limpar(form)
        erros = self.validar(dados)
        if erros:
            return None, erros, dados
        cliente = {"id": self.proximo_id(), **dados, "esim": "", "pacote": ""}
        self.arvore.inserir(cliente["id"], cliente)
        self.salvar()
        return cliente, {}, cliente

    def alterar(self, cliente_id: int, form) -> tuple[dict | None, dict, dict]:
        """Busca + atualização. O ID (chave) não muda; eSIM e pacote são mantidos."""
        atual = self.arvore.buscar(cliente_id)
        dados = self._limpar(form)
        if atual is None:
            return None, {"nome": f"Cliente {cliente_id} não encontrado."}, dados
        erros = self.validar(dados)
        if erros:
            return None, erros, {"id": cliente_id, **dados}
        novo = {**atual, **dados, "id": cliente_id}
        self.arvore.atualizar(cliente_id, novo)
        self.salvar()
        return novo, {}, novo

    def associar_esim(self, cliente_id: int) -> dict | None:
        """Gera e associa um eSIM ao cliente (se ainda não tiver)."""
        atual = self.arvore.buscar(cliente_id)
        if atual is None:
            return None
        if not atual["esim"]:
            atual = {**atual, "esim": f"ESIM-{cliente_id:06d}"}
            self.arvore.atualizar(cliente_id, atual)
            self.salvar()
        return atual

    def associar_pacote(self, cliente_id: int, pacote_id: str) -> tuple[dict | None, str | None]:
        """Associa (ou troca) o pacote. Retorna (cliente, erro)."""
        pacote_id = (pacote_id or "").strip()
        if pacote_id and self.buscar_pacote(pacote_id) is None:
            return None, "Pacote inexistente."
        atual = self.arvore.buscar(cliente_id)
        if atual is None:
            return None, "Cliente não encontrado."
        atual = {**atual, "pacote": pacote_id}
        self.arvore.atualizar(cliente_id, atual)
        self.salvar()
        return atual, None

    def afetados_por_pais(self, codigo: str, limite: int = 15) -> tuple[int, list[dict]]:
        """Clientes com destino no país (percurso em ordem). (total, primeiros)."""
        codigo = (codigo or "").strip().upper()
        total, amostra = 0, []
        for _, cliente in self.arvore.em_ordem():
            if cliente["destino"] == codigo:
                total += 1
                if len(amostra) < limite:
                    amostra.append(cliente)
        return total, amostra

    # -------------------- instrumentação --------------------
    def instrumentacao(self) -> dict:
        return {
            "estatisticas": self.arvore.estatisticas(),
            "metricas": self.arvore.metricas,
            "ultima_busca": self.arvore.ultima_busca,
            "niveis": self.arvore.visao_niveis(),
        }

    def zerar_metricas(self) -> None:
        self.arvore.zerar_metricas()

    def reconstruir(self, grau_minimo: int) -> None:
        """Reconstrói a árvore com outro grau mínimo (para comparar a altura).

        A mudança vale só enquanto a aplicação estiver rodando; os dados no
        JSON não mudam.
        """
        clientes = [c for _, c in self.arvore.em_ordem()]
        nova = ArvoreB(grau_minimo)
        for cliente in clientes:
            nova.inserir(cliente["id"], cliente)
        self.arvore = nova
