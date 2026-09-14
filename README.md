# Doporučovací hub

Statický web pro ukázku z mobilu: rozcestník a čtyři landing pages. Každá stránka se dá sdílet i samostatně.
Nepoužívá frameworky, cookies, tracking ani externí runtime závislosti.

```
/
├── index.html                      rozcestník
├── lp/
│   ├── motivacni-darky.html        partnerská LP pošliRADOST (Lenka Valíčková) + QR
│   ├── kvartalni-planovani.html
│   ├── strategicky-bootcamp.html
│   └── strategicke-analyzy.html
├── assets/
│   ├── css/     hub.css (rozcestník), mv.css (3 LP Miry), darky.css (LP pošliRADOST)
│   ├── fonts/   Hanken Grotesk + Barlow Condensed (self-hosted, woff2)
│   ├── img/     WebP obrázky, og/ = náhledy pro sdílení (JPEG 1200×630)
│   └── qr/      motivacnidarky.svg
├── tools/generate_qr.py            generátor QR (jen standardní knihovna Pythonu)
└── .nojekyll
```

Všechny odkazy a assety používají relativní cesty, web proto funguje pod libovolnou subcestou
(`https://<uzivatel>.github.io/<repo>/`).

## Lokální náhled

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Pak otevřete http://127.0.0.1:8000/.

## Nasazení na GitHub Pages

1. Vytvořte **veřejný** repozitář, např. `like-it-hub-mvp`.
2. Nahrajte obsah složky do větve `main`:
   ```bash
   git init -b main
   git add .
   git commit -m "Doporučovací hub: rozcestník a 4 landing pages"
   git remote add origin https://github.com/PMandStrategy/like-it-hub-mvp.git
   git push -u origin main
   ```
   Pokud máte `gh` CLI, první krok i push zvládne jeden příkaz (po `git commit`):
   ```bash
   gh repo create PMandStrategy/like-it-hub-mvp --public --source . --push
   ```
3. Na GitHubu otevřete **Settings → Pages → Build and deployment → Deploy from a branch**,
   vyberte `main` a `/ (root)` a uložte.
4. Asi po minutě web poběží na **https://pmandstrategy.github.io/like-it-hub-mvp/**.

### Náhledy při sdílení (Open Graph)

`og:image` a `og:url` musí být absolutní URL, jinak LinkedIn ani chatovací aplikace náhled nenačtou.
V HTML je nastavená adresa `https://pmandstrategy.github.io/like-it-hub-mvp/`. Pokud se repozitář
nebo účet jmenuje jinak, nahraďte ji ve všech HTML souborech. Příklad pro PowerShell:

```powershell
Get-ChildItem -Recurse -Filter *.html | ForEach-Object { (Get-Content $_ -Raw -Encoding utf8).Replace('https://pmandstrategy.github.io/like-it-hub-mvp/', 'https://NOVA-ADRESA/') | Set-Content $_ -Encoding utf8 -NoNewline }
```

Náhled po nasazení ověříte v [LinkedIn Post Inspectoru](https://www.linkedin.com/post-inspector/).

## QR kód (LP Motivační dárky)

QR vede na `https://www.motivacnidarky.cz/?utm_source=doporucovaci-hub&utm_medium=qr&utm_campaign=doporuceni`.
Klikací odkazy na stejné stránce mají `utm_medium=lp`, takže Lenka v analytice rozliší skeny od kliknutí.

Přegenerování s jiným cílem:

```bash
python tools/generate_qr.py --url "https://www.motivacnidarky.cz/?utm_source=doporucovaci-hub&utm_medium=qr&utm_campaign=doporuceni"
```

Skript nepotřebuje žádné balíčky. Hotový kód nezávisle přečte zpět (formátové bity, syndromy
Reed-Solomon, obsah) a SVG uloží jen tehdy, když výsledek sedí se zadanou URL. Před tiskem ho
přesto naskenujte telefonem.

## Obsah, který stárne nebo chybí

- **LP Motivační dárky:** odečet ceny vzorkového balíčku platí pro objednávky **do 30. 9. 2026**
  (podle motivacnidarky.cz ke 14. 9. 2026). Po tomto datu upravte text v kroku 2.
- **LP Strategický bootcamp:** termíny běhů jsou aktuální ke 14. 9. 2026.
- Místa označená `[DOPLNIT …]` (žlutě zvýrazněná) je potřeba doplnit:
  - telefon na všech třech LP Miry,
  - délka workshopu a četnost check-inů (kvartální plánování),
  - rytmus společných setkání (bootcamp).

Seznam všech výskytů vypíše:

```bash
git grep -n "DOPLNIT"
```
