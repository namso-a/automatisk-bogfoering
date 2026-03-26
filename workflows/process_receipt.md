# Workflow: Modtag og behandl kvittering

## Formål
Automatisk modtagelse, OCR-scanning og bogføring af kvitteringer fra foreningsmedlemmer.

## Flow
1. Medlem åbner linket og udfylder formularen (navn + billede + evt. kommentar)
2. `app.py` modtager upload og kører pipelinen:
   - **OCR** → `tools/ocr_receipt.py` → udtræk beløb, dato, butik, kategori via Claude Vision
   - **Gem** → `tools/send_to_sheets.py` → sender data + billede til Apps Script Web App
   - Apps Script gemmer billede i Google Drive og tilføjer række i Sheet
3. Medlem ser "Tak!" besked

## Opsætning (én gang)

### 1. Google Sheet + Apps Script
1. Opret et nyt Google Sheet (giv det et navn, fx "Kvitteringer 2026")
2. Gå til **Extensions → Apps Script**
3. Slet alt i `Code.gs`
4. Åbn filen `apps_script/Code.gs` fra dette projekt og kopiér hele indholdet
5. Indsæt det i Apps Script editoren
6. Klik **Deploy → New deployment**
7. Klik tandhjulet ved "Select type" → vælg **Web app**
8. Sæt:
   - **Execute as**: Me
   - **Who has access**: Anyone
9. Klik **Deploy**
10. Klik **Authorize access** og godkend med din Google-konto
11. Kopiér den URL der vises (starter med `https://script.google.com/...`)

### 2. Konfiguration
Åbn `config.json` og udfyld:
```json
{
  "apps_script_url": "INDSÆT URL HER",
  "members": ["Navn1", "Navn2", "Navn3"],
  "forening_name": "Dit Foreningsnavn"
}
```

### 3. API-nøgle
Åbn `.env` og indsæt din Anthropic API-nøgle:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Test
```bash
pip install -r requirements.txt
python app.py
```
Åbn http://localhost:5000 og indsend en kvittering.

## Deploy til Render

1. Opret et Git-repo med projektets filer
2. På [render.com](https://render.com): New → Web Service → vælg repo
3. Sæt miljøvariabel: `ANTHROPIC_API_KEY`
4. Start command: `gunicorn app:app`

**NB:** `config.json` skal committes med `apps_script_url` udfyldt.

## Fejlhåndtering
- **Utydeligt billede**: OCR returnerer data med `confidence_note` → vises i kommentar-kolonnen i Sheet
- **Ikke en kvittering**: Kategori sættes til "Andet" med en note
- **API-fejl**: Fejlbesked vises til bruger, intet skrives til Sheet
- **Stor fil**: Max 16 MB (sat i Flask config)

## Opdater Apps Script
Hvis du ændrer `Code.gs`:
1. Gå til Apps Script editoren i dit Sheet
2. Indsæt ny kode
3. Klik **Deploy → Manage deployments → redigér** (blyant-ikon)
4. Vælg **New version** og klik **Deploy**

## Omkostninger
- Claude API: ~$0.003 pr. kvittering ≈ $0.15/md ved 50 kvitteringer
- Google Sheet + Drive: gratis
- Render: gratis tier
