import streamlit as st
import pandas as pd
import io
import json
import re

# Mapping from original CSV columns to desired output columns
target_mapping = {
    "Tytuł oferty": "Nazwa produktu",
    "Cena PL": "price",
    "Stan": "Kondycja|730|text",
    "Model": "Model|731|text",
    "Rodzaj": "Rodzaj|732|text",
    "Przeznaczenie": "Przeznaczenie|733|text",
    "Napięcie [V]": "Napięcie|734|text",
    "Pojemność dysku [GB]": "Pojemność|735|text",
    "Pojemność (mAh) [mAh]": "Pojemność|735|text",
    "Informacje o gwarancjach (opcjonalne)": "Gwarancja|736|text",
    "Typ": "Typ|737|text",
    "Moc [W]": "Moc|738|text",
    "Informacje dodatkowe": "Informacje dodatkowe|739|text",
    "Załączone wyposażenie": "W zestawie|740|text",
    # Pola dodatkowe bez zmiany nazwy
    "ID oferty": "ID oferty",
    "Podkategoria": "Podkategoria",
    "Liczba sztuk": "Liczba sztuk",
    "Opis oferty": "Opis oferty",
    "Marka": "Marka",
    "Producent": "Producent",
    "Kod producenta": "Kod producenta",
}

st.title("CSV Column Mapper & Exporter")

uploaded = st.file_uploader("Wgraj plik CSV", type=["csv"])
if not uploaded:
    st.info("Proszę wgrać plik CSV (pierwsze 3 wiersze pomijane, 4. wiersz jako nagłówek)")
    st.stop()

# 1) Wczytanie CSV (pomijamy pierwsze 3 wiersze)
df = pd.read_csv(uploaded, header=3, sep=',')

# 2) Podgląd surowych danych
st.subheader("Podgląd pierwotnych danych (pierwsze 100 wierszy)")
st.dataframe(df.head(100))

# 3) Oczyść kolumnę gwarancji: zostaw tylko np. "6 miesięcy"
wcol = 'Informacje o gwarancjach (opcjonalne)'
if wcol in df.columns:
    df[wcol] = (
        df[wcol].astype(str)
               .str.replace(r'^Gwarancja\s*', '', regex=True)
               .str.replace(r'\s*\(.*\)', '', regex=True)
               .str.strip()
    )

# 4) Przetwarzanie "Opis oferty": JSON → HTML, usuń br i puste paragrafy
import json
import re

def clean_description(json_str):
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return ""
    html_parts = []
    for section in data.get('sections', []):
        for item in section.get('items', []):
            if item.get('type') == 'TEXT':
                content = item.get('content', '')
                # 1) Zamiana H1–H6 na H2
                content = re.sub(r'<h[1-6]>(.*?)</h[1-6]>',
                                 r'<h2>\1</h2>',
                                 content,
                                 flags=re.DOTALL)
                # 2) <ul> → usuń, <li> → <p>• …</p>
                content = re.sub(r'</?ul>', '', content)
                content = re.sub(r'<li>(.*?)</li>',
                                 r'<p>• \1</p>',
                                 content,
                                 flags=re.DOTALL)
                # 3) usuń wszystkie tagi inne niż <h2> i <p>
                content = re.sub(r'<(?!\/?(?:h2|p)\b)[^>]+>', '', content)
                html_parts.append(content.strip())
    # 4) połącz w jeden ciąg
    html = ''.join(html_parts)
    # 5) usuń puste paragrafy
    html = re.sub(r'<p>\s*(?:&nbsp;| )?\s*</p>', '', html)
    # 6) usuń entery i powroty karetki (zamień na spację, żeby nie skleić wyrazów)
    html = html.replace('\n', ' ').replace('\r', ' ')
    # 7) tylko teraz usuwamy spacje między tagami, np. '</p>   <h2>' → '</p><h2>'
    html = re.sub(r'>\s+<', '><', html)
    # (opcjonalnie) jeśli chcesz skompresować wielokrotne spacje w treści:
    #    html = re.sub(r' {2,}', ' ', html).strip()
    return html




if 'Opis oferty' in df.columns:
    df['Opis oferty'] = df['Opis oferty'].apply(clean_description)

# 5) Rozdziel 'Zdjęcia' na osobne kolumny URL
img_urls = pd.DataFrame(index=df.index)
if 'Zdjęcia' in df.columns:
    clean = df['Zdjęcia'].astype(str).str.replace(r',\s*', '|', regex=True)
    split_imgs = clean.str.split('|', expand=True)
    split_imgs.columns = [f"Zdjęcie_{i+1}" for i in range(split_imgs.shape[1])]
    img_urls = split_imgs

# 6) Zbuduj wynikowy DataFrame z mapowaniem
result = pd.DataFrame()
for orig_col, target_col in target_mapping.items():
    result[target_col] = df.get(orig_col, "")

# 7) Dodaj kolumny z obrazkami (jeśli są)
if not img_urls.empty:
    result = pd.concat([result, img_urls], axis=1)

# 8) Konwersja ID oferty na typ liczbowy (żeby Excel nie dodawał apostrofu)
if 'ID oferty' in result.columns:
    result['ID oferty'] = pd.to_numeric(result['ID oferty'], errors='coerce')

# 9) Wypełnij brakujące i skonwertuj wszystkie pozostałe kolumny na tekst
text_cols = result.columns.difference(['ID oferty'])
result[text_cols] = result[text_cols].fillna("").astype(str)

# 10) Podgląd wyników
st.subheader("Wynik mapowania (pierwsze 100 wierszy)")
st.dataframe(result.head(100))

# 11) Przygotuj plik do pobrania
buffer = io.BytesIO()
result.to_excel(buffer, index=False, engine='openpyxl')
buffer.seek(0)

st.download_button(
    label="Pobierz pełny plik Excel",
    data=buffer,
    file_name="mapped_output.xlsx",
    mime="application/vnd.openxmlformats-officedocument-spreadsheetml.sheet"
)
