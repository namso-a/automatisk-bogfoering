# Deploy Kvitly landing page som ny Render-service

Landing page og forening-app koerer samme Flask-app, men med forskellige env vars.

| Service | URL | Formaal | `/` rute viser |
|---------|-----|---------|----------------|
| Kvitly marketing | `kvitly.onrender.com` | Landing page for nye kunder | landing.html |
| Din egen forenings instans | `<forening>.onrender.com` | Koerer kvitterings-flowet for en forening | form.html |
| Fremtidige kunder | `<kundenavn>.onrender.com` | Hver forenings egen instans | form.html |

## Opsaet Kvitly-service paa Render

1. **Log ind paa Render** → New → Web Service
2. **Connect repo:** vaelg samme GitHub repo som kunde-servicen bruger
3. **Service-indstillinger:**
   - Name: `kvitly`
   - Region: Frankfurt (EU)
   - Branch: `main`
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app` (samme som kunde)
4. **Instance type:** Free (landing pages har lav trafik)
5. **Environment variables** — kritisk at saette disse:

| Key | Value | Bemaerkning |
|-----|-------|-------------|
| `KVITLY_LANDING` | `true` | Faar `/` til at vise landing.html i stedet for formularen |
| `LOOM_EMBED_URL` | `https://www.loom.com/embed/XXXXX` | Din Loom-videos embed-URL (se nedenfor). Valgfri — hvis tom vises en placeholder |
| `FLASK_SECRET_KEY` | `<tilfaeldig streng>` | Behoeves selvom dashboard ikke bruges paa landing |

**Du behoever IKKE saette:** `GEMINI_API_KEY`, `DASHBOARD_PASSWORD`, `apps_script_url` — landing page bruger ingen af dem.

6. **Click "Create Web Service"** → Render bygger og deployer. Efter 2-3 min er det live paa `kvitly.onrender.com`.

## Find din Loom-embed URL

1. Optag demo-video i Loom (60-90 sek: upload kvittering → OCR → dashboard-drilldown)
2. Klik "Share" → "Embed" → kopier URL'en fra `src="..."` i iframe-koden
3. URL ser saadan ud: `https://www.loom.com/embed/a1b2c3d4e5f6...`
4. Saet den som `LOOM_EMBED_URL` env var paa Render → service genstarter automatisk

## Teste lokalt foer deploy

```bash
# Landing page preview uden env var
python app.py
# -> aabn http://localhost:5000/kvitly

# Simuler Kvitly-mode
KVITLY_LANDING=true python app.py
# -> http://localhost:5000/ viser nu landing page
```

## Custom domain (senere)

Naar du er klar, kan du pege et `.dk`-domaene paa Kvitly-servicen:

1. Koeb fx `kvitly.dk` (~30 kr/aar paa GratisDNS eller UnoEuro)
2. Paa Render → Kvitly service → Settings → Custom Domains → Add `kvitly.dk`
3. Opret CNAME-record hos din DNS-udbyder som Render foreslaar
4. Vent 5-60 min paa DNS-propagation, og SSL er automatisk

Indtil da er `kvitly.onrender.com` fint til LinkedIn-posten.

## Vigtig note om URL'en i marketing-materiale

LinkedIn-posten og landing page's "Book demo" CTA refererer til `kvitly.onrender.com`. Hvis du skifter til custom domain senere, skal du opdatere:

- [marketing/linkedin-post.md](../marketing/linkedin-post.md)
- [marketing/landing-page-copy.md](../marketing/landing-page-copy.md) (hvis relevant)
- Evt. `templates/landing.html` — der er links til `/` som bliver til `kvitly.dk/` automatisk, saa ingen aendringer noedvendigt her

## Hvad Kvitly-servicen IKKE skal

- Den skal ikke modtage kvittering-uploads (`/scan`, `/confirm` er aktive men kunden ser dem aldrig)
- Dashboard-ruterne er ogsaa aktive men uden password saet rammer man bare login-siden
- Hvis du vil vaere sikker: senere kan vi tilfoeje et blokerings-middleware der returnerer 404 paa alle andre end landing-ruterne naar `KVITLY_LANDING=true`. For MVP er det fint som det er.
