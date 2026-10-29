"""寵物好事門市營運數據報告 - Streamlit 版 v2
重點改動（依使用者回饋）：
1. 網頁版：台灣地圖縮小、可點選。地圖用 Plotly 疊在使用者提供的台灣圖上，
   點圖釘就會切換右側門市報告；地圖下方另有 1-14 號按鈕當作備援，點按鈕一樣能切換。
2. 手機版：完全不渲染地圖，直接呈現門市報告與排行，避免地圖撐版。
   頂部有「電腦版 / 手機版」開關，讓你在任何裝置上都能預覽兩種呈現。
   另外也加了手機 CSS：窄螢幕下 Plotly 地圖會被隱藏，當作第二層保險。
3. 排行：不再用 st.dataframe（欄位標題一點就會排序、排名會跑掉）。
   改用固定表格／手機卡片，排序改由上方的「排序依據」下拉控制，
   每次排序後排名都會重算，永遠是第 1 名在最上面。
所有營運數字皆為作品示範數據，非寵物好事實際營運數據。
資料來源：同目錄的 stores.csv。
"""
import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

BASE = Path(__file__).parent
MAP_PATH = BASE / "assets" / "taiwan-map.jpg"
CSV_PATH = BASE / "stores.csv"

st.set_page_config(
    page_title="寵物好事門市營運數據報告",
    page_icon="🐾",
    layout="wide",
)

