import streamlit as st
import pandas as pd
import io
import json
import re

# Mapping from original CSV columns to desired output columns
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

# 1) Pokaż mapowanie kolumn
st.subheader("Połączenia kolumn (źródło → docelowa)")
df_mapping = pd.DataFrame(
    list(target_mapping.items()),
    columns=["Kolumna źródłowa", "Kolumna docelowa"]
)
st.table(df_mapping)

# 2) Wgraj plik CSV
uploaded = st.file_uploader("Wgraj plik CSV", type=["csv"])
if not uploaded:
    st.info("Proszę wgrać plik CSV (pierwsze 3 wiersze pomijane, 4. wiersz jako nagłówek)")
    st.stop()

# 3) Wczytanie CSV (pomijamy pierwsze 3 wiersze)
df = pd.read_csv(uploaded, header=3, sep=',')

# 4) Podgląd pierwotnych danych
st.subheader("Podgląd pierwotnych danych (pierwsze 100 wierszy)")
st.dataframe(df.head(100))

# 5) Usuń wiodące apostrofy z ID oferty
if 'ID oferty' in df.columns:
    df['ID oferty'] = df['ID oferty'].astype(str).str.lstrip("'")

# 6) Oczyść kolumnę gwarancji
wcol = 'Informacje o gwarancjach (opcjonalne)'
if wcol in df.columns:
    df[wcol] = (
        df[wcol].astype(str)
               .str.replace(r'^Gwarancja\s*', '', regex=True)
               .str.replace(r'\s*\(.*\)', '', regex=True)
               .str.strip()
    )

# 7) Przetwórz "Opis oferty" z JSON → HTML (h2, p)
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
                content = re.sub(r'<h[1-6]>(.*?)</h[1-6]>',
                                 r'<h2>\1</h2>', content, flags=re.DOTALL)
                content = re.sub(r'</?ul>', '', content)
                content = re.sub(r'<li>(.*?)</li>',
                                 r'<p>• \1</p>', content, flags=re.DOTALL)
                content = re.sub(r'<(?!/?(?:h2|p)\b)[^>]+>', '', content)
                html_out.append(content.strip())
    return '\n'.join(html_out)

if 'Opis oferty' in df.columns:
    df['Opis oferty'] = df['Opis oferty'].apply(clean_description)

# 8) Rozdziel 'Zdjęcia' na osobne kolumny URL
img_urls = pd.DataFrame(index=df.index)
if 'Zdjęcia' in df.columns:
    clean = df['Zdjęcia'].astype(str).str.replace(r',\s*', '|', regex=True)
    split_imgs = clean.str.split('|', expand=True)
    split_imgs.columns = [f"Zdjęcie_{i+1}" for i in range(split_imgs.shape[1])]
    img_urls = split_imgs

# 9) Buduj wynikowy DataFrame z mapowaniem
result = pd.DataFrame()
for orig_col, target_col in target_mapping.items():
    result[target_col] = df.get(orig_col, "")

# 10) Dodaj kolumny z obrazkami
if not img_urls.empty:
    result = pd.concat([result, img_urls], axis=1)

# 11) Wypełnij puste i skonwertuj na string
result = result.fillna("").astype(str)

# 12) Wyświetl wynik
st.subheader("Wynik mapowania (pierwsze 100 wierszy)")
st.dataframe(result.head(100))

# 13) Przygotuj plik EXCEL do pobrania
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
# 1. git add main.py; git commit -m "Final CSV mapper with ID cleanup"
# 2. pip install streamlit pandas openpyxl
# 3. streamlit run main.py
