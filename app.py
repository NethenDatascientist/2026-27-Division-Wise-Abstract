import re
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st

# ==========================================
# PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="Minor Irrigation (South Zone) Dashboard",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Header Banner matching the Google Sheet Navy Blue UI */
    .main-banner {
        background: linear-gradient(90deg, #003f7f 0%, #0059b3 100%);
        color: white;
        padding: 14px 20px;
        border-radius: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .main-banner h2 {
        margin: 0;
        font-size: 1.35rem;
        color: white;
    }
    .status-badge-all {
        background-color: #fff3cd;
        color: #990000;
        padding: 6px 16px;
        border-radius: 6px;
        font-weight: 800;
        border: 1px solid #ffecb5;
    }
    .status-badge-overdue {
        background-color: #f8d7da;
        color: #842029;
        padding: 6px 16px;
        border-radius: 6px;
        font-weight: 800;
        border: 1px solid #f5c2c7;
    }
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 10px 14px;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# SHEET EXTRACTION CONFIGURATION
# ==========================================
# Maps each of the 19 sheets to its starting row (1-based) and 0-based column indices
# A:AB is indices 0..27. Extra AE/AEE columns are mapped per sheet.
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

STATUS_LIST = [
    "CP", "CF", "P", "TBS", "TP", "ETS", "OTH",
    "CBW", "CEF", "PBW", "CBWPM", "RRR", "BWF",
]

COST_BUCKETS = [
    "Less than 100",
    "0 - 200",
    "100 - 500",
    "200 - 500",
    "500 - 1000",
    "1000 - 2500",
    "2500 - 5000",
    "5000 - 10000",
    "More than 10000",
]

OVERDUE_BUCKETS = [
    "<2 years",
    "2-5 years",
    "5-10 years",
    "More than 10 years",
]

HEADERS_KN = [
    "ಕ್ರ.ಸಂ",
    "ವಲಯ / ವಿಭಾಗ",
    "ಲೆಕ್ಕಶೀರ್ಷಿಕೆ",
    "ಮುಂದುವರೆದ ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ",
    "ಅಂದಾಜು ಮೊತ್ತ (S)",
    "ಹೊಸ ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ",
    "ಅಂದಾಜು ಮೊತ್ತ (F)",
    "ಒಟ್ಟು ಕಾಮಗಾರಿಗಳ ಸಂಖ್ಯೆ",
    "ಒಟ್ಟು ಅಂದಾಜು ಮೊತ್ತ",
    "ಗುತ್ತಿಗೆ ಮೊತ್ತ (ಜಿ.ಎಸ್.ಟಿ ಸೇರಿದಂತೆ)",
    "ಪರಿಷ್ಕೃತ ಅಂದಾಜು ಮೊತ್ತ (ಜಿ.ಎಸ್.ಟಿ ಸೇರಿದಂತೆ)",
    "2026-27ನೇ ಸಾಲಿಗೆ ಹಂಚಿಕೆಯಾದ ಅನುದಾನ",
    "ಮಾರ್ಚ್ 2026 ವರೆಗಿನ ವೆಚ್ಚ",
    "2026-27ನೇ ಸಾಲಿನ ವೆಚ್ಚ",
    "ಒಟ್ಟಾರೆ ವೆಚ್ಚ",
    "ಬಾಕಿ ಬಿಲ್ಲಿನ ಮೊತ್ತ",
    "ಕಾಮಗಾರಿಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲು ಬೇಕಾಗುವ ಬಾಕಿ ಮೊತ್ತ",
    "CP", "CF", "P", "TBS", "TP", "ETS", "OTH",
    "CBW", "CEF", "PBW", "CBWPM", "RRR", "BWF",
    "Overdue %",
    "% of (TBS, OTH, TP, ETS)",
]


# ==========================================
# REGEX MAPPER FOR GRANT ALLOCATION
# ==========================================
def get_regex(v_scheme: str) -> str:
    s = str(v_scheme).strip()
    if s in ("-", ""):
        return "NO_MATCH"
    if s.startswith("SCP"):
        return "ವಿಶೇಷ ಘಟಕ ಯೋಜನೆ"
    if s.startswith("TSP"):
        return "ಗಿರಿಜನ ಉಪಯೋಜನೆ"
    mapping = {
        "KMERC": r"ಕೆ\.ಎಂ\.ಇ\.ಆರ್",
        "PMKSY": "PMKSY",
        "FMP": "FPW",
        "KHARLAND": "KHARLAND",
        "NT": r"\-NT\s*$",
        "MOT": r"\-\s*MOT\s*$",
        "NMOT": r"NMOT\s*$",
        "APB": r"\-APB\s*$",
        "NAPB": r"NAPB\s*$",
        "LIS": r"\-\s*LIS\s*$",
        "NLIS": r"NLIS\s*$",
        "PV": r"\-\s*PV\s*$",
    }
    return mapping.get(s, re.escape(s))


# ==========================================
# DATA LOADING & PREPROCESSING
# ==========================================
@st.cache_data(show_spinner="Consolidating 19 scheme sheets & Abstract...")
def load_workbook_data(file_source) -> tuple[pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(file_source)
    frames = []

    for sheet_name, cfg in SHEET_CONFIG.items():
        if sheet_name not in xls.sheet_names:
            continue
        df_raw = pd.read_excel(
            xls,
            sheet_name=sheet_name,
            header=None,
            skiprows=cfg["start_row"] - 1,
        )
        max_col = max(cfg["cols"])
        if df_raw.shape[1] <= max_col:
            for c in range(df_raw.shape[1], max_col + 1):
                df_raw[c] = np.nan

        sub = df_raw.iloc[:, cfg["cols"]].copy()
        sub.columns = [f"Col{i}" for i in range(1, 31)]
        frames.append(sub)

    if not frames:
        return pd.DataFrame(), pd.DataFrame()

    dataset = pd.concat(frames, ignore_index=True)

    # Clean string columns
    str_cols = ["Col2", "Col3", "Col4", "Col5", "Col6", "Col8", "Col28", "Col29", "Col30"]
    for c in str_cols:
        dataset[c] = dataset[c].fillna("").astype(str).str.strip()

    # Filter out invalid/header rows in Col2 (Division)
    invalid_divs = {"", "ವಿಭಾಗದ ಹೆಸರು", "ವಿಭಾಗ", "2", "F", "S", "nan", "None"}
    dataset = dataset[~dataset["Col2"].isin(invalid_divs)].copy()

    # Numeric columns conversion
    num_cols = ["Col9", "Col15", "Col17", "Col23", "Col24", "Col25", "Col26", "Col27"]
    for c in num_cols:
        dataset[c] = pd.to_numeric(dataset[c], errors="coerce").fillna(0.0)

    # Date columns conversion
    for c in ["Col12", "Col19", "Col21", "Col22"]:
        dataset[c + "_dt"] = pd.to_datetime(dataset[c], dayfirst=True, errors="coerce")

    # Col31: year_col (Right 4 chars of Col12)
    dataset["Col31"] = dataset["Col12"].fillna("").astype(str).str.strip().str[-4:]

    # Col32: is_overdue
    today_ts = pd.Timestamp(date.today())
    actual_empty = dataset["Col22"].fillna("").astype(str).str.strip().eq("") & dataset["Col22_dt"].isna()
    target_present = dataset["Col21_dt"].notna()
    status_p = dataset["Col28"].str.upper().eq("P")

    # Matches G-SQL logic: target > TODAY() (or toggleable if overdue means target < TODAY())
    dataset["Col32"] = np.where(
        actual_empty & target_present & status_p & (dataset["Col21_dt"] > today_ts),
        1,
        0,
    )

    # Load Division_wise ABSTRACT
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
    """Generates realistic demo data so the app works out-of-the-box before file upload."""
    rng = np.random.default_rng(42)
    divs = ["ಬೆಂಗಳೂರು ವಿಭಾಗ", "ಮೈಸೂರು ವಿಭಾಗ", "ಮಂಡ್ಯ ವಿಭಾಗ", "ತುಮಕೂರು ವಿಭಾಗ", "ಹಾಸನ ವಿಭಾಗ"]
    districts = ["ಬೆಂಗಳೂರು", "ಮೈಸೂರು", "ಮಂಡ್ಯ", "ತುಮಕೂರು", "ಹಾಸನ"]
    taluks = ["ನೆಲಮಂಗಲ", "ಹುಣಸೂರು", "ಮದ್ದೂರು", "ಗುಬ್ಬಿ", "ಅರಸೀಕೆರೆ"]
    consts = ["ನೆಲಮಂಗಲ", "ಹುಣಸೂರು", "ಮದ್ದೂರು", "ಗುಬ್ಬಿ", "ಅರಸೀಕೆರೆ"]
    schemes = ["MOT", "NT", "LIS", "SCP-CD", "TSP-BW", "PMKSY", "KMERC"]
    aes = ["A.E. Ramesh", "A.E. Suresh", "A.E. Kavitha", "A.E. Mahesh"]
    aees = ["A.E.E. Prakash", "A.E.E. Nandini", "A.E.E. Girish"]

    n = 450
    df = pd.DataFrame({f"Col{i}": "" for i in range(1, 31)}, index=range(n))
    div_idx = rng.integers(0, len(divs), n)
    df["Col2"] = [divs[i] for i in div_idx]
    df["Col3"] = [districts[i] for i in div_idx]
    df["Col4"] = [taluks[i] for i in div_idx]
    df["Col5"] = [consts[i] for i in div_idx]
    df["Col6"] = rng.choice(schemes, n)
    df["Col8"] = rng.choice(["S", "F"], n, p=[0.65, 0.35])
    df["Col9"] = np.round(rng.uniform(40, 12000, n), 2)
    df["Col15"] = np.round(df["Col9"] * rng.uniform(0.85, 1.05, n), 2)
    df["Col17"] = np.round(df["Col9"] * rng.uniform(1.0, 1.15, n), 2)
    df["Col23"] = np.round(df["Col9"] * rng.uniform(0.2, 0.5, n), 2)
    df["Col24"] = np.round(df["Col9"] * rng.uniform(0.05, 0.25, n), 2)
    df["Col25"] = np.round(df["Col23"] + df["Col24"], 2)
    df["Col26"] = np.round(df["Col9"] * rng.uniform(0.0, 0.15, n), 2)
    df["Col27"] = np.round(np.maximum(df["Col9"] - df["Col25"], 0), 2)
    df["Col28"] = rng.choice(STATUS_LIST, n, p=[0.2, 0.1, 0.35, 0.08, 0.07, 0.05, 0.05, 0.02, 0.02, 0.02, 0.02, 0.01, 0.01])
    df["Col29"] = rng.choice(aes, n)
    df["Col30"] = rng.choice(aees, n)

    df["Col12_dt"] = pd.to_datetime(rng.choice(pd.date_range("2021-04-01", "2026-03-31"), n))
    df["Col19_dt"] = df["Col12_dt"] + pd.to_timedelta(rng.integers(30, 180, n), unit="D")
    df["Col21_dt"] = pd.to_datetime(rng.choice(pd.date_range("2015-01-01", "2027-06-30"), n))
    df["Col22_dt"] = pd.Series([pd.NaT if s == "P" else pd.Timestamp("2025-12-01") for s in df["Col28"]])
    df["Col31"] = df["Col12_dt"].dt.year.astype(str)
    df["Col32"] = np.where(
        df["Col22_dt"].isna() & (df["Col28"] == "P") & (df["Col21_dt"] > pd.Timestamp(date.today())),
        1,
        0,
    )

    abs_rows = [{"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "-MOT", "abs_alloc": 4500.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "-NT", "abs_alloc": 3200.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "-LIS", "abs_alloc": 5100.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "ವಿಶೇಷ ಘಟಕ ಯೋಜನೆ", "abs_alloc": 2800.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "ಗಿರಿಜನ ಉಪಯೋಜನೆ", "abs_alloc": 1900.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "PMKSY", "abs_alloc": 2500.0},
                {"abs_div": "ದಕ್ಷಿಣ ವಲಯ", "abs_scheme": "ಕೆ.ಎಂ.ಇ.ಆರ್", "abs_alloc": 1500.0}]
    for d in divs:
        for r in list(abs_rows[:7]):
            abs_rows.append({
                "abs_div": d,
                "abs_scheme": r["abs_scheme"],
                "abs_alloc": round(r["abs_alloc"] / len(divs), 2),
            })

    return df, pd.DataFrame(abs_rows)


# ==========================================
# ALLOCATION & ROW AGGREGATION ENGINE
# ==========================================
def calc_allocation(abs_df: pd.DataFrame, div_name: str, regex_pattern: str) -> float:
    if abs_df.empty or regex_pattern == "NO_MATCH":
        return 0.0
    sub = abs_df[abs_df["abs_div"] == div_name]
    if sub.empty:
        return 0.0
    matched = sub["abs_scheme"].str.contains(regex_pattern, case=False, regex=True, na=False)
    return float(sub.loc[matched, "abs_alloc"].sum())


def compute_row_metrics(
    df_slice: pd.DataFrame,
    overdue_only: bool,
    col1_label: str,
    col2_label: str,
    alloc_display,
) -> list:
    sf = df_slice["Col8"].str.upper()
    statuses = df_slice["Col28"].str.upper()
    is_overdue = df_slice["Col32"]

    # Unfiltered denominators for True Overdue % and True Special %
    true_cS = int((sf == "S").sum())
    true_cF = int((sf == "F").sum())
    true_total = true_cS + true_cF
    true_overdue = int(is_overdue.sum())
    pct_overdue = "0.00%" if true_total == 0 else f"{(true_overdue / true_total) * 100:.2f}%"

    true_special = int(statuses.isin(["TBS", "OTH", "TP", "ETS"]).sum())
    pct_special = "0.00%" if true_total == 0 else f"{(true_special / true_total) * 100:.2f}%"

    # Apply H3 ("OVERDUE WORKS") mask for displayed counts & amounts
    active_df = df_slice[df_slice["Col32"] == 1] if overdue_only else df_slice
    a_sf = active_df["Col8"].str.upper()
    a_stat = active_df["Col28"].str.upper()

    cS = int((a_sf == "S").sum())
    sS = round(float(active_df.loc[a_sf == "S", "Col9"].sum()), 2)
    cF = int((a_sf == "F").sum())
    sF = round(float(active_df.loc[a_sf == "F", "Col9"].sum()), 2)

    sTender = round(float(active_df["Col15"].sum()), 2)
    sRev = round(float(active_df["Col17"].sum()), 2)
    sExpMar26 = round(float(active_df["Col23"].sum()), 2)
    sExp26_27 = round(float(active_df["Col24"].sum()), 2)
    sCumExp = round(float(active_df["Col25"].sum()), 2)
    sBalBill = round(float(active_df["Col26"].sum()), 2)
    sBalAmt = round(float(active_df["Col27"].sum()), 2)

    status_counts = [int((a_stat == st_code).sum()) for st_code in STATUS_LIST]

    return [
        col1_label,
        col2_label,
        cS,
        sS,
        cF,
        sF,
        cS + cF,
        round(sS + sF, 2),
        sTender,
        sRev,
        alloc_display,
        sExpMar26,
        sExp26_27,
        sCumExp,
        sBalBill,
        sBalAmt,
        *status_counts,
        pct_overdue,
        pct_special,
    ]


def build_abstract_table(base_df: pd.DataFrame, abs_df: pd.DataFrame, overdue_only: bool) -> pd.DataFrame:
    if base_df.empty:
        return pd.DataFrame(columns=HEADERS_KN)

    records = []
    unique_schemes = sorted([s for s in base_df["Col6"].unique() if s != ""])
    unique_divs = sorted([d for d in base_df["Col2"].unique() if d != ""])

    # 1. Zone Details (Scheme-wise for ದಕ್ಷಿಣ ವಲಯ)
    for v_scheme in unique_schemes:
        sub = base_df[base_df["Col6"] == v_scheme]
        rgx = get_regex(v_scheme)
        s_alloc = round(calc_allocation(abs_df, "ದಕ್ಷಿಣ ವಲಯ", rgx), 2)
        if v_scheme.startswith("SCP"):
            alloc_disp = f"{s_alloc} (Combined SCP)"
        elif v_scheme.startswith("TSP"):
            alloc_disp = f"{s_alloc} (Combined TSP)"
        else:
            alloc_disp = s_alloc

        row_vals = compute_row_metrics(sub, overdue_only, "ದಕ್ಷಿಣ ವಲಯ", v_scheme, alloc_disp)
        records.append((1, "Zone", 1, v_scheme, row_vals))

    # 2. Zone Total (👉 ಸಣ್ಣ ನೀರಾವರಿ (ದ) ಒಟ್ಟು)
    active_regexes = sorted({get_regex(s) for s in unique_schemes})
    zone_total_alloc = round(sum(calc_allocation(abs_df, "ದಕ್ಷಿಣ ವಲಯ", r) for r in active_regexes), 2)
    zone_tot_vals = compute_row_metrics(
        base_df, overdue_only, "", "👉 ಸಣ್ಣ ನೀರಾವರಿ (ದ) ಒಟ್ಟು", zone_total_alloc
    )
    records.append((1, "Zone", 2, "ZZZ", zone_tot_vals))

    # 3. Spacer Row (ವಿಭಾಗವಾರು)
    spacer_vals = ["ವಿಭಾಗವಾರು"] + [""] * 30
    records.append((2, "Spacer", 2, "AAA", spacer_vals))

    # 4. Division-wise Details & Division Subtotals
    for v_div in unique_divs:
        div_df = base_df[base_df["Col2"] == v_div]
        div_schemes = sorted([s for s in div_df["Col6"].unique() if s != ""])

        for v_scheme in div_schemes:
            sub = div_df[div_df["Col6"] == v_scheme]
            rgx = get_regex(v_scheme)
            s_alloc = round(calc_allocation(abs_df, v_div, rgx), 2)
            if v_scheme.startswith("SCP"):
                alloc_disp = f"{s_alloc} (Combined SCP)"
            elif v_scheme.startswith("TSP"):
                alloc_disp = f"{s_alloc} (Combined TSP)"
            else:
                alloc_disp = s_alloc

            row_vals = compute_row_metrics(sub, overdue_only, v_div, v_scheme, alloc_disp)
            records.append((3, v_div, 1, v_scheme, row_vals))

        div_regexes = sorted({get_regex(s) for s in div_schemes})
        div_total_alloc = round(sum(calc_allocation(abs_df, v_div, r) for r in div_regexes), 2)
        div_tot_vals = compute_row_metrics(
            div_df, overdue_only, "", f"👉 {v_div} ಒಟ್ಟು", div_total_alloc
        )
        records.append((3, v_div, 2, "ZZZ", div_tot_vals))

    # Filter out rows where Total Works (index 6 in row_vals) == 0 unless Spacer row (tier == 2)
    filtered_records = [
        r for r in records if (r[0] == 2) or (isinstance(r[4][6], (int, float)) and r[4][6] > 0)
    ]

    # Sort by (tier, group, row_type, scheme_key)
    filtered_records.sort(key=lambda x: (x[0], x[1], x[2], x[3]))

    # Generate restarting Serial Numbers (ಕ್ರ.ಸಂ) per group for type == 1
    final_rows = []
    prev_grp = None
    acc = 0
    for tier, grp, r_type, _, vals in filtered_records:
        if r_type == 1:
            acc = 1 if grp != prev_grp else acc + 1
            sl_no = str(acc)
        else:
            sl_no = ""
        prev_grp = grp
        final_rows.append([sl_no] + vals)

    return pd.DataFrame(final_rows, columns=HEADERS_KN)


# ==========================================
# SESSION STATE FOR RESET & OVERDUE TOGGLE
# ==========================================
FILTER_KEYS = [
    "f_sf", "f_status", "f_scheme", "f_div", "f_dist", "f_taluk",
    "f_const", "f_cost", "f_overdue_age", "f_go_yr", "f_ae", "f_aee", "f_wo_yr"
]

if "overdue_mode" not in st.session_state:
    st.session_state.overdue_mode = False

def reset_all_filters():
    for k in FILTER_KEYS:
        st.session_state[k] = []
    st.session_state.overdue_mode = False

def toggle_overdue_mode():
    st.session_state.overdue_mode = not st.session_state.overdue_mode


# ==========================================
# SIDEBAR: DATA SOURCE
# ==========================================
with st.sidebar:
    st.header("📂 Data Source")
    uploaded_file = st.file_uploader(
        "Upload Master Excel Workbook (.xlsx)",
        type=["xlsx", "xls"],
        help="Upload the workbook containing the 19 scheme sheets and 'Division_wise ABSTRACT'.",
    )
    if uploaded_file is not None:
        dataset, abs_df = load_workbook_data(uploaded_file)
        st.success(f"Loaded {len(dataset):,} works from workbook.")
    else:
        dataset, abs_df = generate_demo_data()
        st.info("Showing Demo Dataset. Upload your `.xlsx` workbook above for live data.")

# ==========================================
# TOP BANNER & ACTION BUTTONS
# ==========================================
mode_label = "Overdue Works" if st.session_state.overdue_mode else "All Works"
badge_class = "status-badge-overdue" if st.session_state.overdue_mode else "status-badge-all"

st.markdown(
    f"""
    <div class="main-banner">
        <h2>💧 ಸಣ್ಣ ನೀರಾವರಿ (ದಕ್ಷಿಣ ವಲಯ) — Minor Irrigation Abstract Dashboard</h2>
        <div>
            <span style="font-size:0.85rem; margin-right:8px; opacity:0.9;">CURRENTLY SHOWING:</span>
            <span class="{badge_class}">{mode_label}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

btn_col1, btn_col2, btn_col3 = st.columns([1.2, 1.6, 7.2])
with btn_col1:
    st.button("🔄 RESET", on_click=reset_all_filters, use_container_width=True, type="secondary")
with btn_col2:
    overdue_btn_label = "⏰ SHOW ALL WORKS" if st.session_state.overdue_mode else "⚠️ OVERDUE"
    st.button(overdue_btn_label, on_click=toggle_overdue_mode, use_container_width=True, type="primary")


# ==========================================
# 13 MULTI-SELECT DROPDOWN FILTERS (ROW 3 UI)
# ==========================================
def get_fy_options(dt_series: pd.Series) -> list[str]:
    years = sorted(dt_series.dropna().dt.year.unique())
    return [f"{y}-{str(y+1)[-2:]}" for y in years]

with st.expander("🔍 Filter Controls (All 13 G-SQL Dropdowns — Leave empty for 'ALL')", expanded=True):
    r1c1, r1c2, r1c3, r1c4, r1c5, r1c6, r1c7 = st.columns(7)
    with r1c1:
        f_sf = st.multiselect("S/F (A3)", sorted([x for x in dataset["Col8"].unique() if x]), key="f_sf", placeholder="ALL")
    with r1c2:
        f_status = st.multiselect("PROGRESS STATUS (B3)", sorted([x for x in dataset["Col28"].unique() if x]), key="f_status", placeholder="ALL")
    with r1c3:
        f_scheme = st.multiselect("ಲೆಕ್ಕಶೀರ್ಷಿಕೆ (C3)", sorted([x for x in dataset["Col6"].unique() if x]), key="f_scheme", placeholder="ALL")
    with r1c4:
        f_div = st.multiselect("ವಲಯ / ವಿಭಾಗ (D3)", sorted([x for x in dataset["Col2"].unique() if x]), key="f_div", placeholder="ALL")
    with r1c5:
        f_dist = st.multiselect("ಜಿಲ್ಲೆ (E3)", sorted([x for x in dataset["Col3"].unique() if x]), key="f_dist", placeholder="ALL")
    with r1c6:
        f_taluk = st.multiselect("ತಾಲ್ಲೂಕು (F3)", sorted([x for x in dataset["Col4"].unique() if x]), key="f_taluk", placeholder="ALL")
    with r1c7:
        f_const = st.multiselect("ಮತಕ್ಷೇತ್ರ (G3)", sorted([x for x in dataset["Col5"].unique() if x]), key="f_const", placeholder="ALL")

    r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns(6)
    with r2c1:
        f_cost = st.multiselect("ಮೂಲ ಅಂದಾಜು ಮೊತ್ತ (I3)", COST_BUCKETS, key="f_cost", placeholder="ALL")
    with r2c2:
        f_overdue_age = st.multiselect("Overdue Aging (J3)", OVERDUE_BUCKETS, key="f_overdue_age", placeholder="ALL")
    with r2c3:
        f_go_yr = st.multiselect("ಸರ್ಕಾರದ ಆದೇಶ ದಿನಾಂಕ (K3)", get_fy_options(dataset["Col12_dt"]), key="f_go_yr", placeholder="ALL")
    with r2c4:
        f_ae = st.multiselect("A.E. (M3)", sorted([x for x in dataset["Col29"].unique() if x]), key="f_ae", placeholder="ALL")
    with r2c5:
        f_aee = st.multiselect("A.E.E. (N3)", sorted([x for x in dataset["Col30"].unique() if x]), key="f_aee", placeholder="ALL")
    with r2c6:
        f_wo_yr = st.multiselect("ಕಾರ್ಯಾದೇಶ ದಿನಾಂಕ (O3)", get_fy_options(dataset["Col19_dt"]), key="f_wo_yr", placeholder="ALL")


# ==========================================
# APPLY G-SQL `filterStr` WHERE CLAUSE
# ==========================================
mask = pd.Series(True, index=dataset.index)

if f_sf:
    mask &= dataset["Col8"].isin(f_sf)
if f_status:
    mask &= dataset["Col28"].isin(f_status)
if f_scheme:
    mask &= dataset["Col6"].isin(f_scheme)
if f_div:
    mask &= dataset["Col2"].isin(f_div)
if f_dist:
    mask &= dataset["Col3"].isin(f_dist)
if f_taluk:
    mask &= dataset["Col4"].isin(f_taluk)
if f_const:
    mask &= dataset["Col5"].isin(f_const)
if f_ae:
    mask &= dataset["Col29"].isin(f_ae)
if f_aee:
    mask &= dataset["Col30"].isin(f_aee)

# I3: Original Estimated Cost Buckets (Col9)
if f_cost:
    cost_mask = pd.Series(False, index=dataset.index)
    c9 = dataset["Col9"]
    for b in f_cost:
        if b == "More than 10000":
            cost_mask |= c9 > 10000
        elif b == "5000 - 10000":
            cost_mask |= (c9 >= 5000) & (c9 <= 10000)
        elif b == "2500 - 5000":
            cost_mask |= (c9 >= 2500) & (c9 <= 5000)
        elif b == "1000 - 2500":
            cost_mask |= (c9 >= 1000) & (c9 <= 2500)
        elif b == "500 - 1000":
            cost_mask |= (c9 >= 500) & (c9 <= 1000)
        elif b == "200 - 500":
            cost_mask |= (c9 >= 200) & (c9 <= 500)
        elif b == "0 - 200":
            cost_mask |= (c9 >= 0) & (c9 <= 200)
        elif b == "100 - 500":
            cost_mask |= (c9 >= 100) & (c9 <= 500)
        elif b == "Less than 100":
            cost_mask |= c9 < 100
    mask &= cost_mask

# J3: Overdue Aging Buckets (Col21 IS NOT NULL AND Col22 IS NULL)
if f_overdue_age:
    today_ts = pd.Timestamp(date.today())
    m24 = today_ts - pd.DateOffset(months=24)
    m60 = today_ts - pd.DateOffset(months=60)
    m120 = today_ts - pd.DateOffset(months=120)

    c21 = dataset["Col21_dt"]
    c22_null = dataset["Col22_dt"].isna() & dataset["Col22"].fillna("").astype(str).str.strip().eq("")
    age_mask = pd.Series(False, index=dataset.index)

    for b in f_overdue_age:
        if b == "<2 years":
            age_mask |= (c21 > m24) & (c21 <= today_ts)
        elif b == "2-5 years":
            age_mask |= (c21 <= m24) & (c21 > m60)
        elif b == "5-10 years":
            age_mask |= (c21 <= m60) & (c21 > m120)
        elif b == "More than 10 years":
            age_mask |= c21 <= m120
    mask &= c21.notna() & c22_null & age_mask

# K3: GO Date Financial Year (Col12)
if f_go_yr:
    go_mask = pd.Series(False, index=dataset.index)
    for yr_str in f_go_yr:
        yr = int(yr_str[:4])
        go_mask |= (dataset["Col12_dt"] >= pd.Timestamp(yr, 4, 1)) & (
            dataset["Col12_dt"] <= pd.Timestamp(yr + 1, 3, 31)
        )
    mask &= dataset["Col12_dt"].notna() & go_mask

# O3: Work Order Date Financial Year (Col19)
if f_wo_yr:
    wo_mask = pd.Series(False, index=dataset.index)
    for yr_str in f_wo_yr:
        yr = int(yr_str[:4])
        wo_mask |= (dataset["Col19_dt"] >= pd.Timestamp(yr, 4, 1)) & (
            dataset["Col19_dt"] <= pd.Timestamp(yr + 1, 3, 31)
        )
    mask &= dataset["Col19_dt"].notna() & wo_mask

filtered_base = dataset[mask].copy()

# ==========================================
# KPI SUMMARY CARDS
# ==========================================
kpi_df = filtered_base[filtered_base["Col32"] == 1] if st.session_state.overdue_mode else filtered_base
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("ಒಟ್ಟು ಕಾಮಗಾರಿಗಳು (Total Works)", f"{len(kpi_df):,}")
k2.metric("ಒಟ್ಟು ಅಂದಾಜು ಮೊತ್ತ (Est. Cost)", f"₹ {kpi_df['Col9'].sum():,.2f} L")
k3.metric("ಒಟ್ಟಾರೆ ವೆಚ್ಚ (Cum. Expenditure)", f"₹ {kpi_df['Col25'].sum():,.2f} L")
k4.metric("ಬಾಕಿ ಮೊತ್ತ (Balance Needed)", f"₹ {kpi_df['Col27'].sum():,.2f} L")
k5.metric("Overdue Works (In Selection)", f"{int(filtered_base['Col32'].sum()):,}")

# ==========================================
# BUILD & RENDER 32-COLUMN OUTPUT TABLE
# ==========================================
result_df = build_abstract_table(filtered_base, abs_df, st.session_state.overdue_mode)

def highlight_special_rows(row):
    label = str(row["ಲೆಕ್ಕಶೀರ್ಷಿಕೆ"])
    div_label = str(row["ವಲಯ / ವಿಭಾಗ"])
    if div_label == "ವಿಭಾಗವಾರು":
        return ["background-color: #1e293b; color: white; font-weight: bold;"] * len(row)
    if "👉" in label and "ಸಣ್ಣ ನೀರಾವರಿ" in label:
        return ["background-color: #dbeafe; color: #1e3a8a; font-weight: bold;"] * len(row)
    if "👉" in label:
        return ["background-color: #fef3c7; color: #78350f; font-weight: bold;"] * len(row)
    return [""] * len(row)

st.dataframe(
    result_df.style.apply(highlight_special_rows, axis=1),
    use_container_width=True,
    height=680,
    hide_index=True,
)