# ---------- HTML 風格微調：紅色主色、暖底、圓角卡片 ----------
st.markdown(
    """
    <style>
    .stApp { background-color: #FFF8F0; }
    h1, h2, h3 { color: #C62828 !important; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border-radius: 12px; padding: 12px 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #FFDAD6;
    }
    /* 窄螢幕第二層保險：真的在手機上時，把 Plotly 地圖藏起來 */
    @media (max-width: 768px) {
        div[data-testid="stPlotlyChart"] { display: none !important; }
    }
    .rank-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .rank-table th { background: #C62828; color: #fff; padding: 8px 6px; text-align: right; white-space: nowrap; }
    .rank-table th:first-child, .rank-table td:first-child { text-align: center; }
    .rank-table td:nth-child(2) { text-align: left; font-weight: 600; }
    .rank-table td { padding: 7px 6px; text-align: right; border-bottom: 1px solid #F0D9D5; background: #fff; }
    .rank-table tr:nth-child(even) td { background: #FFF3F0; }
    .pos { color: #2E7D32; font-weight: 700; }
    .neg { color: #C62828; font-weight: 700; }
    .ach-ok { color: #2E7D32; font-weight: 700; }
    .ach-no { color: #C62828; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 資料 ----------
@st.cache_data
def load_stores():
    return pd.read_csv(CSV_PATH)

df_raw = load_stores()
df = df_raw.reset_index(drop=True)
df["no"] = df.index + 1

def period_cols(prefix):
    return {
        "revenue": f"{prefix}_revenue",
        "margin": f"{prefix}_margin_pct",
        "visitors": f"{prefix}_visitors",
        "rev_g": f"{prefix}_rev_growth_pct",
        "gross_g": f"{prefix}_gross_growth_pct",
        "vis_g": f"{prefix}_visitor_growth_pct",
        "ach": f"{prefix}_achievement_pct",
    }

def enrich(row, prefix):
    c = period_cols(prefix)
    revenue = float(row[c["revenue"]])
    margin = float(row[c["margin"]])
    visitors = int(row[c["visitors"]])
    gross = revenue * margin / 100.0
    ticket = revenue / visitors if visitors else 0
    ach = float(row[c["ach"]])
    target = revenue / (ach / 100.0) if ach else 0
    return {
        "revenue": revenue, "margin": margin, "gross": gross,
        "visitors": visitors, "ticket": ticket, "target": target,
        "rev_g": float(row[c["rev_g"]]), "gross_g": float(row[c["gross_g"]]),
        "vis_g": float(row[c["vis_g"]]), "ach": ach,
    }

def money(x):
    return f"NT$ {x:,.0f}"

def pct_signed(x):
    return f"{x:+.1f}%"

def latlon_to_xy(lat, lon):
    # 全圖概略換算：lat 25.35 -> y 0.02（上），21.90 -> y 0.98（下）
    # lon 119.90 -> x 0.05（左），122.00 -> x 0.95（右）
    x = 0.05 + (lon - 119.90) / (122.00 - 119.90) * 0.90
    y_top = 0.02 + (25.35 - lat) / (25.35 - 21.90) * 0.96
    return x, y_top

DISPLAY_OFFSETS = {
    "忠明店": (0.05, 0.03),
    "文心店（櫻花路口）": (-0.08, -0.04),
    "公益店": (-0.03, 0.06),
    "文心店（138-10號）": (-0.05, 0.01),
    "楓康東山店": (0.08, -0.03),
    "楓康高鐵店": (-0.02, 0.07),
    "楓康朝富店": (-0.09, 0.02),
    "楓康黎明店": (-0.06, 0.07),
    "大里店": (0.05, 0.06),
    "水湳店": (0.00, -0.05),
    "復中店": (0.09, 0.02),
}

if "selected_store" not in st.session_state:
    st.session_state.selected_store = str(df.iloc[0]["store"])

# ---------- 頁首 + 版面開關 ----------
st.markdown("<h1>🐾 寵物好事-貓の專門店｜門市營運數據報告</h1>", unsafe_allow_html=True)
st.warning("本頁所有營運數字皆為作品示範數據，非寵物好事實際營運數據，僅用來展示營運數字的整理架構。")

view_mode = st.radio(
    "版面預覽",
    ["電腦版（顯示可點地圖）", "手機版（隱藏地圖，直接看數據）"],
    horizontal=True,
    index=0,
    help="在手機上打開時請切到「手機版」，地圖就不會出現；電腦上請用「電腦版」，地圖可以點。",
)
is_mobile = view_mode.startswith("手機版")

# 全台合計（兩個期間都算，之後會用到）
mtd_total_rev = float(df["mtd_revenue"].sum())
ytd_total_rev = float(df["ytd_revenue"].sum())
mtd_total_gross = float((df["mtd_revenue"] * df["mtd_margin_pct"] / 100).sum())
ytd_total_gross = float((df["ytd_revenue"] * df["ytd_margin_pct"] / 100).sum())
mtd_total_vis = int(df["mtd_visitors"].sum())
ytd_total_vis = int(df["ytd_visitors"].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("全台月至今業績", money(mtd_total_rev))
c2.metric("全台月至今毛利額", money(mtd_total_gross))
c3.metric("全台月至今來客數", f"{mtd_total_vis:,} 人")
c4.metric("全台年至今業績", money(ytd_total_rev))

# ---------- 地圖 + 報告 ----------
def build_map_figure():
    with open(MAP_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    xs, ys, texts, hovers = [], [], [], []
    for _, row in df.iterrows():
        x, y_top = latlon_to_xy(float(row["lat"]), float(row["lon"]))
        dx, dy = DISPLAY_OFFSETS.get(row["store"], (0, 0))
        xs.append(x + dx)
        ys.append(1 - (y_top + dy))  # Plotly y 軸是下到上，要翻轉
        texts.append(str(int(row["no"])))
        hovers.append(f"{row['store']}<br>{row['address']}")
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=f"data:image/jpeg;base64,{b64}",
            xref="x", yref="y", x=0, y=1, sizex=1, sizey=1,
            sizing="stretch", layer="below", opacity=1,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, mode="markers+text",
            marker=dict(size=26, color="#C62828", line=dict(color="white", width=2)),
            text=texts, textposition="middle center",
            textfont=dict(color="white", size=12, family="Arial Black"),
            hovertext=hovers, hoverinfo="text",
            customdata=list(df["store"]),
        )
    )
    fig.update_layout(
        width=340, height=575, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(range=[0, 1], visible=False, fixedrange=True),
        yaxis=dict(range=[0, 1], visible=False, fixedrange=True, scaleanchor="x"),
        showlegend=False, dragmode=False, clickmode="event+select",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig

selected_row = df[df["store"] == st.session_state.selected_store]
if selected_row.empty:
    selected_row = df.iloc[[0]]
    st.session_state.selected_store = str(selected_row.iloc[0]["store"])
selected = selected_row.iloc[0]

if is_mobile:
    # ---- 手機版：不渲染地圖，直接看數據 ----
    st.subheader(f"{selected['store']}")
    st.write(f"📍 {selected['address']}")
    if str(selected["note"]).strip():
        st.write(f"備註：{selected['note']}")
    # 手機版選店用下拉（不是地圖），放在報告上方最順手
    mobile_choice = st.selectbox(
        "選擇門市",
        list(df["store"]),
        index=int(df[df["store"] == st.session_state.selected_store].index[0]),
        key="mobile_store_select",
    )
    if mobile_choice != st.session_state.selected_store:
        st.session_state.selected_store = mobile_choice
        selected = df[df["store"] == mobile_choice].iloc[0]
else:
    # ---- 電腦版：左邊小地圖（可點）+ 右邊報告 ----
    map_col, detail_col = st.columns([0.85, 1.35])
    with map_col:
        st.subheader("台灣門市地圖")
        st.caption("地圖已縮小，點圖釘可切換右側報告；下方編號按鈕也是同樣功能。")
        try:
            fig = build_map_figure()
            selection = st.plotly_chart(
                fig, use_container_width=False,
                on_select="rerun", selection_mode="points", key="taiwan_map",
            )
            # Plotly 點選回傳：把點到的門市設為目前門市
            try:
                point_indices = selection.get("selection", {}).get("point_indices", []) if selection else []
            except Exception:
                point_indices = []
            if point_indices:
                clicked_store = str(df.iloc[int(point_indices[0])]["store"])
                if clicked_store != st.session_state.selected_store:
                    st.session_state.selected_store = clicked_store
                    selected = df[df["store"] == clicked_store].iloc[0]
        except FileNotFoundError:
            st.error("找不到 assets/taiwan-map.jpg，請確認上傳時有保留 assets 資料夾。")
        st.caption("圖釘編號對照（點按鈕也可切換）：")
        # 編號按鈕備援：7 個一排、共兩排
        for start in (0, 7):
            btn_cols = st.columns(7)
            for j, (_, row) in enumerate(df.iloc[start:start + 7].iterrows()):
                with btn_cols[j]:
                    if st.button(f"{int(row['no'])}", key=f"map_btn_{int(row['no'])}", help=str(row["store"])):
                        st.session_state.selected_store = str(row["store"])
                        selected = row
        st.write("1 忠明｜2 文心櫻花｜3 公益｜4 文心138-10｜5 楓康東山｜6 楓康高鐵｜7 楓康朝富")
        st.write("8 楓康黎明｜9 八德｜10 南港｜11 新莊｜12 大里｜13 水湳｜14 復中")
        st.caption("台中密集區圖釘有適度展開，真實位置以引線小圓點為準；復中店為東區概略位置。")
    with detail_col:
        st.subheader(f"{selected['store']}")
        st.write(f"📍 {selected['address']}")
        if str(selected["note"]).strip():
            st.write(f"備註：{selected['note']}")

# 報告本體（電腦版在右欄、手機版在全寬，寫在這裡是為了讓兩種版面共用同一段）
# 注意：電腦版時上面 detail_col 已經寫了店名地址，這裡只補指標，避免重複店名。
st.subheader(f"📊 {selected['store']} 營運報告")
tab_mtd, tab_ytd = st.tabs(["月至今 MTD", "年至今 YTD"])
for tab, prefix, label in [(tab_mtd, "mtd", "月至今"), (tab_ytd, "ytd", "年至今")]:
    with tab:
        d = enrich(selected, prefix)
        st.write(f"**{label}營運狀況（示範數據）**")
        m1, m2 = st.columns(2)
        m1.metric("業績", money(d["revenue"]))
        m2.metric("毛利率", f"{d['margin']:.1f}%")
        m3, m4 = st.columns(2)
        m3.metric("毛利額", money(d["gross"]))
        m4.metric("來客數", f"{d['visitors']:,} 人")
        m5, m6 = st.columns(2)
        m5.metric("客單價", money(d["ticket"]))
        m6.metric("業績達成率", f"{d['ach']:.1f}%")
        st.write(f"目標業績：{money(d['target'])}")
        g1, g2, g3 = st.columns(3)
        g1.metric("業績成長", pct_signed(d["rev_g"]))
        g2.metric("毛利額成長", pct_signed(d["gross_g"]))
        g3.metric("來客數成長", pct_signed(d["vis_g"]))
        if d["ach"] >= 100 and d["rev_g"] >= 0:
            st.success("判讀：達成率達標且業績成長，表現穩健。")
        elif d["ach"] >= 100:
            st.info("判讀：達成率達標，但成長動能偏弱，可看來客與客單價哪一邊拖累。")
        elif d["rev_g"] >= 0:
            st.warning("判讀：業績有成長但未達目標，目標或客流仍有缺口。")
        else:
            st.error("判讀：未達目標且業績衰退，建議優先檢視來客數與主力商品。")

# ---------- 下方排行：固定表格，不可點欄位排序 ----------
st.divider()
st.subheader("門市業績排行")
rank_period = st.radio("期間切換", ["月至今 MTD", "年至今 YTD"], horizontal=True, index=0, key="rank_period")
rank_prefix = "mtd" if rank_period.startswith("月至今") else "ytd"
sort_label_to_key = {
    "業績": "revenue", "毛利額": "gross", "毛利率": "margin",
    "來客數": "visitors", "客單價": "ticket",
    "業績成長率": "rev_g", "業績達成率": "ach",
}
sort_label = st.selectbox(
    "排序依據（換了之後排名會重算，第 1 名永遠在最上面）",
    list(sort_label_to_key.keys()), index=0, key="rank_sort",
)
sort_key = sort_label_to_key[sort_label]

rows = []
for _, row in df.iterrows():
    d = enrich(row, rank_prefix)
    rows.append({
        "門市": row["store"], "區域": row["region"],
        "revenue": d["revenue"], "margin": d["margin"], "gross": d["gross"],
        "visitors": d["visitors"], "ticket": d["ticket"],
        "rev_g": d["rev_g"], "gross_g": d["gross_g"], "vis_g": d["vis_g"], "ach": d["ach"],
    })
rank_df = pd.DataFrame(rows).sort_values(sort_key, ascending=False).reset_index(drop=True)
rank_df.insert(0, "排名", range(1, len(rank_df) + 1))
total_rev = float(rank_df["revenue"].sum())
total_gross = float(rank_df["gross"].sum())
total_vis = int(rank_df["visitors"].sum())
total_margin = total_gross / total_rev * 100 if total_rev else 0
st.write(
    f"合計：業績 {money(total_rev)}｜毛利額 {money(total_gross)}｜"
    f"整體毛利率 {total_margin:.1f}%｜來客數 {total_vis:,} 人｜"
    f"目前排序：{sort_label}由高到低，排名已重算"
)

def growth_class(v):
    return "pos" if v >= 0 else "neg"

if is_mobile:
    # 手機版：卡片式排行，不用寬表格、不會橫向溢出，也沒有可點排序的欄位標題
    for _, r in rank_df.iterrows():
        st.markdown(
            f"**第 {int(r['排名'])} 名｜{r['門市']}（{r['區域']}）**  \n"
            f"業績 {money(r['revenue'])}｜毛利率 {r['margin']:.1f}%｜毛利額 {money(r['gross'])}  \n"
            f"來客 {int(r['visitors']):,} 人｜客單價 {money(r['ticket'])}｜達成率 {r['ach']:.1f}%  \n"
            f"成長：業績 {pct_signed(r['rev_g'])}｜毛利 {pct_signed(r['gross_g'])}｜來客 {pct_signed(r['vis_g'])}",
        )
        if st.button(f"看 {r['門市']} 的報告", key=f"rank_btn_{int(r['排名'])}_{rank_prefix}"):
            st.session_state.selected_store = str(r["門市"])
            st.rerun()
        st.divider()
else:
    # 網頁版：固定 HTML 表格，欄位標題不能點、不能排序，排序只靠上方下拉
    html_rows = []
    for _, r in rank_df.iterrows():
        html_rows.append(
            "<tr>"
            f"<td>{int(r['排名'])}</td><td>{r['門市']}</td>"
            f"<td>{money(r['revenue'])}</td><td>{r['margin']:.1f}%</td>"
            f"<td>{money(r['gross'])}</td><td>{int(r['visitors']):,}</td>"
            f"<td>{money(r['ticket'])}</td>"
            f"<td class='{growth_class(r['rev_g'])}'>{pct_signed(r['rev_g'])}</td>"
            f"<td class='{growth_class(r['gross_g'])}'>{pct_signed(r['gross_g'])}</td>"
            f"<td class='{growth_class(r['vis_g'])}'>{pct_signed(r['vis_g'])}</td>"
            f"<td class='{'ach-ok' if r['ach'] >= 100 else 'ach-no'}'>{r['ach']:.1f}%</td>"
            "</tr>"
        )
    st.markdown(
        "<table class='rank-table'><thead><tr>"
        "<th>排名</th><th>門市</th><th>業績</th><th>毛利率</th><th>毛利額</th>"
        "<th>來客數</th><th>客單價</th><th>業績成長</th><th>毛利成長</th><th>來客成長</th><th>達成率</th>"
        "</tr></thead><tbody>" + "".join(html_rows) + "</tbody></table>"
        "<p style='font-size:13px;color:#666;'>這個表格的欄位標題不能點選排序，排序請用上方「排序依據」下拉，排名會跟著重算。</p>",
        unsafe_allow_html=True,
    )
    st.caption("要看某一間的報告，請回到上方地圖點圖釘，或用手機版的門市下拉選擇。")

with st.expander("如何判讀這份報告"):
    st.write(
        "- 先看達成率：是否達到目標；再看成長率：是成長還是衰退。\n"
        "- 業績成長但來客衰退，可能是客單價拉高；來客成長但毛利衰退，可能是毛利率下滑或促銷拉低毛利。\n"
        "- 毛利額 = 業績 × 毛利率，客單價 = 業績 ÷ 來客數，目標業績 = 業績 ÷ 達成率。\n"
        "- 本頁數字皆為示範，重點是欄位邏輯與交叉判讀，不是宣稱公司真實數字。"
    )
st.caption("資料：stores.csv（14 間門市）｜地圖：assets/taiwan-map.jpg｜要換數字請直接改 stores.csv 後重新部署。")
