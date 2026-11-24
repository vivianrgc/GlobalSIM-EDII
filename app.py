"""GlobalSIM — Etapa 1 (Tabela Hash) + Etapa 2 (Árvore B e clientes) em Flask.

As rotas só tratam HTTP (request, render_template, redirect, flash). Toda a
lógica das estruturas fica em estruturas/ e servicos/.
Rotas que alteram dados usam POST e o padrão Post/Redirect/Get.
"""

import os

from flask import Flask, flash, redirect, render_template, request, url_for

from servicos import (ESTADOS, TECNOLOGIAS, ClientesService, PaisesService,
                      consulta_integrada, gerar_clientes)
from servicos.clientes_service import interpretar_id

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POR_PAGINA = 25


def criar_app(caminho_paises: str | None = None,
              caminho_clientes: str | None = None,
              caminho_pacotes: str | None = None,
              grau_minimo: int | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "globalsim-dev-key")

    arquivos = os.path.join(BASE_DIR, "arquivos")
    caminho_paises = caminho_paises or os.path.join(arquivos, "paises.json")
    caminho_clientes = caminho_clientes or os.path.join(arquivos, "clientes.json")
    caminho_pacotes = caminho_pacotes or os.path.join(arquivos, "pacotes.json")
    grau_minimo = grau_minimo or int(os.environ.get("GLOBALSIM_GRAU_B", "3"))

    paises = PaisesService(caminho_paises)
    app.config["PAISES"] = paises

    # Na primeira execução gera ~1000 clientes fictícios (mesmo que
    # `python scripts/gerar_clientes.py`), se o arquivo ainda não existir.
    if not os.path.exists(caminho_clientes):
        gerar_clientes(caminho_clientes, caminho_paises, caminho_pacotes)
    clientes = ClientesService(caminho_clientes, caminho_pacotes, paises=paises,
                               grau_minimo=grau_minimo)
    app.config["CLIENTES"] = clientes

    # ------------------------- Página inicial -------------------------
    @app.get("/")
    def index():
        return render_template(
            "index.html",
            total=len(paises.tabela),
            estatisticas=paises.tabela.estatisticas(),
            total_clientes=len(clientes),
            arvore=clientes.arvore.estatisticas(),
        )

    # ------------------------- Países (CRUD) -------------------------
    @app.get("/paises")
    def listar_paises():
        return render_template("paises.html", paises=paises.listar())

    @app.route("/paises/novo", methods=["GET", "POST"])
    def novo_pais():
        if request.method == "POST":
            _, erros, dados = paises.cadastrar(request.form)
            if not erros:
                flash(f"País {dados['pais']} ({dados['codigo']}) cadastrado.", "success")
                return redirect(url_for("listar_paises"))
            return render_template("pais_form.html", modo="novo", dados=dados,
                                   erros=erros, tecnologias=TECNOLOGIAS)
        return render_template("pais_form.html", modo="novo", dados={}, erros={},
                               tecnologias=TECNOLOGIAS)

    @app.route("/paises/<codigo>/editar", methods=["GET", "POST"])
    def editar_pais(codigo):
        atual = paises.buscar(codigo)
        if atual is None:
            flash(f"País {codigo.upper()} não encontrado.", "danger")
            return redirect(url_for("listar_paises"))
        if request.method == "POST":
            _, erros, dados = paises.alterar(codigo, request.form)
            if not erros:
                flash(f"Dados de {dados['pais']} ({dados['codigo']}) atualizados.", "success")
                return redirect(url_for("listar_paises"))
            return render_template("pais_form.html", modo="editar", dados=dados,
                                   erros=erros, tecnologias=TECNOLOGIAS)
        return render_template("pais_form.html", modo="editar", dados=atual,
                               erros={}, tecnologias=TECNOLOGIAS)

    @app.post("/paises/<codigo>/remover")
    def remover_pais(codigo):
        if paises.remover(codigo):
            flash(f"País {codigo.upper()} removido.", "success")
        else:
            flash(f"País {codigo.upper()} não encontrado.", "danger")
        return redirect(url_for("listar_paises"))

    @app.post("/paises/<codigo>/estado")
    def estado_pais(codigo):
        """Diferencial: marca o país como ativo ou em falha."""
        estado = request.form.get("estado", "")
        if estado in ESTADOS and paises.definir_estado(codigo, estado):
            texto = "em falha operacional" if estado == "falha" else "ativo novamente"
            flash(f"País {codigo.upper()} marcado como {texto}.",
                  "warning" if estado == "falha" else "success")
        else:
            flash(f"Não foi possível alterar o estado de {codigo.upper()}.", "danger")
        return redirect(url_for("cobertura", codigo=codigo.upper()))

    # ------------------------- Cobertura -------------------------
    @app.get("/cobertura")
    def cobertura():
        codigo = (request.args.get("codigo") or "").strip().upper()
        pais = None
        consultou = bool(codigo)
        busca = None
        afetados = (0, [])
        if consultou:
            pais = paises.buscar(codigo)
            busca = paises.tabela.ultima_operacao
            if pais and pais.get("estado") == "falha":
                afetados = clientes.afetados_por_pais(codigo)
        return render_template("cobertura.html", codigo=codigo, pais=pais,
                               consultou=consultou, busca=busca,
                               afetados_total=afetados[0], afetados=afetados[1])

    # ------------------------- Instrumentação -------------------------
    @app.get("/instrumentacao")
    def instrumentacao():
        codigo = (request.args.get("codigo") or "").strip().upper()
        explicacao = paises.explicar(codigo) if codigo else None
        return render_template("instrumentacao.html", dados=paises.instrumentacao(),
                               codigo=codigo, explicacao=explicacao)

    @app.post("/instrumentacao/zerar")
    def zerar_instrumentacao():
        paises.zerar_metricas()
        flash("Contadores da instrumentação zerados (os dados foram mantidos).", "info")
        return redirect(url_for("instrumentacao"))

    # ------------------------- Clientes (Árvore B) -------------------------
    @app.get("/clientes")
    def listar_clientes():
        try:
            pagina = int(request.args.get("pagina", 1))
        except ValueError:
            pagina = 1
        itens, total_paginas = clientes.listar_pagina(pagina, POR_PAGINA)
        pagina = min(max(1, pagina), total_paginas)
        return render_template("clientes.html", clientes=itens, pagina=pagina,
                               total_paginas=total_paginas, total=len(clientes),
                               por_pagina=POR_PAGINA)

    @app.get("/clientes/buscar")
    def buscar_cliente():
        cliente_id = interpretar_id(request.args.get("id"))
        if cliente_id is None:
            flash("Informe um ID de cliente válido (número inteiro).", "warning")
            return redirect(url_for("listar_clientes"))
        return redirect(url_for("detalhe_cliente", cliente_id=cliente_id))

    @app.get("/clientes/<int:cliente_id>")
    def detalhe_cliente(cliente_id):
        cliente = clientes.buscar(cliente_id)
        busca = clientes.arvore.ultima_busca
        if cliente is None:
            flash(f"Cliente {cliente_id} não encontrado na Árvore B "
                  f"({busca['nos_visitados']} nós visitados).", "danger")
            return redirect(url_for("listar_clientes"))
        return render_template("cliente_detalhe.html", cliente=cliente, busca=busca,
                               pacote=clientes.buscar_pacote(cliente["pacote"]),
                               pacotes=clientes.pacotes, paises=paises.listar())

    @app.route("/clientes/novo", methods=["GET", "POST"])
    def novo_cliente():
        if request.method == "POST":
            cliente, erros, dados = clientes.cadastrar(request.form)
            if not erros:
                flash(f"Cliente {cliente['nome']} cadastrado com o ID {cliente['id']}.", "success")
                return redirect(url_for("detalhe_cliente", cliente_id=cliente["id"]))
            return render_template("cliente_form.html", modo="novo", dados=dados,
                                   erros=erros, paises=paises.listar())
        return render_template("cliente_form.html", modo="novo", dados={}, erros={},
                               paises=paises.listar())

    @app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
    def editar_cliente(cliente_id):
        atual = clientes.buscar(cliente_id)
        if atual is None:
            flash(f"Cliente {cliente_id} não encontrado.", "danger")
            return redirect(url_for("listar_clientes"))
        if request.method == "POST":
            cliente, erros, dados = clientes.alterar(cliente_id, request.form)
            if not erros:
                flash(f"Dados do cliente {cliente_id} atualizados.", "success")
                return redirect(url_for("detalhe_cliente", cliente_id=cliente_id))
            return render_template("cliente_form.html", modo="editar", dados=dados,
                                   erros=erros, paises=paises.listar())
        return render_template("cliente_form.html", modo="editar", dados=atual,
                               erros={}, paises=paises.listar())

    @app.post("/clientes/<int:cliente_id>/esim")
    def associar_esim(cliente_id):
        if clientes.associar_esim(cliente_id) is None:
            flash(f"Cliente {cliente_id} não encontrado.", "danger")
            return redirect(url_for("listar_clientes"))
        flash("eSIM associado ao cliente.", "success")
        return redirect(url_for("detalhe_cliente", cliente_id=cliente_id))

    @app.post("/clientes/<int:cliente_id>/pacote")
    def associar_pacote(cliente_id):
        _, erro = clientes.associar_pacote(cliente_id, request.form.get("pacote", ""))
        flash(erro or "Pacote atualizado.", "danger" if erro else "success")
        return redirect(url_for("detalhe_cliente", cliente_id=cliente_id))

    @app.get("/pacotes")
    def listar_pacotes():
        return render_template("pacotes.html", pacotes=clientes.pacotes)

    # ------------------------- Consulta integrada -------------------------
    @app.get("/consulta")
    def consulta():
        cliente_id = (request.args.get("cliente") or "").strip()
        destino = (request.args.get("destino") or "").strip()
        resultado = (consulta_integrada(clientes, paises, cliente_id, destino)
                     if (cliente_id or destino) else None)
        return render_template("consulta.html", cliente_id=cliente_id, destino=destino,
                               resultado=resultado, paises=paises.listar())

    # ------------------------- Instrumentação da Árvore B -------------------------
    @app.get("/arvore")
    def arvore():
        return render_template("arvore.html", dados=clientes.instrumentacao())

    @app.post("/arvore/zerar")
    def zerar_arvore():
        clientes.zerar_metricas()
        flash("Contadores da Árvore B zerados (os dados foram mantidos).", "info")
        return redirect(url_for("arvore"))

    @app.post("/arvore/reconstruir")
    def reconstruir_arvore():
        try:
            grau = int(request.form.get("grau", ""))
        except ValueError:
            grau = 0
        if not 2 <= grau <= 50:
            flash("Informe um grau mínimo inteiro entre 2 e 50.", "danger")
        else:
            clientes.reconstruir(grau)
            flash(f"Árvore B reconstruída com grau mínimo t = {grau} "
                  f"(vale até reiniciar a aplicação).", "success")
        return redirect(url_for("arvore"))

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True)
