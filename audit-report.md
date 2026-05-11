# Kvitly E2E-audit — 2026-05-11

Komplet gennemtest af alle hovedflows på https://kvitly.dk via Playwright. Bugs fikset løbende (commits angivet); UX/UI-polish samlet i bunden til godkendelse.

---

## Sammenfatning

| Område | Status | Bemærkning |
|---|---|---|
| Anonymous upload (/u/&lt;token&gt;) | 🟢 OK | Heavy-tested gennem sessionen; intet nyt fundet |
| Login / Forkert-pwd-fejl | 🟢 OK | Generisk fejlbesked på dansk |
| Logout | 🟢 OK | Cookie clearet, redirect / |
| Forgot password form | 🟢 OK | Mailflow ikke testet (kræver email-modtagelse) |
| Reset password (uden token) | 🟢 OK | Tydelig advarsel: "Reset-linket er ugyldigt eller udløbet" |
| Signup (invite-code-validering) | 🟢 OK | Forkert kode → "Ugyldig eller allerede brugt invite-kode" |
| Signup (kort password) | 🟡 P2 | Browser-native validering på engelsk |
| Landing page | 🟢 OK | Hero, demo-form, footer-links virker |
| Dashboard · Oversigt | 🟢 OK | 4 KPI-kort + 3 charts + upload-link card |
| Dashboard · Udgifter | 🟢 Fixed | Godkend var BROKEN — fikset i commit `7578b68` |
| Dashboard · Eksport | 🟢 OK | CSV-knap + post-count |
| Dashboard · Indstillinger | 🟢 OK | Forening-navn-save + email-toggle + udvalg-CRUD verificeret live |
| Mobile (390px) | 🟢 Fixed | Tab-nav overflowede — fikset i commit `15fa332` |

---

## Bugs fikset under auditten

### 1. Godkend / Marker udbetalt / række-expansion gjorde intet — commit `7578b68`

**Symptom:** Klik på "Godkend" eller "Marker udbetalt" gjorde intet synligt. Også: klik på en data-række udvidede ikke detaljerne.

**Root cause:** Onclick-attributter interpolerede kvittering-UUID som et bart JavaScript-identifier i stedet for en streng:

```html
<!-- FØR (knækket) -->
onclick="event.stopPropagation();godkend(e97a8426-1cdf-4cf2-a71c-f19bb891fb7c)"
```

JS-parser læser `e97a8426-1cdf-4cf2-...` som matematisk udtryk på udefinerede symboler → throw'er `SyntaxError: Invalid or unexpected token` i den inline-handler. Klikket gør intet.

**Fix:** Quote UUID'en så den bliver et string-literal:

```html
<!-- EFTER -->
onclick="event.stopPropagation();godkend('e97a8426-1cdf-4cf2-a71c-f19bb891fb7c')"
```

Tre steder ramt:
- `actionBtnHTML()` for både `godkend(${rowNum})` og `markUdbetalt(${rowNum})`
- `renderTable()` for `toggleDetail(${rowNum})` (række-udvidelse)

Verificeret live efter deploy: Godkend-klik → toast "Status opdateret." + knappen skifter til "Marker udbetalt".

### 2. Dashboard tab-nav overflowede 375px viewports — commit `15fa332`

**Symptom:** Hele dashboardet havde horisontal scrollbar på mobile (375-390px). Føltes broken selv om indholdet stort set var synligt.

**Root cause:** 4× tab-knapper (Oversigt, Udgifter, Eksport, Indstillinger) summede til ~384px på 375px viewport. "Indstillinger" som længste label var den der stak ud.

**Fix:** På `@media (max-width: 520px)` får `.tab-nav` `overflow-x: auto` + skjult scrollbar; tab-knapper får `flex-shrink: 0` så de bevarer størrelse og scrollbaren lever lokalt i nav'en (uden synlig scrollbar).

---

## UX/UI-polish til godkendelse

