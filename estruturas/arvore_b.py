"""Árvore B própria (grau mínimo t configurável) com instrumentação.

Usada na Etapa 2 para guardar os clientes (chave = ID inteiro do cliente).

Definições (grau mínimo t >= 2):
  * todo nó, exceto a raiz, tem entre t-1 e 2t-1 chaves;
  * a raiz tem entre 1 e 2t-1 chaves (ou 0, se a árvore está vazia);
  * um nó interno com k chaves tem k+1 filhos;
  * todas as folhas ficam no mesmo nível.

Inserção "proativa" (estilo CLRS): ao descer, todo nó cheio (2t-1 chaves) é
dividido ANTES de entrar nele, então nunca é preciso subir de volta. Quando a
raiz está cheia, a árvore cresce em altura por cima (nova raiz).

Não há remoção: o enunciado só pede busca, inserção, alteração e listagem.
A alteração é uma busca seguida de substituição do registro no nó achado.

Nenhum dict/lista nativa é usada como mecanismo de busca: a busca desce pelos
nós comparando chaves. As listas Python são só o contêiner das chaves, dos
registros e dos filhos de cada nó.

Instrumentação:
  * altura, total de nós, total de chaves, ocupação dos nós;
  * total de divisões de nó (splits) acumulado;
  * por busca: nós visitados, comparações de chave e caminho percorrido.
"""

from __future__ import annotations

from typing import Any, Iterator


class NoB:
    """Nó da Árvore B: chaves ordenadas, registros paralelos e filhos."""

    __slots__ = ("chaves", "registros", "filhos", "folha")

    def __init__(self, folha: bool = True):
        self.chaves: list[int] = []
        self.registros: list[Any] = []
        self.filhos: list[NoB] = []
        self.folha = folha

    def cheio(self, t: int) -> bool:
        return len(self.chaves) == 2 * t - 1


