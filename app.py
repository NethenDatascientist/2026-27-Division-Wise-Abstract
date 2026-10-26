import re
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st

# ==========================================
# PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="Minor Irrigation Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clean, Professional Light Theme
st.markdown(
    """
    <style>
    .dashboard-header {
        background: linear-gradient(135deg, #047857 0%, #064E3B 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .dashboard-header h1 {
        margin: 0;
        font-size: 1.75rem;
        font-weight: 600;
        color: white;
        letter-spacing: -0.025em;
    }
    .badge-all {
        background-color: #F1F5F9;
        color: #334155;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.875rem;
        border: 1px solid #CBD5E1;
    }
    .badge-overdue {
        background-color: #FEF2F2;
        color: #DC2626;
        padding: 0.5rem 1rem;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 0.875rem;
        border: 1px solid #FECACA;
    }
    div[data-testid="stMetric"] {
        background-color: white;
        border-left: 4px solid #10B981;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #0F172A;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.875rem !important;
        color: #64748B;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# CONSTANTS & CONFIGURATIONS
# ==========================================
SHEET_CONFIG = {
    "4702_MOT": {"start_row": 4, "cols": list(range(28)) + [32, 33]},
    "4702-New Tanks": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "4702_A&P": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "4702-LIS": {"start_row": 1, "cols": list(range(28)) + [32, 33]},
    "4702_Paschima Vahini": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "4711__Other Flood Control": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "4702-Kharland": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "NABARD - A&P": {"start_row": 4, "cols": list(range(28)) + [32, 33]},
    "TSP (LIS)": {"start_row": 2, "cols": list(range(28)) + [33, 34]},
    "SCP (Checkdam)": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "SCP (LIS)": {"start_row": 2, "cols": list(range(28)) + [34, 35]},
    "TSP (Borewell)": {"start_row": 2, "cols": list(range(28)) + [38, 39]},
    "SCP (Borewell)": {"start_row": 4, "cols": list(range(27)) + [29, 38, 39]},
    "TSP (Checkdam)": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "NABARD - Other Flood Control": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "NABARD - LIS": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "NABARD_MOT": {"start_row": 4, "cols": list(range(28)) + [32, 33]},
    "PMKSY-SMI-RRR": {"start_row": 2, "cols": list(range(28)) + [32, 33]},
    "KMERC": {"start_row": 4, "cols": list(range(28)) + [32, 33]},
}

STATUS_LIST = ["CP", "CF", "P", "TBS", "TP", "ETS", "OTH", "CBW", "CEF", "PBW", "CBWPM", "RRR", "BWF"]
COST_BUCKETS = ["Less than 100", "0 - 200", "100 - 500", "200 - 500", "500 - 1000", "1000 - 2500", "2500 - 5000", "5000 - 10000", "More than 10000"]

REQUIRED_SCHEMES = [
    "SCP- CHECKDAM", "SCP-BOREWELL", "SCP-LIS", 
    "TSP-BOREWELL", "TSP-CHECKDAM", "TSP-LIS"
]

HEADERS_KN = [
    "ಕ್ರ.ಸಂ", "ವಲಯ / ವಿಭಾಗ", "ಲೆಕ್ಕಶೀರ್ಷಿಕೆ", "ಮುಂದುವರೆದ ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ", "ಅಂದಾಜು ಮೊತ್ತ (S)",
    "ಹೊಸ ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ", "ಅಂದಾಜು ಮೊತ್ತ (F)", "ಒಟ್ಟು ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ", "ಒಟ್ಟು ಅಂದಾಜು ಮೊತ್ತ",
    "ಗುತ್ತಿಗೆ ಮೊತ್ತ (ಜಿ.ಎಸ್.ಟಿ ಸೇರಿದಂತೆ)", "ಪರಿಷ್ಕೃತ ಅಂದಾಜು ಮೊತ್ತ", "26-27ನೇ ಸಾಲಿನ ಹಂಚಿಕೆ",
    "ಮಾರ್ಚ್ 2026 ವರೆಗಿನ ವೆಚ್ಚ", "2026-27ನೇ ಸಾಲಿನ ವೆಚ್ಚ", "ಒಟ್ಟಾರೆ ವೆಚ್ಚ", "ಬಾಕಿ ಬಿಲ್ಲಿನ ಮೊತ್ತ",
    "ಬಾಕಿ ಮೊತ್ತ", "CP", "CF", "P", "TBS", "TP", "ETS", "OTH", "CBW", "CEF", "PBW", "CBWPM",
    "RRR", "BWF", "Overdue %", "% of (TBS, OTH, TP, ETS)"
]

def get_regex(v_scheme: str) -> str:
    s = str(v_scheme).strip()
    if s in ("-", ""): return "NO_MATCH"
    if s.startswith("SCP"): return "ವಿಶೇಷ ಘಟಕ ಯೋಜನೆ"
    if s.startswith("TSP"): return "ಗಿರಿಜನ ಉಪಯೋಜನೆ"
    mapping = {
        "KMERC": r"ಕೆ\.ಎಂ\.ಇ\.ಆರ್", "PMKSY": "PMKSY", "FMP": "FPW", "KHARLAND": "KHARLAND",
        "NT": r"\-NT\s*$", "MOT": r"\-\s*MOT\s*$", "NMOT": r"NMOT\s*$", "APB": r"\-APB\s*$",
        "NAPB": r"NAPB\s*$", "LIS": r"\-\s*LIS\s*$", "NLIS": r"NLIS\s*$", "PV": r"\-\s*PV\s*$",
    }
    return mapping.get(s, re.escape(s))

# ==========================================
# DATA PROCESSING
# ==========================================
@st.cache_data(show_spinner="Processing Dataset...")
def load_workbook_data(file_source) -> tuple[pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(file_source)
    frames = []

    for sheet_name, cfg in SHEET_CONFIG.items():
        if sheet_name not in xls.sheet_names: continue
        df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, skiprows=cfg["start_row"] - 1)
        max_col = max(cfg["cols"])
        if df_raw.shape[1] <= max_col:
            for c in range(df_raw.shape[1], max_col + 1): df_raw[c] = np.nan
        sub = df_raw.iloc[:, cfg["cols"]].copy()
        sub.columns = [f"Col{i}" for i in range(1, 31)]
        frames.append(sub)

    if not frames: return pd.DataFrame(), pd.DataFrame()
    dataset = pd.concat(frames, ignore_index=True)

    str_cols = ["Col2", "Col3", "Col4", "Col5", "Col6", "Col8", "Col28", "Col29", "Col30"]
    for c in str_cols: dataset[c] = dataset[c].fillna("").astype(str).str.strip()

    invalid_divs = {"", "ವಿಭಾಗದ ಹೆಸರು", "ವಿಭಾಗ", "2", "F", "S", "nan", "None"}
    dataset = dataset[~dataset["Col2"].isin(invalid_divs)].copy()

    # Robust Numeric Conversion
    num_cols = ["Col9", "Col15", "Col17", "Col23", "Col24", "Col25", "Col26", "Col27"]
    for c in num_cols: dataset[c] = pd.to_numeric(dataset[c], errors="coerce").fillna(0.0)

    for c in ["Col12", "Col19", "Col21", "Col22"]:
        dataset[c + "_dt"] = pd.to_datetime(dataset[c], dayfirst=True, errors="coerce")

    today_ts = pd.Timestamp(date.today())
    actual_empty = dataset["Col22"].fillna("").astype(str).str.strip().eq("") & dataset["Col22_dt"].isna()
    dataset["Col32"] = np.where(actual_empty & dataset["Col21_dt"].notna() & dataset["Col28"].str.upper().eq("P") & (dataset["Col21_dt"] > today_ts), 1, 0)

    if "Division_wise ABSTRACT" in xls.sheet_names:
        abs_raw = pd.read_excel(xls, sheet_name="Division_wise ABSTRACT", header=None, skiprows=1)
        abs_df = pd.DataFrame({
            "abs_div": abs_raw.iloc[:, 1].fillna("").astype(str).str.strip(),
            "abs_scheme": abs_raw.iloc[:, 2].fillna("").astype(str).str.strip(),
            "abs_alloc": pd.to_numeric(abs_raw.iloc[:, 11], errors="coerce").fillna(0.0),
        })
    else:
        abs_df = pd.DataFrame(columns=["abs_div", "abs_scheme", "abs_alloc"])

    return dataset, abs_df

def generate_demo_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(42)
    divs = ["ಬೆಂಗಳೂರು ವಿಭಾಗ", "ಮೈಸೂರು ವಿಭಾಗ", "ಮಂಡ್ಯ ವಿಭಾಗ"]
    schemes = ["MOT", "NT"] + REQUIRED_SCHEMES + ["PMKSY"]
    
    n = 300
    df = pd.DataFrame({f"Col{i}": "" for i in range(1, 31)}, index=range(n))
    div_idx = rng.integers(0, len(divs), n)
    
    df["Col2"] = [divs[i] for i in div_idx]
    df["Col6"] = rng.choice(schemes, n)
    df["Col8"] = rng.choice(["S", "F"], n, p=[0.6, 0.4])
    df["Col9"] = np.round(rng.uniform(50, 8000, n), 2)
    df["Col25"] = np.round(df["Col9"] * rng.uniform(0.3, 0.6, n), 2)
    df["Col27"] = np.round(df["Col9"] - df["Col25"], 2)
    df["Col28"] = rng.choice(STATUS_LIST, n)
    df["Col21_dt"] = pd.to_datetime(rng.choice(pd.date_range("2023-01-01", "2027-12-31"), n))
    df["Col22_dt"] = pd.Series([pd.NaT if s == "P" else pd.Timestamp("2025-10-01") for s in df["Col28"]])
    df["Col32"] = np.where(df["Col22_dt"].isna() & (df["Col28"] == "P") & (df["Col21_dt"] > pd.Timestamp(date.today())), 1, 0)

    # Initialize remaining numerical columns safely
    for col in ["Col15", "Col17", "Col23", "Col24", "Col26"]:
        df[col] = 0.0

    abs_rows = [{"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": s, "abs_alloc": 2000.0} for s in ["-MOT", "-NT", "ವಿಶೇಷ ಘಟಕ ಯೋಜನೆ", "ಗಿರಿಜನ ಉಪಯೋಜನೆ"]]
    return df, pd.DataFrame(abs_rows)

# ==========================================
# AGGREGATION ENGINE (ERROR-PROOFED)
# ==========================================
def calc_allocation(abs_df: pd.DataFrame, div_name: str, regex_pattern: str) -> float:
    if abs_df.empty or regex_pattern == "NO_MATCH": return 0.0
    sub = abs_df[abs_df["abs_div"] == div_name]
    if sub.empty: return 0.0
    matched = sub["abs_scheme"].str.contains(regex_pattern, case=False, regex=True, na=False)
    return float(sub.loc[matched, "abs_alloc"].sum())

def compute_row_metrics(df_slice: pd.DataFrame, overdue_only: bool, col1_label: str, col2_label: str, alloc_display) -> list:
    sf = df_slice["Col8"].str.upper()
    is_overdue = df_slice["Col32"]
    
    true_tot = int((sf == "S").sum() + (sf == "F").sum())
    pct_overdue = "0.00%" if true_tot == 0 else f"{(int(is_overdue.sum()) / true_tot) * 100:.2f}%"
    pct_special = "0.00%" if true_tot == 0 else f"{(int(df_slice['Col28'].str.upper().isin(['TBS', 'OTH', 'TP', 'ETS']).sum()) / true_tot) * 100:.2f}%"

    active_df = df_slice[df_slice["Col32"] == 1] if overdue_only else df_slice
    a_sf = active_df["Col8"].str.upper()
    
    def safe_sum(series):
        return round(pd.to_numeric(series, errors='coerce').fillna(0).sum(), 2)

    cS = int((a_sf == "S").sum())
    sS = safe_sum(active_df.loc[a_sf == "S", "Col9"])
    cF = int((a_sf == "F").sum())
    sF = safe_sum(active_df.loc[a_sf == "F", "Col9"])
    st_counts = [int((active_df["Col28"].str.upper() == s).sum()) for s in STATUS_LIST]

    # Exactly 31 elements returned
    return [
        col1_label, col2_label, cS, sS, cF, sF, cS + cF, round(sS + sF, 2),
        safe_sum(active_df["Col15"]), safe_sum(active_df["Col17"]), alloc_display,
        safe_sum(active_df["Col23"]), safe_sum(active_df["Col24"]),
        safe_sum(active_df["Col25"]), safe_sum(active_df["Col26"]),
        safe_sum(active_df["Col27"]), *st_counts, pct_overdue, pct_special
    ]

def build_table(base_df: pd.DataFrame, abs_df: pd.DataFrame, overdue_only: bool) -> pd.DataFrame:
    if base_df.empty: return pd.DataFrame(columns=HEADERS_KN)
    records = []
    
    unique_schemes = sorted([s for s in base_df["Col6"].unique() if s])
    unique_divs = sorted([d for d in base_df["Col2"].unique() if d])

    for v_scheme in unique_schemes:
        s_alloc = round(calc_allocation(abs_df, "ದಕ್ಷಿಣ ವಲಯ", get_regex(v_scheme)), 2)
        disp = f"{s_alloc} (Comb. SCP)" if v_scheme.startswith("SCP") else f"{s_alloc} (Comb. TSP)" if v_scheme.startswith("TSP") else s_alloc
        records.append((1, "Zone", 1, v_scheme, compute_row_metrics(base_df[base_df["Col6"] == v_scheme], overdue_only, "ದಕ್ಷಿಣ ವಲಯ", v_scheme, disp)))

    active_rgx = sorted({get_regex(s) for s in unique_schemes})
    tot_alloc = round(sum(calc_allocation(abs_df, "ದಕ್ಷಿಣ ವಲಯ", r) for r in active_rgx), 2)
    records.append((1, "Zone", 2, "ZZZ", compute_row_metrics(base_df, overdue_only, "", "👉 ದಕ್ಷಿಣ ವಲಯ ಒಟ್ಟು", tot_alloc)))
    
    # FIX: Ensure spacer values align perfectly to 31 elements (1 string + 30 blanks)
    records.append((2, "Spacer", 2, "AAA", ["ವಿಭಾಗವಾರು"] + [""] * 30))

    for v_div in unique_divs:
        div_df = base_df[base_df["Col2"] == v_div]
        div_schemes = sorted([s for s in div_df["Col6"].unique() if s])
        for v_scheme in div_schemes:
            s_alloc = round(calc_allocation(abs_df, v_div, get_regex(v_scheme)), 2)
            disp = f"{s_alloc} (Comb. SCP)" if v_scheme.startswith("SCP") else f"{s_alloc} (Comb. TSP)" if v_scheme.startswith("TSP") else s_alloc
            records.append((3, v_div, 1, v_scheme, compute_row_metrics(div_df[div_df["Col6"] == v_scheme], overdue_only, v_div, v_scheme, disp)))
        
        div_rgx = sorted({get_regex(s) for s in div_schemes})
        div_tot_alloc = round(sum(calc_allocation(abs_df, v_div, r) for r in div_rgx), 2)
        records.append((3, v_div, 2, "ZZZ", compute_row_metrics(div_df, overdue_only, "", f"👉 {v_div} ಒಟ್ಟು", div_tot_alloc)))

    valid = [r for r in records if r[0] == 2 or (isinstance(r[4][6], (int, float)) and r[4][6] > 0)]
    valid.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    
    final_rows = []
    acc = 0; prev_grp = None
    for tier, grp, r_type, _, vals in valid:
        if r_type == 1:
            acc = 1 if grp != prev_grp else acc + 1
            final_rows.append([str(acc)] + vals)
        else:
            final_rows.append([""] + vals)
        prev_grp = grp
        
    return pd.DataFrame(final_rows, columns=HEADERS_KN)

# ==========================================
# SIDEBAR UI & PRIMARY FILTERS
# ==========================================
st.sidebar.markdown("### 📂 Data Pipeline")
uploaded_file = st.sidebar.file_uploader("Upload Master Excel (.xlsx)", type=["xlsx", "xls"])
dataset, abs_df = load_workbook_data(uploaded_file) if uploaded_file else generate_demo_data()
if not uploaded_file: st.sidebar.info("Currently viewing generated Demo Data.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Primary Filters")

all_divs = sorted([x for x in dataset["Col2"].unique() if x])
all_sf = sorted([x for x in dataset["Col8"].unique() if x])
all_status = sorted([x for x in dataset["Col28"].unique() if x])
dataset_schemes = [x for x in dataset["Col6"].unique() if x]
combined_schemes = sorted(list(set(dataset_schemes + REQUIRED_SCHEMES)))

if "overdue_mode" not in st.session_state: st.session_state.overdue_mode = False
def reset_filters():
    for k in ["f_div", "f_scheme", "f_sf", "f_status", "f_dist", "f_taluk", "f_const", "f_cost", "f_ae", "f_aee"]:
        st.session_state[k] = []
    st.session_state.overdue_mode = False

f_div = st.sidebar.multiselect("ವಲಯ / ವಿಭಾಗ (Division)", all_divs, key="f_div")
f_scheme = st.sidebar.multiselect("ಲೆಕ್ಕಶೀರ್ಷಿಕೆ (Scheme)", combined_schemes, key="f_scheme")
f_sf = st.sidebar.multiselect("S/F (Spillover/Fresh)", all_sf, key="f_sf")
f_status = st.sidebar.multiselect("PROGRESS STATUS", all_status, key="f_status")

st.sidebar.markdown("---")
st.session_state.overdue_mode = st.sidebar.toggle("⚠️ Show Overdue Works Only", value=st.session_state.overdue_mode)
st.sidebar.button("🔄 Clear All Filters", on_click=reset_filters, use_container_width=True)

# ==========================================
# MAIN DASHBOARD AREA
# ==========================================
mode_lbl = "OVERDUE WORKS" if st.session_state.overdue_mode else "ALL WORKS"
badge_class = "badge-overdue" if st.session_state.overdue_mode else "badge-all"

st.markdown(
    f"""
    <div class="dashboard-header">
        <div>
            <h1>💧 Minor Irrigation Dashboard</h1>
            <span style="color: #E2E8F0; font-size: 0.95rem;">South Zone Data Engine | Abstract Reporting</span>
        </div>
        <div><span class="{badge_class}">SHOWING: {mode_lbl}</span></div>
    </div>
    """, unsafe_allow_html=True
)

with st.expander("📍 Location, Cost & Advanced Attributes"):
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_dist = st.multiselect("ಜಿಲ್ಲೆ (District)", sorted([x for x in dataset["Col3"].unique() if x]), key="f_dist")
    with c2: f_taluk = st.multiselect("ತಾಲ್ಲೂಕು (Taluk)", sorted([x for x in dataset["Col4"].unique() if x]), key="f_taluk")
    with c3: f_const = st.multiselect("ಮತಕ್ಷೇತ್ರ (Constituency)", sorted([x for x in dataset["Col5"].unique() if x]), key="f_const")
    with c4: f_cost = st.multiselect("ಮೂಲ ಅಂದಾಜು ಮೊತ್ತ (Cost)", COST_BUCKETS, key="f_cost")
    
    c5, c6, c7, c8 = st.columns(4)
    with c5: f_ae = st.multiselect("A.E.", sorted([x for x in dataset["Col29"].unique() if x]), key="f_ae")
    with c6: f_aee = st.multiselect("A.E.E.", sorted([x for x in dataset["Col30"].unique() if x]), key="f_aee")
    with c7: st.caption("*(Date/Aging filters omitted for brevity, can be expanded similarly)*")

# Filter logic
mask = pd.Series(True, index=dataset.index)
if f_div: mask &= dataset["Col2"].isin(f_div)
if f_scheme: mask &= dataset["Col6"].isin(f_scheme)
if f_sf: mask &= dataset["Col8"].isin(f_sf)
if f_status: mask &= dataset["Col28"].isin(f_status)
if f_dist: mask &= dataset["Col3"].isin(f_dist)
if f_taluk: mask &= dataset["Col4"].isin(f_taluk)
if f_const: mask &= dataset["Col5"].isin(f_const)
if f_ae: mask &= dataset["Col29"].isin(f_ae)
if f_aee: mask &= dataset["Col30"].isin(f_aee)
if f_cost:
    c9 = dataset["Col9"]
    cost_mask = pd.Series(False, index=dataset.index)
    for b in f_cost:
        if b == "More than 10000": cost_mask |= c9 > 10000
        elif b == "5000 - 10000": cost_mask |= (c9 >= 5000) & (c9 <= 10000)
        elif b == "2500 - 5000": cost_mask |= (c9 >= 2500) & (c9 <= 5000)
        elif b == "1000 - 2500": cost_mask |= (c9 >= 1000) & (c9 <= 2500)
        elif b == "500 - 1000": cost_mask |= (c9 >= 500) & (c9 <= 1000)
        elif b == "200 - 500": cost_mask |= (c9 >= 200) & (c9 <= 500)
        elif b == "0 - 200": cost_mask |= (c9 >= 0) & (c9 <= 200)
        elif b == "100 - 500": cost_mask |= (c9 >= 100) & (c9 <= 500)
        elif b == "Less than 100": cost_mask |= c9 < 100
    mask &= cost_mask

filtered_base = dataset[mask].copy()

kpi_df = filtered_base[filtered_base["Col32"] == 1] if st.session_state.overdue_mode else filtered_base
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("ಒಟ್ಟು ಕಾಮಗಾರಿಗಳು (Total Works)", f"{len(kpi_df):,}")
m2.metric("ಒಟ್ಟು ಅಂದಾಜು ಮೊತ್ತ (Est. Cost)", f"₹ {kpi_df['Col9'].sum():,.2f} L")
m3.metric("ಒಟ್ಟಾರೆ ವೆಚ್ಚ (Cum. Exp)", f"₹ {kpi_df['Col25'].sum():,.2f} L")
m4.metric("ಬಾಕಿ ಮೊತ್ತ (Balance Need)", f"₹ {kpi_df['Col27'].sum():,.2f} L")
m5.metric("Overdue Works (Active)", f"{int(filtered_base['Col32'].sum()):,}")

st.markdown("<br>", unsafe_allow_html=True)

# Light Mode Table Highlighting
def highlight_rows(row):
    label = str(row["ಲೆಕ್ಕಶೀರ್ಷಿಕೆ"])
    div_label = str(row["ವಲಯ / ವಿಭಾಗ"])
    
    if div_label == "ವಿಭಾಗವಾರು":
        return ["background-color: #334155; color: white; font-weight: bold; font-size: 1.05em;"] * len(row)
    if "👉" in label and "ದಕ್ಷಿಣ ವಲಯ" in label:
        return ["background-color: #047857; color: white; font-weight: bold;"] * len(row)
    if "👉" in label:
        return ["background-color: #E2E8F0; color: #0F172A; font-weight: bold;"] * len(row)
        
    return [""] * len(row)

result_df = build_table(filtered_base, abs_df, st.session_state.overdue_mode)

st.dataframe(
    result_df.style.apply(highlight_rows, axis=1),
    use_container_width=True,
    height=650,
    hide_index=True
)
