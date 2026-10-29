"""寵物好事門市營運數據報告 - Streamlit 版
用法：把這個資料夾整個上傳到 GitHub，根目錄要有 app.py，
再到 Streamlit Cloud 選這個 repo、主檔案選 app.py 部署即可。
所有營運數字皆為作品示範數據，非寵物好事實際營運數據。
資料來源：同目錄的 stores.csv，改 CSV 後重新部署就會更新。
"""
import io
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
MAP_PATH = BASE / "assets" / "taiwan-map.jpg"
CSV_PATH = BASE / "stores.csv"

st.set_page_config(
    page_title="寵物好事門市營運數據報告",
    page_icon="🐾",
    layout="wide",
)

# ---------- 資料 ----------
@st.cache_data
def load_stores():
    df = pd.read_csv(CSV_PATH)
    return df

df = load_stores()

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
    visitors = float(row[c["visitors"]])
    gross = revenue * margin / 100.0
    ticket = revenue / visitors if visitors else 0
    target = revenue / (float(row[c["ach"]]) / 100.0) if float(row[c["ach"]]) else 0
    return {
        "revenue": revenue,
        "margin": margin,
        "gross": gross,
        "visitors": int(visitors),
        "ticket": ticket,
        "target": target,
        "rev_g": float(row[c["rev_g"]]),
        "gross_g": float(row[c["gross_g"]]),
        "vis_g": float(row[c["vis_g"]]),
        "ach": float(row[c["ach"]]),
    }

def money(x):
    return f"NT$ {x:,.0f}"

def pct(x):
    return f"{x:+.1f}%" if x != 0 else "0.0%"

# ---------- 地圖圖釘 ----------
# 台灣全圖的概略線性換算（只用來在示意圖上定位，不是精確地理底圖）
# lat 25.35 -> y 0.02，lat 21.90 -> y 0.98；lon 119.90 -> x 0.05，lon 122.00 -> x 0.95
def latlon_to_xy(lat, lon):
    x = 0.05 + (lon - 119.90) / (122.00 - 119.90) * 0.90
    y = 0.02 + (25.35 - lat) / (25.35 - 21.90) * 0.96
    return x, y

# 台中密集區在全圖上適度展開的位移（分數），真實位置仍以小圓點標示並以引線連接
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

