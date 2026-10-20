"""Tabela Hash com encadeamento separado (separate chaining) e instrumentação.

Implementação própria, sem usar dict como mecanismo de busca: o dict nativo
NÃO é usado para guardar os registros. Cada posição (bucket) da tabela é uma
lista encadeada de pares [chave, valor]; as listas Python são usadas apenas
como contêiner interno dos buckets, como permitido no enunciado.

Principais decisões:
  * Função hash polinomial (djb2): h = h * 33 + ord(c), começando em 5381.
  * Índice = h mod capacidade. Capacidade sempre PRIMA para espalhar melhor.
  * Colisões resolvidas por encadeamento.
  * Redimensionamento (rehash) automático quando o fator de carga passa do
    limite (padrão 0,75): a capacidade vira o próximo primo >= 2 * capacidade.
  * Instrumentação: contadores globais + registro da última operação
    (índice, hash, comparações, colisão) para observar a estrutura na Web.
"""

from __future__ import annotations

from typing import Any, Iterator


def _eh_primo(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def proximo_primo(n: int) -> int:
    """Menor número primo >= n."""
    while not _eh_primo(n):
        n += 1
    return n


def funcao_hash(chave: str) -> int:
    """Hash djb2 (valor inteiro completo, antes do mod)."""
    h = 5381
    for caractere in chave:
        h = h * 33 + ord(caractere)
    return h


def explicar_hash(chave: str, capacidade: int) -> dict:
    """Passo a passo do cálculo do hash, para fins didáticos na interface."""
    passos = []
    h = 5381
    for caractere in chave:
        antes = h
        h = h * 33 + ord(caractere)
        passos.append({
            "caractere": caractere,
            "codigo": ord(caractere),
            "calculo": f"{antes} × 33 + {ord(caractere)}",
            "resultado": h,
        })
    return {
        "chave": chave,
        "passos": passos,
        "hash": h,
        "capacidade": capacidade,
        "indice": h % capacidade,
    }


class TabelaHash:
    """Tabela Hash com encadeamento separado e redimensionamento dinâmico."""

    def __init__(self, capacidade_inicial: int = 7, fator_carga_max: float = 0.75):
        self._capacidade = proximo_primo(max(2, capacidade_inicial))
        self._fator_carga_max = fator_carga_max
        self._buckets: list[list[list[Any]]] = [[] for _ in range(self._capacidade)]
        self._tamanho = 0
        self.zerar_metricas()

    # ------------------------------------------------------------------
    # Instrumentação
    # ------------------------------------------------------------------
    def zerar_metricas(self) -> None:
        """Zera contadores acumulados (não altera os dados armazenados)."""
        self.metricas = {
            "insercoes": 0,
            "buscas": 0,
            "buscas_com_sucesso": 0,
            "atualizacoes": 0,
            "remocoes": 0,
            "colisoes": 0,
            "redimensionamentos": 0,
            "comparacoes": 0,
        }
        self.ultima_operacao: dict | None = None
        self.historico_redimensionamentos: list[dict] = []

    def _registrar(self, operacao: str, chave: str, hash_completo: int,
                   indice: int, comparacoes: int, **extras) -> None:
        self.metricas["comparacoes"] += comparacoes
        self.ultima_operacao = {
            "operacao": operacao,
            "chave": chave,
            "hash": hash_completo,
            "indice": indice,
            "comparacoes": comparacoes,
            "capacidade": self._capacidade,
            **extras,
        }

    def estatisticas(self) -> dict:
        """Retrato atual da estrutura (tamanho, carga, distribuição)."""
        comprimentos = [len(b) for b in self._buckets]
        usados = [c for c in comprimentos if c > 0]
        return {
            "tamanho": self._tamanho,
            "capacidade": self._capacidade,
            "fator_carga": self._tamanho / self._capacidade,
            "fator_carga_max": self._fator_carga_max,
            "buckets_usados": len(usados),
            "buckets_vazios": self._capacidade - len(usados),
            "maior_cadeia": max(comprimentos) if comprimentos else 0,
            "media_cadeia": (sum(usados) / len(usados)) if usados else 0.0,
            "comprimentos": comprimentos,
        }

    def visao_buckets(self) -> list[dict]:
        """Conteúdo de cada bucket (índice + chaves encadeadas)."""
        return [
            {"indice": i, "chaves": [par[0] for par in bucket], "tamanho": len(bucket)}
            for i, bucket in enumerate(self._buckets)
        ]

    # ------------------------------------------------------------------
    # Operações principais
    # ------------------------------------------------------------------
    def _indice(self, chave: str) -> tuple[int, int]:
        h = funcao_hash(chave)
        return h, h % self._capacidade

    def inserir(self, chave: str, valor: Any) -> bool:
        """Insere um novo par. Retorna False (sem alterar) se a chave já existe."""
        if (self._tamanho + 1) / self._capacidade > self._fator_carga_max:
            self._redimensionar()

        h, indice = self._indice(chave)
        bucket = self._buckets[indice]
        comparacoes = 0
        for par in bucket:
            comparacoes += 1
            if par[0] == chave:
                self._registrar("inserir", chave, h, indice, comparacoes,
                                colisao=False, resultado="duplicada")
                return False

        colisao = len(bucket) > 0
        bucket.append([chave, valor])
        self._tamanho += 1
        self.metricas["insercoes"] += 1
        if colisao:
            self.metricas["colisoes"] += 1
        self._registrar("inserir", chave, h, indice, comparacoes,
                        colisao=colisao, resultado="inserida")
        return True

    def buscar(self, chave: str) -> Any | None:
        """Retorna o valor associado à chave, ou None se não existir."""
        h, indice = self._indice(chave)
        comparacoes = 0
        valor = None
        encontrado = False
        for par in self._buckets[indice]:
            comparacoes += 1
            if par[0] == chave:
                valor = par[1]
                encontrado = True
                break
        self.metricas["buscas"] += 1
        if encontrado:
            self.metricas["buscas_com_sucesso"] += 1
        self._registrar("buscar", chave, h, indice, comparacoes,
                        colisao=False,
                        resultado="encontrada" if encontrado else "não encontrada")
        return valor

    def atualizar(self, chave: str, novo_valor: Any) -> bool:
        """Substitui o valor de uma chave existente. False se não existir."""
        h, indice = self._indice(chave)
        comparacoes = 0
        for par in self._buckets[indice]:
            comparacoes += 1
            if par[0] == chave:
                par[1] = novo_valor
                self.metricas["atualizacoes"] += 1
                self._registrar("atualizar", chave, h, indice, comparacoes,
                                colisao=False, resultado="atualizada")
                return True
        self._registrar("atualizar", chave, h, indice, comparacoes,
                        colisao=False, resultado="não encontrada")
        return False

    def remover(self, chave: str) -> bool:
        """Remove a chave. Retorna False se ela não existir."""
        h, indice = self._indice(chave)
        bucket = self._buckets[indice]
        comparacoes = 0
        for posicao, par in enumerate(bucket):
            comparacoes += 1
            if par[0] == chave:
                del bucket[posicao]
                self._tamanho -= 1
                self.metricas["remocoes"] += 1
                self._registrar("remover", chave, h, indice, comparacoes,
                                colisao=False, resultado="removida")
                return True
        self._registrar("remover", chave, h, indice, comparacoes,
                        colisao=False, resultado="não encontrada")
        return False

    def contem(self, chave: str) -> bool:
        """Verificação de existência SEM afetar as métricas."""
        _, indice = self._indice(chave)
        return any(par[0] == chave for par in self._buckets[indice])

    # ------------------------------------------------------------------
    # Rehash
    # ------------------------------------------------------------------
    def _redimensionar(self) -> None:
        capacidade_antiga = self._capacidade
        itens = [(par[0], par[1]) for bucket in self._buckets for par in bucket]
        self._capacidade = proximo_primo(capacidade_antiga * 2)
        self._buckets = [[] for _ in range(self._capacidade)]
        for chave, valor in itens:  # reinserção sem contar como operação do usuário
            _, indice = self._indice(chave)
            self._buckets[indice].append([chave, valor])
        self.metricas["redimensionamentos"] += 1
        self.historico_redimensionamentos.append({
            "de": capacidade_antiga,
            "para": self._capacidade,
            "elementos": len(itens),
        })

    # ------------------------------------------------------------------
    # Iteração
    # ------------------------------------------------------------------
    def itens(self) -> Iterator[tuple[str, Any]]:
        """Percorre os pares na ordem física da tabela (bucket a bucket)."""
        for bucket in self._buckets:
            for chave, valor in bucket:
                yield chave, valor

    def __len__(self) -> int:
        return self._tamanho

    def __contains__(self, chave: str) -> bool:
        return self.contem(chave)
