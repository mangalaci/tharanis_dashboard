import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="General Data Reporting", layout="wide")
st.title("Általános adatszolgáltatás")

@st.cache_data
def load_data():
    df = pd.read_csv("merged.csv")
    # dátumoszlopok normalizálása
    for dcol in ["kelt", "Adat feladás dátuma", "date", "date_sent"]:
        if dcol in df.columns:
            df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    return df

df = load_data()

# ---- Oszlopnév-választó segédfüggvény ----
def pick_col(candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

# ---- Oszlopok feltérképezése (rugalmasan) ----
DATE_COL    = pick_col(["kelt", "date", "date_sent", "Adat feladás dátuma"])
COUNTRY_COL = pick_col(["Célország", "country"])
SHOP_COL    = pick_col(["shop", "Shop"])
CARRIER_COL = pick_col(["Carrier", "carrier"])

# Árak / költségek oszlop neve
PRICE_COL = pick_col(["Alap ár", "base_fee", "shipping_price"])

# Szállítási költség
COST_COL = None
if "szall_kltsg" in df.columns:
    COST_COL = "szall_kltsg"
else:
    fee_cols = [c for c in [
        "Alap ár","Utánvét","Biztosítás","Üzemanyag felár","Útdíj",
        "Kártyás fizetés","Depon kívüli fel.","Viszáru felár","Egyéb",
        "base_fee","cod_fee","insurance","fuel_surcharge","road_toll",
        "card_fee","depot_out","return_fee","other_fee","shipping_cost"
    ] if c in df.columns]
    if fee_cols:
        df["_calc_shipping_cost"] = df[fee_cols].sum(axis=1)
        COST_COL = "_calc_shipping_cost"

# ---- Szűrők ----
filter_cols = st.container()
with filter_cols:
    c1, c2, c3 = st.columns(3)

    # Country
    if COUNTRY_COL:
        countries = ["(all)"] + sorted(df[COUNTRY_COL].dropna().astype(str).unique().tolist())
        country_sel = c1.selectbox("Country", countries)
    else:
        country_sel = c1.selectbox("Country", ["(all)"])

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

    # Dátum intervallum
    if DATE_COL:
        min_d = pd.to_datetime(df[DATE_COL], errors="coerce").min()
        max_d = pd.to_datetime(df[DATE_COL], errors="coerce").max()

        col_from, col_to = st.columns(2)

        # alapértelmezett értékek
        default_from = min_d.date() if pd.notnull(min_d) else date.today()
        default_to   = max_d.date() if pd.notnull(max_d) else date.today()

        from_d = col_from.date_input("From", value=default_from)
        to_d   = col_to.date_input("To",   value=default_to)

        # ha véletlenül fordítva választja ki (From > To), akkor cseréljük
        if from_d > to_d:
            from_d, to_d = to_d, from_d
    else:
        st.info("Nincs dátum oszlop a fájlban (pl. 'kelt' vagy 'Adat feladás dátuma').")
        from_d = to_d = None


# ---- Szűrés alkalmazása ----
mask = pd.Series(True, index=df.index)
if COUNTRY_COL and country_sel != "(all)":
    mask &= df[COUNTRY_COL].astype(str) == str(country_sel)
if SHOP_COL and shop_sel != "(all)":
    mask &= df[SHOP_COL].astype(str) == str(shop_sel)
if CARRIER_COL and carrier_sel != "(all)":
    mask &= df[CARRIER_COL].astype(str) == str(carrier_sel)
if DATE_COL and from_d and to_d:
    mask &= (df[DATE_COL] >= pd.Timestamp(from_d)) & (df[DATE_COL] <= pd.Timestamp(to_d))

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

# Price mutatók
avg_price = min_price = max_price = None
if PRICE_COL and PRICE_COL in f.columns:
    s = safe_num(f[PRICE_COL])
    if s is not None:
        avg_price = s.mean()
        min_price = s.min()
        max_price = s.max()

# Összköltség (ha kellene később)
total_cost = None
if COST_COL and COST_COL in f.columns:
    s = safe_num(f[COST_COL])
    if s is not None:
        total_cost = s.sum()

# --- Revenue: netto vagy net_sales összege ---
revenue = None
REV_COL = pick_col(["netto", "net_sales"])
if REV_COL and REV_COL in f.columns:
    revenue_series = safe_num(f[REV_COL])
    if revenue_series is not None:
        revenue = revenue_series.sum()

# --- Margin: nyereseg_nyilv_ar vagy margin oszlopok összege ---
margin = None
MARG_COL = pick_col(["nyereseg_nyilv_ar", "margin_amount", "margin"])
if MARG_COL and MARG_COL in f.columns:
    margin_series = safe_num(f[MARG_COL])
    if margin_series is not None:
        margin = margin_series.sum()

# ---- Megjelenítés ----
st.subheader("Data Summary")

display_df = pd.DataFrame([{
    "Shipping Count": shipping_count,
    "Avg. Price (Alap ár)": avg_price,
    "Min Price (Alap ár)": min_price,
    "Max Price (Alap ár)": max_price,
    "Revenue": revenue,
    "Margin": margin
}])

# --- Formázás ---
fmt = {
    "Shipping Count": "{:,.0f}",
    "Avg. Price (Alap ár)": "{:,.2f}",
    "Min Price (Alap ár)": "{:,.2f}",
    "Max Price (Alap ár)": "{:,.2f}",
    "Revenue": "{:,.0f}",
    "Margin": "{:,.2f}",
}

df_show = display_df.copy()
df_show.index = [''] * len(df_show)
st.table(df_show.style.format(fmt, na_rep="—"))

# --- Export gomb: Data Summary -> Excel ---
from io import BytesIO

# ...
excel_buffer = BytesIO()
# NINCS xlsxwriter, inkább openpyxl-t kérünk, ami már telepítve van
with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
    f.to_excel(writer, index=False, sheet_name="Data")

excel_buffer.seek(0)

st.download_button(
    label="Export Data Summary to Excel",
    data=excel_buffer,
    file_name="data_summary.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
