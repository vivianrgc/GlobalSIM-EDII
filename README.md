# GlobalSIM EDII — Serviço Internacional de Internet por eSIM

Trabalho prático de **Estruturas de Dados II** · Sistemas de Informação · DCET/UNEB · Profa. Maria Inés Restovic

> **Status:** Etapa 2 — Árvore B + clientes (entrega 24/11/2026) · Etapa 1 (Tabela Hash + Web, 20/10/2026) já entregue

## 1. Identificação da equipe

| Nome | Matrícula | GitHub |
|------|-----------|--------|
| Vivian Rafaela Gonzaga | _preencher_ | _preencher_ |
| _integrante 2_ | _preencher_ | _preencher_ |
| _integrante 3_ | _preencher_ | _preencher_ |

## 2. Como executar

Requisitos: Python 3.10+.

```bash
git clone <url-do-repositorio>
cd globalsim

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python app.py                    # http://127.0.0.1:5000
```

Na primeira execução a aplicação gera `arquivos/clientes.json` (1.000 clientes fictícios, sempre os mesmos) se o arquivo não existir. Para gerar de novo, com outra quantidade ou semente:

```bash
python scripts/gerar_clientes.py            # 1000 clientes, semente 2026
python scripts/gerar_clientes.py 1500 7     # quantidade e semente
```

O grau mínimo da Árvore B é 3 por padrão; mude com a variável `GLOBALSIM_GRAU_B` (ex.: `GLOBALSIM_GRAU_B=5 python app.py`) ou, com a aplicação rodando, na tela `/arvore`.

Testes automatizados (Tabela Hash, Árvore B, Grafo e rotas Flask):

```bash
python -m unittest discover -s tests -v
```

## 3. Estrutura do projeto

```
globalsim/
├── app.py                    # rotas Flask (somente HTTP)
├── estruturas/
│   ├── tabela_hash.py        # Tabela Hash própria + instrumentação (Etapa 1)
│   ├── arvore_b.py           # Árvore B própria + instrumentação (Etapa 2)
│   └── grafo.py              # Grafo ponderado: lista de adjacência, BFS, DFS, Dijkstra (adiantado da Etapa 3)
├── servicos/
│   ├── paises_service.py     # países: Tabela Hash + persistência JSON
│   ├── clientes_service.py   # clientes: Árvore B + persistência JSON
│   ├── integracao.py         # consulta integrada cliente (Árvore B) + país (Hash) + pacote
│   └── gerador_clientes.py   # gerador dos clientes fictícios
├── scripts/
│   └── gerar_clientes.py     # linha de comando do gerador
├── arquivos/
│   ├── paises.json           # persistência dos países
│   ├── pacotes.json          # os 5 pacotes de dados
│   └── clientes.json         # ~1000 clientes (gerado na primeira execução)
├── templates/                # Jinja (países, clientes, consulta, árvore, instrumentação...)
├── static/css/estilo.css
└── tests/                   # test_etapa1.py e test_etapa2.py
```

A lógica das estruturas está **separada das rotas**: `app.py` só usa `request`, `render_template`, `redirect` e `flash`; as regras ficam em `servicos/` e `estruturas/`.

## 4. Estrutura implementada na Etapa 1: Tabela Hash

Arquivo: [`estruturas/tabela_hash.py`](estruturas/tabela_hash.py). Chave: **código do país** (2 letras, ex.: `IT`).

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Função hash | djb2 (`h = h·33 + ord(c)`, início 5381) | Simples, bem distribuída para strings curtas |
| Índice | `hash mod capacidade` | |
| Capacidade | Sempre **número primo** (inicial 7) | Reduz agrupamentos no mod |
| Colisões | **Encadeamento separado** (cada bucket é uma cadeia de pares chave/valor) | Remoção simples, degrada de forma suave |
| Rehash | Se `(n+1)/capacidade > 0,75`, a capacidade vira o próximo primo ≥ 2× | Mantém cadeias curtas (busca média O(1)) |
| Uso de `dict` | **Não** é usado para guardar nem buscar registros | Listas Python são só o contêiner interno dos buckets |

Operações: `inserir`, `buscar`, `atualizar`, `remover`, `contem` (sem afetar métricas), `itens`, `estatisticas`.

### Persistência (JSON → estrutura → JSON)

1. Na inicialização, `arquivos/paises.json` é lido e **cada país é inserido na Tabela Hash**.
2. Todas as consultas, alterações e remoções são feitas **na Tabela Hash** (nunca na lista do JSON).
3. Após cada alteração, a tabela é gravada de volta no JSON (escrita atômica: arquivo temporário + `os.replace`).

