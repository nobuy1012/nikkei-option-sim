import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------------------------------------------------
# 1. ページ設定とCSSデザイン
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="OpSim Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSSの適用
st.markdown("""
<style>
    /* タイトルスタイル */
    .pro-title {
        font-family: "Helvetica Neue", Arial, sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        color: #333;
        border-bottom: 4px solid #d4af37; /* 金色の下線 */
        padding-bottom: 10px;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }
    .pro-subtitle {
        color: #d4af37;
        font-size: 1.2rem;
    }
    
    /* スプレッドシート風テーブルのスタイル補正 */
    .dataframe {
        font-family: "Courier New", monospace !important;
    }
    
    /* サイドバーのアコーディオン調整 */
    .st-emotion-cache-16idsys p {
        font-size: 14px;
        font-weight: bold;
    }
    
    /* メインエリアのパディング調整 */
    .block-container {
        padding-top: 2rem;
    }
    
    /* 損益の文字色定義（Pandas Stylerで使用するが念のためクラス定義） */
    .profit-text { color: #0056b3; font-weight: bold; }
    .loss-text { color: #d9534f; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# タイトル表示
st.markdown('<div class="pro-title">OpSim Pro <span class="pro-subtitle">| 日経225戦略マスター</span></div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. サイドバー：入力エリア
# -----------------------------------------------------------------------------
st.sidebar.header("⚙️ 設定・ポジション入力")

# 基本設定
base_price = st.sidebar.number_input("基準価格 (円)", value=38000, step=100)
unit_select = st.sidebar.radio("取引単位", ["ラージ (x1000)", "ミニ (x100)"], horizontal=True)
multiplier = 1000 if "ラージ" in unit_select else 100

# ポジションデータ格納用リスト
all_positions = []
groups_metadata = [] # 資金計算用（グループごとのポジションリスト）

# 入力グループ生成 (1〜14組)
for i in range(1, 15):
    # 第1組のみデフォルトで展開
    is_expanded = (i == 1)
    
    with st.sidebar.expander(f"第{i}組 ポジション", expanded=is_expanded):
        # 幅 (Spread) 設定
        spread = st.number_input(f"第{i}組 幅 (Spread)", value=500, step=125, key=f"g{i}_spread")
        
        # デフォルト値の計算ロジック
        # 1行目: Call 買い (基準 + 幅)
        # 2行目: Call 売り (基準 + 幅*2)
        # 3行目: Put 売り (基準 - 幅*2)
        # 4行目: Put 買い (基準 - 幅)
        defaults = [
            {"type": "Call", "side": "Buy",  "strike": base_price + spread},
            {"type": "Call", "side": "Sell", "strike": base_price + spread * 2},
            {"type": "Put",  "side": "Sell", "strike": base_price - spread * 2},
            {"type": "Put",  "side": "Buy",  "strike": base_price - spread},
        ]

        group_positions = []
        
        # 4つのスロット生成
        for slot in range(4):
            cols = st.columns([1.2, 1.2, 1.5, 1.0, 1.2]) # レイアウト調整
            
            d_val = defaults[slot]
            
            # 各項目の入力ウィジェット
            # キーを一意にするために f"g{i}_s{slot}_..." を使用
            with cols[0]:
                p_type = st.selectbox("", ["Call", "Put"], index=0 if d_val["type"]=="Call" else 1, key=f"g{i}_s{slot}_type", label_visibility="collapsed")
            with cols[1]:
                p_side = st.selectbox("", ["Buy", "Sell"], index=0 if d_val["side"]=="Buy" else 1, key=f"g{i}_s{slot}_side", label_visibility="collapsed")
            with cols[2]:
                # デフォルトStrikeはSpread変更時に連動させたいが、ユーザー編集も許容するためvalueに計算値をセット
                # ここでは簡易的に、Spreadが変わると再計算されるStreamlitの仕様を利用
                calc_strike = base_price + spread if slot == 0 else (base_price + spread*2 if slot == 1 else (base_price - spread*2 if slot == 2 else base_price - spread))
                p_strike = st.number_input("", value=calc_strike, step=125, key=f"g{i}_s{slot}_strike", label_visibility="collapsed")
            with cols[3]:
                p_qty = st.number_input("", value=0, min_value=0, step=1, key=f"g{i}_s{slot}_qty", label_visibility="collapsed", help="枚数")
            with cols[4]:
                p_prem = st.number_input("", value=0, step=5, key=f"g{i}_s{slot}_prem", label_visibility="collapsed", help="プレミアム単価")

            # 有効なポジション（枚数 > 0）をリストに追加
            if p_qty > 0:
                pos_data = {
                    "group": i,
                    "type": p_type,
                    "side": p_side,
                    "strike": p_strike,
                    "qty": p_qty,
                    "premium": p_prem,
                    "multiplier": multiplier
                }
                all_positions.append(pos_data)
                group_positions.append(pos_data)
        
        groups_metadata.append(group_positions)

# -----------------------------------------------------------------------------
# 3. 計算ロジック
# -----------------------------------------------------------------------------

def calculate_single_pos_pnl(price, pos):
    """単一ポジションの特定価格における損益を計算"""
    strike = pos["strike"]
    premium = pos["premium"]
    qty = pos["qty"]
    mult = pos["multiplier"]
    
    intrinsic_value = 0
    if pos["type"] == "Call":
        intrinsic_value = max(price - strike, 0)
    else: # Put
        intrinsic_value = max(strike - price, 0)
        
    if pos["side"] == "Buy":
        # 買い: (本質的価値 - 支払プレミアム) * 枚数 * 倍率
        return (intrinsic_value - premium) * qty * mult
    else:
        # 売り: (受取プレミアム - 本質的価値) * 枚数 * 倍率
        return (premium - intrinsic_value) * qty * mult

def calculate_group_max_loss(group_pos_list, multiplier):
    """
    グループごとの最大損失額（投下資金）を簡易シミュレーションで算出
    範囲: 0円 〜 60,000円 (広範囲でチェック)
    """
    if not group_pos_list:
        return 0
    
    # チェックする価格帯
    check_prices = list(range(1000, 60000, 500)) 
    # ストライク価格周辺も念入りにチェック
    for p in group_pos_list:
        check_prices.append(p["strike"])
        check_prices.append(p["strike"] + 1)
        check_prices.append(p["strike"] - 1)
    
    check_prices = sorted(list(set(check_prices)))
    
    min_pnl = float('inf')
    
    for price in check_prices:
        pnl_sum = 0
        for pos in group_pos_list:
            pnl_sum += calculate_single_pos_pnl(price, pos)
        if pnl_sum < min_pnl:
            min_pnl = pnl_sum
            
    # 損失なので負の値を正の「必要資金」として返す（損失がない場合は0）
    return abs(min_pnl) if min_pnl < 0 else 0

# -----------------------------------------------------------------------------
# 4. メイン画面上部：資金管理・調整エリア
# -----------------------------------------------------------------------------

# 投下資金（最大損失合計）の計算
total_invested_capital = 0
for g_pos in groups_metadata:
    total_invested_capital += calculate_group_max_loss(g_pos, multiplier)

cols_fund = st.columns(3)

with cols_fund[0]:
    st.metric(label="💰 投下資金 (最大リスク合計)", value=f"{total_invested_capital:,} 円")

with cols_fund[1]:
    adj_profit = st.number_input("📈 コール売り (利益調整)", value=0, step=1000, help="早見表全体にプラスします")

with cols_fund[2]:
    adj_loss = st.number_input("📉 損切り (損失調整)", value=0, step=1000, help="早見表全体からマイナスします")

st.divider()

# -----------------------------------------------------------------------------
# 5. メイン画面：損益早見表
# -----------------------------------------------------------------------------
st.subheader("📊 損益早見表")

# シミュレーション範囲の設定 (基準価格 ± 3000円程度)
price_min = max(0, base_price - 3000)
price_max = base_price + 3000
price_step = 100 # 刻み幅

prices = range(price_min, price_max + price_step, price_step)
results = []

for p in prices:
    gross_pnl = 0
    for pos in all_positions:
        gross_pnl += calculate_single_pos_pnl(p, pos)
    
    # 調整額の反映
    net_pnl = gross_pnl + adj_profit - adj_loss
    results.append({"日経平均価格": p, "損益額": net_pnl})

df_result = pd.DataFrame(results)

# スタイリング用関数
def color_pnl(val):
    """損益の色分け: プラスは青・太字、マイナスは赤・太字"""
    if val > 0:
        return 'color: #0056b3; font-weight: bold;'
    elif val < 0:
        return 'color: #d9534f; font-weight: bold;'
    else:
        return 'color: #333;'

def format_currency(val):
    return f"{int(val):,}"

if not df_result.empty:
    # インデックスを日経平均価格に設定して見やすくする
    df_display = df_result.set_index("日経平均価格")
    
    # Pandas Stylerによるデザイン適用
    styler = df_display.style\
        .format("{:,}")\
        .applymap(color_pnl)\
        .bar(subset=["損益額"], align='zero', color=['#ffb3b3', '#b3d9ff'], width=90)\
        .set_table_styles([
            # ヘッダーデザイン: 薄い黄色背景
            {'selector': 'th', 'props': [
                ('background-color', '#fff2cc'),
                ('color', 'black'),
                ('font-weight', 'bold'),
                ('border', '1px solid #ddd'),
                ('text-align', 'center')
            ]},
            # セルデザイン: 罫線
            {'selector': 'td', 'props': [
                ('border', '1px solid #eee'),
                ('text-align', 'right'),
                ('padding', '8px')
            ]},
            # 全体
            {'selector': 'table', 'props': [
                ('width', '100%'),
                ('border-collapse', 'collapse')
            ]}
        ])

    st.dataframe(styler, height=600, use_container_width=True)
else:
    st.info("サイドバーからポジションを入力してください。")

# -----------------------------------------------------------------------------
# 6. メイン画面下部：ポジション一覧
# -----------------------------------------------------------------------------
st.subheader("📝 現在のポジション一覧")

if all_positions:
    df_pos = pd.DataFrame(all_positions)
    # 表示用にカラム名を日本語化・整理
    df_pos_display = df_pos[["group", "type", "side", "strike", "qty", "premium"]].copy()
    df_pos_display.columns = ["組", "Call/Put", "売買", "権利行使価格", "枚数", "プレミアム"]
    
    # 見やすいようにスタイリング
    st.dataframe(
        df_pos_display, 
        use_container_width=True,
        column_config={
            "組": st.column_config.NumberColumn("Group", format="%d組"),
            "権利行使価格": st.column_config.NumberColumn("Strike", format="%d円"),
            "プレミアム": st.column_config.NumberColumn("Premium", format="%d円"),
        },
        hide_index=True
    )
else:
    st.text("有効なポジションはありません（枚数0）")
