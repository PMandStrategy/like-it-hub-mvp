# Doporučovací hub

Statický web pro ukázku z mobilu: rozcestník a pět landing pages. Každá stránka se dá sdílet i samostatně.
Nepoužívá frameworky, cookies, tracking ani externí runtime závislosti.

```
/
├── index.html                            rozcestník
├── lp/
│   ├── kvartalni-planovani.html          brand Mira Vlach (mv.css)
│   ├── strategicky-bootcamp.html         brand Strategický bootcamp (sb.css)
│   ├── strategicke-analyzy.html          Strategický bootcamp – Analytická divize (sb.css, body.analytics)
│   ├── skoleni-projektoveho-rizeni.html  brand skolenipm.cz (pm.css)
│   └── motivacni-darky.html              partnerská LP pošliRADOST (darky.css) + QR
├── assets/
│   ├── css/     hub.css, mv.css, sb.css, pm.css, darky.css
│   ├── fonts/   Hanken Grotesk, Barlow Condensed, DM Sans, Roboto Condensed (self-hosted woff2)
│   ├── img/
│   │   ├── sb/  logo bootcampu, logo Analytické divize (text i štítek), ikony diamantu, fotky
│   │   ├── pm/  fotky ze školení
│   │   ├── mv/  logo Mira Vlach
│   │   ├── darky/
│   │   └── og/  náhledy pro sdílení (JPEG 1200×630)
│   └── qr/      motivacnidarky.svg
├── tools/generate_qr.py                  generátor QR (jen standardní knihovna Pythonu)
└── .nojekyll
```

Všechny odkazy a assety používají relativní cesty, web proto funguje pod libovolnou subcestou
(`https://<uzivatel>.github.io/<repo>/`).

Živá verze: **https://pmandstrategy.github.io/like-it-hub-mvp/**

## Grafika Analytické divize

Ve složce `assets/img/sb/` jsou varianty podle návrhu loga:

- `logo-analyticka-divize.webp` – modrý diamant + podtitul „ANALYTICKÁ DIVIZE“ (použité v záhlaví LP),
- `logo-analyticka-divize-stitek.webp` – podtitul v modrém štítku,
- `diamant.svg`, `diamant-3.svg`, `diamant-5.svg`, `diamant-7.svg` – ikona diamantu bez paprsků a se 3, 5 a 7 paprsky (vektor).

Loga vznikla z originálního loga ze strategickybootcamp.cz (diamant přebarvený na modrou #3DA5DC,
podtitul písmem DM Sans).

## Lokální náhled

```bash
python -m http.server 8000 --bind 127.0.0.1
```

Pak otevřete http://127.0.0.1:8000/.

## Nasazení a aktualizace

Web běží z větve `main` (Settings → Pages → Deploy from a branch → `main` / `/ (root)`).
Každý push do `main` se do minuty promítne na živou adresu.

### Náhledy při sdílení (Open Graph)

`og:image` a `og:url` musí být absolutní URL, jinak LinkedIn ani chatovací aplikace náhled nenačtou.
V HTML je nastavená adresa `https://pmandstrategy.github.io/like-it-hub-mvp/`. Při přejmenování
repozitáře ji nahraďte ve všech HTML souborech. Náhled ověříte v
[LinkedIn Post Inspectoru](https://www.linkedin.com/post-inspector/).

## QR kódy

Každá LP je jen stručná ilustrační verze. Na konferenci ji ukážete z mobilu a protějšek si přes QR
otevře plnou cílovou stránku. Tlačítko **QR** vpravo dole (nebo odkaz „Ukázat QR kód“) zobrazí kód
přes celou obrazovku, „Zavřít“ ho skryje. Funguje bez JavaScriptu (`assets/css/qr.css`, `:target`).

| LP | QR i hlavní tlačítko vedou na |
|---|---|
| Motivační dárky | motivacnidarky.cz |
| Strategické kvartální plánování | QR: tato stránka (vlastní web zatím není), tlačítko: LinkedIn |
| Strategický bootcamp | strategickybootcamp.cz |
| Strategické analýzy | strategickybootcamp.cz/thinktank |
| Školení projektových manažerů | skolenipm.cz |

Na LP nejsou žádná `mailto` tlačítka – poptávky vždy řeší cílová stránka nebo LinkedIn.

Externí cíle mají UTM parametry: QR `utm_medium=qr`, klikací odkazy `utm_medium=lp`,
`utm_campaign` podle stránky. Měřit je umí jen web, který má analytiku.

Cíle a barvy kódů jsou v `tools/qr_targets.json`. Po změně (např. až bude mít kvartální plánování
vlastní stránku) přegenerujte všechny kódy:

```bash
python tools/generate_qr.py --all
```

Skript nepotřebuje žádné balíčky. Každý kód nezávisle přečte zpět (formátové bity, syndromy
Reed-Solomon, obsah) a SVG uloží jen tehdy, když výsledek sedí se zadanou URL. Při změně cílové
adresy upravte i odkaz pod kódem v HTML dané LP.

## Obsah, který stárne (stav ke 14. 9. 2026)

- **Motivační dárky:** odečet ceny vzorkového balíčku platí pro objednávky do 30. 9. 2026.
- **Strategický bootcamp:** termíny běhů 30. 9.–27. 10. a 18. 11.–16. 12. 2026.
- **Školení:** termín 10.–11. 10. 2026 a počet volných míst (3).
- **Strategické analýzy:** orientační cena od 10 000 Kč a pilotní fáze služby.
