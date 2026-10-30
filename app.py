"""寵物好事門市營運數據報告 - Streamlit 版 v3（無地圖、左邊選單）
選單（左側，Streamlit sidebar；手機上會自動縮成左上角箭頭，點一下才打開）：
  首頁 / 業績狀況 / 來客狀況 / 促銷品各店銷售業績狀況 / 各店呆滯品項 / 各店滯銷品項
所有營運數字、商品、廠商、庫存皆為作品示範數據，非寵物好事實際營運數據。
資料來源：同目錄的 stores.csv、products.csv、promo_sales.csv、slow_items.csv
定義：
  呆滯品項：超過 90 天未動銷（呆滯天數 >= 91 天）
  滯銷品項：超過 30 天未動銷，但未達呆滯標準（呆滯天數 31-90 天）
  兩者不重複，方便區分處理層級。若你希望滯銷含呆滯，請改 slow 頁的篩選條件。
  業績／來客表的排名：表頭點一下會排序，排序後排名會重算，永遠第 1 名在最上面。
"""
import html as html_lib
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

BASE = Path(__file__).parent

st.set_page_config(
    page_title="寵物好事門市營運數據報告",
    page_icon="🐾",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #FFF8F0; }
    h1, h2, h3 { color: #C62828 !important; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border-radius: 12px; padding: 12px 14px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #FFDAD6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 資料 ----------
@st.cache_data
def load_all():
    stores = pd.read_csv(BASE / "stores.csv")
    products = pd.read_csv(BASE / "products.csv")
    promo = pd.read_csv(BASE / "promo_sales.csv")
    slow = pd.read_csv(BASE / "slow_items.csv")
    return stores, products, promo, slow

stores_df, products_df, promo_df, slow_df = load_all()
prod_map = products_df.set_index("sku").to_dict("index")

def enrich(row, prefix):
    rev = float(row[f"{prefix}_revenue"])
    margin = float(row[f"{prefix}_margin_pct"])
    vis = int(row[f"{prefix}_visitors"])
    gross = rev * margin / 100.0
    ticket = rev / vis if vis else 0
    ach = float(row[f"{prefix}_achievement_pct"])
    target = rev / (ach / 100.0) if ach else 0
    return {
        "revenue": rev, "margin": margin, "gross": gross, "visitors": vis,
        "ticket": ticket, "target": target, "ach": ach,
        "rev_g": float(row[f"{prefix}_rev_growth_pct"]),
        "gross_g": float(row[f"{prefix}_gross_growth_pct"]),
        "vis_g": float(row[f"{prefix}_visitor_growth_pct"]),
    }

def money(x):
    return f"NT$ {x:,.0f}"

def pct_signed(x):
    return f"{x:+.1f}%"

def pct_plain(x):
    return f"{x:.1f}%"

# 全台 YTD 總計（加權成長率：以業績／來客數加權）
ytd_rows = [enrich(r, "ytd") for _, r in stores_df.iterrows()]
ytd_total_rev = sum(d["revenue"] for d in ytd_rows)
ytd_total_gross = sum(d["gross"] for d in ytd_rows)
ytd_total_vis = sum(d["visitors"] for d in ytd_rows)
ytd_total_target = sum(d["target"] for d in ytd_rows)
ytd_ach = ytd_total_rev / ytd_total_target * 100 if ytd_total_target else 0
ytd_margin = ytd_total_gross / ytd_total_rev * 100 if ytd_total_rev else 0
ytd_rev_g = sum(d["rev_g"] * d["revenue"] for d in ytd_rows) / ytd_total_rev if ytd_total_rev else 0
ytd_vis_g = sum(d["vis_g"] * d["visitors"] for d in ytd_rows) / ytd_total_vis if ytd_total_vis else 0

# ---------- 左邊選單（手機上 Streamlit 會自動縮成左上角箭頭，點一下打開） ----------
with st.sidebar:
    st.markdown("## 🐾 寵物好事")
    st.caption("門市營運數據報告（作品示範）")
    page = st.radio(
        "頁面選單",
        ["首頁", "業績狀況", "來客狀況", "促銷品各店銷售業績狀況", "各店呆滯品項", "各店滯銷品項"],
        index=0,
    )
    st.divider()
    st.warning("本頁所有數字、商品、廠商、庫存皆為作品示範數據，非公司實際數據。")
    st.caption("手機版：左上角箭頭點一下，選單就會打開；選完頁面後選單會再收起來。")

st.markdown("<h1>🐾 寵物好事-貓の專門店｜門市營運數據報告</h1>", unsafe_allow_html=True)

# ---------- 可點表頭排序的 HTML 表格：排序後排名重算 ----------
def sortable_table(table_id, headers, rows, numeric_idx):
    """headers: 顯示文字 list；rows: list of list，每格是 (顯示文字, 排序用數值或文字)。
    第 0 欄是排名，表頭不可點；其他欄點一下先由大到小排，再點一下由小到大排，排完排名重算 1..n。"""
    th_html = []
    for i, h in enumerate(headers):
        if i == 0:
            th_html.append(f"<th>{html_lib.escape(h)}</th>")
        else:
            th_html.append(
                f"<th onclick=\"sortTable('{table_id}', {i}, {str(i in numeric_idx).lower()})\" "
                f"title=\"點一下排序\">{html_lib.escape(h)} <span class='arrow'></span></th>"
            )
    tr_html = []
    for row in rows:
        tds = []
        for j, (disp, sort_val) in enumerate(row):
            tds.append(f"<td data-sort=\"{html_lib.escape(str(sort_val))}\">{disp}</td>")
        tr_html.append("<tr>" + "".join(tds) + "</tr>")
    html_doc = f"""
    <style>
      .wrap {{ overflow-x: auto; }}
      table {{ border-collapse: collapse; width: 100%; min-width: 1050px; font-size: 14px; }}
      th {{ background: #C62828; color: #fff; padding: 8px 6px; text-align: right; cursor: pointer; white-space: nowrap; }}
      th:first-child {{ cursor: default; text-align: center; }}
      td:first-child {{ text-align: center; font-weight: 700; }}
      td:nth-child(2) {{ text-align: left; font-weight: 600; white-space: nowrap; }}
      td {{ padding: 7px 6px; text-align: right; border-bottom: 1px solid #F0D9D5; background: #fff; white-space: nowrap; }}
      tr:nth-child(even) td {{ background: #FFF3F0; }}
      .pos {{ color: #2E7D32; font-weight: 700; }}
      .neg {{ color: #C62828; font-weight: 700; }}
    </style>
    <div class="wrap"><table id="{table_id}"><thead><tr>{"".join(th_html)}</tr></thead>
    <tbody>{"".join(tr_html)}</tbody></table></div>
    <script>
    function sortTable(tableId, colIdx, isNumeric) {{
      const table = document.getElementById(tableId);
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const ths = table.querySelectorAll('th');
      const th = ths[colIdx];
      const prevDir = th.getAttribute('data-dir') || 'asc';
      const newDir = prevDir === 'desc' ? 'asc' : 'desc';
      ths.forEach(h => {{ h.removeAttribute('data-dir'); const a = h.querySelector('.arrow'); if (a) a.textContent = ''; }});
      th.setAttribute('data-dir', newDir);
      const arrow = th.querySelector('.arrow'); if (arrow) arrow.textContent = newDir === 'desc' ? ' ▼' : ' ▲';
      rows.sort((a, b) => {{
        let av = a.cells[colIdx].getAttribute('data-sort');
        let bv = b.cells[colIdx].getAttribute('data-sort');
        if (isNumeric) {{
          av = parseFloat(av); bv = parseFloat(bv);
          if (isNaN(av)) av = -Infinity; if (isNaN(bv)) bv = -Infinity;
        }}
        if (av < bv) return newDir === 'desc' ? 1 : -1;
        if (av > bv) return newDir === 'desc' ? -1 : 1;
        return 0;
      }});
      rows.forEach((r, i) => {{ tbody.appendChild(r); r.cells[0].textContent = i + 1; }});
    }}
    </script>
    <p style="font-size:13px;color:#666;">點表頭可排序（第一次點由大到小，再點一下由小到大），排序後排名會重算，第 1 名永遠在最上面；排名欄本身不可點。</p>
    """
    return html_doc

def coloured_pct(v):
    cls = "pos" if v >= 0 else "neg"
    return f"<span class='{cls}'>{pct_signed(v)}</span>"

# ================= 首頁 =================
if page == "首頁":
    st.subheader("營運總表（年至今 YTD）")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全台總營業額（年至今）", money(ytd_total_rev))
    c2.metric("營業額達成率", pct_plain(ytd_ach))
    c3.metric("營業額成長率（加權）", pct_signed(ytd_rev_g))
    c4.metric("毛利率", pct_plain(ytd_margin))
    c5, c6, c7 = st.columns(3)
    c5.metric("毛利額", money(ytd_total_gross))
    c6.metric("來客數", f"{ytd_total_vis:,} 人")
    c7.metric("來客數成長率（加權）", pct_signed(ytd_vis_g))
    st.caption(f"目標營業額合計：{money(ytd_total_target)}｜毛利額 = 業績 × 毛利率｜成長率為各店以業績／來客數加權平均，僅作示範彙總。")

    # 達成率排序：前三、後二
    ach_sorted = sorted(
        [(r["store"], enrich(r, "ytd")) for _, r in stores_df.iterrows()],
        key=lambda x: x[1]["ach"], reverse=True,
    )
    st.subheader("目前營業額達成率前三名")
    top3 = pd.DataFrame([
        {"排名": i + 1, "門市": name, "年至今業績": money(d["revenue"]),
         "達成率": pct_plain(d["ach"]), "目標業績": money(d["target"]), "毛利率": pct_plain(d["margin"])}
        for i, (name, d) in enumerate(ach_sorted[:3])
    ])
    st.table(top3)
    st.subheader("目前營業額達成率最後兩名")
    last2 = pd.DataFrame([
        {"排名": len(ach_sorted) - 1 + i, "門市": name, "年至今業績": money(d["revenue"]),
         "達成率": pct_plain(d["ach"]), "目標業績": money(d["target"]), "毛利率": pct_plain(d["margin"])}
        for i, (name, d) in enumerate(ach_sorted[-2:])
    ])
    st.table(last2)
    st.caption("最後兩名的排名是 13、14 名（共 14 間門市，依達成率由高到低排）。")

    st.subheader("全台營運總表（年至今，依達成率由高到低）")
    total_rows = []
    for i, (name, d) in enumerate(ach_sorted):
        total_rows.append({
            "排名": i + 1, "門市": name, "年至今業績": money(d["revenue"]),
            "達成率": pct_plain(d["ach"]), "業績成長率": pct_signed(d["rev_g"]),
            "毛利率": pct_plain(d["margin"]), "毛利額": money(d["gross"]),
            "來客數": f"{d['visitors']:,}", "客單價": money(d["ticket"]),
        })
    st.table(pd.DataFrame(total_rows))

# ================= 業績狀況 =================
elif page == "業績狀況":
    st.subheader("各店營業表現數據")
    st.caption("表頭點一下可排序，第一次點由大到小，再點一下由小到大；排序後排名會重算，第 1 名永遠在最上面。")
    headers = ["排名", "門市", "月至今業績", "月至今毛利率", "月至今毛利額", "月至今達成率",
               "年至今業績", "年至今毛利率", "年至今毛利額", "年至今來客數",
               "年至今業績成長率", "年至今毛利成長率", "年至今達成率"]
    numeric_idx = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
    # 初始：年至今業績由高到低
    ordered = sorted(stores_df.iterrows(), key=lambda x: enrich(x[1], "ytd")["revenue"], reverse=True)
    rows = []
    for i, (_, r) in enumerate(ordered, start=1):
        m = enrich(r, "mtd"); y = enrich(r, "ytd")
        rows.append([
            (str(i), i), (html_lib.escape(str(r["store"])), str(r["store"])),
            (money(m["revenue"]), m["revenue"]), (pct_plain(m["margin"]), m["margin"]),
            (money(m["gross"]), m["gross"]), (pct_plain(m["ach"]), m["ach"]),
            (money(y["revenue"]), y["revenue"]), (pct_plain(y["margin"]), y["margin"]),
            (money(y["gross"]), y["gross"]), (f"{y['visitors']:,}", y["visitors"]),
            (coloured_pct(y["rev_g"]), y["rev_g"]), (coloured_pct(y["gross_g"]), y["gross_g"]),
            (pct_plain(y["ach"]), y["ach"]),
        ])
    components.html(sortable_table("sales_table", headers, rows, numeric_idx), height=640, scrolling=True)

# ================= 來客狀況 =================
elif page == "來客狀況":
    st.subheader("各店來客表現數據")
    st.caption("表頭點一下可排序，排序後排名會重算，第 1 名永遠在最上面。來客佔比 = 該店年至今來客數 ÷ 全台年至今來客數。")
    headers = ["排名", "門市", "月至今來客數", "月至今來客成長率",
               "年至今來客數", "年至今來客成長率", "年至今客單價", "來客佔全台比", "年至今業績", "年至今業績成長率"]
    numeric_idx = {2, 3, 4, 5, 6, 7, 8, 9}
    ordered = sorted(stores_df.iterrows(), key=lambda x: enrich(x[1], "ytd")["visitors"], reverse=True)
    rows = []
    for i, (_, r) in enumerate(ordered, start=1):
        m = enrich(r, "mtd"); y = enrich(r, "ytd")
        share = y["visitors"] / ytd_total_vis * 100 if ytd_total_vis else 0
        rows.append([
            (str(i), i), (html_lib.escape(str(r["store"])), str(r["store"])),
            (f"{m['visitors']:,}", m["visitors"]), (coloured_pct(m["vis_g"]), m["vis_g"]),
            (f"{y['visitors']:,}", y["visitors"]), (coloured_pct(y["vis_g"]), y["vis_g"]),
            (money(y["ticket"]), y["ticket"]), (pct_plain(share), share),
            (money(y["revenue"]), y["revenue"]), (coloured_pct(y["rev_g"]), y["rev_g"]),
        ])
    components.html(sortable_table("visitor_table", headers, rows, numeric_idx), height=640, scrolling=True)

# ================= 促銷品 =================
elif page == "促銷品各店銷售業績狀況":
    st.subheader("促銷品各店銷售業績狀況")
    promo_merged = promo_df.merge(products_df, on="sku", how="left")
    promo_total_rev = int(promo_merged["promo_revenue"].sum())
    promo_total_qty = int(promo_merged["promo_qty"].sum())
    c1, c2, c3 = st.columns(3)
    c1.metric("全台促銷總業績", money(promo_total_rev))
    c2.metric("全台促銷總數量", f"{promo_total_qty:,} 件")
    c3.metric("促銷佔年至今業績比", pct_plain(promo_total_rev / ytd_total_rev * 100 if ytd_total_rev else 0))
    st.caption("促銷業績為示範期間內的促銷商品銷售合計，佔比 = 全台促銷總業績 ÷ 全台年至今業績。")

    st.subheader("全台賣最好的 TOP5 商品（依促銷業績）")
    overall = (promo_merged.groupby(["sku", "product_name", "vendor_name", "category"], as_index=False)
               .agg(促銷數量=("promo_qty", "sum"), 促銷業績=("promo_revenue", "sum"))
               .sort_values("促銷業績", ascending=False).head(5).reset_index(drop=True))
    overall.insert(0, "排名", range(1, len(overall) + 1))
    overall["促銷業績"] = overall["促銷業績"].map(money)
    overall["促銷數量"] = overall["促銷數量"].map(lambda x: f"{int(x):,}")
    overall.columns = ["排名", "貨號", "商品名稱", "廠商名稱", "類別", "促銷數量", "促銷業績"]
    st.table(overall)

    st.subheader("各店業績排名與該店賣最好的 TOP5 商品")
    st.caption("各店先依年至今業績由高到低排（排名固定），點開每一間可以看到該店的 TOP5。")
    store_rank = sorted(stores_df.iterrows(), key=lambda x: enrich(x[1], "ytd")["revenue"], reverse=True)
    for rank, (_, r) in enumerate(store_rank, start=1):
        y = enrich(r, "ytd")
        store_promo = promo_merged[promo_merged["store"] == r["store"]].sort_values("promo_revenue", ascending=False).head(5)
        store_promo_total = int(promo_merged[promo_merged["store"] == r["store"]]["promo_revenue"].sum())
        with st.expander(f"第 {rank} 名｜{r['store']}｜年至今業績 {money(y['revenue'])}｜本店促銷業績 {money(store_promo_total)}"):
            t = pd.DataFrame([
                {"排名": i + 1, "貨號": prow["sku"], "商品名稱": prow["product_name"],
                 "廠商名稱": prow["vendor_name"], "促銷數量": f"{int(prow['promo_qty']):,}",
                 "促銷業績": money(int(prow["promo_revenue"]))}
                for i, (_, prow) in enumerate(store_promo.iterrows())
            ])
            st.table(t)

# ================= 呆滯 / 滯銷（共用邏輯） =================
elif page in ["各店呆滯品項", "各店滯銷品項"]:
    is_stagnant = page == "各店呆滯品項"
    if is_stagnant:
        st.subheader("各店呆滯品項")
        st.caption("呆滯定義：超過 90 天未動銷（呆滯天數 >= 91 天），依呆滯天數由長到短排。")
        filt = slow_df["days_since_last_sale"] >= 91
        threshold_text = "呆滯天數 >= 91 天"
    else:
        st.subheader("各店滯銷品項")
        st.caption("滯銷定義：超過 30 天未動銷，但未達呆滯標準（呆滯天數 31-90 天），依呆滯天數由長到短排；兩張表不重複，方便分層處理。")
        filt = (slow_df["days_since_last_sale"] >= 31) & (slow_df["days_since_last_sale"] <= 90)
        threshold_text = "呆滯天數 31-90 天"
    store_choice = st.selectbox("點選店別切換數據", list(stores_df["store"]), index=0)
    merged = slow_df.merge(products_df, on="sku", how="left")
    sub = merged[(merged["store"] == store_choice) & filt].sort_values("days_since_last_sale", ascending=False)
    st.write(f"**{store_choice}｜{threshold_text}｜共 {len(sub)} 項｜庫存金額合計 {money(int(sub['stock_amount'].sum())) if len(sub) else money(0)}**")
    if len(sub) == 0:
        st.info("這間店在這個區間目前沒有品項。")
    else:
        t = pd.DataFrame([
            {"貨號": prow["sku"], "商品名稱": prow["product_name"], "廠商名稱": prow["vendor_name"],
             "廠商編號": prow["vendor_code"], "呆滯天數": int(prow["days_since_last_sale"]),
             "庫存": int(prow["stock_qty"]), "庫存金額": money(int(prow["stock_amount"]))}
            for _, prow in sub.iterrows()
        ])
        st.table(t)
    st.caption("庫存金額為示範值（庫存數量 × 示範單位成本），要換成實際成本請改 slow_items.csv 的 stock_amount 欄位。")
