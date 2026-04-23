# Kvitly demo-video script

## Specs

- **Længde:** 60 sekunder (max 90)
- **Værktøj:** Loom (desktop app eller Chrome-extension)
- **Opløsning:** 1080p minimum, gerne 1440p
- **Format:** Landscape 16:9
- **Lyd:** Voiceover på dansk, rolig tone. Optag i stille rum. Brug evt. AirPods/headset-mikrofon.
- **Cursor:** Loom zoomer auto ind ved klik, godt for detaljer
- **Tempo:** Hurtigt, ingen lange pauser. Klip alle "øhh"s og pauser i Loom-editoren bagefter.

## Forberedelse (inden optagelse)

1. Åbn **2 browservinduer** i rækkefølge (så du kan Alt+Tab mellem dem):
   - Vindue A: din Kvitly-instans (formular, route `/`)
   - Vindue B: din Kvitly-instans (dashboard, route `/dashboard`)
2. **Luk alle andre tabs** — ingen Gmail, Slack, notifikationer i baggrunden
3. **Rens dashboardet**: slå filtre til så der er 15-30 kvitteringer synlige med rigtig data
4. **Forbered en test-kvittering** på din telefon eller ét klar-til-upload billede
5. **Luk notification center** (macOS: top bar ren), slå telefonens lydløs til
6. **Brug "clean" browserprofil** uden bookmarks-bar synlig og uden extensions som bryder layoutet
7. **Zoom browser til 100%** (cmd/ctrl + 0)

## Storyboard (60 sek)

### 0:00 til 0:06 — Krog (det værste problem)

**Visuelt:** Åbn Messenger-samtale med fotos af kvitteringer fra frivillige. Scroll hurtigt gennem 5-6 billeder.

**Voiceover:**
> "Som kasserer i en forening ser jeg på det her hver måned. Kvitteringer spredt i Messenger, mails og sms'er."

**Note:** Hvis du ikke har en rigtig Messenger-tråd med kvitteringer, lav et fake-screenshot eller brug Fotos-appen med skærmbilleder af kvitteringer.

---

### 0:06 til 0:15 — Upload (det nemme)

**Visuelt:** Skift til formular-siden (Vindue A). Klik "Tag et billede", vælg et kvitteringsbillede fra kamera-rulle (eller upload fra mappe). Viser progress mens OCR kører.

**Voiceover:**
> "Med Kvitly uploader frivillige bare et billede. Kvitly læser beløb, dato, butik og kategori automatisk."

**Note:** Sørg for at upload-animationen er synlig (cirka 3-4 sek). Hvis OCR går for hurtigt, nævn bare "AI'en gør resten" mens siden loader.

---

### 0:15 til 0:25 — Review + indsend

**Visuelt:** Vis review-skærmen efter OCR: alle felter udfyldt (vendor, beløb, dato, kategori, udvalg). Zoom lidt ind på de udfyldte felter. Scroll ned og tryk "Indsend".

**Voiceover:**
> "Frivillige bekræfter, vælger udvalg, og sender. Hele processen tager 20 sekunder."

**Note:** Hvis udvalgs-dropdown er hurtigt klart, vis at man åbner den og ser flere muligheder. Det signalerer at produktet kender foreningsliv.

---

### 0:25 til 0:50 — Dashboard (den store payoff)

**Visuelt:** Alt+Tab til dashboard (Vindue B). Gør dette i rækkefølge:

1. **0:25–0:30** — Vis forside med summary-cards og grafen over forbrug per udvalg. Peg/cursor over ét udvalg.
   > "Som kasserer har jeg alt samlet ét sted. Forbrug per udvalg, kategorifordeling, udvikling over tid."

2. **0:30–0:38** — Klik på "Udgifter"-fanen. Filtrér på et udvalg. Table vises med rækker.
   > "Jeg kan filtrere på udvalg, dato, kategori. Her er alle festudvalgets køb det sidste halve år."

