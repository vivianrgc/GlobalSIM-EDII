"""Testes da Etapa 1 (rodar com: python -m unittest discover -s tests -v)."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import criar_app  # noqa: E402
from estruturas import TabelaHash  # noqa: E402

ARQUIVO_ORIGINAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "arquivos", "paises.json"
)


class TesteTabelaHash(unittest.TestCase):
    def test_inserir_buscar_atualizar_remover(self):
        t = TabelaHash()
        self.assertTrue(t.inserir("IT", {"pais": "Itália"}))
        self.assertFalse(t.inserir("IT", {"pais": "outra"}))  # duplicada
        self.assertEqual(t.buscar("IT")["pais"], "Itália")
        self.assertIsNone(t.buscar("XX"))
        self.assertTrue(t.atualizar("IT", {"pais": "Italia"}))
        self.assertFalse(t.atualizar("XX", {}))
        self.assertTrue(t.remover("IT"))
        self.assertFalse(t.remover("IT"))
        self.assertEqual(len(t), 0)

    def test_rehash_preserva_dados(self):
        t = TabelaHash(capacidade_inicial=3)
        chaves = [f"K{i}" for i in range(200)]
        for c in chaves:
            t.inserir(c, c.lower())
        self.assertEqual(len(t), 200)
        self.assertGreater(t.metricas["redimensionamentos"], 0)
        self.assertLessEqual(t.estatisticas()["fator_carga"], 0.75 + 1e-9)
        for c in chaves:
            self.assertEqual(t.buscar(c), c.lower())

    def test_colisao_e_cadeia(self):
        t = TabelaHash(capacidade_inicial=2, fator_carga_max=100)  # sem rehash
        for c in ("A", "B", "C", "D", "E", "F"):
            t.inserir(c, c)
        self.assertGreater(t.metricas["colisoes"], 0)
        self.assertGreater(t.estatisticas()["maior_cadeia"], 1)
        for c in "ABCDEF":
            self.assertEqual(t.buscar(c), c)

    def test_instrumentacao_ultima_operacao(self):
        t = TabelaHash()
        t.inserir("IT", 1)
        t.buscar("IT")
        ult = t.ultima_operacao
        self.assertEqual(ult["operacao"], "buscar")
        self.assertEqual(ult["resultado"], "encontrada")
        self.assertEqual(ult["indice"], ult["hash"] % ult["capacidade"])
        self.assertGreaterEqual(ult["comparacoes"], 1)

    def test_contem_nao_afeta_metricas(self):
        t = TabelaHash()
        t.inserir("IT", 1)
        antes = dict(t.metricas)
        self.assertTrue(t.contem("IT"))
        self.assertEqual(antes, t.metricas)


class TesteApp(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.caminho = os.path.join(self.pasta, "paises.json")
        shutil.copy(ARQUIVO_ORIGINAL, self.caminho)
        self.app = criar_app(self.caminho)
        self.app.config["TESTING"] = True
        self.c = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def _json(self):
        with open(self.caminho, encoding="utf-8") as f:
            return json.load(f)

    def test_paginas_get(self):
        for rota in ("/", "/paises", "/paises/novo", "/cobertura", "/instrumentacao",
                     "/paises/IT/editar", "/instrumentacao?codigo=IT"):
            self.assertEqual(self.c.get(rota).status_code, 200, rota)

    def test_carga_inicial_de_8_paises(self):
        html = self.c.get("/paises").get_data(as_text=True)
        for nome in ("Brasil", "Portugal", "Espanha", "França", "Itália",
                     "Estados Unidos", "Canadá", "Japão"):
            self.assertIn(nome, html)

    def test_cobertura_disponivel_e_indisponivel(self):
        ok = self.c.get("/cobertura?codigo=it").get_data(as_text=True)
        self.assertIn("COBERTURA DISPONÍVEL", ok)
        self.assertIn("Operadora IT", ok)
        nok = self.c.get("/cobertura?codigo=ZZ").get_data(as_text=True)
        self.assertIn("COBERTURA INDISPONÍVEL", nok)

    def test_cadastro_post_redirect_get_e_persistencia(self):
        r = self.c.post("/paises/novo", data={
            "codigo": "ar", "pais": "Argentina", "regiao": "América do Sul",
            "operadora": "Operadora AR", "tecnologia": "4G"})
        self.assertEqual(r.status_code, 302)  # Post/Redirect/Get
        self.assertIn("AR", [p["codigo"] for p in self._json()])
        self.assertIn("Argentina", self.c.get("/paises").get_data(as_text=True))

    def test_cadastro_invalido_e_duplicado(self):
        r = self.c.post("/paises/novo", data={"codigo": "IT", "pais": "", "regiao": "",
                                              "operadora": "", "tecnologia": "9G"})
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("Já existe um país", html)
        self.assertEqual(len(self._json()), 8)

    def test_alterar_pais(self):
        r = self.c.post("/paises/IT/editar", data={
            "codigo": "XX", "pais": "Itália", "regiao": "Europa Sul",
            "operadora": "Nova Operadora", "tecnologia": "4G"})
        self.assertEqual(r.status_code, 302)
        it = next(p for p in self._json() if p["codigo"] == "IT")
        self.assertEqual(it["operadora"], "Nova Operadora")
        self.assertEqual(it["tecnologia"], "4G")
        self.assertNotIn("XX", [p["codigo"] for p in self._json()])  # chave imutável

    def test_remover_somente_por_post(self):
        self.assertEqual(self.c.get("/paises/IT/remover").status_code, 405)
        r = self.c.post("/paises/IT/remover")
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("IT", [p["codigo"] for p in self._json()])
        self.assertIn("COBERTURA INDISPONÍVEL",
                      self.c.get("/cobertura?codigo=IT").get_data(as_text=True))

    def test_recarregar_do_json_reconstroi_a_tabela(self):
        self.c.post("/paises/novo", data={
            "codigo": "AR", "pais": "Argentina", "regiao": "América do Sul",
            "operadora": "Operadora AR", "tecnologia": "4G"})
        outra = criar_app(self.caminho).test_client()
        self.assertIn("COBERTURA DISPONÍVEL",
                      outra.get("/cobertura?codigo=AR").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
