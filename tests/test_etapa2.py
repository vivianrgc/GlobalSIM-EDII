"""Testes da Etapa 2 (rodar com: python -m unittest discover -s tests -v)."""

import json
import os
import random
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app import criar_app  # noqa: E402
from estruturas import ArvoreB, Grafo  # noqa: E402
from servicos import gerar_clientes  # noqa: E402

ARQUIVOS = os.path.join(RAIZ, "arquivos")


class TesteArvoreB(unittest.TestCase):
    def test_grau_invalido(self):
        with self.assertRaises(ValueError):
            ArvoreB(1)

    def test_inserir_buscar_e_chave_unica(self):
        a = ArvoreB(2)
        for k in (10, 20, 5, 6, 12, 30, 7, 17):
            self.assertTrue(a.inserir(k, {"id": k}))
        self.assertFalse(a.inserir(10, {"id": 10}))  # duplicada
        self.assertEqual(len(a), 8)
        self.assertEqual(a.buscar(12), {"id": 12})
        self.assertIsNone(a.buscar(99))
        a.verificar_invariantes()

    def test_divisao_cria_nova_raiz_e_aumenta_altura(self):
        a = ArvoreB(2)  # nó cheio com 3 chaves
        for k in (1, 2, 3):
            a.inserir(k, k)
        self.assertEqual(a.altura(), 1)
        self.assertEqual(a.metricas["divisoes"], 0)
        a.inserir(4, 4)  # raiz cheia -> divide
        self.assertEqual(a.altura(), 2)
        self.assertEqual(a.metricas["divisoes"], 1)
        self.assertEqual(a.total_nos, 3)
        self.assertEqual(a.raiz.chaves, [2])
        a.verificar_invariantes()

    def test_invariantes_com_varios_graus_e_ordens(self):
        for t in (2, 3, 4, 5, 10):
            for ordem in ("crescente", "decrescente", "aleatoria"):
                chaves = list(range(1, 501))
                if ordem == "decrescente":
                    chaves.reverse()
                elif ordem == "aleatoria":
                    random.Random(t).shuffle(chaves)
                a = ArvoreB(t)
                for k in chaves:
                    a.inserir(k, k * 2)
                a.verificar_invariantes()
                self.assertEqual(len(a), 500)
                self.assertEqual([k for k, _ in a.em_ordem()], list(range(1, 501)))
                for k in (1, 250, 500):
                    self.assertEqual(a.buscar(k), k * 2)

    def test_altura_cai_com_grau_maior(self):
        chaves = list(range(1, 1001))
        random.Random(1).shuffle(chaves)
        alturas = []
        for t in (2, 3, 8, 20):
            a = ArvoreB(t)
            for k in chaves:
                a.inserir(k, k)
            alturas.append(a.altura())
        self.assertEqual(alturas, sorted(alturas, reverse=True))
        self.assertGreater(alturas[0], alturas[-1])

    def test_instrumentacao_da_busca(self):
        a = ArvoreB(2)
        for k in range(1, 40):
            a.inserir(k, k)
        a.buscar(25)
        u = a.ultima_busca
        self.assertTrue(u["encontrado"])
        self.assertGreaterEqual(u["nos_visitados"], 1)
        self.assertLessEqual(u["nos_visitados"], a.altura())
        self.assertEqual(len(u["caminho"]), u["nos_visitados"])
        a.buscar(1000)
        self.assertFalse(a.ultima_busca["encontrado"])
        self.assertEqual(a.ultima_busca["nos_visitados"], a.altura())  # desce até a folha

    def test_contem_nao_afeta_metricas(self):
        a = ArvoreB(3)
        a.inserir(1, "x")
        antes = dict(a.metricas)
        self.assertTrue(a.contem(1))
        self.assertFalse(a.contem(2))
        self.assertEqual(antes, a.metricas)

    def test_atualizar_e_maior_chave(self):
        a = ArvoreB(2)
        self.assertIsNone(a.maior_chave())
        for k in (5, 3, 9, 1):
            a.inserir(k, {"v": k})
        self.assertTrue(a.atualizar(9, {"v": "novo"}))
        self.assertEqual(a.buscar(9), {"v": "novo"})
        self.assertFalse(a.atualizar(42, {}))
        self.assertEqual(a.maior_chave(), 9)
        self.assertEqual(a.metricas["atualizacoes"], 1)

    def test_estatisticas(self):
        a = ArvoreB(3)
        for k in range(100):
            a.inserir(k, k)
        e = a.estatisticas()
        self.assertEqual(e["total_chaves"], 100)
        self.assertEqual(e["total_nos"], sum(e["nos_por_nivel"]))
        self.assertEqual(e["altura"], len(e["nos_por_nivel"]))
        self.assertEqual(e["max_chaves_no"], 5)