3. **0:38–0:45** — Klik på én række. Drill-down åbner med kvitteringsbillede. Scroll let.
   > "Klik på en række, og jeg ser den oprindelige kvittering. Ingen gravning i Drive, ingen mails."

4. **0:45–0:50** — Gå tilbage til listen. Klik "Godkend" på en række. Status-badge skifter.
   > "Når jeg har godkendt, skifter status. Når den er udbetalt, markerer jeg det — og så er det ude af min indbakke."

---

### 0:50 til 0:60 — Outro (CTA'en)

**Visuelt:** Skift til `kvitly.onrender.com` landing page. Vis hero briefly.

**Voiceover:**
> "Jeg har brugt det selv i et halvt år. Nu har jeg åbnet det for andre foreninger. Link i kommentarerne."

**Slut:** Frys på landing page-hero i 1-2 sek. Stop optagelse.

---

## Efter optagelse (Loom editor)

1. **Klip begyndelse og slutning** — fjern de første 1-2 sek (klik på record) og sidste sek
2. **Skær pauser** — Loom har "remove silence" som kan bruges med varsomhed
3. **Tilføj en title** — fx "Kvitly — 60 sek rundvisning"
4. **Sæt thumbnail** — Loom vælger en frame; hvis den er dårlig, vælg en anden i editoren
5. **Hent embed URL** — klik Share, Embed, kopier iframe `src=`
6. **Sæt i Render** — env var `LOOM_EMBED_URL=https://www.loom.com/embed/xxxxx` på Kvitly-servicen
7. **Download MP4 også** — til LinkedIn-post hvis du vil uploade direkte (LinkedIn straffer eksterne links, så native MP4 kan give bedre rækkevidde)

## Hvis noget går galt under optagelse

- **OCR tager for lang tid** → Optag bare skærmen, klip pausen væk i editoren
- **Du siger noget forkert** → Fortsæt, klip det væk bagefter
- **Ikke sammenhængende første gang** → Tag det 2-3 gange, vælg bedste version. Første optagelse er altid klodset.

## Version B: 30-sek version (til LinkedIn reels eller TikTok-lignende)

Samme struktur, men halvt så hurtig:

- **0–4s:** Kvitteringskaos (Messenger-screenshots)
- **4–12s:** Upload + OCR + indsend
- **12–25s:** Dashboard rundvisning (kort)
- **25–30s:** "Link i kommentarer"

## Alternative hooks (hvis du vil prøve flere versioner)

**Hook A — Frustration** (anbefalet, den der er i scriptet):
> "Som kasserer i en forening ser jeg på det her hver måned..."

**Hook B — Konkret tid:**
> "Jeg har sparet 4 timer om måneden som kasserer. Sådan her."

**Hook C — Demo først:**
> "Det her er Kvitly. 60 sekunder, og du ser hvorfor jeg byggede det."

**Hook D — Mock-problem:**
> "Kvitterings-bon i Messenger. Mail fra Netto. Sms fra bestyrelsen. Lyder det bekendt?"

Vælg den der føles mest naturlig når du siger den højt.

## Tekniske tips

- **Optag i inkognito-vindue** for at undgå auto-udfyldte passwords og browser-bookmarks
- **Skjul Windows taskbar / macOS dock** (auto-hide aktiveret)
- **Clean dashboard-data** — sørg for at navne der vises er plausible foreninger (ikke test-data som "asdf" eller "Test bruger")
- **Slet demo_requests.jsonl** inden optagelse hvis du viser dev-console
- **Tjek lyd** med en 5-sek test-optagelse først

## Gmail / Messenger screenshots til intro

Hvis du ikke har en rigtig Messenger-tråd med kvitteringer du kan vise, opret en ny og få en ven til at sende dig 3-4 eksempel-kvitteringer (eller tag selv billeder af 3-4 rigtige kvitteringer og send til dig selv). Det tager 5 minutter og giver en meget stærkere krog end en tom skærm.
