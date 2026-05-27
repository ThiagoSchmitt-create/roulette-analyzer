# Padrões de Ingestão (4 formas de coletar giros)

Todas as 4 fontes desembocam no mesmo formato canônico:

```json
{
  "wheel_id": "casino-x-mesa-3",
  "wheel_type": "european",
  "number": "17",
  "timestamp": "2026-05-26T18:42:13Z",
  "source": "webhook"
}
```

---

## 1. Webhook API (cassino online com API oficial)

**Quando usar:** o provedor oferece webhook ou API REST.

**Setup no n8n:**
```
[Webhook Trigger]
  POST /webhook/roulette/spin
  ▼
[Code: valida + normaliza]  →  garante number em [0..36] ou ['00']
  ▼
[Supabase Insert]            →  tabela roulette_spins
  ▼
[Respond to Webhook]         →  { "ok": true }
```

**Latência:** sub-segundo. É a forma ideal.

**Segurança:** valide um HMAC/secret no header. No Code node:
```js
const sig = $request.headers['x-signature'];
const expected = crypto
  .createHmac('sha256', $env.WEBHOOK_SECRET)
  .update(JSON.stringify($json))
  .digest('hex');
if (sig !== expected) throw new Error('signature mismatch');
```

---

## 2. Scraper (site de resultados ao vivo, sem API)

**Quando usar:** o cassino mostra giros num feed HTML/JS público.

**Opção A: n8n HTTP Request + HTML parsing**
```
[Schedule: every 30s]
  ▼
[HTTP Request]              →  GET https://cassino.com/live-results
  ▼
[HTML Extract / Code node]  →  parseia DOM, extrai últimos N números
  ▼
[Function]                  →  filtra apenas novos (não vistos antes)
  ▼
[Supabase Insert]
```

**Opção B: Claude in Chrome para sites com JS pesado**

Se a página é client-rendered (React/Vue) e o HTML cru não tem os números, use `mcp__Claude_in_Chrome__navigate` + `mcp__Claude_in_Chrome__get_page_text` num agente n8n custom, ou chame um sub-agente Claude periodicamente.

**Cuidado legal:** muitos sites proíbem scraping em ToS. Leia antes.

**Latência:** depende do intervalo do schedule. 15-60s é típico.

---

## 3. Captura visual (OCR de roleta física)

**Quando usar:** cassino presencial, sem acesso a feed digital.

**Pipeline:**
```
[Câmera celular / laptop]
  ▼  (foto do display de resultados)
[Webhook: upload de imagem]
  ▼
[OCR — Tesseract / Google Vision / Claude vision]
  ▼
[Code: regex extrai número(s)]
  ▼
[Supabase Insert]
```

**No n8n:**
1. Node `Webhook` configurado para `binaryProperty`
2. Node `HTTP Request` para Google Vision API (ou) node `Code` que chama Claude com a imagem
3. Node `Code` com regex `\b(\d{1,2}|00)\b` para extrair o número

**Alternativa:** app mobile próprio que tira foto, faz OCR local e bate no webhook.

**Latência:** 2-5s (OCR é o gargalo). Aceitável para roleta presencial.

**Honestidade:** captura visual é a fonte mais ruidosa. Aplique double-check (envie duas fotos consecutivas, descarte se OCR diverge).

---

## 4. Manual / CSV upload (estudo retroativo)

**Quando usar:** análise histórica de logs antigos, ou estudo de uma planilha.

**No n8n:**
```
[Webhook (multipart)]
  ▼
[Read CSV / Spreadsheet]
  ▼
[Loop Over Items]
  ▼
[Supabase Insert]
```

**Ou direto pela CLI:**
```bash
python analyze.py --input meus_giros.csv --wheel european --json out.json
```

**Formato esperado:**
```csv
spin_id,number
1,32
2,7
3,15
...
```

---

## Roteamento unificado (todos os 4 caminhos)

No n8n, depois de qualquer fonte, passe por um Code node "Normalizador":

```js
// Normaliza pra schema canônico
const out = items.map(item => {
  const num = String(item.json.number ?? item.json.value ?? item.json.result).trim();
  if (!/^(0|00|[1-9]|[12]\d|3[0-6])$/.test(num)) {
    throw new Error(`numero invalido: ${num}`);
  }
  return {
    json: {
      wheel_id: item.json.wheel_id || 'default',
      wheel_type: item.json.wheel_type || 'european',
      number: num,
      timestamp: item.json.timestamp || new Date().toISOString(),
      source: item.json.source || $node.name,
    }
  };
});
return out;
```

Depois disso, todas seguem o mesmo branch: Insert → trigger análise.

## Tabela comparativa

| Forma | Latência | Custo | Confiabilidade | Volume |
|---|---|---|---|---|
| Webhook API | <1s | $$ (depende do provedor) | ★★★★★ | alto |
| Scraper HTML | 15-60s | $ | ★★★ | médio |
| Scraper JS pesado | 30-120s | $$ (Chrome headless) | ★★★ | médio |
| OCR | 2-5s | $ a $$ (API vision) | ★★ | baixo |
| CSV manual | n/a | gratis | ★★★★★ | retroativo |

**Recomendação MVP:** começar com **CSV manual** + **webhook**. Adicionar scraper/OCR só quando o restante do pipeline estiver maduro.
