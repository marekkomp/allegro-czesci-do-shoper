import streamlit as st
import pandas as pd
import io

# Mapping from original CSV columns to desired output columns (without Kod produktu and Reguła Cenowa)
target_mapping = {
    "Tytuł oferty": "Nazwa produktu",
    "Stan": "Kondycja|730|text",
    "Model": "Model|731|text",
    "Rodzaj": "Rodzaj|732|text",
    "Przeznaczenie": "Przeznaczenie|733|text",
    "Napięcie [V]": "Napięcie|734|text",
    # Pojemność: choose disk GB or battery mAh
    "Pojemność dysku [GB]": "Pojemność|735|text",
    "Pojemność (mAh) [mAh]": "Pojemność|735|text",
    "Informacje o gwarancjach (opcjonalne)": "Gwarancja|736|text",
    "Typ": "Typ|737|text",
    "Moc [W]": "Moc|738|text",
    "Informacje dodatkowe": "Informacje dodatkowe|739|text",
    "Załączone wyposażenie": "W zestawie|740|text",
    # Additional fields
    "ID oferty": "ID oferty",
    "Podkategoria": "Podkategoria",
    "Liczba sztuk": "Liczba sztuk",
    "Opis oferty": "Opis oferty",
    "Marka": "Marka",
    "Kod producenta": "Kod producenta",
}

st.title("CSV Column Mapper & Exporter")

uploaded = st.file_uploader("Wgraj plik CSV", type=["csv"])
if not uploaded:
    st.info("Proszę wgrać plik CSV (pierwsze 3 wiersze pomijane, 4. wiersz jako nagłówek)")
    st.stop()

# Wczytanie CSV (pomijamy pierwsze 3 wiersze)
df = pd.read_csv(uploaded, header=3, sep=',')

# 1) Oczyść kolumnę gwarancji: zostaw tylko np. "6 miesięcy"
wcol = 'Informacje o gwarancjach (opcjonalne)'
if wcol in df.columns:
    df[wcol] = (
        df[wcol].astype(str)
               .str.replace(r'^Gwarancja\s*', '', regex=True)
               .str.replace(r'\s*\(.*\)', '', regex=True)
               .str.strip()
    )

# 2) Rozdziel 'Zdjęcia' na oddzielne kolumny URL-ów
img_urls = pd.DataFrame(index=df.index)
if 'Zdjęcia' in df.columns:
    # Zamień separację przecinkiem na '|', rozdziel
    clean = df['Zdjęcia'].astype(str).str.replace(r',\s*', '|', regex=True)
    split_imgs = clean.str.split('|', expand=True)
    # Nazwij kolumny Zdjęcie_1, Zdjęcie_2, ...
    split_imgs.columns = [f"Zdjęcie_{i+1}" for i in range(split_imgs.shape[1])]
    img_urls = split_imgs

# 3) Zbuduj wynikowy DataFrame z mapowaniem
result = pd.DataFrame()
for orig_col, target_col in target_mapping.items():
    result[target_col] = df.get(orig_col, "")

# 4) Dodaj kolumny z obrazkami (jeśli są)
if not img_urls.empty:
    result = pd.concat([result, img_urls], axis=1)

# 5) Wypełnij puste wartości i konwertuj całość na string (usuwa problemy z Arrow)
result = result.fillna("").astype(str)

# 6) Wyświetl wynik (tylko pierwsze 100 wierszy, żeby uniknąć błędów dużych DataFrame)
st.dataframe(result.head(100))

# 7) Przygotuj plik do pobrania
buffer = io.BytesIO()
result.to_excel(buffer, index=False, engine='openpyxl')
buffer.seek(0)

st.download_button(
    label="Pobierz pełny plik Excel",
    data=buffer,
    file_name="mapped_output.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Uruchomienie:
# 1. git add main.py; git commit -m "Fix: split images into columns, clamp display, cast to str"
# 2. pip install streamlit pandas openpyxl
# 3. streamlit run main.py
