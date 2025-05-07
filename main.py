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
    "Zdjęcia": "Zdjęcia",
    "Opis oferty": "Opis oferty",
    "Marka": "Marka",
    "Kod producenta": "Kod producenta",
}

# Desired output column order
output_cols = [
    "Nazwa produktu", "Kondycja|730|text", "Model|731|text",
    "Rodzaj|732|text", "Przeznaczenie|733|text", "Napięcie|734|text", "Pojemność|735|text",
    "Gwarancja|736|text", "Typ|737|text", "Moc|738|text", "Informacje dodatkowe|739|text",
    "W zestawie|740|text", "ID oferty", "Podkategoria", "Liczba sztuk",
    "Zdjęcia", "Opis oferty", "Marka", "Kod producenta"
]

st.title("CSV Column Mapper & Exporter")

uploaded = st.file_uploader("Wgraj plik CSV", type=["csv"])
if uploaded:
    # Skip first 3 rows, use 4th as header
    df = pd.read_csv(uploaded, header=3, sep=',')

    # Clean warranty column: keep only "6 miesięcy", "12 miesięcy" etc.
    wcol = 'Informacje o gwarancjach (opcjonalne)'
    if wcol in df.columns:
        df[wcol] = (
            df[wcol].astype(str)
                   .str.replace(r'^Gwarancja\s*', '', regex=True)
                   .str.replace(r'\s*\(.*\)', '', regex=True)
                   .str.strip()
        )

    # Normalize 'Zdjęcia' column: join any commas into '|'
    if 'Zdjęcia' in df.columns:
        df['Zdjęcia'] = (
            df['Zdjęcia'].astype(str)
                       .str.replace(r',\s*', '|', regex=True)
                       .str.strip()
        )

    # Build result DataFrame
    result = pd.DataFrame()
    for orig, target in target_mapping.items():
        result[target] = df.get(orig, "")

    # Reorder to match desired output_cols
    result = result.reindex(columns=output_cols)

    st.dataframe(result)

    # Export to Excel
    buffer = io.BytesIO()
    result.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    st.download_button(
        label="Pobierz wynikowy Excel",
        data=buffer,
        file_name="mapped_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# To run:
# 1. git init; git add main.py; git commit -m "Update mapping: remove Kod produktu, Reguła Cenowa; clean warranty; unify images"
# 2. pip install streamlit pandas openpyxl
# 3. streamlit run main.py
