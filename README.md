# mappine-rassegna

Rassegna stampa settimanale automatica per la newsletter **mappine**.

Ogni mercoledì alle 5:00 (ora di Roma) un workflow GitHub Actions:
1. legge `fonti_datadriven.json`,
2. scarica i feed RSS di tutte le fonti elencate,
3. filtra i post degli ultimi 7 giorni,
4. invia una mail HTML a `riccardo@mappine.it` via [Resend](https://resend.com).

Le fonti senza RSS (Reuters Graphics, Bloomberg, profili giornalisti senza feed, ecc.) compaiono in fondo alla mail come promemoria da controllare a mano.

## Setup

1. Crea un account su [resend.com](https://resend.com) e genera un'API key.
2. Su GitHub → **Settings → Secrets and variables → Actions → New repository secret**:
   - `RESEND_API_KEY` = la chiave appena creata.
3. (Opzionale) Verifica un dominio su Resend e imposta la variabile `MAIL_FROM` nel workflow (es. `rassegna@mappine.it`). Senza dominio verificato la mail parte da `onboarding@resend.dev` ma rischia lo spam.

## Test manuale

Dal tab **Actions** del repo → workflow **Rassegna settimanale** → **Run workflow** → metti `force: true`. Bypassa il controllo orario e manda la mail subito.

In locale, senza inviare nulla:

```bash
pip install -r requirements.txt
FORCE_RUN=1 python rassegna.py
```

Stampa l'HTML su stdout (`RESEND_API_KEY` non impostata = no invio).

## Aggiornare l'elenco fonti

Modifica `fonti_datadriven.json` (direttamente su GitHub o in locale e poi push). Lo schema è documentato dentro il file stesso, in `meta.campi`.

## Schedulazione e DST

GitHub Actions usa cron in UTC. Per centrare le 5:00 di Roma sia in ora solare che legale il workflow ha **due** cron (03:00 UTC e 04:00 UTC), e lo script esce subito se l'orario di Roma non è davvero le 5 — così non parte due volte nei periodi di transizione.

## Costi

- GitHub Actions: gratis (repo pubblico).
- Resend: free tier (3.000 mail/mese, 100/giorno) ampiamente sufficiente.
