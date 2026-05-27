# Roadmap em Fases

Cada fase entrega valor independente. Não passe à próxima sem ter a anterior funcionando.

## Fase 0 — MVP local (✅ entregue)

**Objetivo:** validar que o pipeline estatístico funciona em dados sintéticos.

- [x] Definições de rodas europeia/americana com layout físico
- [x] Bateria de testes (chi-square números/cores/setores, runs, autocorr, z-scores, gaps)
- [x] Detector de viés com veredito honesto e cálculo de sample size
- [x] EV calibrado + Kelly fraction
- [x] Simulação Monte Carlo de 5 estratégias clássicas
- [x] CLI com `--demo unbiased` e `--demo biased`
- [x] Relatório textual humano-legível
- [x] FastAPI wrapper

**Critério de pronto:** `python analyze.py --demo biased --wheel european` detecta corretamente o setor enviesado.

**Como rodar agora:**
```bash
cd roulette_analyzer
pip install -r requirements.txt
python analyze.py --demo biased --wheel european
```

---

## Fase 1 — Ingestão de dados reais (manual + CSV)

**Objetivo:** sair do sintético, processar dados reais.

- [ ] Subir o FastAPI service (`uvicorn api:app`)
- [ ] Criar tabelas no Supabase (schema em `docs/ARCHITECTURE.md`)
- [ ] Endpoint que aceita upload de CSV e popula `roulette_spins`
- [ ] CLI: `python analyze.py --supabase-wheel-id casino-x-mesa-3`
- [ ] Dashboard simples Streamlit (gráfico de frequências + tabela de testes)

**Critério de pronto:** você consegue subir um CSV de 5000 giros reais (de qualquer cassino que você consiga obter) e ver o relatório completo no browser.

**Estimativa:** 4-8h de trabalho.

---

## Fase 2 — Coleta automática (n8n)

**Objetivo:** alimentar o sistema continuamente.

- [ ] Importar `n8n/workflow_roulette_collector.json` no seu n8n
- [ ] Configurar credenciais Supabase + Slack
- [ ] Webhook ativo recebendo giros (escolher 1 fonte: scraper, OCR ou webhook do cassino)
- [ ] Cron de 6h chamando `/analyze` e gravando alertas
- [ ] Validar end-to-end: giro chega → DB → cron → analyzer → alerta

**Pré-requisito:** ter pelo menos 1 fonte de giros (ver `docs/INGESTION_PATTERNS.md`).

**Critério de pronto:** após 24h, o sistema recebeu >100 giros automaticamente e fez 4+ análises sem intervenção.

**Estimativa:** 8-16h dependendo da fonte (webhook é fácil, scraper médio, OCR mais trabalhoso).

---

## Fase 3 — Detecção de viés em rodas reais

**Objetivo:** coletar amostra suficiente em 1 roda específica e auditá-la.

- [ ] Identificar 1 cassino com feed público de resultados ao vivo
- [ ] Coletar **5000+ giros** da mesma roda física (60-70h de operação)
- [ ] Rodar `detect_bias` na amostra completa
- [ ] Documentar os resultados (chi-square, top hot, hot sectors)
- [ ] Se houver viés, calcular EV calibrado + Kelly

**Critério de pronto:** relatório final em PDF/Markdown com a auditoria de 1 roda.

**Estimativa:** dias a semanas de coleta passiva + algumas horas de análise.

**Realista:** provavelmente vai dar `sem_vies_detectado`. Isso é um resultado válido e útil — confirma que o cassino opera limpo.

---

## Fase 4 — Auditoria de RNG (roleta online)

**Objetivo:** aplicar bateria NIST STS num provedor online.

- [ ] `pip install nistrng`
- [ ] Adaptador que converte giros em bitstream (red=1/black=0, ou módulo 2 dos números)
- [ ] Rodar os 15 testes NIST SP 800-22
- [ ] Comparar com expectativa teórica para um RNG audited

**Critério de pronto:** relatório técnico estilo paper, com p-values de cada teste e veredito sobre o RNG.

---

## Fase 5 — Detecção de anomalias em stream (avançado)

**Objetivo:** alertar em tempo real se um stream de giros começa a desviar.

- [ ] Integrar `aeon` (do K-Dense scientific-skills) para anomaly detection em séries
- [ ] Rolling chi-square com janela deslizante de 500 giros
- [ ] Alerta no Slack quando p-value cai abaixo de threshold
- [ ] Dashboard temporal: chi-square ao longo do tempo

**Critério de pronto:** sistema dispara alerta dentro de 30min de uma roda começar a apresentar viés simulado.

**Estimativa:** 16-24h. Esta é uma melhoria de produto, não essencial para o MVP.

---

## Fase 6 — Dashboard e relatórios (UX)

**Objetivo:** interface visual para o usuário não-técnico.

- [ ] Streamlit ou Next.js front-end
- [ ] Visualização da roda física com heatmap de frequências
- [ ] Gráfico evolução de chi-square ao longo do tempo
- [ ] Export PDF do relatório
- [ ] Multi-tenant: várias rodas/cassinos por usuário

**Estimativa:** 24-40h.

---

## Antipatterns (o que evitar)

- ❌ **Pular Fase 0 para "ganhar dinheiro".** Sem o pipeline estatístico testado, qualquer aposta é jogo de azar puro.
- ❌ **Apostar em "números quentes" antes do verdict ser `vies_provavel` com confidence alta.** Variância parece padrão.
- ❌ **Apostar em sequência sem sample size suficiente.** García-Pelayo coletou meses antes de apostar.
- ❌ **Não logar nada.** Toda decisão precisa ser auditável depois.
- ❌ **Adicionar ML "que prevê o próximo número".** Não há sinal. Você estará treinando um modelo a memorizar ruído.

## Decisões em aberto

| pergunta | quando responder |
|---|---|
| Qual cassino vai ser a fonte primária? | antes da Fase 2 |
| Multi-tenant ou single-user? | antes da Fase 6 |
| Deploy: VPS, Render, Fly.io? | antes da Fase 2 |
| Frontend separado ou Streamlit? | antes da Fase 6 |
