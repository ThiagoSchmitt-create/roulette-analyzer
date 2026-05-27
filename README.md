# Roulette Analyzer

Sistema honesto de análise estatística de roleta. Detecta viés mecânico, testa aleatoriedade do gerador, simula estratégias de aposta e calcula EV calibrado.

> **Aviso matemático.** Roleta é um jogo com vantagem fixa da casa (−2,7% europeia, −5,26% americana). **Nenhum sistema prevê o próximo número.** O único edge real, historicamente, vem de detectar viés mecânico em rodas físicas com **milhares de giros** — método García-Pelayo, Casino Gran Madrid, anos 90. Cassinos modernos monitoram suas próprias rodas e corrigem qualquer viés rapidamente. Este projeto é uma **ferramenta de análise**, não uma máquina de fazer dinheiro. Veja [`docs/HONEST_MATH.md`](docs/HONEST_MATH.md).

## O que ele faz

1. **Bateria de testes de aleatoriedade**: chi-square (números, cores, setores), runs test, Ljung-Box (autocorrelação), z-scores por número, distribuição de gaps.
2. **Detecção de viés** com veredito honesto e cálculo de tamanho de amostra necessário (metodologia García-Pelayo).
3. **EV calibrado** por número com smoothing de Laplace + Kelly fraction.
4. **Simulação Monte Carlo** de Martingale, Fibonacci, D'Alembert, Paroli, Flat — mostra que nenhuma supera o house edge.
5. **API HTTP** (FastAPI) para integração com n8n, Supabase, dashboards.

## Quick start

```bash
pip install -r requirements.txt

# Roda análise em dados sintéticos (sem viés)
python analyze.py --demo unbiased --wheel european

# Roda análise em dados com viés injetado (5 números adjacentes turbinados)
python analyze.py --demo biased --wheel european

# Roda em um CSV próprio (coluna "number" obrigatória)
python analyze.py --input examples/sample_biased_spins.csv --wheel european

# Salva resultado completo em JSON
python analyze.py --input meus_giros.csv --wheel european --json out.json

# Sobe a API HTTP
uvicorn api:app --reload --port 8000

# Sobe o dashboard visual (Streamlit): heatmap da roda, testes, frequencias, EV
pip install -e ".[dashboard]"
streamlit run dashboard.py
```

## Estrutura

```
roulette_analyzer/
├── analyze.py                 # CLI
├── api.py                     # FastAPI service
├── dashboard.py               # dashboard Streamlit (heatmap, testes, EV)
├── requirements.txt
├── core/                      # logica reutilizavel
│   ├── wheel.py               # rodas europeia/americana + layout fisico
│   ├── stats.py               # bateria de testes estatisticos
│   ├── bias.py                # detector de vies + sample size
│   ├── ev.py                  # EV calibrado + Kelly
│   ├── strategies.py          # Monte Carlo de estrategias
│   └── report.py              # relatorio textual
├── examples/
│   ├── sample_unbiased_spins.csv
│   └── sample_biased_spins.csv
├── n8n/
│   ├── workflow_roulette_collector.json   # workflow esqueleto (coleta + analise)
│   └── workflow_roulette_simulator.json   # simulador local: gera giros -> POST /spin
└── docs/
    ├── ARCHITECTURE.md
    ├── HONEST_MATH.md
    ├── INGESTION_PATTERNS.md
    ├── SKILLS_AND_MCPS.md
    └── ROADMAP.md
```

## Arquitetura recomendada (híbrida)

```
[Coleta]  ──webhook/scraper/OCR/CSV──►  [n8n]  ──persist──►  [Supabase]
                                          │                       │
                                          │ HTTP                  │ SELECT
                                          ▼                       ▼
                                   [FastAPI Python]  ◄────────────┘
                                          │
                                          │ verdict + flags
                                          ▼
                                   [n8n IF]  ──vies?──► [Slack / e-mail]
```

Detalhes em [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Endpoints da API

| método | path | descrição |
|---|---|---|
| GET | `/health` | health check |
| POST | `/spin` | registra 1 giro |
| GET | `/history/{wheel_id}` | últimos N giros |
| POST | `/analyze` | roda bateria completa em uma lista de giros |
| GET | `/report/{wheel_id}` | último relatório consolidado |
| DELETE | `/history/{wheel_id}` | limpa histórico do wheel |

Exemplo:
```bash
curl -X POST http://localhost:8000/analyze \
  -H 'content-type: application/json' \
  -d '{"wheel":"european","spins":["7","32","15","19",...]}'
```

## Veredito do analisador

| veredito | significado | ação |
|---|---|---|
| `amostra_insuficiente` | < 1000 giros | colete mais |
| `inconclusivo` | nenhum teste rejeita H0 | colete mais |
| `indicio_fraco` | flags presentes mas n < recomendado | provável variância, colete mais |
| `vies_provavel` | n ≥ recomendado **ou** p < 0.001 com n ≥ 3000 | há indício real; verifique `top_hot` e `hot_sectors` |
| `sem_vies_detectado` | n ≥ recomendado e sem flags | jogo justo, **não jogue para lucrar** |

## Licença

Uso educacional. Veja `docs/HONEST_MATH.md` antes de qualquer aposta com dinheiro real.
