"""Serviço de países atendidos: Tabela Hash + persistência em JSON.

Esta camada concentra a lógica de negócio e fica FORA das rotas Flask.
Fluxo (conforme o enunciado):
    JSON --carregar--> Tabela Hash --operações--> Tabela Hash --persistir--> JSON
Todas as buscas/alterações passam pela Tabela Hash; o JSON é só persistência.
"""

from __future__ import annotations

import json
import os
import re
import tempfile

from estruturas import TabelaHash, explicar_hash

TECNOLOGIAS = ["3G", "4G", "5G"]
CAMPOS = ("codigo", "pais", "regiao", "operadora", "tecnologia")
_REGEX_CODIGO = re.compile(r"^[A-Z]{2}$")


def normalizar_codigo(codigo: str | None) -> str:
    return (codigo or "").strip().upper()


class PaisesService:
    def __init__(self, caminho_json: str, capacidade_inicial: int = 7):
        self.caminho_json = caminho_json
        self.tabela = TabelaHash(capacidade_inicial=capacidade_inicial)
        self.carregar()

    # -------------------- persistência --------------------
    def carregar(self) -> int:
        """Lê o JSON e insere cada país na Tabela Hash."""
        if not os.path.exists(self.caminho_json):
            return 0
        with open(self.caminho_json, encoding="utf-8") as arquivo:
            registros = json.load(arquivo)
        for registro in registros:
            registro = {campo: str(registro.get(campo, "")).strip() for campo in CAMPOS}
            registro["codigo"] = normalizar_codigo(registro["codigo"])
            self.tabela.inserir(registro["codigo"], registro)
        return len(self.tabela)

    def salvar(self) -> None:
        """Grava a Tabela Hash no JSON (escrita atômica, ordenada por código)."""
        registros = self.listar()
        pasta = os.path.dirname(self.caminho_json) or "."
        os.makedirs(pasta, exist_ok=True)
        fd, caminho_tmp = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
                json.dump(registros, arquivo, ensure_ascii=False, indent=2)
            os.replace(caminho_tmp, self.caminho_json)
        except Exception:
            if os.path.exists(caminho_tmp):
                os.remove(caminho_tmp)
            raise

    # -------------------- validação --------------------
    def validar(self, dados: dict, *, novo: bool) -> dict:
        """Retorna um dict {campo: mensagem} com os erros encontrados."""
        erros = {}
        codigo = dados.get("codigo", "")
        if not _REGEX_CODIGO.match(codigo):
            erros["codigo"] = "Informe o código de 2 letras (ex.: IT)."
        elif novo and self.tabela.contem(codigo):
            erros["codigo"] = f"Já existe um país cadastrado com o código {codigo}."
        for campo, rotulo in (("pais", "país"), ("regiao", "região"), ("operadora", "operadora")):
            if not dados.get(campo):
                erros[campo] = f"Informe o campo {rotulo}."
        if dados.get("tecnologia") not in TECNOLOGIAS:
            erros["tecnologia"] = "Escolha uma tecnologia válida."
        return erros

    @staticmethod
    def _limpar(form: dict, codigo: str | None = None) -> dict:
        dados = {campo: (form.get(campo) or "").strip() for campo in CAMPOS}
        if codigo is not None:
            dados["codigo"] = codigo
        dados["codigo"] = normalizar_codigo(dados["codigo"])
        return dados

    # -------------------- operações --------------------
    def listar(self) -> list[dict]:
        """Todos os países, ordenados por código (para exibição)."""
        return sorted((valor for _, valor in self.tabela.itens()),
                      key=lambda p: p["codigo"])

    def buscar(self, codigo: str) -> dict | None:
        return self.tabela.buscar(normalizar_codigo(codigo))

    def cadastrar(self, form: dict) -> tuple[dict | None, dict, dict]:
        """Retorna (país cadastrado | None, erros, dados limpos)."""
        dados = self._limpar(form)
        erros = self.validar(dados, novo=True)
        if erros:
            return None, erros, dados
        self.tabela.inserir(dados["codigo"], dados)
        self.salvar()
        return dados, {}, dados

    def alterar(self, codigo: str, form: dict) -> tuple[dict | None, dict, dict]:
        """O código (chave) não muda: só os demais campos são alterados."""
        codigo = normalizar_codigo(codigo)
        dados = self._limpar(form, codigo=codigo)
        if not self.tabela.contem(codigo):
            return None, {"codigo": f"País {codigo} não encontrado."}, dados
        erros = self.validar(dados, novo=False)
        if erros:
            return None, erros, dados
        self.tabela.atualizar(codigo, dados)
        self.salvar()
        return dados, {}, dados

    def remover(self, codigo: str) -> bool:
        removido = self.tabela.remover(normalizar_codigo(codigo))
        if removido:
            self.salvar()
        return removido

    # -------------------- instrumentação --------------------
    def instrumentacao(self) -> dict:
        return {
            "estatisticas": self.tabela.estatisticas(),
            "metricas": self.tabela.metricas,
            "ultima_operacao": self.tabela.ultima_operacao,
            "buckets": self.tabela.visao_buckets(),
            "redimensionamentos": self.tabela.historico_redimensionamentos,
        }

    def explicar(self, codigo: str) -> dict:
        return explicar_hash(normalizar_codigo(codigo), self.tabela._capacidade)

    def zerar_metricas(self) -> None:
        self.tabela.zerar_metricas()
