# Ezermalas iesniegumu sistēma · m1-lab

Mācību prototips M1 modulim "Programmatūras izstrāde un MI koda palīgi" (2. nodarbība). Iedzīvotājs iesniedz iesniegumu, sistēma piešķir numuru, atbildes termiņu un atbildes kanālu.

> Noteikumi vienkāršoti mācību vajadzībām. Ezermalas novada pašvaldība un OMD reģistrs ir izdomāti. **Visi dati ir sintētiski.** Reālus personas datus šeit neievadiet.

## Kā sākt

1. Šī ir veidne (template). Spiediet **Use this template → Create a new repository**, nosaukums precīzi **`m1-lab`**, **Public**.
2. Savā kopijā: **Code → Codespaces → Create codespace on main**. Pirmā palaišana ilgst 2–3 minūtes.
3. Cilnē **Claude Code** pieslēdzieties ar kursa kontu.
4. Terminālī: `make run`. Cilnē **Ports** pie porta 8000 spiediet globusa ikonu un adreses beigās pievienojiet `/ui`.

## Komandas

| Komanda | Ko dara |
|---|---|
| `make run` | Palaiž lietotni: forma `/ui`, Swagger UI `/docs` |
| `make mock` | Palaiž izdomātā OMD reģistra imitāciju (ports 8001) |
| `make test` | Palaiž testus |
| `make fmt` | Formatē kodu pirms komita |
| `make check` | Skeneri: ruff, bandit, pip-audit |
| `make rung N=1` | Uzvedņu kāpņu pakāpiens 1, 2 vai 3 (zars `cr1-rN`) |
| `make skill` | Pievieno prasmi `ezermala-ui` |
| `make vendor-pr` | Piegādātāja izmaiņa CR-3 (zars `vendor/cr-3`) |
| `make reset-to-after-cr1` | Aizstāj `main` ar kontrolpunktu, ja atpalikāt |
| `make help` | Visas komandas |

## Kur kas atrodas

| Mape vai fails | Saturs |
|---|---|
| `tracker/` | Pieteikumi (tickets), eksportēti no pieteikumu uzskaites sistēmas |
| `docs/openapi.yaml` | API līgums (API contract), patiesības avots |
| `docs/review-checklist.md` | 10 punktu pārskatīšanas kontrolsaraksts |
| `app/` | Lietotnes kods (FastAPI) |
| `ui/` | Lietotāja saskarne: statiski HTML faili, pieejami adresē `/ui/<fails>.html` |
| `mock_omd/` | Izdomātā OMD reģistra imitācija |
| `tests/` | Automātiskie testi |
| `CLAUDE.md` | Projekta noteikumi MI aģentam |
| `.claude/agents/` | Apakšaģenti: `testetajs`, `parskatitajs` |
| `.github/workflows/ci.yml` | CI: stila pārbaude, testi, izsekojamība |

## OMD reģistra imitācija: izsaukšanas kodi

| Personas kods | Reģistrs atbild |
|---|---|
| `32000000001` | e-adrese aktīva (`ACTIVE`) |
| `32000000002` | e-adrese nav aktivizēta (`NOT_ACTIVATED`) |
| `32000000404` | 404, reģistrā nav ieraksta |
| `32000000503` | 503, apkope |
| `32000000408` | atbild pēc 10 sekundēm |
| `32000000999` | nedokumentēts statuss `SUSPENDED` |
| `32000000500` | bojāta atbilde |

## Kontrolpunkti

Ja atpalikāt, `make reset-to-<kontrolpunkts>` aizstāj jūsu `main` ar gatavu stāvokli no veidnes:

| Kontrolpunkts | Stāvoklis |
|---|---|
| `after-cr0` | CR-0 izstrādāts |
| `after-cr1` | CR-1 izstrādāts, ar testiem |
| `after-cr2` | CR-2 izstrādāts, ar testiem |
| `after-cr3` | CR-3 piegādātāja izmaiņa salabota |
