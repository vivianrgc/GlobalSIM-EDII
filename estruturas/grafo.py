"""Grafo ponderado não direcionado (lista de adjacência) — adiantado da Etapa 3.

Vértices são códigos de país ("BR", "PT"...) e o peso de cada aresta é a
latência em ms. Ainda não há tela nem rede.json: aqui só existe a estrutura
e os algoritmos (BFS, DFS e Dijkstra), cobertos por testes.

Representação (sem dict):
  * _vertices : lista com os códigos, na ordem de criação (posição = índice);
  * _indice   : TabelaHash própria (Etapa 1) código -> índice do vértice;
  * _adj      : lista de adjacência; _adj[i] é a lista de pares
                (índice_vizinho, peso) do vértice i.
Os algoritmos trabalham com listas indexadas pelo índice do vértice.
"""

from __future__ import annotations

from .tabela_hash import TabelaHash

INFINITO = float("inf")


class Grafo:
    def __init__(self):
        self._vertices: list[str] = []
        self._indice = TabelaHash()
        self._adj: list[list[tuple[int, int]]] = []

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self._vertices)

    @property
    def vertices(self) -> list[str]:
        return list(self._vertices)

    def tem_vertice(self, codigo: str) -> bool:
        return self._indice.contem(codigo)

    def adicionar_vertice(self, codigo: str) -> int:
        """Cria o vértice se não existir; devolve o índice dele."""
        existente = self._indice.contem(codigo)
        if existente:
            return self._indice.buscar(codigo)
        indice = len(self._vertices)
        self._vertices.append(codigo)
        self._adj.append([])
        self._indice.inserir(codigo, indice)
        return indice

    def adicionar_aresta(self, a: str, b: str, peso: int) -> None:
        """Aresta não direcionada a—b. Se já existir, só troca o peso."""
        if peso <= 0:
            raise ValueError("O peso (latência) da aresta deve ser positivo.")
        if a == b:
            raise ValueError("Não são permitidas arestas de um vértice para ele mesmo.")
        i, j = self.adicionar_vertice(a), self.adicionar_vertice(b)
        self._definir(i, j, peso)
        self._definir(j, i, peso)

    def _definir(self, de: int, para: int, peso: int) -> None:
        lista = self._adj[de]
        for k, (vizinho, _) in enumerate(lista):
            if vizinho == para:
                lista[k] = (para, peso)
                return
        lista.append((para, peso))

    def arestas(self) -> list[tuple[str, str, int]]:
        """Cada aresta uma única vez, como (a, b, peso)."""
        resultado = []
        for i, lista in enumerate(self._adj):
            for j, peso in lista:
                if i < j:
                    resultado.append((self._vertices[i], self._vertices[j], peso))
        return resultado

    def vizinhos(self, codigo: str) -> list[tuple[str, int]]:
        if not self._indice.contem(codigo):
            return []
        i = self._indice.buscar(codigo)
        return [(self._vertices[j], peso) for j, peso in self._adj[i]]

    def _posicao(self, codigo: str) -> int:
        if not self._indice.contem(codigo):
            raise KeyError(f"Vértice {codigo} não existe no grafo.")
        return self._indice.buscar(codigo)

    # ------------------------------------------------------------------
    # BFS — busca em largura (fila)
    # ------------------------------------------------------------------
    def bfs(self, origem: str) -> list[str]:
        """Ordem de visita da busca em largura a partir de origem."""
        inicio = self._posicao(origem)
        visitado = [False] * len(self._vertices)
        fila = [inicio]
        visitado[inicio] = True
        cabeca = 0  # fila por índice: evita o custo de pop(0)
        ordem = []
        while cabeca < len(fila):
            atual = fila[cabeca]
            cabeca += 1
            ordem.append(self._vertices[atual])
            for vizinho, _ in self._adj[atual]:
                if not visitado[vizinho]:
                    visitado[vizinho] = True
                    fila.append(vizinho)
        return ordem

    # ------------------------------------------------------------------
    # DFS — busca em profundidade (recursiva)
    # ------------------------------------------------------------------
    def dfs(self, origem: str) -> list[str]:
        """Ordem de visita da busca em profundidade a partir de origem."""
        inicio = self._posicao(origem)
        visitado = [False] * len(self._vertices)
        ordem: list[str] = []

        def visitar(v: int) -> None:
            visitado[v] = True
            ordem.append(self._vertices[v])
            for vizinho, _ in self._adj[v]:
                if not visitado[vizinho]:
                    visitar(vizinho)

        visitar(inicio)
        return ordem

    # ------------------------------------------------------------------
    # Dijkstra — caminho de menor latência
    # ------------------------------------------------------------------
    def dijkstra(self, origem: str, destino: str) -> dict | None:
        """Menor caminho entre origem e destino.

        Retorna {"caminho": [códigos], "custo": ms, "arestas": [(a, b, ms)]}
        ou None se o destino for inalcançável. Seleção do próximo vértice por
        varredura linear (O(V²)): simples e suficiente para poucos países.
        """
        s, d = self._posicao(origem), self._posicao(destino)
        n = len(self._vertices)
        dist = [INFINITO] * n
        anterior = [-1] * n
        fechado = [False] * n
        dist[s] = 0

        for _ in range(n):
            u, melhor = -1, INFINITO
            for v in range(n):
                if not fechado[v] and dist[v] < melhor:
                    u, melhor = v, dist[v]
            if u == -1 or u == d:
                break
            fechado[u] = True
            for v, peso in self._adj[u]:
                if not fechado[v] and dist[u] + peso < dist[v]:
                    dist[v] = dist[u] + peso
                    anterior[v] = u

        if dist[d] == INFINITO:
            return None
        indices = []
        atual = d
        while atual != -1:
            indices.append(atual)
            atual = anterior[atual]
        indices.reverse()
        caminho = [self._vertices[i] for i in indices]
        trechos = []
        for x, y in zip(indices, indices[1:]):
            peso = next(p for v, p in self._adj[x] if v == y)
            trechos.append((self._vertices[x], self._vertices[y], peso))
        return {"caminho": caminho, "custo": dist[d], "arestas": trechos}
