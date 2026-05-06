# Re-deploy Apps Script (når dashboard ikke loader data)

Hvis dashboardet viser "Apps Script svarer ikke JSON" eller HTTP 502, er din Apps Script-deployment sandsynligvis udløbet eller privat. Det sker ofte når:

- Du redigerede koden uden at oprette en ny version
- Google har auto-disabled deployment efter inaktivitet
- Permissions blev ændret til "Only myself"

## Sådan fixer du det (3-4 minutter)

### 1. Åbn Apps Script editor

Åbn det Google Sheet der hører til Kvitly → **Extensions → Apps Script**.

### 2. Tjek nuværende deployment

I editor-toppen: **Deploy → Manage deployments**.

- Hvis der **ingen** aktive deployments er → gå til "Ny deployment" nedenfor
- Hvis der **er** en deployment der hedder "Web app", klik ⚙ ud for den → **Edit**

### 3. Re-deploy (opret ny version)

Hvis du redigerer eksisterende:
- **Version:** vælg "New version"
- **Description:** (valgfri) "Re-deploy YYYY-MM-DD"
- **Execute as:** `Me (din@email.com)`
- **Who has access:** **Anyone** ← dette er kritisk
- Klik **Deploy**

Hvis du laver en ny:
- **Type:** Web app
- Samme indstillinger som ovenfor
- Klik **Deploy**

### 4. Kopier den nye URL

Efter deploy får du en URL i formatet:
```
https://script.google.com/macros/s/AKfycb.../exec
```

Hvis URL'en er **uændret** efter "Edit existing deployment", kan du springe step 5 over — bare prøv dashboardet igen.

### 5. Opdater config.json

Hvis URL'en er ny, åbn `config.json` i Kvitly-projektet og udskift `apps_script_url`:

```json
{
  "apps_script_url": "https://script.google.com/macros/s/NY_URL_HER/exec",
  ...
}
```

### 6. Genstart Flask (hvis lokal) og test

Lokalt: stop og genstart `python app.py`. På Render: redeploy automatisk når du pusher til main.

Åbn dashboard → forventet: data loader.

## Verifikation

Du kan teste Apps Script direkte uden Flask:

```bash
curl -sS "DIN_NYE_URL"
```

Forventet output:
```json
{"status":"ok","headers":["Dato","Indsendt",...],"rows":[...]}
```

Hvis du får HTML eller 403 → permissions er stadig forkerte. Gå tilbage til step 3 og dobbelttjek "Who has access: Anyone".

## Forebyggelse

Apps Script-deployments udløber typisk ikke selv, men:
- **Hver gang du ændrer kode i Code.gs**, opret en ny deployment-version (ellers kører den live URL stadig den GAMLE kode)
- **Aldrig** del en URL der er deployet "Execute as: User accessing the web app" — den vil bede besøgende om at logge ind
