-- ============================================================================
-- Roulette Analyzer -- schema inicial (schema dedicado "roulette")
-- ============================================================================
-- Cria um schema dedicado "roulette" e cria as tabelas dentro dele, isolando-as
-- do schema "public" deste banco (que neste projeto Supabase hospeda a
-- plataforma Cognix em producao).
--
-- Nota de seguranca: o schema "roulette" NAO entra na lista de "Exposed schemas"
-- do PostgREST por padrao, entao estas tabelas nao sao acessiveis pela API
-- REST/anon do Supabase -- apenas por conexao Postgres direta (ex.: o node
-- Postgres do n8n). Nao adicione "roulette" aos exposed schemas a menos que
-- queira expor via API.
--
-- Aplique via:
--   - Plugin Cognix Supabase: apply_migration({ name: "roulette_schema_init", query: <conteudo> })
--   - OU Supabase CLI: supabase db push
--   - OU psql direto: psql $SUPABASE_DB_URL -f 0001_initial.sql
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS roulette;
COMMENT ON SCHEMA roulette IS 'Roulette Analyzer -- isolado do schema public (plataforma Cognix).';

-- Tabela primaria: cada giro ingerido
CREATE TABLE IF NOT EXISTS roulette.roulette_spins (
  id            BIGSERIAL PRIMARY KEY,
  wheel_id      TEXT NOT NULL,
  wheel_type    TEXT NOT NULL CHECK (wheel_type IN ('european', 'american')),
  number        TEXT NOT NULL,
  timestamp     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source        TEXT NOT NULL CHECK (source IN ('webhook', 'scraper', 'ocr', 'manual', 'demo')),
  raw           JSONB,
  -- garante que numero e valido para o tipo de roda
  CONSTRAINT valid_number_for_wheel CHECK (
    (wheel_type = 'european' AND number ~ '^(0|[1-9]|[12][0-9]|3[0-6])$')
    OR
    (wheel_type = 'american' AND number ~ '^(00|0|[1-9]|[12][0-9]|3[0-6])$')
  )
);

CREATE INDEX IF NOT EXISTS idx_spins_wheel_time
  ON roulette.roulette_spins(wheel_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_spins_source
  ON roulette.roulette_spins(source);

COMMENT ON TABLE roulette.roulette_spins IS 'Cada linha = 1 giro observado de uma roda especifica.';
COMMENT ON COLUMN roulette.roulette_spins.wheel_id IS 'Identificador estavel da roda fisica (ex.: casino-x-mesa-3).';
COMMENT ON COLUMN roulette.roulette_spins.source IS 'Canal de coleta para auditoria.';
COMMENT ON COLUMN roulette.roulette_spins.raw IS 'Payload original do source (debug).';

-- Tabela de alertas: cada vez que o analyzer rejeita H0 com confidence alta
CREATE TABLE IF NOT EXISTS roulette.roulette_bias_alerts (
  id            BIGSERIAL PRIMARY KEY,
  wheel_id      TEXT NOT NULL,
  verdict       TEXT NOT NULL,
  confidence    TEXT NOT NULL,
  n_spins       INTEGER NOT NULL,
  flags_json    JSONB NOT NULL,
  hot_numbers   JSONB,
  hot_sectors   JSONB,
  summary       TEXT,
  detected_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_wheel_time
  ON roulette.roulette_bias_alerts(wheel_id, detected_at DESC);

COMMENT ON TABLE roulette.roulette_bias_alerts IS 'Historico de veredictos do analyzer.';

-- Tabela de metadados das rodas (lookup)
CREATE TABLE IF NOT EXISTS roulette.roulette_wheel_meta (
  wheel_id      TEXT PRIMARY KEY,
  wheel_type    TEXT NOT NULL CHECK (wheel_type IN ('european', 'american')),
  casino        TEXT,
  table_number  TEXT,
  is_active     BOOLEAN DEFAULT TRUE,
  notes         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE roulette.roulette_wheel_meta IS 'Cadastro das rodas monitoradas.';

-- View auxiliar: contagem por roda
CREATE OR REPLACE VIEW roulette.roulette_spin_counts AS
SELECT
  wheel_id,
  wheel_type,
  COUNT(*) AS n_spins,
  MIN(timestamp) AS first_seen,
  MAX(timestamp) AS last_seen
FROM roulette.roulette_spins
GROUP BY wheel_id, wheel_type;

COMMENT ON VIEW roulette.roulette_spin_counts IS 'Sumario rapido de quantos giros temos por roda.';

-- RLS: o schema "roulette" nao e exposto via API, entao anon/authenticated nao
-- alcancam estas tabelas. Habilite RLS so se vier a expor o schema via PostgREST.
-- ALTER TABLE roulette.roulette_spins ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE roulette.roulette_bias_alerts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE roulette.roulette_wheel_meta ENABLE ROW LEVEL SECURITY;