class ArvoreB:
    def __init__(self, grau_minimo: int = 3):
        if grau_minimo < 2:
            raise ValueError("O grau mínimo da Árvore B deve ser >= 2.")
        self.t = grau_minimo
        self.raiz = NoB(folha=True)
        self._tamanho = 0
        self._total_nos = 1
        self.zerar_metricas()

    # ------------------------------------------------------------------
    # Métricas
    # ------------------------------------------------------------------
    def zerar_metricas(self) -> None:
        """Zera os contadores de uso (a estrutura e os dados não mudam)."""
        self.metricas = {
            "insercoes": 0,
            "buscas": 0,
            "buscas_com_sucesso": 0,
            "atualizacoes": 0,
            "nos_visitados_total": 0,
            "comparacoes": 0,
            "divisoes": 0,
        }
        self.ultima_busca: dict | None = None

    def __len__(self) -> int:
        return self._tamanho

    @property
    def max_chaves(self) -> int:
        return 2 * self.t - 1

    @property
    def total_nos(self) -> int:
        return self._total_nos

    def altura(self) -> int:
        """Número de níveis (uma árvore só com a raiz tem altura 1)."""
        nivel, no = 1, self.raiz
        while not no.folha:
            no = no.filhos[0]
            nivel += 1
        return nivel

    def estatisticas(self) -> dict:
        niveis = self.niveis()
        chaves = self._tamanho
        capacidade_total = self._total_nos * self.max_chaves
        return {
            "grau_minimo": self.t,
            "min_chaves_no": self.t - 1,
            "max_chaves_no": self.max_chaves,
            "max_filhos_no": 2 * self.t,
            "altura": self.altura(),
            "total_nos": self._total_nos,
            "total_chaves": chaves,
            "ocupacao": (chaves / capacidade_total) if capacidade_total else 0.0,
            "nos_por_nivel": [len(n) for n in niveis],
            "total_divisoes": self.metricas["divisoes"],
        }

    def niveis(self) -> list[list[NoB]]:
        """Nós agrupados por nível (da raiz para as folhas)."""
        atual = [self.raiz]
        resultado = []
        while atual:
            resultado.append(atual)
            proximo = []
            for no in atual:
                proximo.extend(no.filhos)
            atual = proximo
        return resultado

    def visao_niveis(self, limite_nos: int = 24) -> list[dict]:
        """Estrutura pronta para a tela: por nível, os primeiros nós e as chaves."""
        visao = []
        for i, nos in enumerate(self.niveis()):
            visao.append({
                "nivel": i,
                "total_nos": len(nos),
                "nos": [list(no.chaves) for no in nos[:limite_nos]],
                "truncado": len(nos) > limite_nos,
            })
        return visao

    # ------------------------------------------------------------------
    # Busca
    # ------------------------------------------------------------------
    def _descer(self, chave: int) -> tuple[NoB | None, int, int, int, list[list[int]]]:
        """Desce da raiz até a chave.

        Retorna (nó onde achou | None, posição no nó, nós visitados,
        comparações, caminho). Em cada nó a busca é linear: avança enquanto
        a chave procurada for maior que a chave do nó.
        """
        no = self.raiz
        visitados = 0
        comparacoes = 0
        caminho: list[list[int]] = []
        while True:
            visitados += 1
            caminho.append(list(no.chaves))
            i = 0
            while i < len(no.chaves):
                comparacoes += 1
                if chave > no.chaves[i]:
                    i += 1
                else:
                    break
            if i < len(no.chaves):
                comparacoes += 1  # teste de igualdade
                if chave == no.chaves[i]:
                    return no, i, visitados, comparacoes, caminho
            if no.folha:
                return None, i, visitados, comparacoes, caminho
            no = no.filhos[i]

    def _registrar_busca(self, operacao: str, chave: int, achou: bool,
                         visitados: int, comparacoes: int, caminho: list) -> None:
        self.metricas["buscas"] += 1
        self.metricas["nos_visitados_total"] += visitados
        self.metricas["comparacoes"] += comparacoes
        if achou:
            self.metricas["buscas_com_sucesso"] += 1
        self.ultima_busca = {
            "operacao": operacao,
            "chave": chave,
            "encontrado": achou,
            "nos_visitados": visitados,
            "comparacoes": comparacoes,
            "caminho": caminho,
            "altura": self.altura(),
        }

    def buscar(self, chave: int) -> Any | None:
        """Registro da chave, ou None. Atualiza a instrumentação."""
        no, i, visitados, comparacoes, caminho = self._descer(chave)
        self._registrar_busca("buscar", chave, no is not None, visitados,
                              comparacoes, caminho)
        return no.registros[i] if no is not None else None

    def contem(self, chave: int) -> bool:
        """Existe a chave? Não mexe nas métricas (uso interno/validação)."""
        return self._descer(chave)[0] is not None

    def atualizar(self, chave: int, novo_registro: Any) -> bool:
        """Alteração = busca + troca do registro no nó encontrado."""
        no, i, visitados, comparacoes, caminho = self._descer(chave)
        self._registrar_busca("atualizar", chave, no is not None, visitados,
                              comparacoes, caminho)
        if no is None:
            return False
        no.registros[i] = novo_registro
        self.metricas["atualizacoes"] += 1
        return True

    # ------------------------------------------------------------------
    # Inserção (com divisão de nó)
    # ------------------------------------------------------------------
    def _dividir_filho(self, pai: NoB, i: int) -> None:
        """Divide o filho cheio pai.filhos[i] em dois nós de t-1 chaves.

        A chave do meio sobe para o pai, na posição i.
        """
        t = self.t
        y = pai.filhos[i]
        z = NoB(folha=y.folha)

        chave_meio, registro_meio = y.chaves[t - 1], y.registros[t - 1]
        z.chaves = y.chaves[t:]
        z.registros = y.registros[t:]
        y.chaves = y.chaves[: t - 1]
        y.registros = y.registros[: t - 1]
        if not y.folha:
            z.filhos = y.filhos[t:]
            y.filhos = y.filhos[:t]

        pai.chaves.insert(i, chave_meio)
        pai.registros.insert(i, registro_meio)
        pai.filhos.insert(i + 1, z)

        self._total_nos += 1
        self.metricas["divisoes"] += 1

    def inserir(self, chave: int, registro: Any) -> bool:
        """Insere a chave. Retorna False se ela já existir (chave única)."""
        if self.contem(chave):
            return False

        raiz = self.raiz
        if raiz.cheio(self.t):
            nova_raiz = NoB(folha=False)
            nova_raiz.filhos.append(raiz)
            self.raiz = nova_raiz
            self._total_nos += 1
            self._dividir_filho(nova_raiz, 0)
            raiz = nova_raiz

        no = raiz
        while not no.folha:
            i = len(no.chaves) - 1
            while i >= 0 and chave < no.chaves[i]:
                i -= 1
            i += 1
            if no.filhos[i].cheio(self.t):
                self._dividir_filho(no, i)
                if chave > no.chaves[i]:
                    i += 1
            no = no.filhos[i]

        i = len(no.chaves) - 1
        while i >= 0 and chave < no.chaves[i]:
            i -= 1
        no.chaves.insert(i + 1, chave)
        no.registros.insert(i + 1, registro)

        self._tamanho += 1
        self.metricas["insercoes"] += 1
        return True

    # ------------------------------------------------------------------
    # Percurso em ordem (listagem)
    # ------------------------------------------------------------------
    def em_ordem(self) -> Iterator[tuple[int, Any]]:
        """Gera (chave, registro) em ordem crescente de chave."""
        yield from self._em_ordem(self.raiz)

    def _em_ordem(self, no: NoB) -> Iterator[tuple[int, Any]]:
        for i, chave in enumerate(no.chaves):
            if not no.folha:
                yield from self._em_ordem(no.filhos[i])
            yield chave, no.registros[i]
        if not no.folha:
            yield from self._em_ordem(no.filhos[-1])

    def maior_chave(self) -> int | None:
        """Maior chave: desce sempre pelo filho mais à direita."""
        if self._tamanho == 0:
            return None
        no = self.raiz
        while not no.folha:
            no = no.filhos[-1]
        return no.chaves[-1]

    # ------------------------------------------------------------------
    # Verificação (usada nos testes)
    # ------------------------------------------------------------------
    def verificar_invariantes(self) -> None:
        """Levanta AssertionError se alguma propriedade da Árvore B falhar."""
        folhas: list[int] = []
        contagem = {"nos": 0, "chaves": 0}

        def visitar(no: NoB, nivel: int, minimo: Any, maximo: Any, eh_raiz: bool) -> None:
            contagem["nos"] += 1
            contagem["chaves"] += len(no.chaves)
            assert len(no.chaves) == len(no.registros)
            assert len(no.chaves) <= self.max_chaves, "nó com chaves demais"
            if not eh_raiz:
                assert len(no.chaves) >= self.t - 1, "nó com chaves de menos"
            assert no.chaves == sorted(no.chaves), "chaves fora de ordem no nó"
            assert len(set(no.chaves)) == len(no.chaves), "chave repetida no nó"
            for c in no.chaves:
                assert minimo is None or c > minimo
                assert maximo is None or c < maximo
            if no.folha:
                assert not no.filhos
                folhas.append(nivel)
                return
            assert len(no.filhos) == len(no.chaves) + 1, "filhos != chaves + 1"
            limites = [minimo] + list(no.chaves) + [maximo]
            for j, filho in enumerate(no.filhos):
                visitar(filho, nivel + 1, limites[j], limites[j + 1], False)

        visitar(self.raiz, 1, None, None, True)
        assert len(set(folhas)) <= 1, "folhas em níveis diferentes"
        assert contagem["nos"] == self._total_nos, "contador de nós diverge"
        assert contagem["chaves"] == self._tamanho, "contador de chaves diverge"