class TesteGrafo(unittest.TestCase):
    """Rede de teste só para os algoritmos (a rede.json oficial é da Etapa 3)."""

    def setUp(self):
        self.g = Grafo()
        for a, b, p in [("BR", "PT", 90), ("PT", "ES", 25), ("PT", "FR", 45),
                        ("ES", "FR", 30), ("FR", "IT", 50), ("BR", "US", 130),
                        ("US", "CA", 20)]:
            self.g.adicionar_aresta(a, b, p)
        self.g.adicionar_vertice("JP")  # isolado

    def test_lista_de_adjacencia(self):
        self.assertEqual(len(self.g), 8)
        self.assertEqual(len(self.g.arestas()), 7)
        self.assertIn(("PT", 90), self.g.vizinhos("BR"))
        self.assertIn(("BR", 90), self.g.vizinhos("PT"))  # não direcionado
        self.assertEqual(self.g.vizinhos("JP"), [])

    def test_bfs_por_niveis(self):
        self.assertEqual(self.g.bfs("BR"), ["BR", "PT", "US", "ES", "FR", "CA", "IT"])

    def test_dfs(self):
        self.assertEqual(self.g.dfs("BR"), ["BR", "PT", "ES", "FR", "IT", "US", "CA"])

    def test_dijkstra_menor_latencia(self):
        r = self.g.dijkstra("BR", "IT")
        self.assertEqual(r["caminho"], ["BR", "PT", "FR", "IT"])
        self.assertEqual(r["custo"], 185)
        self.assertEqual(sum(p for _, _, p in r["arestas"]), 185)

    def test_dijkstra_mesmo_vertice_e_inalcancavel(self):
        self.assertEqual(self.g.dijkstra("BR", "BR")["custo"], 0)
        self.assertIsNone(self.g.dijkstra("BR", "JP"))

    def test_vertice_inexistente_e_aresta_invalida(self):
        with self.assertRaises(KeyError):
            self.g.bfs("XX")
        with self.assertRaises(ValueError):
            self.g.adicionar_aresta("BR", "PT", 0)
        with self.assertRaises(ValueError):
            self.g.adicionar_aresta("BR", "BR", 10)

    def test_aresta_repetida_troca_o_peso(self):
        self.g.adicionar_aresta("BR", "PT", 10)
        self.assertEqual(len(self.g.arestas()), 7)
        self.assertEqual(self.g.dijkstra("BR", "PT")["custo"], 10)


