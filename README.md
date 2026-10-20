# GlobalSIM EDII — Serviço Internacional de Internet por eSIM

Trabalho prático de **Estruturas de Dados II** · Sistemas de Informação · DCET/UNEB · Profa. Maria Inés Restovic

> **Status:** Etapa 1 — Tabela Hash + Aplicação Web (entrega 20/10/2026)

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

Testes automatizados (Tabela Hash + rotas Flask):

```bash
python -m unittest discover -s tests -v
```

## 3. Estrutura do projeto

```
globalsim/
├── app.py                    # rotas Flask (somente HTTP)
├── estruturas/
│   └── tabela_hash.py        # Tabela Hash própria + instrumentação
├── servicos/
│   └── paises_service.py     # regras de negócio + persistência JSON
├── arquivos/
│   └── paises.json           # persistência dos países
├── templates/                # Jinja (base, index, paises, pais_form, cobertura, instrumentacao)
├── static/css/estilo.css
└── tests/test_etapa1.py
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
- A página de **cobertura** também mostra como a tabela respondeu (índice e comparações).

Exemplo real após a carga inicial dos 8 países (capacidade 7 → 17 com 1 rehash):

| Métrica | Valor |
|---------|-------|
| Elementos / capacidade | 8 / 17 (fator de carga 0,47) |
| Colisões | 3 (durante a carga e antes do rehash) |
| Buckets usados / vazios | 7 / 10 |
| Maior cadeia | 2 (`US → CA` no bucket 7) |

## 5. Funcionalidades Web (Etapa 1)

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

Rotas que alteram dados usam **POST** com **Post/Redirect/Get** (`redirect` + `flash`). Validações: código com 2 letras, sem duplicidade, campos obrigatórios, tecnologia válida.

## 6. Diferencial da equipe (descrição inicial) — a confirmar

> ⚠️ **Proposta para validação da equipe e aprovação da professora** (o enunciado exige aprovação prévia). Se a equipe preferir outro, é só substituir esta seção.

**Simulação de falhas de conexões e recálculo automático das rotas.**

- **Problema resolvido:** a rede internacional não é estável; um enlace ou país pode cair. O sistema deve mostrar o impacto e continuar oferecendo a melhor rota possível.
- **Algoritmo/estrutura:** o grafo ponderado da Etapa 3 (latência nas arestas), com **Dijkstra** recalculado após marcar arestas/vértices como inativos; comparação da rota original × rota alternativa e identificação de destinos que ficam inalcançáveis (via BFS/DFS).
- **Integração ao restante do sistema:**
  - **Tabela Hash (Etapa 1):** além de "atendido/não atendido", cada país terá um estado operacional (ex.: `ativo`/`em falha`), consultado na verificação de cobertura. *(Ponto de preparo já nesta etapa: o registro do país é um dicionário extensível.)*
  - **Árvore B (Etapa 2):** ao simular a queda de um país/enlace, listar os clientes cujo destino foi afetado.
  - **Grafo (Etapa 3):** botão "simular falha" na tela da rede e recálculo automático na consulta integrada.
- **Cronograma:** descrição nesta entrega → primeira versão funcional na Etapa 2 (estado de falha e cobertura) → totalmente integrado na Etapa 3.

## 7. Entregas

| Etapa | Conteúdo | Data | Situação |
|-------|----------|------|----------|
| 1 | Tabela Hash + Web/Flask | 20/10/2026 | ✅ Implementada |
| 2 | Árvore B + clientes | 24/11/2026 | ⏳ |
| 3 | Grafos + integração final | 01/12/2026 | ⏳ |
