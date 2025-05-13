import streamlit as st
import pandas as pd
import io
import json
import re

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

# **Nowość: podgląd pierwotnych danych**
st.subheader("Podgląd pierwotnych danych (pominięte nagłówki)")
st.dataframe(df.head(100))  # pokaż pierwsze 100 wierszy surowych danych

# 1) Oczyść kolumnę gwarancji: zostaw tylko np. "6 miesięcy"
wcol = 'Informacje o gwarancjach (opcjonalne)'
if wcol in df.columns:
    df[wcol] = (
        df[wcol].astype(str)
               .str.replace(r'^Gwarancja\s*', '', regex=True)
               .str.replace(r'\s*\(.*\)', '', regex=True)
               .str.strip()
    )

# 2) Przetwórz kolumnę "Opis oferty": zamiana JSON na prosty HTML (h2, p)
def clean_description(json_str):
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return ""
    html_out = []
    for section in data.get('sections', []):
        for item in section.get('items', []):
            if item.get('type') == 'TEXT':
                content = item.get('content', '')
                # Zastąp wszystkie nagłówki na <h2>
                content = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<h2>\1</h2>', content, flags=re.DOTALL)
                # Usuń znaczniki <ul>
                content = re.sub(r'</?ul>', '', content)
                # Zamień <li> na paragraf z punktorami
                content = re.sub(r'<li>(.*?)</li>', r'<p>• \1</p>', content, flags=re.DOTALL)
                # Pozostaw tylko <h2> i <p>
                # Usuń inne tagi
                content = re.sub(r'<(?!/?(?:h2|p)\b)[^>]+>', '', content)
                html_out.append(content.strip())
    return '\n'.join(html_out)

if 'Opis oferty' in df.columns:
    df['Opis oferty'] = df['Opis oferty'].apply(clean_description)

# 3) Rozdziel 'Zdjęcia' na oddzielne kolumny URL-ów
img_urls = pd.DataFrame(index=df.index)
if 'Zdjęcia' in df.columns:
    clean = df['Zdjęcia'].astype(str).str.replace(r',\s*', '|', regex=True)
    split_imgs = clean.str.split('|', expand=True)
    split_imgs.columns = [f"Zdjęcie_{i+1}" for i in range(split_imgs.shape[1])]
    img_urls = split_imgs

# 4) Zbuduj wynikowy DataFrame z mapowaniem
result = pd.DataFrame()
for orig_col, target_col in target_mapping.items():
    result[target_col] = df.get(orig_col, "")

# 5) Dodaj kolumny z obrazkami (jeśli są)
if not img_urls.empty:
    result = pd.concat([result, img_urls], axis=1)

# 6) Wypełnij puste wartości i konwertuj całość na string (usuwa problemy z Arrow)
result = result.fillna("").astype(str)

# 7) Wyświetl wynik (tylko pierwsze 100 wierszy)
st.subheader("Wynik mapowania (pierwsze 100 wierszy)")
st.dataframe(result.head(100))

# 8) Przygotuj plik do pobrania
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
# 1. git add main.py; git commit -m "Add HTML cleaning for 'Opis oferty' and raw data preview"
# 2. pip install streamlit pandas openpyxl
# 3. streamlit run main.py
