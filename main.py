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

    # Normalize and split 'Zdjęcia' column into separate URL columns
    img_urls = pd.DataFrame()
    if 'Zdjęcia' in df.columns:
        # Replace commas with '|', split into multiple columns
        clean = df['Zdjęcia'].astype(str).str.replace(r',\s*', '|', regex=True)
        img_urls = clean.str.split('|', expand=True)
        img_urls = img_urls.rename(columns=lambda x: f"Zdjęcie_{x+1}")

    # Build result DataFrame with mapped columns
    result = pd.DataFrame()
    for orig, target in target_mapping.items():
        result[target] = df.get(orig, "")

    # Append image URL columns
    if not img_urls.empty:
        # Ensure same index alignment
        img_urls.index = result.index
        result = pd.concat([result, img_urls], axis=1)

    # Reorder: base mapped columns, then image columns
    base_cols = list(target_mapping.values())
    img_cols = list(img_urls.columns)
    result = result[ base_cols + img_cols ]

    # Show and export
    st.dataframe(result)
    
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
# 1. git add main.py; git commit -m "Split images into separate columns"
# 2. pip install streamlit pandas openpyxl
# 3. streamlit run main.py
