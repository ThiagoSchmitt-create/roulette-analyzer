#!/usr/bin/env bash
# Quickstart: tudo em 1 comando. Roda apos clonar/baixar o projeto.
set -euo pipefail

cd "$(dirname "$0")/.."

echo ">>> 1. Criando venv (se nao existir)..."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo ">>> 2. Instalando dependencias (runtime + dev)..."
pip install --upgrade pip -q
pip install -e ".[dev]" -q

echo ">>> 3. Rodando testes..."
pytest tests/ -q

echo ">>> 4. Demo: dados sem vies (deve dar veredito honesto)..."
python analyze.py --demo unbiased --wheel european --no-sim | tail -5

echo ""
echo ">>> 5. Demo: dados com vies injetado (deve dar vies_provavel)..."
python analyze.py --demo biased --wheel european --no-sim | grep -E "Veredito|Confianca|HOT SECTOR" | head -5

echo ""
echo ">>> 6. Subindo FastAPI em background na porta 8000..."
nohup uvicorn api:app --host 0.0.0.0 --port 8000 > /tmp/roulette_api.log 2>&1 &
API_PID=$!
sleep 2

echo ">>> 7. Smoke test /health..."
if curl -sf http://localhost:8000/health > /dev/null; then
  echo "OK — API rodando (pid=$API_PID, logs em /tmp/roulette_api.log)"
else
  echo "FALHOU — verifique /tmp/roulette_api.log"
  exit 1
fi

echo ""
echo "===================================================================="
echo " Quickstart concluido."
echo " - API:        http://localhost:8000"
echo " - Docs:       http://localhost:8000/docs (Swagger)"
echo " - Para parar: kill $API_PID"
echo " - Proximo:    leia docs/ROADMAP.md (Fase 1)"
echo "===================================================================="
