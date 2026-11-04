import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, OneHotEncoder, OrdinalEncoder
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Data Science Diagnostic Lab",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PREMIUM DARK THEME CSS ---
st.markdown("""
<style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stApp { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #1a1c24;
        border-radius: 4px 4px 0px 0px;
        color: #8b949e;
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #58a6ff !important;
        color: white !important;
    }
    .diagnostic-card {
        background: #1a1c24; border: 1px solid #30363d;
        padding: 1.5em; border-radius: 12px; margin-bottom: 1em;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .status-badge {
        padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 0.8em;
    }
    .badge-high { background: #fee2e2; color: #991b1b; }
    .badge-mid { background: #fef3c7; color: #92400e; }
    .badge-low { background: #d1fae5; color: #065f46; }
    h1, h2, h3 { color: #ffffff !important; }
    .instruction-ptr { color: #58a6ff; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- DATA GENERATOR ---
@st.cache_data
def load_sample_data():
    np.random.seed(42)
    n = 200
    data = {
        'Age': np.random.normal(35, 12, n).astype(int),
        'Income': np.random.lognormal(10, 0.5, n),
        'Experience': np.random.randint(0, 40, n),
        'Education': np.random.choice(['High School', 'Bachelor', 'Master', 'PhD'], n),
        'Department': np.random.choice(['Sales', 'Tech', 'HR', 'R&D'], n),
        'Satisfaction': np.random.uniform(1, 10, n),
        'Target': np.random.binomial(1, 0.3, n)
    }
    df = pd.DataFrame(data)
    
    # Introduce Outliers
    df.loc[0, 'Age'] = 150
    df.loc[1, 'Income'] = 1_000_000
    
    # Introduce Duplicates
    df = pd.concat([df, df.iloc[:5]], ignore_index=True)
    
    # Introduce Missingness (MCAR)
    mask = np.random.rand(*df.shape) < 0.1
    df_missing = df.mask(mask)
    
    # Ensure some columns have no missingness for target
    df_missing['Target'] = df['Target']
    
    return df_missing, df

df_missing, df_clean = load_sample_data()

# --- SIDEBAR NAVIGATION ---
st.sidebar.image("https://img.icons8.com/bubbles/200/experimental-brain-bubbles.png", width=100)
st.sidebar.title("Diagnostic Lab")
st.sidebar.markdown("---")

app_mode = st.sidebar.selectbox(
    "Choose Your Lab Module:",
    ["🏠 Landing Page", "🏥 The Data Quality Hospital", "🔬 The Feature Lab"]
)

st.sidebar.markdown("---")
st.sidebar.info("🧪 **Module 2: Basic Concepts of Data Science**")

# --- MAIN APP LOGIC ---

if app_mode == "🏠 Landing Page":
    st.title("🧪 Data Science Diagnostic Lab")
    st.markdown("""
    Welcome to the interactive laboratory for **Module 2: Basic Concepts of Data Science**. 
    Choose a module from the sidebar to begin your data diagnostic journey.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="diagnostic-card">
            <h3>🏥 The Data Quality Hospital</h3>
            <p>Diagnose and treat the "health" of your datasets.</p>
            <ul>
                <li>Missingness Diagnosis (MCAR/MAR)</li>
                <li>Imputation Treatments</li>
                <li>Misleading Graph Clinic</li>
                <li>Data Surgery (Outliers/Duplicates)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="diagnostic-card">
            <h3>🔬 The Feature Lab</h3>
            <p>Engineer and transmute features for optimal performance.</p>
            <ul>
                <li>Distribution Centrifuge</li>
                <li>Numerical Particle Sorter</li>
                <li>Categorical Transmutaion</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

elif app_mode == "🏥 The Data Quality Hospital":
    st.title("🏥 The Data Quality Hospital")
    tabs = st.tabs(["🩺 Diagnosis (Missingness)", "💊 Treatment (Imputation)", "👓 The Optician (Misleading Graphs)", "🔪 Surgery (Cleaning)"])
    
    with tabs[0]:
        st.subheader("🩺 Session 1: The Diagnosis Ward")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Identify if missingness is random (MCAR), conditional (MAR), or systematic (MNAR).
        """, unsafe_allow_html=True)
        
        col_diag1, col_diag2 = st.columns([1, 1])
        
        with col_diag1:
            st.markdown("### Missingness Matrix")
            # Custom missingno-like matrix
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(df_missing.isnull(), cbar=False, yticklabels=False, cmap='Blues_r', ax=ax)
            ax.set_xlabel("Features")
            ax.set_title("Missing Value Matrix (White = Missing)")
            plt.xticks(rotation=45)
            st.pyplot(fig)
            
        with col_diag2:
            st.markdown("### Null Correlation")
            # Correlation of nullity
            fig, ax = plt.subplots(figsize=(10, 6))
            sns.heatmap(df_missing.isnull().corr(), annot=True, cmap='RdBu', center=0, ax=ax)
            ax.set_title("Nullity Correlation Heatmap")
            plt.xticks(rotation=45)
            st.pyplot(fig)
            
        st.markdown("---")
        st.markdown("### 📊 Dataset Profile Summary")
        null_counts = df_missing.isnull().sum()
        total_rows = len(df_missing)
        metrics = st.columns(4)
        metrics[0].metric("Total Rows", total_rows)
        metrics[1].metric("Null Values", null_counts.sum())
        metrics[2].metric("Max Sparse Col", f"{null_counts.max()} ({ (null_counts.max()/total_rows*100):.1f}%)")
        metrics[3].metric("Duplicate Rows", df_missing.duplicated().sum())

    with tabs[1]:
        st.subheader("💊 Session 2: The Treatment Lab")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Compare imputation strategies and their impact on data "vitals" (distribution).
        """, unsafe_allow_html=True)
        
        col_select = st.selectbox("Select a Numeric Patient to Treat:", df_missing.select_dtypes(include=[np.number]).columns)
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.markdown("#### Imputation Strategy")
            strategy = st.radio("Choose a 'Cure':", ["Mean", "Median", "Mode", "KNN (k=5)", "Zero Fill"])
            
            # Application logic
            raw_series = df_missing[col_select]
            clean_series = df_clean[col_select]
            
            if strategy == "Mean":
                imputed_series = raw_series.fillna(raw_series.mean())
            elif strategy == "Median":
                imputed_series = raw_series.fillna(raw_series.median())
            elif strategy == "Mode":
                imputed_series = raw_series.fillna(raw_series.mode()[0])
            elif strategy == "KNN (k=5)":
                knn = KNNImputer(n_neighbors=5)
                # For KNN we need more context, so we use numeric cols
                numeric_df = df_missing.select_dtypes(include=[np.number])
                imputed_data = knn.fit_transform(numeric_df)
                idx = list(numeric_df.columns).index(col_select)
                imputed_series = pd.Series(imputed_data[:, idx], index=df_missing.index)
            else:
                imputed_series = raw_series.fillna(0)
            
            st.success(f"Strategy '{strategy}' applied!")
            
            st.metric("Mean Shift", f"{(imputed_series.mean() - clean_series.mean()):.2f}")
            st.metric("Std Dev Shift", f"{(imputed_series.std() - clean_series.std()):.2f}")

        with c2:
            st.markdown("#### Distribution Impact")
            fig = go.Figure()
            # Original (Clean)
            fig.add_trace(go.Histogram(x=clean_series, name="Original (True)", marker_color='#2ecc71', opacity=0.5))
            # Imputed
            fig.add_trace(go.Histogram(x=imputed_series, name="Imputed (Experimental)", marker_color='#e74c3c', opacity=0.5))
            
            fig.update_layout(
                barmode='overlay',
                template="plotly_dark",
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("💡 Note how 'Mean' imputation creates a large spike at the center, potentially reducing variance and introducing bias.")
        
    with tabs[2]:
        st.subheader("👓 Session 3: The Optician Clinic")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Detect how design choices can distort data interpretation.
        """, unsafe_allow_html=True)
        
        viz_type = st.radio("Select a Clinical Case:", ["The Truncated Y-Axis", "The Cherry-Picked Range"])
        
        col_viz_left, col_viz_right = st.columns([1, 1])
        
        with col_viz_left:
            st.markdown("#### ❌ Distorted View")
            if viz_type == "The Truncated Y-Axis":
                # Simulated data: small growth made to look big
                years = [2020, 2021, 2022, 2023]
                values = [100, 102, 101, 103]
                fig = px.bar(x=years, y=values, range_y=[99, 104], title="Revenue Growth (?)")
                st.plotly_chart(fig, use_container_width=True)
                st.warning("Warning: Y-axis starts at 99. The growth looks massive!")
            else:
                # Cherry picking
                x = np.linspace(0, 10, 100)
                y = np.sin(x) + np.random.normal(0, 0.1, 100)
                # Show only 2 to 4
                mask = (x >= 2) & (x <= 4)
                fig = px.line(x=x[mask], y=y[mask], title="Stock Market 'Crash'")
                st.plotly_chart(fig, use_container_width=True)
                st.warning("Warning: Only showing 20% of the timeline where it looks like a crash.")

        with col_viz_right:
            st.markdown("#### ✅ Truth Filter")
            if viz_type == "The Truncated Y-Axis":
                years = [2020, 2021, 2022, 2023]
                values = [100, 102, 101, 103]
                fig = px.bar(x=years, y=values, range_y=[0, 150], title="Actual Revenue Growth")
                st.plotly_chart(fig, use_container_width=True)
                st.info("The 2-3% growth is correctly contextualized by starting at 0.")
            else:
                x = np.linspace(0, 10, 100)
                y = np.sin(x) + np.random.normal(0, 0.1, 100)
                fig = px.line(x=x, y=y, title="Full Market Cycle")
                st.plotly_chart(fig, use_container_width=True)
                st.info("The full cycle shows the 'crash' was just a regular oscillation.")

    with tabs[3]:
        st.subheader("🔪 Session 4: Quality Control Surgery")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Detect and excise 'malignant' data point (Outliers and Duplicates).
        """, unsafe_allow_html=True)
        
        c_clean_1, c_clean_2 = st.columns([1, 2])
        
        with c_clean_1:
            st.markdown("### Surgical Settings")
            z_threshold = st.slider("Z-Score Sensitivity (Outliers):", 1.0, 5.0, 3.0)
            st.markdown("---")
            remove_dupes = st.checkbox("Remove Duplicate Rows", value=True)
            
            if st.button("🚀 Perform Surgery", type="primary"):
                # Outlier detection
                numeric_df = df_missing.select_dtypes(include=[np.number])
                z_scores = np.abs((numeric_df - numeric_df.mean()) / numeric_df.std())
                outlier_mask = (z_scores > z_threshold).any(axis=1)
                
                cleaned_df = df_missing[~outlier_mask]
                if remove_dupes:
                    cleaned_df = cleaned_df.drop_duplicates()
                
                st.session_state.cleaned_df = cleaned_df
                st.success("Surgery successful! Viewing report...")

        with c_clean_2:
            if 'cleaned_df' in st.session_state:
                st.markdown("### Surgical Report")
                res = st.session_state.cleaned_df
                orig = df_missing
                
                col_rep1, col_rep2, col_rep3 = st.columns(3)
                col_rep1.metric("Rows Removed", len(orig) - len(res))
                col_rep2.metric("Final Sample Size", len(res))
                col_rep3.metric("Data Health %", f"{(len(res)/len(orig)*100):.1f}%")
                
                st.dataframe(res.head(10), use_container_width=True)
                st.download_button("📥 Download Cleaned Dataset", res.to_csv(), "cleaned_data.csv")
            else:
                st.info("Configure settings and click 'Perform Surgery' to generate a report.")

