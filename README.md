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

Dal tab **Actions** del repo → workflow **Rassegna settimanale** → **Run workflow**. Lo script gira sempre quando invocato manualmente.

In locale, senza inviare nulla:

```bash
pip install -r requirements.txt
python rassegna.py
```

Senza `RESEND_API_KEY` nell'ambiente, lo script stampa l'HTML su stdout invece di spedire.

## Aggiornare l'elenco fonti

Modifica `fonti_datadriven.json` (direttamente su GitHub o in locale e poi push). Lo schema è documentato dentro il file stesso, in `meta.campi`.

## Schedulazione, DST e ritardi

Cron: `0 3 * * 3` = mercoledì 03:00 UTC → 5:00 Roma in ora legale (mar-ott), 4:00 in ora solare (nov-mar). Tenuto un solo cron per evitare doppi invii nei periodi di transizione DST.

GitHub Actions free non garantisce la puntualità del cron: durante i picchi può ritardare anche di alcune ore. Per la rassegna settimanale è accettabile — arriva comunque "mercoledì mattina". Se serve precisione al minuto, usare uno scheduler esterno (es. cron-job.org) che richiami il workflow via API.

## Costi

- GitHub Actions: gratis (repo pubblico).
- Resend: free tier (3.000 mail/mese, 100/giorno) ampiamente sufficiente.
