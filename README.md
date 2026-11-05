# settler-pipeline

Prosty model 3D osadnika → rig → animacja → wzorzec do rysowania pixel artu w Aseprite.

Model jest **wzorcem**, nie gotowym spritem. Pokazuje, gdzie jest każda część ciała w każdej klatce i w każdym z 8 kierunków. Gotowy pixel art rysujesz na nim ręcznie.

## Szybki start

```
pip install -r requirements.txt      # Blender jako moduł Pythona (bpy), ok. 1 min
python3 pipeline/run.py characters/base/params.json
```

Opcjonalnie z porównaniem do Twoich sprite'ów (8 sprite'ów w jednym rzędzie: S, SW, W, NW, N, NE, E, SE):

```
python3 pipeline/run.py characters/base/params.json --original sprites.png --scale 10
```

Pełny przebieg trwa ok. 10 s. Wyniki trafiają do `out/`.

## Co dostajesz w `out/`

| Plik | Do czego |
|---|---|
| `settler_walk_ref.aseprite` | Wzorzec do rysowania: 8 kierunków × 6 klatek, tag na każdy kierunek, warstwa referencyjna + pusta warstwa „rysuj tutaj” |
| `viewer.html` | Podgląd: animacja 3D obok animacji pixel artu, 8 kierunków, przewijanie klatek |
| `settler.glb` | Model z rigiem i animacją (np. do Godota) |
| `settler.blend` | To samo dla Blendera |
| `settler_walk_sheet.png` | Szary pixel art (wiersze = kierunki, kolumny = klatki) |
| `settler_walk_ref_sheet.png` | Wzorzec kolorowy jako sprite sheet |
| `compare.png` | Twój wzór vs render (tylko z `--original`) |

## Kolory wzorca

Lewa strona postaci jest ciepła, prawa zimna.

| Część | Kolor |
|---|---|
| Głowa | jasnoszary |
| Włosy | brązowy |
| Tułów | ciemnoszary |
| Lewa dłoń | czerwony |
| Lewa stopa | żółty |
| Prawa dłoń | niebieski |
| Prawa stopa | zielony |
| Oczy | czarny |

## Model

Jednostka = 1 piksel sprite'a. Postać patrzy w −Y, ziemia to z = 0.

- **Głowa** – superelipsoida (coś między kulą a sześcianem), krótkie włosy.
- **Tułów** – walec.
- **Dłonie i stopy** – kule, bez ramion i nóg.
- **Rig** – 7 kości: `root`, `body`, `head`, `hand.L`, `hand.R`, `foot.L`, `foot.R`. Każda część jest sztywna (waga 1).

## Parametry (`characters/base/params.json`)

### Kształt

| Parametr | Co robi |
|---|---|
| `head_c`, `head_r` | Środek i promienie głowy (x, y, z) |
| `head_roundness_n` | 2 = kula, im więcej, tym bliżej sześcianu (teraz 3,6) |
| `hairline_front`, `hairline_side`, `hairline_back` | Wysokość linii włosów: nad czołem, nad uszami, na karku (−1…1) |
| `body_c`, `body_radius`, `body_height` | Tułów |
| `hand_x`, `hand_y`, `hand_z`, `hand_radius` | Dłonie (lustrzane) |
| `foot_x`, `foot_y`, `foot_radius` | Stopy (lustrzane) |
| `eye_dx`, `eye_dz`, `eye_r` | Oczy |

### Chód

| Parametr | Co robi |
|---|---|
| `walk_frames` | Klatki pętli w 3D (musi dzielić się przez liczbę klatek sprite'a) |
| `phase_offset` | Przesunięcie, z której fazy kroku startuje pierwsza klatka |
| `stance` | Jaką część cyklu stopa stoi na ziemi (0,6 = 60%) |
| `stride_front`, `stride_back` | Jak daleko stopa sięga do przodu i do tyłu |
| `lift` | Jak wysoko stopa się unosi |
| `heel_kick` | 0 = stopa jest najwyżej w połowie zamachu; 1 = pięta najpierw idzie w górę z tyłu, a dopiero potem stopa leci do przodu (stopę widać w widoku N) |
| `hand_swing`, `hand_arc` | Zamach rąk i jak bardzo dłoń z przodu idzie w górę |
| `hand_cross` | Jak bardzo dłoń z przodu wchodzi do środka ciała (dłoń z tyłu idzie o połowę tego na zewnątrz); daje ruch rąk w poziomie w widokach S i N |
| `hand_even` | 0 = ręka kopiuje ruch stopy (szybki powrót do tyłu); 1 = równe tempo, pół cyklu do przodu i pół do tyłu |
| `bob_up` | Jaką część kroku tułów jest w górze; 0,67 = przy 6 klatkach 1 klatka w dole (stopa ląduje) i 2 w górze. Brak parametru = w górze tylko w szczycie zamachu stopy |

Tułów z głową podskakuje zawsze dokładnie o 1 px, żeby kształt głowy nie „pływał”.

### Kamera

| Parametr | Co robi |
|---|---|
| `elev_deg` | Kąt kamery nad poziomem (widok top-down) |
| `target_z`, `cam_dx` | Wyśrodkowanie w klatce 24×24 i wyrównanie do siatki pikseli |

## Jak to działa

1. `build.py` – buduje model, rig i animację w Blenderze, eksportuje `.blend` i `.glb`.
2. `render.py` – renderuje 8 kierunków. Każdy piksel zapisuje część ciała, głębię i kierunek powierzchni.
3. `pixelize.py` – zmniejsza render do pikseli sprite'a (głosowanie większościowe), dodaje kontur i cień.
4. `make_ref.py` – składa kolorowy wzorzec i zapisuje plik `.aseprite`.
5. `make_viewer.py` – składa stronę z podglądem.
6. `run.py` – uruchamia wszystko po kolei.
