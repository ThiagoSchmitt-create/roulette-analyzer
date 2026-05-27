# CLAUDE.md

Memória do projeto. Lida automaticamente por Claude Code ao abrir esta pasta.

## Sobre o projeto

**Roulette Analyzer** — sistema de análise estatística de roleta. Detecta viés mecânico em rodas físicas, audita aleatoriedade de RNGs online, simula estratégias e calcula EV calibrado.

Stack:
- Python 3.10+ (scipy/numpy/pandas) — núcleo estatístico
- FastAPI — serviço HTTP
- n8n — orquestração e ingestão (via plugin Cognix)
- Supabase — persistência (via plugin Cognix)

## REGRA DA CASA (não-negociável)

**Honestidade matemática primeiro.** Toda saída do sistema é calibrada e honesta sobre incerteza.

- Roleta justa tem house edge fixo: −2,7% (europeia), −5,26% (americana). Nenhuma estratégia muda isso.
- "Prever o próximo número" em roda justa é impossível. Não escreva, não sugira, não implemente.
- O único edge documentado historicamente é detecção de viés mecânico em **rodas físicas** com 3000+ giros (metodologia García-Pelayo).
- Cassinos modernos monitoram suas rodas. Não conte com viés explorável.
- Sempre que reportar resultado para o usuário, inclua p-value, tamanho de amostra, e sample-size-recomendado.

Se uma feature solicitada violar esta regra, recuse e explique por quê. Veja `docs/HONEST_MATH.md`.

## Estrutura

```
roulette_analyzer/
├── analyze.py             # CLI
├── api.py                 # FastAPI service
├── core/                  # logica pura, testavel
│   ├── wheel.py           # rodas + layout fisico
│   ├── stats.py           # chi-square, runs, Ljung-Box, z-scores, gaps
│   ├── bias.py            # detector + sample size
│   ├── ev.py              # EV calibrado + Kelly
│   ├── strategies.py      # Monte Carlo de Martingale/Fib/etc.
│   └── report.py          # relatorio textual
├── tests/                 # pytest smoke + property tests
├── supabase/migrations/   # SQL versionado
├── n8n/                   # workflows JSON exportados
├── examples/              # CSVs de demo
└── docs/                  # ARCHITECTURE, HONEST_MATH, ROADMAP, ...
```

## Comandos comuns

```bash
make install     # instala dependencias
make test        # roda pytest
make demo        # roda analise em dados sinteticos enviesados
make dev         # sobe FastAPI com hot reload em :8000
make lint        # ruff check + format
```

Sem make? Use diretamente:
```bash
pip install -r requirements.txt
pytest tests/ -v
python analyze.py --demo biased --wheel european
uvicorn api:app --reload --port 8000
```

## Convenções de código

- Python 3.10+, type hints obrigatórios em assinaturas públicas
- `from __future__ import annotations` no topo de cada módulo
- Sem emojis em código nem em commit messages
- Strings em ASCII puro (acentos só em docs/comentários se necessário) — evita problemas de encoding em workflows n8n
- Funções de teste estatístico retornam `dict` JSON-serializável, nunca classes ricas
- Seeds fixos em qualquer simulação Monte Carlo (`seed=42` por padrão)
- Logs com `print` no CLI, com `logging` na API

## Como rodar testes antes de mergear

```bash
make test                                 # smoke
python analyze.py --demo unbiased         # deve dar "indicio_fraco" ou "sem_vies"
python analyze.py --demo biased           # DEVE dar "vies_provavel" com confidence alta
```

Se demo biased não dá `vies_provavel`, **algo quebrou** na bateria estatística — investigar antes de fazer qualquer outra coisa.

## MCPs disponíveis neste workspace

Você (Claude Code) tem acesso a:
- **plugin:cognix-core:supabase** — `list_tables`, `apply_migration`, `execute_sql`, `get_logs`, `get_advisors`
- **plugin:cognix-core:n8n** — `n8n_create_workflow`, `n8n_update_full_workflow`, `n8n_test_workflow`, `search_nodes`

### Uso recomendado

- Antes de qualquer schema change: `list_tables`
- Aplicar migration: `apply_migration` lendo o SQL de `supabase/migrations/`
- Importar workflow: `n8n_create_workflow` com o JSON de `n8n/`
- Debugar produção: `get_logs` para Supabase, `n8n_executions` para n8n

## Roadmap atual

Fase 0 (✅ completa) — MVP local funcional.

**Próxima**: Fase 1 — ingestão real.

1. [ ] Aplicar `supabase/migrations/0001_initial.sql` no projeto Supabase
2. [ ] Importar `n8n/workflow_roulette_collector.json` no n8n
3. [ ] Configurar credencial Supabase no n8n
4. [ ] Subir FastAPI (`make dev`) e expor via tunnel (ngrok/cloudflared) ou hospedar
5. [ ] Apontar HTTP node do workflow para a URL pública
6. [ ] Smoke test: POST giro → ver chegando no DB → ver análise rodando no cron

Detalhes em `docs/ROADMAP.md`.

## Decisões já tomadas

| decisão | escolha | razão |
|---|---|---|
| Arquitetura | Híbrida n8n + Python FastAPI | scipy é insubstituível; n8n é imbatível em orquestração visual |
| Coleta | 4 caminhos suportados (webhook/scraper/OCR/CSV) | flexibilidade — MVP com CSV manual |
| Persistência | Supabase Postgres | já no stack via plugin Cognix |
| Frontend | adiar até Fase 6 | dashboard só faz sentido com dados reais fluindo |
| ML preditivo | NÃO | violaria a regra da casa |

## Anti-features (não implementar, mesmo se pedirem)

1. "Modelo que prevê o próximo número" — sem fundamento estatístico em jogo justo
2. "Sistema garantido de aposta" — não existe matematicamente
3. "Recomendação automática de aposta sem verdict `vies_provavel`" — induz dano financeiro
4. Scraper que viola ToS do cassino sem aviso ao usuário
5. Endpoint público que aceita giros sem autenticação — abre para envenenamento da amostra

## Glossário rápido

- **chi-square goodness-of-fit**: testa se distribuição observada bate com a teórica uniforme
- **runs test (Wald-Wolfowitz)**: testa independência numa sequência binária
- **Ljung-Box**: testa autocorrelação em múltiplos lags simultaneamente
- **z-score por número**: quantos desvios-padrão acima/abaixo do esperado
- **Kelly fraction**: tamanho ótimo de aposta dada probabilidade e payout
- **EV (Expected Value)**: retorno esperado por unidade apostada
- **house edge**: vantagem da casa = -EV teórico do jogador
- **wheel clocking**: medir velocidades de roda e bola para prever octante (método Thorp/Eudaemons)
- **viés mecânico**: desgaste físico que cria probabilidades não-uniformes

## Quando estiver em dúvida

Releia `docs/HONEST_MATH.md`. Se o que você está prestes a fazer não está coberto lá, pergunte.
