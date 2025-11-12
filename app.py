import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="General Data Reporting", layout="wide")
st.title("General Data Reporting")

@st.cache_data
def load_data():
    # A projekt által előállított merged.csv-t olvassuk
    df = pd.read_csv("merged.csv")
    # dátumoszlopok normalizálása
    for dcol in ["kelt", "Adat feladás dátuma", "date"]:
        if dcol in df.columns:
            df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    return df

df = load_data()

# ---- Oszlopok feltérképezése (rugalmasan) ----
# Dátum (elsődlegesen 'kelt', ha nincs, akkor 'Adat feladás dátuma' vagy 'date')
DATE_COL = "kelt" if "kelt" in df.columns else ("Adat feladás dátuma" if "Adat feladás dátuma" in df.columns else ("date" if "date" in df.columns else None))

# Ország, Shop, Carrier
COUNTRY_COL = "Célország" if "Célország" in df.columns else None
SHOP_COL    = "shop"      if "shop" in df.columns      else None
CARRIER_COL = "Szállító"  if "Szállító" in df.columns  else None

# Árak/költségek
# Avg/Min/Max Price a GLS "Alap ár"-ból, ha nincs, próbáljuk 'shipping_price' oszlopból,
# végső fallback: None
if "Alap ár" in df.columns:
    PRICE_COL = "Alap ár"
elif "shipping_price" in df.columns:
    PRICE_COL = "shipping_price"
else:
    PRICE_COL = None

# Összes szállítási költség: ha van előkészített 'szall_kltsg', azt használjuk,
# különben megpróbáljuk a GLS díjtételek összegét kiszámolni.
COST_COL = None
if "szall_kltsg" in df.columns:
    COST_COL = "szall_kltsg"
else:
    fee_cols = [c for c in [
        "Alap ár","Utánvét","Biztosítás","Üzemanyag felár","Útdíj",
        "Kártyás fizetés","Depon kívüli fel.","Viszáru felár","Egyéb"
    ] if c in df.columns]
    if fee_cols:
        df["_calc_shipping_cost"] = df[fee_cols].sum(axis=1)
        COST_COL = "_calc_shipping_cost"

# ---- Szűrők (Countries, Shop, Carrier, Date Range) ----
filter_cols = st.container()
with filter_cols:
    c1, c2, c3 = st.columns(3)
    # Countries
    if COUNTRY_COL:
        countries = ["(all)"] + sorted(df[COUNTRY_COL].dropna().astype(str).unique().tolist())
        country_sel = c1.selectbox("County", countries)
    else:
        country_sel = c1.selectbox("Countries", ["(all)"])

    # Shop
    if SHOP_COL:
        shops = ["(all)"] + sorted(df[SHOP_COL].dropna().astype(str).unique().tolist())
        shop_sel = c2.selectbox("Shop", shops)
    else:
        shop_sel = c2.selectbox("Shop", ["(all)"])

    # Carrier
    if CARRIER_COL:
        carriers = ["(all)"] + sorted(df[CARRIER_COL].dropna().astype(str).unique().tolist())
        carrier_sel = c3.selectbox("Carrier", carriers)
    else:
        carrier_sel = c3.selectbox("Carrier", ["(all)"])

    # Date Range
    if DATE_COL:
        min_d = pd.to_datetime(df[DATE_COL], errors="coerce").min()
        max_d = pd.to_datetime(df[DATE_COL], errors="coerce").max()
        # alap: teljes idősáv
        start_d, end_d = st.date_input(
            "Date Range",
            value=(min_d.date() if pd.notnull(min_d) else date.today(),
                   max_d.date() if pd.notnull(max_d) else date.today())
        )
    else:
        st.info("Nincs dátum oszlop a fájlban (pl. 'kelt' vagy 'Adat feladás dátuma'). A szűrés dátum nélkül történik.")
        start_d = end_d = None

# ---- Szűrés alkalmazása ----
mask = pd.Series(True, index=df.index)

if COUNTRY_COL and country_sel != "(all)":
    mask &= df[COUNTRY_COL].astype(str) == str(country_sel)

if SHOP_COL and shop_sel != "(all)":
    mask &= df[SHOP_COL].astype(str) == str(shop_sel)

if CARRIER_COL and carrier_sel != "(all)":
    mask &= df[CARRIER_COL].astype(str) == str(carrier_sel)

if DATE_COL and start_d and end_d:
    mask &= (df[DATE_COL] >= pd.Timestamp(start_d)) & (df[DATE_COL] <= pd.Timestamp(end_d))

f = df[mask].copy()

# ---- Mutatók számítása ----
shipping_count = len(f)

def safe_num(series):
    if series is None:
        return None
    series = pd.to_numeric(series, errors="coerce")
    if series.notna().any():
        return series
    return None

avg_price = min_price = max_price = None
if PRICE_COL and PRICE_COL in f.columns:
    s = safe_num(f[PRICE_COL])
    if s is not None:
        avg_price = s.mean()
        min_price = s.min()
        max_price = s.max()

total_cost = None
if COST_COL and COST_COL in f.columns:
    s = safe_num(f[COST_COL])
    if s is not None:
        total_cost = s.sum()

# Revenue és Margin most még nincs – helyet hagyunk nekik
revenue = None
margin = None

# ---- Megjelenítés ----
st.subheader("Display Data")

display_df = pd.DataFrame([{
    "Shipping Count": shipping_count,
    "Avg. Price": avg_price,
    "Min Price": min_price,
    "Max Price": max_price,
    "Revenue": revenue,      # később kitöltjük, ha meglesz az adat
    "Margin": margin         # később kitöltjük, ha meglesz az adat
}])


# --- Megjelenítés (index eltüntetése, verziófüggetlen) ---
fmt = {
    "Shipping Count": "{:,.0f}",
    "Avg. Price": "{:,.2f}",
    "Min Price": "{:,.2f}",
    "Max Price": "{:,.2f}",
    "Revenue": "{:,.2f}",
    "Margin": "{:,.2f}",
}

df_show = display_df.copy()
df_show.index = [''] * len(df_show)  # <- üres indexcímkék, így nem látszik a "0"

st.table(df_show.style.format(fmt, na_rep="—"))