def draw_map(stores_df):
    img = Image.open(MAP_PATH).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
        small_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        small_font = font
    for idx, (_, row) in enumerate(stores_df.iterrows(), start=1):
        x, y = latlon_to_xy(float(row["lat"]), float(row["lon"]))
        dx, dy = DISPLAY_OFFSETS.get(row["store"], (0, 0))
        px, py = int(x * w), int(y * h)
        qx, qy = int((x + dx) * w), int((y + dy) * h)
        # 引線（只有位移的店才畫）
        if dx != 0 or dy != 0:
            draw.line([(px, py), (qx, qy)], fill=(229, 57, 53), width=2)
            draw.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(229, 57, 53), outline=(255, 255, 255), width=2)
        # 編號圖釘
        r = 17
        draw.ellipse([qx - r, qy - r, qx + r, qy + r], fill=(229, 57, 53), outline=(255, 255, 255), width=3)
        label = str(idx)
        bbox = draw.textbbox((0, 0), label, font=small_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((qx - tw / 2, qy - th / 2 - 1), label, fill=(255, 255, 255), font=small_font)
    return img

# ---------- 頁面 ----------
st.markdown(
    "<h1 style='color:#C62828;'>🐾 寵物好事-貓の專門店｜門市營運數據報告</h1>",
    unsafe_allow_html=True,
)
st.warning("本頁所有營運數字皆為作品示範數據，非寵物好事實際營運數據，僅用來展示營運數字的整理架構。")
st.caption("左側選單選門市，右側看該店報告；下方排行可切換月至今／年至今。台中密集區圖釘有適度展開，復中店為東區概略位置。")

# 側邊選單（對應原網頁右側選單）
with st.sidebar:
    st.header("門市選單")
    region = st.radio("區域篩選", ["全部", "北部", "中部"], index=0)
    filtered = df if region == "全部" else df[df["region"] == region]
    # 用編號 + 店名對應地圖圖釘編號（編號以原始 14 間順序為準）
    df_with_no = df.reset_index(drop=True)
    df_with_no["no"] = df_with_no.index + 1
    filtered_with_no = df_with_no[df_with_no["store"].isin(filtered["store"])]
    options = [f"{int(r['no'])}. {r['store']}" for _, r in filtered_with_no.iterrows()]
    choice = st.radio("選擇門市", options, index=0)
    selected_no = int(choice.split(".")[0])
    selected = df_with_no[df_with_no["no"] == selected_no].iloc[0]

# 全台合計
mtd_total_rev = float(df["mtd_revenue"].sum())
ytd_total_rev = float(df["ytd_revenue"].sum())
mtd_total_vis = int(df["mtd_visitors"].sum())
ytd_total_vis = int(df["ytd_visitors"].sum())
mtd_total_gross = float((df["mtd_revenue"] * df["mtd_margin_pct"] / 100).sum())
ytd_total_gross = float((df["ytd_revenue"] * df["ytd_margin_pct"] / 100).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("全台月至今業績", money(mtd_total_rev))
c2.metric("全台月至今毛利額", money(mtd_total_gross))
c3.metric("全台月至今來客數", f"{mtd_total_vis:,} 人")
c4.metric("全台年至今業績", money(ytd_total_rev))

# 中間地圖 + 右側報告
map_col, detail_col = st.columns([1.15, 1])
with map_col:
    st.subheader("台灣門市地圖")
    try:
        map_img = draw_map(df)
        st.image(map_img, caption="圖釘編號對應下方門市編號，台中密集區以引線展開顯示。", use_container_width=True)
    except FileNotFoundError:
        st.error("找不到 assets/taiwan-map.jpg，請確認上傳時有保留 assets 資料夾。")
    st.markdown("**圖釘編號對照**")
    legend = df_with_no[["no", "store", "address", "region"]].copy()
    legend.columns = ["編號", "門市", "地址", "區域"]
    st.dataframe(legend, hide_index=True, use_container_width=True)

with detail_col:
    st.subheader(f"{selected['store']}")
    st.write(f"📍 {selected['address']}")
    if str(selected["note"]).strip():
        st.write(f"備註：{selected['note']}")
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
            st.write("成長率")
            g1, g2, g3 = st.columns(3)
            g1.metric("業績成長", pct(d["rev_g"]))
            g2.metric("毛利額成長", pct(d["gross_g"]))
            g3.metric("來客數成長", pct(d["vis_g"]))
            # 簡單判讀
            if d["ach"] >= 100 and d["rev_g"] >= 0:
                st.success("判讀：達成率達標且業績成長，表現穩健。")
            elif d["ach"] >= 100:
                st.info("判讀：達成率達標，但成長動能偏弱，可看來客與客單價哪一邊拖累。")
            elif d["rev_g"] >= 0:
                st.warning("判讀：業績有成長但未達目標，目標或客流仍有缺口。")
            else:
                st.error("判讀：未達目標且業績衰退，建議優先檢視來客數與主力商品。")

# 下方排行
st.divider()
st.subheader("門市業績排行")
period = st.radio("期間切換", ["月至今 MTD", "年至今 YTD"], horizontal=True, index=0)
prefix = "mtd" if period.startswith("月至今") else "ytd"
rows = []
for _, row in df.iterrows():
    d = enrich(row, prefix)
    rows.append({
        "門市": row["store"],
        "區域": row["region"],
        "業績": d["revenue"],
        "毛利率": d["margin"],
        "毛利額": d["gross"],
        "來客數": d["visitors"],
        "客單價": d["ticket"],
        "業績成長率": d["rev_g"],
        "毛利額成長率": d["gross_g"],
        "來客數成長率": d["vis_g"],
        "業績達成率": d["ach"],
    })
rank_df = pd.DataFrame(rows).sort_values("業績", ascending=False).reset_index(drop=True)
rank_df.insert(0, "排名", range(1, len(rank_df) + 1))
# 合計列
total_rev = rank_df["業績"].sum()
total_gross = rank_df["毛利額"].sum()
total_vis = rank_df["來客數"].sum()
total_margin = total_gross / total_rev * 100 if total_rev else 0
st.write(
    f"合計：業績 {money(total_rev)}｜毛利額 {money(total_gross)}｜"
    f"整體毛利率 {total_margin:.1f}%｜來客數 {total_vis:,} 人"
)
display = rank_df.copy()
display["業績"] = display["業績"].map(money)
display["毛利率"] = display["毛利率"].map(lambda x: f"{x:.1f}%")
display["毛利額"] = display["毛利額"].map(money)
display["來客數"] = display["來客數"].map(lambda x: f"{x:,}")
display["客單價"] = display["客單價"].map(money)
for col in ["業績成長率", "毛利額成長率", "來客數成長率"]:
    display[col] = display[col].map(pct)
display["業績達成率"] = display["業績達成率"].map(lambda x: f"{x:.1f}%")
st.dataframe(display, hide_index=True, use_container_width=True)

with st.expander("如何判讀這份報告"):
    st.write(
        "- 先看達成率：是否達到目標；再看成長率：是成長還是衰退。\n"
        "- 業績成長但來客衰退，可能是客單價拉高；來客成長但毛利衰退，可能是毛利率下滑或促銷拉低毛利。\n"
        "- 毛利額 = 業績 × 毛利率，客單價 = 業績 ÷ 來客數，目標業績 = 業績 ÷ 達成率。\n"
        "- 本頁數字皆為示範，重點是欄位邏輯與交叉判讀，不是宣稱公司真實數字。"
    )
st.caption("資料：stores.csv（14 間門市）｜地圖：assets/taiwan-map.jpg｜要換數字請直接改 stores.csv 後重新部署。")
