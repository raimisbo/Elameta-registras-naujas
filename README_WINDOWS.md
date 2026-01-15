# Registras – Windows paleidimas (testuotojui)

Šis projektas yra Django aplikacija. Paleidimas automatizuotas per `bootstrap.ps1`.

## 0) Reikalavimai (vieną kartą)
1. Windows 10/11
2. Python 64-bit (rekomenduojama)  
   - Įdiegiant Python pažymėkite: **“Add python.exe to PATH”**
3. Internetas (pirmam `pip install`)

## 1) ZIP išskleidimas
1. Išskleiskite ZIP į paprastą vietą, pvz.:
   - `C:\Projects\registras\`
2. Patikrinkite, kad tame aplanke būtų:
   - `manage.py`
   - `requirements.txt`
   - `bootstrap.ps1`
   - katalogai `registras\` ir `pozicijos\`
   - katalogas `media\` (brėžiniai + šriftai)

Svarbu: `media\` turi likti **šalia `manage.py`**.

## 2) Paleidimas (viena komanda)
Atidarykite PowerShell projekto aplanke:
- Explorer → atsidarykite projekto aplanką
- į adreso juostą įrašykite `powershell` ir spauskite Enter

Paleiskite:

powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1

Skriptas automatiškai:
- sukurs virtualią aplinką `.venv`
- atnaujins `pip`
- suinstaliuos priklausomybes iš `requirements.txt`
- paleis `python manage.py check`
- paleis `python manage.py migrate` (tai automatiškai sukuria DB, jei naudojamas SQLite)
- paleis serverį `http://127.0.0.1:8000/` ir (dažniausiai) atidarys naršyklę

## 3) Sustabdymas
Serverį sustabdykite su **Ctrl+C** PowerShell lange.

## 4) Media (brėžiniai, šriftai, preview)
ZIP’e yra `media\` katalogas. Jo neištrinkite ir nekeiskite vietos – jis turi likti šalia `manage.py`.

Jei PDF’e nematote LT raidžių arba vietoj jų rodo simbolius:
- patikrinkite, ar yra:
  - `media\fonts\NotoSans-Regular.ttf`
  - `media\fonts\NotoSans-Bold.ttf`

## 5) Dažniausios problemos
### A) “python / py nerastas”
Perinstaliuokite Python ir pažymėkite **“Add Python to PATH”**, tada iš naujo atsidarykite PowerShell.

### B) `pip install` klaidos (retai)
Skriptas automatiškai atnaujina `pip`, todėl dažniausiai viskas praeina.
Jei vis tiek nepavyksta:
- nukopijuokite pilną klaidos log’ą iš PowerShell
- pridėkite `python -V` (versiją)
ir atsiųskite projekto autoriui.

### C) Migrations nerastos
Jei `bootstrap.ps1` parašo, kad nerado `migrations\__init__.py`:
- ZIP’e trūksta migracijų katalogų (pvz. `pozicijos\migrations\`).
Tokiu atveju reikia naujo ZIP su migracijomis.

## 6) Pastaba dėl veikimo aplinkos
Paleidimas naudoja lokalią aplinką (`.venv`) tik šiame projekto aplanke.
Jei norite “švaraus” paleidimo iš naujo:
- ištrinkite `.venv\` katalogą (nebūtina, tik jei reikia)
- paleiskite `bootstrap.ps1` dar kartą