Følgende er kosmetiske eller mindre forbedringer der kræver dit designvalg. Intet er kritisk — implementeres kun hvis du siger god for det.

### P1 — Synlighed og feedback

#### P1.1 — Toast er for diskret
**Observation:** Toast'en ("Status opdateret.", "Tilføjet.", "Slettet.") forsvinder hurtigt og er let at overse — særligt på dashboardet hvor man stirrer på rækker/tabel. Når brugeren klikkede "Godkend" på en kvittering kan de let tro intet skete fordi rækken stadig er i view + filter='Alle' viser stadig den nu-godkendte række (med ny "Godkendt"-badge) — toast'en er den primære success-confirmation og forsvinder hurtigt.

**Forslag:** Bump toast-varighed fra ~2s → 3.5s og gør den visuelt mere markant (skygge + slide-in fra højre øverst). Alternativt: animér status-badgen i den ændrede række (pulse-effekt i 1-2s) som visuel "succes"-confirmation.

#### P1.2 — Browser-native HTML5-fejlbeskeder på engelsk
**Observation:** Signup-formens password-felt har `minLength="8"`. Når brugeren submitter en kortere password viser browseren: *"Please lengthen this text to 8 characters or more (you are currently using 5 characters)."* — på engelsk midt i en dansk app.

**Forslag:** Tilføj `oninvalid="setCustomValidity('Vælg en adgangskode på mindst 8 tegn')"` + `oninput="setCustomValidity('')"` på password-feltet. Samme bør tjekkes på email-felter (`type=email`-fejl på engelsk). Estimeret 10-15 min arbejde, gælder login + signup + reset.

### P2 — Tilgængelighed og styling

#### P2.1 — 🗑 emoji som delete-knap uden tekst-fallback
**Observation:** I Indstillinger har udvalg/kategori-rækker en delete-knap der er kun emoji 🗑. `<button>` har `title="Slet"` (hover tooltip) men screen-readers læser "wastebasket emoji" højt — ikke "Slet".

**Forslag:** Tilføj `aria-label="Slet"` på begge delete-knapper. Samme for save-knappen ✓ → `aria-label="Gem omdøbning"`. ~5 min.

#### P2.2 — "+ Tilføj" og delete-knap savner focus-visible state
**Observation:** Tab-navigering gennem indstillinger viser ingen synlig focus-ring på add/delete-knapperne. Mistet keyboard a11y.

**Forslag:** Tilføj `.icon-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` (og samme for `.settings-add button`). ~5 min.

#### P2.3 — Hidden save-button kan klikkes programmatisk
**Observation:** I udvalg-rækken bytter UI mellem save-knap (✓) og delete-knap (🗑) baseret på "dirty" state. Den skjulte knap er `display: none` men kan stadig modtage programmatisk `.click()`. Det er ikke en bruger-vendt bug, men en lille robusthedsting hvis nogensinde nogen automatiserer dashboard.

**Forslag:** Når en knap skjules via `display: none`, sæt `disabled = true` parallelt. ~10 min.

### P3 — Copy og information

#### P3.1 — Landing page har "Skriv til mig" 3 gange tæt på hinanden
**Observation:** "Skriv til mig" optræder som CTA i header, hero, og beta-sektionen — tre gange i de første ~600px scroll. Føles repetitivt.

**Forslag:** Behold CTA i header + hero. I beta-sektionen erstat med en kontrast-CTA som "Se hvordan det virker" eller "Bestil en demo". Designvalg — vil du have det ændret?

#### P3.2 — Indsamlingslink-kort dupliceres på tværs af tabs
**Observation:** "Indsamlingslink til medlemmer" (med Regenerér, Sæt på pause, Kopier, QR-download) vises på TOPPEN af alle 4 tabs (Oversigt, Udgifter, Eksport, Indstillinger). Det er sandsynligvis bevidst, men det giver lange scrolls især på mobile, da kortet er ret stort og funktionel-tunge actions repeat'es.