elif app_mode == "🔬 The Feature Lab":
    st.title("🔬 The Feature Lab")
    tabs = st.tabs(["🌀 The Centrifuge (Transforms)", "🔢 Particle Sorter (Numerical)", "🧬 The Transmuster (Categorical)"])

    with tabs[0]:
        st.subheader("🌀 Session 5: The Distribution Centrifuge")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Transmute skewed data into a Normal (Gaussian) distribution.
        """, unsafe_allow_html=True)
        
        col_c_select = st.selectbox("Select Numeric Feature to Centrifuge:", ["Income", "Age", "Satisfaction"])
        
        c_cent_1, c_cent_2 = st.columns([1, 2])
        
        with c_cent_1:
            st.markdown("### Transform Controls")
            transform_type = st.radio("Centrifuge Protocol:", ["Raw (None)", "Log Transform", "Square Root", "Box-Cox"])
            
            from scipy import stats
            raw_data = df_clean[col_c_select]
            
            if transform_type == "Log Transform":
                transformed = np.log1p(raw_data)
            elif transform_type == "Square Root":
                transformed = np.sqrt(raw_data)
            elif transform_type == "Box-Cox":
                # Box-cox requires positive values
                transformed, _ = stats.boxcox(raw_data + 1)
                transformed = pd.Series(transformed)
            else:
                transformed = raw_data
            
            # Shapiro-Wilk Test for Normality
            shapiro_test = stats.shapiro(transformed)
            st.metric("Shapiro-Wilk Score", f"{shapiro_test.statistic:.4f}")
            st.caption("Score closer to 1.0 indicates higher normality.")
            
        with c_cent_2:
            st.markdown("### Centrifuge Output")
            fig = px.histogram(transformed, nbins=30, title=f"Distribution after {transform_type}", 
                               color_discrete_sequence=['#58a6ff'])
            fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.subheader("🔢 Session 6: The Particle Sorter")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Discretize and Scale numerical particles for model readiness.
        """, unsafe_allow_html=True)
        
        sub_tab1, sub_tab2 = st.tabs(["📦 Binning Lab", "📏 Scaling Workbench"])
        
        with sub_tab1:
            st.markdown("#### Feature Binning")
            col_b = st.selectbox("Feature to Bin:", ["Age", "Experience"])
            bin_method = st.radio("Binning Strategy:", ["Equal Width", "Equal Frequency (Quantiles)"], horizontal=True)
            n_bins = st.slider("Number of Bins:", 2, 10, 5)
            
            if bin_method == "Equal Width":
                binned = pd.cut(df_clean[col_b], bins=n_bins)
            else:
                binned = pd.qcut(df_clean[col_b], q=n_bins, duplicates='drop')
                
            fig = px.histogram(x=binned.astype(str), title=f"{bin_method} Binning Results", 
                               labels={'x': 'Bins', 'y': 'Count'}, color_discrete_sequence=['#ffca28'])
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        with sub_tab2:
            st.markdown("#### Feature Scaling")
            col_s = st.selectbox("Feature to Scale:", ["Income", "Age", "Experience"])
            scaler_type = st.select_slider("Select Scaler:", ["MinMax", "Standard", "Robust"])
            
            data_to_scale = df_clean[[col_s]]
            if scaler_type == "MinMax":
                scaled = MinMaxScaler().fit_transform(data_to_scale)
            elif scaler_type == "Standard":
                scaled = StandardScaler().fit_transform(data_to_scale)
            else:
                scaled = RobustScaler().fit_transform(data_to_scale)
            
            scaled_df = pd.DataFrame(scaled, columns=[col_s])
            
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.write(f"**{col_s}** (Before)")
                st.write(df_clean[col_s].describe())
            with c_s2:
                st.write(f"**{col_s}** (After {scaler_type})")
                st.write(scaled_df[col_s].describe())
            
            st.info(f"💡 {scaler_type} Scaler mapped the data range to approximately [{scaled_df[col_s].min():.2f}, {scaled_df[col_s].max():.2f}].")

    with tabs[2]:
        st.subheader("🧬 Session 7: The Transmuster")
        st.markdown("""
        <div class='instruction-ptr'>ANALYSIS GOAL:</div> Transmute categorical labels into numerical vectors.
        """, unsafe_allow_html=True)
        
        col_t = st.selectbox("Select Categorical Feature:", ["Education", "Department"])
        enc_type = st.radio("Encoding Protocol:", ["One-Hot (Sparse)", "Ordinal (Label)"], horizontal=True)
        
        raw_cat = df_clean[[col_t]]
        
        c_t1, c_t2 = st.columns([1, 2])
        
        with c_t1:
            if enc_type == "One-Hot (Sparse)":
                enc = OneHotEncoder(sparse_output=False)
                encoded = enc.fit_transform(raw_cat)
                encoded_df = pd.DataFrame(encoded, columns=enc.get_feature_names_out())
                st.info(f"Generated {encoded_df.shape[1]} new binary features.")
            else:
                enc = OrdinalEncoder()
                encoded = enc.fit_transform(raw_cat)
                encoded_df = pd.DataFrame(encoded, columns=[f"{col_t}_encoded"])
                st.info("Mapped categories to integers based on discovery order.")
            
            st.write("**Transmuted Matrix (Preview):**")
            st.dataframe(encoded_df.head(10), use_container_width=True)

        with c_t2:
            st.markdown("#### Dimensionality Impact")
            labels = ['Original', 'Encoded']
            values = [1, encoded_df.shape[1]]
            fig = px.bar(x=labels, y=values, title="Feature Count Evolution",
                         labels={'x': 'Stage', 'y': 'Number of Columns'},
                         color_discrete_sequence=['#81c784'])
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            if enc_type == "One-Hot (Sparse)":
                st.warning("⚠️ High Cardinality Warning: One-Hot encoding can lead to the 'Curse of Dimensionality' if the category has many unique values.")
            else:
                st.warning("⚠️ Assumption Warning: Ordinal encoding implies a mathematical order (1 < 2 < 3) which might not exist in the data.")
