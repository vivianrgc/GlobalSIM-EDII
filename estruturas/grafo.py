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
PENDENTE
