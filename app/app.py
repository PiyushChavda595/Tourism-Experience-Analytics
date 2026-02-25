import streamlit as st
import pandas as pd
import joblib
import os
import sqlite3
import numpy as np

# ==========================================
# 1. PATH CONFIGURATION
# ==========================================
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "database", "tourism.db")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")

# ==========================================
# 2. UI CONFIG & PREMIUM DARK STYLING
# ==========================================
st.set_page_config(page_title="VoyageAI | Analytics", layout="wide", page_icon="🧭")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    /* Global App Styles */
    .stApp {
        background-color: #0E1117;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar Background */
    section[data-testid="stSidebar"] {
        background-color: #161B22 !important;
    }

    /* Metric Cards: Glassmorphism Effect */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-card h3 { 
        color: #6366F1 !important; 
        font-size: 2rem !important;
        margin: 0 !important;
        font-weight: 700;
    }
    .metric-card p { 
        color: #94A3B8 !important; 
        font-size: 0.9rem !important;
        margin: 5px 0 0 0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Recommendation Cards: Midnight High-Contrast */
    .rec-card {
        background: #1E293B; /* Solid slate background for maximum readability */
        padding: 24px;
        border-radius: 20px;
        border-left: 6px solid #6366F1;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
        margin-bottom: 25px;
        min-height: 240px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s ease;
    }
    .rec-card:hover {
        transform: translateY(-5px);
        background: #233044;
    }

    .score-tag {
        background: #4F46E5;
        color: #FFFFFF !important;
        padding: 5px 14px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 700;
        width: fit-content;
    }

    .rec-title {
        color: #FFFFFF !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        margin: 15px 0 5px 0 !important;
        line-height: 1.2;
    }

    .rec-location {
        color: #CBD5E1 !important;
        font-size: 0.95rem !important;
        margin-bottom: 15px !important;
    }

    .rec-divider {
        border: 0;
        border-top: 1px solid #334155;
        margin: 15px 0;
    }

    .rec-category {
        color: #818CF8 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Force all header text to be visible */
    h1, h2, h3, span, p, label {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. DATA & MODEL LOADERS
# ==========================================
@st.cache_resource
def load_assets():
    model = joblib.load(os.path.join(MODEL_DIR, "xgb_model.pkl"))
    cols = joblib.load(os.path.join(MODEL_DIR, "feature_columns.pkl"))
    catalog = joblib.load(os.path.join(MODEL_DIR, "attraction_catalog.pkl"))
    return model, cols, catalog

@st.cache_data
def get_user_context():
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT t.*, u.CityId as UserCityId, ty.AttractionType, m.VisitMode 
    FROM TransactionTable t
    JOIN User u ON t.UserId = u.UserId
    JOIN Attraction a ON t.AttractionId = a.AttractionId
    JOIN Type ty ON a.AttractionTypeId = ty.AttractionTypeId
    JOIN Mode m ON t.VisitModeId = m.VisitModeId
    """
    df = pd.read_sql(query, conn)
    
    # Calculate User Preferences
    user_type_pref = df.groupby(["UserId", "AttractionType"]).size().reset_index(name="TypeVisitCount")
    user_total = df.groupby("UserId").size().reset_index(name="UserTotalVisits")
    user_type_pref = user_type_pref.merge(user_total, on="UserId")
    user_type_pref["UserTypePreference"] = user_type_pref["TypeVisitCount"] / user_type_pref["UserTotalVisits"]
    
    # Historical Context
    df["UserHistoricalAvg"] = df.groupby("UserId")["Rating"].transform(lambda x: x.expanding().mean().shift(1))
    df["UserHistoricalCount"] = df.groupby("UserId").cumcount()
    df["UserHistoricalAvg"] = df["UserHistoricalAvg"].fillna(df["Rating"].mean())
    
    conn.close()
    return df, user_type_pref

# ==========================================
# 4. RECOMMENDATION ENGINE
# ==========================================
feature_columns_base = ["VisitMonth", "Quarter", "PostCovid", "UserHistoricalAvg", "UserHistoricalCount", 
                        "AttractionHistoricalAvg", "AttractionHistoricalCount", "UserAttractionHistoryCount", 
                        "UserTypePreference", "VisitMode", "AttractionType"]

def build_candidate_features(user_id, df_master, df_all_attractions, user_type_pref, feature_columns):
    user_history = df_master[df_master["UserId"] == user_id]
    if len(user_history) == 0: return None, None
    
    user_profile = user_history.sort_values("TransactionId").iloc[-1]
    visited = set(user_history["AttractionId"])
    
    candidates = df_all_attractions[~df_all_attractions["AttractionId"].isin(visited)].copy()
    
    candidates["UserId"] = user_id
    candidates["VisitMonth"] = user_profile["VisitMonth"]
    candidates["Quarter"] = (user_profile["VisitMonth"] - 1) // 3 + 1
    candidates["PostCovid"] = 1 if user_profile["VisitYear"] >= 2020 else 0
    candidates["UserHistoricalAvg"] = user_profile["UserHistoricalAvg"]
    candidates["UserHistoricalCount"] = user_profile["UserHistoricalCount"]
    candidates["UserAttractionHistoryCount"] = 0
    
    attr_stats = df_master.groupby("AttractionId").agg({"Rating": "mean", "TransactionId": "count"}).reset_index()
    attr_stats.columns = ["AttractionId", "AttractionHistoricalAvg", "AttractionHistoricalCount"]
    
    candidates = candidates.merge(attr_stats, on="AttractionId", how="left")
    candidates["AttractionHistoricalAvg"] = candidates["AttractionHistoricalAvg"].fillna(df_master["Rating"].mean())
    candidates["AttractionHistoricalCount"] = candidates["AttractionHistoricalCount"].fillna(0)
    
    candidates = candidates.merge(user_type_pref[["UserId", "AttractionType", "UserTypePreference"]], on=["UserId", "AttractionType"], how="left")
    candidates["UserTypePreference"] = candidates["UserTypePreference"].fillna(0)
    candidates["VisitMode"] = user_profile["VisitMode"]
    
    model_df = pd.get_dummies(candidates[feature_columns_base], columns=["VisitMode", "AttractionType"], drop_first=True)
    model_df = model_df.reindex(columns=feature_columns, fill_value=0)
    
    return candidates, model_df

# ==========================================
# 5. UI LAYOUT
# ==========================================
try:
    model, feature_cols, catalog = load_assets()
    df_master, user_prefs = get_user_context()

    # SIDEBAR
    with st.sidebar:
        st.markdown("<h2 style='color:white;'>⚙️ Control Panel</h2>", unsafe_allow_html=True)
        user_list = sorted(df_master['UserId'].unique())
        selected_user = st.selectbox("Select Traveler ID", user_list, index=0)
        num_recs = st.slider("Recommendations to show", 3, 12, 6)
        st.divider()
        st.markdown("### Model Diagnostics")
        st.code("XGBoost-V1.2\nLatency: 42ms\nState: Ready")

    # MAIN HEADER
    st.title("VoyageAI :blue[Experience Analytics]")
    st.markdown("<p style='color:#94A3B8; font-size:1.1rem;'>Predicting your next 5-star memory with Big Data.</p>", unsafe_allow_html=True)

    # USER PROFILE SECTION
    u_data = df_master[df_master['UserId'] == selected_user]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><h3>{len(u_data)}</h3><p>Past Trips</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><h3>{u_data["Rating"].mean():.1f} ⭐</h3><p>Avg Rating</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><h3>{u_data["AttractionType"].mode()[0]}</h3><p>Fav Category</p></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><h3>{u_data["VisitMode"].mode()[0]}</h3><p>Travel Mode</p></div>', unsafe_allow_html=True)

    st.divider()

    # GENERATE RECOMMENDATIONS
    st.subheader("🎯 Personalized Recommendations")
    
    candidates, model_input = build_candidate_features(selected_user, df_master, catalog, user_prefs, feature_cols)
    
    if candidates is not None:
        probs = model.predict_proba(model_input)[:, 1]
        candidates["Score"] = probs
        top_recs = candidates.sort_values("Score", ascending=False).head(num_recs)
        
        # Grid Display
        cols_per_row = 3
        for i in range(0, len(top_recs), cols_per_row):
            columns = st.columns(cols_per_row)
            for j, (idx, row) in enumerate(top_recs.iloc[i : i + cols_per_row].iterrows()):
                if j < len(columns):
                    with columns[j]:
                        st.markdown(f"""
                            <div class="rec-card">
                                <div class="score-tag">{row['Score']*100:.1f}% Match</div>
                                <h3 class="rec-title">{row['Attraction']}</h3>
                                <p class="rec-location">📍 {row['CityName']}, {row['Country']}</p>
                                <div>
                                    <hr class="rec-divider">
                                    <p class="rec-category">{row['AttractionType']}</p>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
    else:
        st.error("No historical data found for this user ID.")

except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.info("Ensure `models/` and `database/` folders are in your project root.")