### Instrumentação básica (página `/instrumentacao`)

- **Contadores acumulados:** inserções, buscas (com sucesso), atualizações, remoções, colisões, comparações de chave, redimensionamentos.
- **Retrato da estrutura:** elementos, capacidade, fator de carga, buckets usados/vazios, maior cadeia, média por bucket usado.
- **Última operação:** chave, hash completo, índice, nº de comparações, se houve colisão.
- **Histórico de rehash** (ex.: `7 → 17`).
- **Visão dos buckets** com as cadeias (linhas amarelas = colisão).
- **Calculadora de hash** passo a passo (`/instrumentacao?codigo=IT`).
- A página de **cobertura** também mostra como a tabela respondeu (indice e comparações).

Exemplo real após a carga inicial dos 8 países (capacidade 7 → 17 com 1 rehash):

| Métrica | Valor |
|---------|-------|
| Elementos / capacidade | 8 / 17 (fator de carga 0,47) |
| Colisões | 3 (durante a carga e antes do rehash) |
| Buckets usados / vazios | 7 / 10 |
| Maior cadeia | 2 (`US → CA` no bucket 7) |

## 5. Estrutura implementada na Etapa 2: Árvore B

Arquivo: `estruturas/arvore_b.py`. Chave: **ID do cliente** (inteiro, único). Guarda o registro completo do cliente no próprio nó.

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Grau mínimo `t` | Configurável (padrão 3) | Cada nó tem de `t-1` a `2t-1` chaves (a raiz, de 1 a `2t-1`) e até `2t` filhos |
| Busca | Desce da raiz comparando as chaves do nó e escolhe o filho | Conta nós visitados, comparações e guarda o caminho |
| Inserção | Divisão preventiva (proativa): todo nó cheio é dividido **antes** de descer | Nunca precisa subir de volta; se a raiz está cheia, a árvore cresce por cima (nova raiz) |
| Chave duplicada | Recusada (a inserção devolve `False`) | O ID do cliente é único |
| Alteração | Busca + troca do registro no nó encontrado | O ID (chave) não muda |
| Listagem | Percurso **em ordem** (ordem crescente de ID); a paginação pula os itens anteriores | Não precisa ordenar nada à parte |
| Remoção | Não implementada | O enunciado só pede busca, inserção, alteração e listagem |

As listas Python são só o conteiner interno de cada nó (chaves, registros e filhos); a busca é feita descendo pelos nós, sem `dict`.

**Persistência:** `arquivos/clientes.json` é lido ao iniciar (cada cliente é inserido na árvore) e regravado após cada alteração (escrita atômica, em ordem de ID). Toda consulta passa pela Árvore B.

**Dados:** `scripts/gerar_clientes.py` gera ~1.000 clientes fictícios com ID único (campos: `id`, `nome`, `email`, `pais_origem`, `destino`, `esim`, `pacote`). `arquivos/pacotes.json` traz os 5 pacotes (id, nome, regiões cobertas, GB, validade e preço).

### Instrumentação da Árvore B (página `/arvore`)

- **Altura** (níveis), **total de nós**, nós por nível, ocupação média dos nós.
- **Total de divisões de nó** (splits), acumulado, incluindo a carga inicial.
- **Nós visitados na última busca**, com as comparações e o caminho percorrido (também exibidos no cadastro do cliente e na consulta integrada).
- Contadores acumulados (inserções, buscas, atualizações, comparações) e visão dos nós por nível.
- "Reconstruir com t": refaz a árvore com outro grau mínimo para comparar altura e número de nós (vale até reiniciar; o JSON não muda).

### Consulta integrada (`/consulta`)

Recebe o ID do cliente e o país de destino e mostra as duas etapas:

1. **Árvore B:** busca o cliente pelo ID (nós visitados e caminho).
2. **Tabela Hash:** busca o país pelo código (hash, índice e comparações).

Depois cruza com o eSIM, o pacote contratado (a região do país precisa estar nas regiões do pacote) e o estado operacional do país, e sugere pacotes que cobrem a região quando o atual não cobre.

### Grafo (adiantado da Etapa 3, ainda sem tela)

`estruturas/grafo.py`: lista de adjacência com pesos (latência em ms), **BFS**, **DFS** e **Dijkstra**. Sem `dict`: os vértices ficam numa lista, e o índice de cada código é guardado na própria Tabela Hash. Os algoritmos têm testes em `tests/test_etapa2.py` com uma rede pequena de exemplo; a `rede.json` oficial e as telas entram na Etapa 3.

