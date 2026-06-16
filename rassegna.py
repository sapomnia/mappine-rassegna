#!/usr/bin/env python3
"""Rassegna stampa settimanale datadriven per la newsletter mappine."""
from __future__ import annotations

import html
import json
import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

ROME = ZoneInfo("Europe/Rome")
WINDOW_DAYS = 7
FONTI_PATH = Path(__file__).parent / "fonti_datadriven.json"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
DEFAULT_TO = "riccardo@mappine.it"
USER_AGENT = "mappine-rassegna/1.0 (+https://mappine.it)"


@dataclass
class Articolo:
    titolo: str
    link: str
    pubblicato: datetime
    fonte_nome: str
    fonte_tipo: str


def parse_data(entry) -> datetime | None:
    for attr in ("published", "updated", "created"):
        raw = entry.get(attr)
        if not raw:
            continue
        struct = entry.get(f"{attr}_parsed")
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
        try:
            d = parsedate_to_datetime(raw)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


def raccogli_articoli(fonti: list[dict], soglia: datetime) -> tuple[list[Articolo], list[str]]:
    articoli: list[Articolo] = []
    errori: list[str] = []
    visti: set[str] = set()
    for fonte in fonti:
        for url in fonte.get("rss_feed") or []:
            try:
                feed = feedparser.parse(url, agent=USER_AGENT)
                if feed.bozo and not feed.entries:
                    raise RuntimeError(str(feed.bozo_exception))
                for entry in feed.entries:
                    data = parse_data(entry)
                    if not data or data < soglia:
                        continue
                    link = (entry.get("link") or "").strip()
                    if not link or link in visti:
                        continue
                    visti.add(link)
                    articoli.append(Articolo(
                        titolo=(entry.get("title") or "(senza titolo)").strip(),
                        link=link,
                        pubblicato=data,
                        fonte_nome=fonte["nome"],
                        fonte_tipo=fonte["tipo"],
                    ))
            except Exception as e:
                errori.append(f"{fonte['nome']} — {url}: {e}")
    articoli.sort(key=lambda a: a.pubblicato, reverse=True)
    return articoli, errori


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def render_html(articoli: list[Articolo], fonti_senza_rss: list[dict], errori: list[str]) -> str:
    ordine = ["testata", "newsletter", "blog", "giornalista"]
    etichette = {"testata": "Testate", "newsletter": "Newsletter", "blog": "Blog", "giornalista": "Giornalisti"}
    raggr: dict[str, list[Articolo]] = {t: [] for t in ordine}
    for a in articoli:
        raggr.setdefault(a.fonte_tipo, []).append(a)

    out = [
        '<div style="font-family:-apple-system,system-ui,sans-serif;max-width:640px;margin:0 auto;color:#222;">',
        f'<h1 style="font-size:22px;margin-bottom:4px;">Rassegna mappine</h1>',
        f'<p style="color:#666;margin-top:0;">Ultimi {WINDOW_DAYS} giorni · {len(articoli)} articoli</p>',
    ]
    for tipo in ordine:
        items = raggr.get(tipo, [])
        if not items:
            continue
        out.append(
            f'<h2 style="font-size:16px;margin-top:24px;border-bottom:1px solid #eee;padding-bottom:4px;">'
            f'{etichette[tipo]} ({len(items)})</h2><ul style="padding-left:18px;">'
        )
        for a in items:
            data_str = a.pubblicato.astimezone(ROME).strftime("%d/%m")
            out.append(
                f'<li style="margin-bottom:10px;">'
                f'<a href="{esc(a.link)}" style="color:#1a73e8;text-decoration:none;">{esc(a.titolo)}</a><br>'
                f'<span style="color:#888;font-size:13px;">{esc(a.fonte_nome)} · {data_str}</span></li>'
            )
        out.append('</ul>')

    if fonti_senza_rss:
        out.append(
            '<h2 style="font-size:16px;margin-top:32px;">Da controllare a mano (senza RSS)</h2>'
            '<ul style="padding-left:18px;color:#444;">'
        )
        for f in fonti_senza_rss:
            out.append(
                f'<li><a href="{esc(f["url"])}" style="color:#1a73e8;">{esc(f["nome"])}</a> '
                f'<span style="color:#888;">— {esc(f["tipo"])}</span></li>'
            )
        out.append('</ul>')

    if errori:
        out.append(
            '<h2 style="font-size:16px;margin-top:32px;color:#b00;">Feed non raggiungibili</h2>'
            '<ul style="padding-left:18px;color:#888;font-size:13px;">'
        )
        for e in errori:
            out.append(f'<li>{esc(e)}</li>')
        out.append('</ul>')

    out.append('</div>')
    return "\n".join(out)


def invia_mail(corpo_html: str, n_articoli: int) -> None:
    user = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not password:
        print("GMAIL_USER/GMAIL_APP_PASSWORD mancanti: stampo l'HTML su stdout, non invio.", file=sys.stderr)
        print(corpo_html)
        return
    destinatario = os.environ.get("MAIL_TO", DEFAULT_TO)
    oggi = datetime.now(ROME).strftime("%d/%m/%Y")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = destinatario
    msg["Subject"] = f"Rassegna mappine {oggi} — {n_articoli} articoli"
    msg.set_content(f"Apri la mail in HTML per leggere la rassegna ({n_articoli} articoli).")
    msg.add_alternative(corpo_html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"Mail inviata a {destinatario} via Gmail SMTP.")


def main() -> int:
    data = json.loads(FONTI_PATH.read_text(encoding="utf-8"))
    fonti = data["fonti"]
    soglia = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    articoli, errori = raccogli_articoli(fonti, soglia)
    fonti_senza_rss = [f for f in fonti if not f.get("rss_feed")]
    html = render_html(articoli, fonti_senza_rss, errori)
    print(f"Trovati {len(articoli)} articoli, {len(errori)} feed in errore, {len(fonti_senza_rss)} fonti senza RSS.")
    invia_mail(html, len(articoli))
    return 0


if __name__ == "__main__":
    sys.exit(main())
