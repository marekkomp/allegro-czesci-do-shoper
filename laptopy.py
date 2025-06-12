import streamlit as st
import pandas as pd
import io
import json
import re

# Mapping from original CSV columns to desired output columns
target_mapping = {
    "Cena PL": "price",
    "Cod producenta": "Kod producenta",
    "ID oferty": "ID oferty",
    "Informacje dodatkowe": "Informacje dodatkowe|739|text",
    "Informacje o gwarancjach (opcjonalne)": "Gwarancja|736|text",
    "Kod producenta": "Kod producenta",
    "Liczba rdzeni procesora": "Liczba rdzeni procesora",
    "Liczba sztuk": "Liczba sztuk",
    "Marka": "Marka",
    "Model": "Model|731|text",
    "Moc [W]": "Moc|738|text",
    "Moc zasilacza [W]": "Moc|738|text",
    "Napięcie [V]": "Napięcie|734|text",
    "Opis oferty": "Opis oferty",
    "Pojemność dysku [GB]": "Pojemność dysku",
    "Podkategoria": "Podkategoria",
    "Przeznaczenie": "Przeznaczenie|733|text",
    "Przekątna ekranu [\"]": "Przekątna ekranu [\"]",
    "Producent": "Producent",
    "Rodzaj": "Rodzaj|732|text",
    "Rodzaj karty graficznej": "Rodzaj karty graficznej",
    "Seria": "Seria",
    "Seria procesora": "Seria procesora",
    "Stan": "Kondycja|730|text",
    "System operacyjny": "System operacyjny",
    "Taktowanie bazowe procesora [GHz]": "Taktowanie bazowe procesora [GHz]",
    "Tytuł oferty": "Nazwa produktu",
    "Typ": "Typ|737|text",
    "Typ dysku twardego": "Typ dysku twardego",
    "Typ pamięci RAM": "Typ pamięci RAM",
    "Wielkość pamięci RAM": "Wielkość pamięci RAM",
    "Zdjęcia": "Zdjęcia",
    "Załączone wyposażenie": "W zestawie|740|text",
    "Rozdzielczość (px)": "Rozdzielczość (px)",
}


st.title("CSV Column Mapper & Exporter")

uploaded = st.file_uploader("Wgraj plik CSV", type=["csv"])
if not uploaded:
    st.info("Proszę wgrać plik CSV (pierwsze 3 wiersze pomijane, 4. wiersz jako nagłówek)")
    st.stop()

# 1) Wczytanie CSV (pomijamy pierwsze 3 wiersze)
df = pd.read_csv(uploaded, header=3, sep=',')
# 1.a) Ujednolicenie nagłówków: usuń leading/trailing spacje
df.columns = df.columns.str.strip()

# 1.b) Debug: podejrzyj wszystkie kolumny
st.write("🔍 Kolumny w wczytanym df:", df.columns.tolist())

# 1.c) Debug: co ma 'dysku' w nazwie?
st.write("🔍 Kolumny zawierające 'dysku':", 
         [col for col in df.columns if 'dysku' in col.lower()])

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
            if item.get('type') != 'TEXT':
                continue

            content = item.get('content', '').strip()

            # Rozbij po tagach otwierających, np. <h2>, <p>, <ul>...
            lines = re.split(r'(?=<h[1-6]>|<p>|<ul>)', content)

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # ❌ Pomiń separator — usuń całkowicie <h1>__________</h1>
                line = re.sub(r'<h[1-6]>_+</h[1-6]>', '', line).strip()
                if not line:
                    continue

                # Zamień pozostałe nagłówki H1–H6 na H2
                line = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<h2>\1</h2>', line, flags=re.DOTALL)

                # Zostaw gotowe <ul>, <li>, <h2>, <p>
                if re.match(r'^\s*<(ul|li|h2|p)\b', line):
                    html_parts.append(line)
                else:
                    # Usuń inne tagi i opakuj w <p>
                    text = re.sub(r'<[^>]+>', '', line).strip()
                    if text:
                        html_parts.append(f'<p>{text}</p>')

    html = ''.join(html_parts)
    html = re.sub(r'<p>\s*(?:&nbsp;|\s)*</p>', '', html)
    html = re.sub(r'>\s+<', '><', html)

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
missing = []
for orig_col, target_col in target_mapping.items():
    if orig_col in df.columns:
        result[target_col] = df[orig_col]
    else:
        missing.append(orig_col)
        # i mimo braku, twórz pustą kolumnę, żeby struktura była spójna
        result[target_col] = ""
# pokaż, co nie zostało znalezione
st.write("⚠️ Nie znaleziono w pliku kolumn (mapowane jako puste):", missing)

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