## 6. Funcionalidades Web

| Rota | Método | Função |
|------|--------|--------|
| `/` | GET | Página inicial |
| `/paises` | GET | Listagem dos países |
| `/paises/novo` | GET, POST | Cadastro (validação + Post/Redirect/Get) |
| `/paises/<codigo>/editar` | GET, POST | Alteração (o código/chave é imutável) |
| `/paises/<codigo>/remover` | POST | Remoção |
| `/cobertura?codigo=IT` | GET | Consulta de cobertura por código |
| `/instrumentacao` | GET | Instrumentação da Tabela Hash |
| `/instrumentacao/zerar` | POST | Zera contadores (mantém os dados) |
| `/paises/<codigo>/estado` | POST | Marca o país como `ativo` ou `falha` (diferencial) |
| `/clientes?pagina=N` | GET | Listagem paginada (25 por página), em ordem de ID |
| `/clientes/buscar?id=N` | GET | Consulta por ID (redireciona ao cadastro do cliente) |
| `/clientes/<id>` | GET | Cadastro do cliente + como a Árvore B respondeu |
| `/clientes/novo` | GET, POST | Cadastro (ID automático, validação + Post/Redirect/Get) |
| `/clientes/<id>/editar` | GET, POST | Alteração (o ID é imutável) |
| `/clientes/<id>/esim` | POST | Gera e associa o eSIM |
| `/clientes/<id>/pacote` | POST | Associa (ou troca) o pacote |
| `/pacotes` | GET | Os 5 pacotes de dados |
| `/consulta?cliente=ID&destino=IT` | GET | Consulta integrada (Árvore B + Tabela Hash + pacote) |
| `/arvore` | GET | Instrumentação da Árvore B |
| `/arvore/zerar` | POST | Zera contadores (mantém os dados) |
| `/arvore/reconstruir` | POST | Reconstrói a árvore com outro grau mínimo `t` |

Rotas que alteram dados usam **POST** com **Post/Redirect/Get** (`redirect` + `flash`). Validações: código do país com 2 letras, sem duplicidade, campos obrigatórios, tecnologia válida; nos clientes, nome, e-mail e país de origem/destino existentes na Tabela Hash.

## 7. Diferencial da equipe (descrição inicial) — a confirmar

> ⚠️ **Proposta para validação da equipe e aprovação da professora** (o enunciado exige aprovação prévia). Se a equipe preferir outro, é só substituir esta seção.

**Simulação de falhas de conexões e recálculo automático das rotas.**

- **Problema resolvido:** a rede internacional não é estável; um enlace ou país pode cair. O sistema deve mostrar o impacto e continuar oferecendo a melhor rota possível.
- **Algoritmo/estrutura:** o grafo ponderado da Etapa 3 (latência nas arestas), com **Dijkstra** recalculado após marcar arestas/vértices como inativos; comparação da rota original × rota alternativa e identificação de destinos que ficam inalcançáveis (via BFS/DFS).
- **Integração ao restante do sistema:**
  - **Tabela Hash (Etapa 1):** além de "atendido/não atendido", cada país terá um estado operacional (ex.: `ativo`/`em falha`), consultado na verificação de cobertura. *(Implementado na Etapa 2: campo `estado` no registro do país, botão "Simular falha"/"Restabelecer país" na tela de cobertura, persistido no JSON.)*
  - **Árvore B (Etapa 2):** ao simular a queda de um país/enlace, listar os clientes cujo destino foi afetado. *(Implementado: a tela de cobertura de um país em falha lista os clientes afetados, por percurso em ordem da árvore, e a consulta integrada avisa que o destino está em falha.)*
  - **Grafo (Etapa 3):** botão "simular falha" na tela da rede e recálculo automático na consulta integrada.
- **Cronograma:** descrição nesta entrega → primeira versão funcional na Etapa 2 (estado de falha, cobertura e clientes afetados — pronta) → totalmente integrado na Etapa 3.

## 8. Entregas

| Etapa | Conteúdo | Data | Situação |
|-------|----------|------|----------|
| 1 | Tabela Hash + Web/Flask | 20/10/2026 | ✅ Implementada |
| 2 | Árvore B + clientes | 24/11/2026 | ✅ Implementada |
| 3 | Grafos + integração final | 01/12/2026 | ⏳ |
