# Arquitetura do Sistema

## Visão geral

Pipeline em 7 estágios, do giro cru ao veredito honesto:

```
1. INGESTÃO         → captura giros de múltiplas fontes
2. PERSISTÊNCIA     → grava em Supabase Postgres
3. ESTATÍSTICA      → chi-square, runs test, Ljung-Box, z-scores, gaps
4. DETECÇÃO VIÉS    → consolida testes em veredito + tamanho de amostra
5. EV CALIBRADO     → EV empírico por número + Kelly fraction
6. SIMULAÇÃO        → Monte Carlo de estratégias clássicas
7. RELATÓRIO        → texto, JSON, alerta (Slack/e-mail)
```

## Stack escolhida (híbrida n8n + Python)

| Camada | Tecnologia | Por quê |
|---|---|---|
| Ingestão (webhook, scraper, OCR, CSV) | **n8n** | connectors prontos, visual, fácil mudar |
| Persistência | **Supabase Postgres** | já está no seu stack, real-time row-level |
| Análise estatística | **Python (FastAPI + scipy)** | scipy e numpy são insubstituíveis |
| Orquestração e alertas | **n8n** | IF, Slack, e-mail, WhatsApp em 2 cliques |
| Dashboard (opcional) | **Streamlit / Metabase** | leitura direta do Supabase |

## Diagrama de fluxo completo

```
┌─────────────────────────────────────────────────────────────┐
│                       INGESTÃO                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Webhook  │  │ Scraper  │  │   OCR    │  │   CSV    │    │
│  │ (cassino)│  │ (Claude- │  │ (camera) │  │ (manual) │    │
│  │          │  │ in-Chrome│  │          │  │          │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └────────────┬┴───────────────┴────────────┘         │
│                    │                                        │
│                    ▼                                        │
│             ┌─────────────┐                                 │
│             │  n8n: valida│  (formato uniforme:             │
│             │  + normaliza│   wheel_id, number, timestamp)  │
│             └─────┬───────┘                                 │
└───────────────────┼─────────────────────────────────────────┘
                    ▼
            ┌───────────────┐         ┌───────────────┐
            │   Supabase    │ ◄────── │  n8n: INSERT  │
            │ roulette_spins│         └───────────────┘
            └───────┬───────┘
                    │ trigger (a cada N giros ou cron 5min)
                    ▼
            ┌───────────────┐
            │ n8n: monta    │
            │ payload com   │
            │ historico do  │
            │ wheel_id      │
            └───────┬───────┘
                    │ HTTP POST /analyze
                    ▼
            ┌───────────────────────────────────────┐
            │   FastAPI Python (roulette_analyzer)  │
            │                                       │
            │   ┌───────────────────────────────┐   │
            │   │ core.stats.run_all_tests      │   │
            │   │  - chi_square_numbers         │   │
            │   │  - chi_square_color           │   │
            │   │  - chi_square_sectors         │   │
            │   │  - runs_test_color            │   │
            │   │  - autocorrelation (Ljung-Box)│   │
            │   │  - z_scores_per_number        │   │
            │   │  - gap_distribution           │   │
            │   └───────────────────────────────┘   │
            │   ┌───────────────────────────────┐   │
            │   │ core.bias.detect_bias         │   │
            │   │  - consolida flags            │   │
            │   │  - calcula sample_size_needed │   │
            │   │  - emite verdict honesto      │   │
            │   └───────────────────────────────┘   │
            │   ┌───────────────────────────────┐   │
            │   │ core.ev.calibrated_ev         │   │
            │   │  - smoothing Laplace          │   │
            │   │  - EV por numero              │   │
            │   │  - Kelly fraction             │   │
            │   └───────────────────────────────┘   │
            │   ┌───────────────────────────────┐   │
            │   │ core.strategies.compare_all   │   │
            │   │  - Monte Carlo 1000 sessoes   │   │
            │   │  - Martingale, Fib, etc.      │   │
            │   └───────────────────────────────┘   │
            └─────────────┬─────────────────────────┘
                          │ JSON: {verdict, flags, top_hot, hot_sectors, ...}
                          ▼
            ┌───────────────────────────────────────┐
            │   n8n: IF verdict == "vies_provavel"  │
            └───────────────┬───────────────────────┘
                            │
                ┌───────────┴────────────┐
                ▼                        ▼
      ┌─────────────────┐      ┌─────────────────┐
      │ Slack alert     │      │ Supabase: log   │
      │ + topo do report│      │ em bias_alerts  │
      └─────────────────┘      └─────────────────┘
```

## Schema do Supabase

```sql
CREATE TABLE roulette_spins (
  id BIGSERIAL PRIMARY KEY,
  wheel_id TEXT NOT NULL,
  wheel_type TEXT NOT NULL CHECK (wheel_type IN ('european','american')),
  number TEXT NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source TEXT NOT NULL,        -- 'webhook' | 'scraper' | 'ocr' | 'manual'
  raw JSONB                    -- payload original (debug)
);
CREATE INDEX idx_spins_wheel_time ON roulette_spins(wheel_id, timestamp);

CREATE TABLE roulette_bias_alerts (
  id BIGSERIAL PRIMARY KEY,
  wheel_id TEXT NOT NULL,
  verdict TEXT NOT NULL,
  confidence TEXT NOT NULL,
  n_spins INT NOT NULL,
  flags_json JSONB,
  hot_numbers JSONB,
  hot_sectors JSONB,
  summary TEXT,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE roulette_wheel_meta (
  wheel_id TEXT PRIMARY KEY,
  wheel_type TEXT NOT NULL,
  casino TEXT,
  table_number TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  notes TEXT
);
```

## Princípios de projeto

1. **Honestidade matemática primeiro.** Toda saída do sistema é honesta sobre incerteza. Nada de "número quente vai sair" sem teste estatístico.
2. **Camadas desacopláveis.** Coleta (n8n), análise (Python), persistência (Supabase), notificação (n8n) trocáveis individualmente.
3. **Determinismo onde possível.** Seeds fixos em testes/simulações; reprodutibilidade é regra.
4. **Falhar barulhento.** `validate_spins` rejeita números fora da roda; API retorna 400 explícito.
5. **Stateless onde dá.** A análise é função pura do histórico; pode rodar em qualquer worker.
