# Catálogo de Skills e MCPs Úteis

Resultado da pesquisa em skills Anthropic, repositórios GitHub e diretórios de MCP. Organizado por função no pipeline.

## 1. Análise estatística e detecção de padrões

### K-Dense-AI / claude-scientific-skills (★ topo da lista)
- **Repo:** https://github.com/K-Dense-AI/claude-scientific-skills
- **O que é:** coleção de 134+ skills científicas prontas para Claude. Originalmente para pesquisa científica mas o módulo de séries temporais é exatamente o que precisamos.
- **Destaques úteis aqui:**
  - Time series forecasting (com `aeon` toolkit)
  - Anomaly detection (STOMP/MERLIN matrix profile, CBLOF, COPOD, isolation forest)
  - Statistical hypothesis testing
- **Como usar:** `npx skills add K-Dense-AI/claude-scientific-skills` (instalação local) ou via MCP `claude-skills-mcp`
- **Encaixe no nosso pipeline:** módulo de detecção de anomalias para identificar giros suspeitos no stream em tempo real (anti-fraude, mas também detecção de viés).

### Statistical Analysis Claude Skill (mcpmarket.com)
- **URL:** https://mcpmarket.com/tools/skills/statistical-analysis-3
- **O que é:** skill focada em hypothesis testing, trend forecasting, anomaly detection.
- **Encaixe:** alternativa mais leve à coleção K-Dense; útil se você quer só a parte estatística.

### Analytical MCP Server (Quantic Soul AI Research)
- **URL:** https://www.pulsemcp.com/servers/quanticsoul4772-analytical
- **O que é:** servidor MCP genérico para análise quantitativa.
- **Encaixe:** ferramenta de back-office para Claude rodar regressões, testes, etc. sob demanda.

## 2. Raciocínio sequencial e debugging

### Sequential Thinking MCP (Anthropic oficial)
- **Repo:** https://github.com/modelcontextprotocol/servers (módulo sequential-thinking)
- **O que é:** server MCP oficial da Anthropic que dá ao agente um state machine de pensamento estruturado: thoughts numeradas, revisões, branches, replanning.
- **Encaixe no nosso pipeline:**
  - Ao **debugar resultados** do analyzer (ex.: "por que o chi-square ficou borderline?"), o agente Claude usa Sequential Thinking para enumerar hipóteses e descartá-las uma a uma.
  - Ao **planejar coleta** de uma nova roda, planeja em fases: identifica wheel, define amostragem, agenda turnos.

## 3. Testes de aleatoriedade (RNG)

### NIST Statistical Test Suite — implementações Python
| pacote | repo | notas |
|---|---|---|
| `sts-pylib` | https://github.com/honno/sts-pylib | wrapper Python da implementação C oficial NIST |
| `nistrng` | https://github.com/InsaneMonster/NistRng | OO, fácil de usar |
| `randomness_testsuite` | https://github.com/stevenang/randomness_testsuite | implementação pura Python do SP 800-22 |
| `TRNG-Test-Suite` | https://github.com/BrooksOlney/TRNG-Test-Suite | otimizado pra bitstreams grandes |

**Encaixe:** ao auditar roleta **online** (RNG-based), aplique os 15 testes NIST. Para roleta física, os testes mais relevantes do nosso `core/stats.py` (chi-square, runs, Ljung-Box) cobrem bem.

**Como integrar:** `pip install nistrng`, depois converter sequência de giros em bitstream (ex.: red=1/black=0) e rodar `nistrng.run_all_battery(bits, params, check_eligibility=True)`.

## 4. Análise de séries temporais (caso queira expandir)

### aeon (já incluso no K-Dense)
- **URL:** https://www.aeon-toolkit.org/
- **Encaixe:** anomaly detection no stream de giros (não para prever — para **detectar quando o stream começa a se desviar do uniforme**).

### statsmodels
- `acorr_ljungbox` — autocorrelação (já usamos via implementação manual)
- `runstest_1samp` — runs test
- `chisquare` em scipy.stats — já usamos

### sktime
- Mais para forecasting que não se aplica diretamente a roleta justa, mas útil se você quiser monitorar **a evolução do chi-square ao longo do tempo** (é uma série temporal de métrica).

## 5. Repositórios de referência (Python específico para roleta)

| repo | autor | utilidade |
|---|---|---|
| `mikeosborne90/RouletteSim` | Mike Osborne | simulador de estratégias, base para nossos `core/strategies.py` |
| `tjbay/Martingale-Gambling-Simulation` | T.J. Bay | foco em Martingale; ótimo para validar nossa simulação |

Code já replicado e melhorado em `core/strategies.py` (5 estratégias, Monte Carlo paralelo).

## 6. Literatura primária (papers)

| título | autores | ano | link |
|---|---|---|---|
| Predicting the outcome of roulette | Small, Tse | 2012 | https://arxiv.org/pdf/1204.6412 |
| Beat the Dealer (livro) | Edward Thorp | 1966 | — (clássico) |
| The Eudaemonic Pie (livro) | Thomas Bass | 1985 | sobre Doyne Farmer & Norman Packard |
| Method of beating roulette using bias detection | García-Pelayo (família) | 1991-1994 | https://royal888.es/en/game-chronicles-gonzalo-garcia-pelayo-roulette-mathematics/ |

## 7. MCPs que NÃO recomendo para este caso

| MCP/skill | por quê pular |
|---|---|
| LLM-based "prediction" skills | tentar prever número via LLM é cargo cult; não há sinal no histórico de roleta justa |
| Generic forecasting skills (Prophet, ARIMA) sem teste de aleatoriedade primeiro | aplicar ARIMA em sequência i.i.d. produz ruído como "previsão" |
| Casino-specific scraping tools fechados | maioria viola ToS; legalmente arriscado |

## Decisão final do stack de skills

| Necessidade | Solução |
|---|---|
| Lógica estatística core | **scipy + numpy** (já em `core/stats.py`) |
| Auditoria de RNG (caso online) | **nistrng** (pip install nistrng) |
| Detecção de anomalias em stream | K-Dense scientific-skills (aeon) — opcional fase 2 |
| Raciocínio do agente | Sequential Thinking MCP — opcional, para sessions com Claude |
| Orquestração visual | **n8n** (você já tem) |
| Persistência | **Supabase** (você já tem) |