class TesteGerador(unittest.TestCase):
    def test_gera_mil_clientes_unicos_e_reprodutiveis(self):
        pasta = tempfile.mkdtemp()
        try:
            destino = os.path.join(pasta, "c.json")
            total = gerar_clientes(destino, os.path.join(ARQUIVOS, "paises.json"),
                                   os.path.join(ARQUIVOS, "pacotes.json"))
            self.assertEqual(total, 1000)
            with open(destino, encoding="utf-8") as f:
                dados = json.load(f)
            self.assertEqual(len({c["id"] for c in dados}), 1000)
            with open(os.path.join(ARQUIVOS, "pacotes.json"), encoding="utf-8") as f:
                self.assertEqual(len(json.load(f)), 5)
            outro = os.path.join(pasta, "d.json")
            gerar_clientes(outro, os.path.join(ARQUIVOS, "paises.json"),
                           os.path.join(ARQUIVOS, "pacotes.json"))
            with open(destino, encoding="utf-8") as a, open(outro, encoding="utf-8") as b:
                self.assertEqual(a.read(), b.read())
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class TesteAppEtapa2(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp()
        self.paises = os.path.join(self.pasta, "paises.json")
        self.clientes = os.path.join(self.pasta, "clientes.json")
        shutil.copy(os.path.join(ARQUIVOS, "paises.json"), self.paises)
        shutil.copy(os.path.join(ARQUIVOS, "pacotes.json"), self.pasta)
        # clientes.json não existe: a aplicação deve gerá-lo na primeira execução
        self.app = criar_app(self.paises, self.clientes,
                             os.path.join(self.pasta, "pacotes.json"))
        self.app.config["TESTING"] = True
        self.c = self.app.test_client()
        self.servico = self.app.config["CLIENTES"]

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def _json(self):
        with open(self.clientes, encoding="utf-8") as f:
            return json.load(f)

    def _cliente(self, **filtros):
        for _, c in self.servico.arvore.em_ordem():
            if all(c[k] == v for k, v in filtros.items()):
                return c
        raise AssertionError(f"nenhum cliente com {filtros}")

    def test_carga_gerada_e_arvore_valida(self):
        self.assertEqual(len(self.servico), 1000)
        self.servico.arvore.verificar_invariantes()
        self.assertEqual(len(self._json()), 1000)

    def test_paginas_get(self):
        cid = self._cliente()["id"]
        for rota in ("/", "/clientes", "/clientes?pagina=3", "/clientes?pagina=abc",
                     "/clientes/novo", f"/clientes/{cid}", f"/clientes/{cid}/editar",
                     "/pacotes", "/consulta", f"/consulta?cliente={cid}", "/arvore",
                     "/cobertura?codigo=IT"):
            self.assertEqual(self.c.get(rota).status_code, 200, rota)

    def test_listagem_paginada_em_ordem(self):
        p1, total = self.servico.listar_pagina(1, 25)
        self.assertEqual(total, 40)
        ids = [c["id"] for c in p1]
        self.assertEqual(len(ids), 25)
        self.assertEqual(ids, sorted(ids))
        p2, _ = self.servico.listar_pagina(2, 25)
        self.assertGreater(p2[0]["id"], ids[-1])
        ultima, _ = self.servico.listar_pagina(999, 25)  # página fora do limite
        self.assertEqual(len(ultima), 25)

    def test_consulta_por_id(self):
        cid = self._cliente()["id"]
        html = self.c.get(f"/clientes/{cid}").get_data(as_text=True)
        self.assertIn("nós visitados", html)
        r = self.c.get("/clientes/99999999")
        self.assertEqual(r.status_code, 302)  # não encontrado -> volta à lista
        r = self.c.get("/clientes/buscar?id=abc")
        self.assertEqual(r.status_code, 302)

    def test_cadastro_com_id_automatico_e_persistencia(self):
        maior = self.servico.arvore.maior_chave()
        r = self.c.post("/clientes/novo", data={
            "nome": "Teste Silva", "email": "teste@exemplo.com",
            "pais_origem": "br", "destino": "it"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], f"/clientes/{maior + 1}")
        novo = next(c for c in self._json() if c["id"] == maior + 1)
        self.assertEqual((novo["pais_origem"], novo["destino"]), ("BR", "IT"))
        self.assertEqual(len(self._json()), 1001)

    def test_cadastro_invalido(self):
        r = self.c.post("/clientes/novo", data={
            "nome": "", "email": "x", "pais_origem": "ZZ", "destino": "QQ"})
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("Informe o nome", html)
        self.assertIn("e-mail válido", html)
        self.assertIn("não está cadastrado na Tabela Hash", html)
        self.assertEqual(len(self._json()), 1000)

    def test_alterar_mantem_id_esim_e_pacote(self):
        c = next(cl for _, cl in self.servico.arvore.em_ordem() if cl["esim"] and cl["pacote"])
        r = self.c.post(f"/clientes/{c['id']}/editar", data={
            "nome": "Nome Novo", "email": "novo@exemplo.com",
            "pais_origem": "PT", "destino": ""})
        self.assertEqual(r.status_code, 302)
        depois = next(x for x in self._json() if x["id"] == c["id"])
        self.assertEqual(depois["nome"], "Nome Novo")
        self.assertEqual(depois["destino"], "")
        self.assertEqual((depois["esim"], depois["pacote"]), (c["esim"], c["pacote"]))

    def test_associar_esim_e_pacote(self):
        c = next(cl for _, cl in self.servico.arvore.em_ordem() if not cl["esim"])
        self.assertEqual(self.c.post(f"/clientes/{c['id']}/esim").status_code, 302)
        depois = next(x for x in self._json() if x["id"] == c["id"])
        self.assertEqual(depois["esim"], f"ESIM-{c['id']:06d}")
        self.c.post(f"/clientes/{c['id']}/pacote", data={"pacote": "EUR-5"})
        depois = next(x for x in self._json() if x["id"] == c["id"])
        self.assertEqual(depois["pacote"], "EUR-5")
        self.c.post(f"/clientes/{c['id']}/pacote", data={"pacote": "INEXISTENTE"})
        depois = next(x for x in self._json() if x["id"] == c["id"])
        self.assertEqual(depois["pacote"], "EUR-5")  # inválido não altera

    def test_recarregar_do_json_reconstroi_a_arvore(self):
        self.c.post("/clientes/novo", data={
            "nome": "Persistido", "email": "p@exemplo.com", "pais_origem": "BR", "destino": ""})
        outra = criar_app(self.paises, self.clientes, os.path.join(self.pasta, "pacotes.json"))
        self.assertEqual(len(outra.config["CLIENTES"]), 1001)

    def test_consulta_integrada_cenarios(self):
        # cliente com eSIM e pacote europeu consultando um país europeu: ok
        europeu = next(cl for _, cl in self.servico.arvore.em_ordem()
                       if cl["esim"] and cl["pacote"] == "EUR-5")
        html = self.c.get(f"/consulta?cliente={europeu['id']}&destino=IT").get_data(as_text=True)
        self.assertIn("Cobertura confirmada", html)
        self.assertIn("Etapa 1", html)
        self.assertIn("Etapa 2", html)
        # mesmo cliente, destino fora da região do pacote
        html = self.c.get(f"/consulta?cliente={europeu['id']}&destino=JP").get_data(as_text=True)
        self.assertIn("não cobre a região", html)
        # destino inexistente na Tabela Hash e cliente inexistente
        html = self.c.get(f"/consulta?cliente={europeu['id']}&destino=ZZ").get_data(as_text=True)
        self.assertIn("não é atendido", html)
        html = self.c.get("/consulta?cliente=1&destino=IT").get_data(as_text=True)
        self.assertIn("não encontrado na Árvore B", html)
        html = self.c.get("/consulta?cliente=abc").get_data(as_text=True)
        self.assertIn("ID do cliente", html)
        # cliente sem eSIM
        sem = next(cl for _, cl in self.servico.arvore.em_ordem() if not cl["esim"])
        html = self.c.get(f"/consulta?cliente={sem['id']}&destino=IT").get_data(as_text=True)
        self.assertIn("ainda não tem eSIM", html)

    def test_busca_e_hash_aparecem_na_instrumentacao(self):
        cid = self._cliente()["id"]
        self.c.get(f"/consulta?cliente={cid}&destino=IT")
        self.assertTrue(self.servico.arvore.ultima_busca["encontrado"])
        html = self.c.get("/arvore").get_data(as_text=True)
        for texto in ("altura", "divisões de nó", "nós visitados na última busca"):
            self.assertIn(texto, html)

    def test_reconstruir_com_outro_grau(self):
        antes = self.servico.arvore.altura()
        self.assertEqual(self.c.post("/arvore/reconstruir", data={"grau": "2"}).status_code, 302)
        self.assertEqual(self.servico.arvore.t, 2)
        self.assertGreaterEqual(self.servico.arvore.altura(), antes)
        self.servico.arvore.verificar_invariantes()
        self.assertEqual(len(self.servico), 1000)
        self.c.post("/arvore/reconstruir", data={"grau": "1"})  # inválido: não muda
        self.assertEqual(self.servico.arvore.t, 2)
        self.c.post("/arvore/zerar")
        self.assertEqual(self.servico.arvore.metricas["buscas"], 0)

    def test_estado_de_falha_do_pais_e_clientes_afetados(self):
        r = self.c.post("/paises/IT/estado", data={"estado": "falha"})
        self.assertEqual(r.status_code, 302)
        paises = self.app.config["PAISES"]
        self.assertEqual(paises.buscar("IT")["estado"], "falha")
        with open(self.paises, encoding="utf-8") as f:
            self.assertEqual(next(p for p in json.load(f) if p["codigo"] == "IT")["estado"], "falha")
        html = self.c.get("/cobertura?codigo=IT").get_data(as_text=True)
        self.assertIn("EM FALHA", html)
        self.assertIn("Clientes afetados", html)
        total, _ = self.servico.afetados_por_pais("IT")
        self.assertEqual(total, sum(1 for _, c in self.servico.arvore.em_ordem() if c["destino"] == "IT"))
        # consulta integrada reconhece a falha
        cid = next(c["id"] for _, c in self.servico.arvore.em_ordem() if c["destino"] == "IT")
        html = self.c.get(f"/consulta?cliente={cid}").get_data(as_text=True)
        self.assertIn("falha operacional", html)
        # editar o país não apaga o estado; restabelecer volta a ativo
        self.c.post("/paises/IT/editar", data={
            "pais": "Itália", "regiao": "Europa", "operadora": "Op", "tecnologia": "5G"})
        self.assertEqual(paises.buscar("IT")["estado"], "falha")
        self.c.post("/paises/IT/estado", data={"estado": "ativo"})
        self.assertEqual(paises.buscar("IT")["estado"], "ativo")
        self.c.post("/paises/IT/estado", data={"estado": "qualquer"})  # inválido
        self.assertEqual(paises.buscar("IT")["estado"], "ativo")


if __name__ == "__main__":
    unittest.main()
