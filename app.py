"""GlobalSIM — Etapa 1: Tabela Hash + Aplicação Web (Flask).

As rotas só tratam HTTP (request, render_template, redirect, flash). Toda a
lógica das estruturas fica em estruturas/ e servicos/.
Rotas que alteram dados usam POST e o padrão Post/Redirect/Get.
"""

import os

from flask import Flask, flash, redirect, render_template, request, url_for

from servicos import TECNOLOGIAS, PaisesService

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def criar_app(caminho_paises: str | None = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "globalsim-dev-key")

    paises = PaisesService(
        caminho_paises or os.path.join(BASE_DIR, "arquivos", "paises.json")
    )
    app.config["PAISES"] = paises

    # ------------------------- Página inicial -------------------------
    @app.get("/")
    def index():
        return render_template(
            "index.html",
            total=len(paises.tabela),
            estatisticas=paises.tabela.estatisticas(),
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

    # ------------------------- Cobertura -------------------------
    @app.get("/cobertura")
    def cobertura():
        codigo = (request.args.get("codigo") or "").strip().upper()
        pais = None
        consultou = bool(codigo)
        busca = None
        if consultou:
            pais = paises.buscar(codigo)
            busca = paises.tabela.ultima_operacao
        return render_template("cobertura.html", codigo=codigo, pais=pais,
                               consultou=consultou, busca=busca)

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

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True)
