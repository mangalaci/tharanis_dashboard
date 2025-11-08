import streamlit as st
import pandas as pd

st.title("Száll_költség összesítő dashboard")

@st.cache_data
def load_data():
    # A Jupyterben legenerált merged.csv-t olvassa
    return pd.read_csv("merged.csv")

df = load_data()

# (Opcionális) kelt dátummá alakítása a szebb grafikonért
if "kelt" in df.columns:
    df["kelt"] = pd.to_datetime(df["kelt"], errors="coerce")

# Shop szűrő, ha van 'shop' oszlop
if "shop" in df.columns:
    shops = df["shop"].dropna().unique().tolist()
    shop_list = ["(összes)"] + sorted(shops)
    selected_shop = st.selectbox("Shop szűrő:", shop_list)

    if selected_shop != "(összes)":
        df_filtered = df[df["shop"] == selected_shop]
    else:
        df_filtered = df
else:
    st.warning("Nincs 'shop' oszlop, szűrés nélkül mutatom az adatokat.")
    df_filtered = df

# Ellenőrizzük, hogy van-e 'szall_kltsg' és 'kelt'
missing = [c for c in ["kelt", "szall_kltsg"] if c not in df_filtered.columns]
if missing:
    st.error(f"Hiányzó oszlop(ok) a merged.csv-ben: {missing}")
else:
    grouped = (
        df_filtered
        .groupby("kelt", as_index=False)[["szall_kltsg"]]
        .sum()
        .sort_values("kelt")
    )

    st.subheader("Napi összes szállítási költség (táblázat)")
    st.dataframe(grouped)

    st.subheader("Napi összes szállítási költség (vonaldiagram)")
    st.line_chart(grouped.set_index("kelt")[["szall_kltsg"]])