**Forslag-A:** Behold på Oversigt og Indstillinger; skjul på Udgifter og Eksport (hvor man er fokuseret på data).
**Forslag-B:** Behold som permanent header — men gør det mere kompakt (skjul URL i en tooltip/popover, kun "Del link" + QR ikon).
Begge kræver designvalg. Sig hvilken du foretrækker.

#### P3.3 — Dashboard har ingen synlig "logged in as ..."-indikator
**Observation:** I dashboard-headeren står kun "Kvitly · Dashboard". Ingen visning af hvilken email/forening man er logget ind som, og intet logout-link i UI'et (man skal kende `/logout`-URLen).

**Forslag:** Tilføj en lille bruger-pille i header-højre: `[email] · Log ud`. Eller dropdown med `[Forening] ▾` → udklap viser email + logout. ~30 min.

#### P3.4 — Glemt password "Send link"-flow giver ingen visuel bekræftelse
**Observation:** På /forgot-password er knappen "Send link" — men jeg testede ikke selve indsendelsen (kræver email-modtagelse), så jeg ved ikke om bruger kommer tilbage med "Vi har sendt en link til din email"-tekst. Hvis ikke, det er en blackhole.

**Forslag:** Verificér at indsendelse rendere en bekræftelses-state ("Hvis emailen findes sender vi et link inden for få minutter."). Sig til hvis du vil have mig til at teste flowet end-to-end med en throwaway-email.

### P4 — Mikro-polish (laveste prioritet)

- `.tab-btn` har ikke `min-height: 44px` på desktop (apple touch-target) — kun under mobil media-query. Hvis touchscreen-laptop bruger dashboardet bliver tabs lidt fnuller.
- Login-form "Forkert email eller adgangskode."-besked har ingen ikon eller farve som indikator — ren tekst. Subtilt erstattes med rød ⚠️ + tekst for hurtigere visuel scanning.
- Signup-form har ikke "vis password"-toggle. Standard på moderne forms; estimerer 5-10 min.
- Dashboard's "Andet"-udvalg (last entry) har samme styling som de øvrige; det kunne markeres som "system-udvalg" (kursivt / dæmpet) så brugeren ved at det er en fallback man ikke bør slette.
- Receipt-modal/detail-row mangler "Slet kvittering" UI? Jeg så `DELETE /dashboard/api/kvittering/<id>`-route men ingen klar UI-knap. Hvis ikke implementeret, vil du have den tilføjet?

---

## Hvad jeg ikke testede

Disse blev sprunget over fordi de kræver eksterne ressourcer eller risikerer at ødelægge brugerens data:

- **Full OCR-scan af reelle billeder** end-to-end → review-screen → confirm → DB-insert (kræver upload af faktiske kvittering-billeder; bedre at du gør det med dine egne testfiler)
- **Forgot-password mail-modtagelse** (kræver Gmail-konto under min kontrol)
- **Reset-password med gyldig token** (samme grund)
- **CSV-eksport faktisk download** (kunne ikke validere indhold uden at hente filen ud af browseren)
- **Delete af reel kvittering** fra dashboardet (destruktiv handling)
- **Pause/genstart upload-token** (ville påvirke en aktiv link)
- **Regenerér upload-token** (ville bryde din eksisterende QR/link)
- **Performance under last** (samtidige uploads, store filer)
- **Sikkerheds-audit** (CSRF, XSS, RLS-test) — separat disciplin

---

## Forslag til opfølgning

1. **Du vurderer** UX/UI-listen ovenfor og siger hvilke punkter jeg skal implementere
2. **Jeg implementerer** de godkendte punkter i én commit-runde
3. **Du tester** Godkend-flowet selv (commit 7578b68 deployed — virker live)
4. **Vi parker** OCR-mail-deliverability-tests til en separat session

---

**Commits under denne audit:**
- `7578b68` — fix(dashboard): quote UUID in onclick handlers
- `15fa332` — fix(dashboard): tab-nav horizontal overflow on <520px viewports
