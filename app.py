import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from io import BytesIO

# --------------------------
# iOS 极致风格
# --------------------------
st.set_page_config(
    page_title="跨境电商数据分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def add_ios_style():
    st.markdown("""
    <style>
    .stApp { background-color: #F2F2F7; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E5E5EA; }
    .ios-card {
        background: rgba(255,255,255,0.9);
        backdrop-filter: blur(20px);
        border-radius: 16px; padding:20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        margin-bottom:20px;
    }
    .stButton>button {
        background-color:#007AFF; color:white; border:none;
        border-radius:12px; padding:10px 18px; font-weight:500;
    }
    .stButton>button:hover { background-color:#0051D5; transform:translateY(-1px); }
    .metric-card {
        background:#fff; border-radius:14px; padding:18px; text-align:center;
        box-shadow:0 1px 3px rgba(0,0,0,0.06);
    }
    .alert-card {
        background:#FFF6F6; border:1px solid #FF3B30;
        border-radius:12px; padding:14px; margin-bottom:16px;
    }
    h1,h2,h3,h4 { color:#1D1D1F; font-weight:600; }
    </style>
    """, unsafe_allow_html=True)

add_ios_style()

# --------------------------
# 状态初始化
# --------------------------
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'df' not in st.session_state: st.session_state.df = None
if 'processed_df' not in st.session_state: st.session_state.processed_df = None
if 'time_column' not in st.session_state: st.session_state.time_column = None
if 'selected_page' not in st.session_state: st.session_state.selected_page = "销量分析看板"

WEEK_ORDER = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

# --------------------------
# 工具函数
# --------------------------
def validate_date(d):
    if isinstance(d, date): return d
    if isinstance(d, datetime): return d.date()
    return date.today()

def process_order_data(df, time_col):
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df['小时'] = df[time_col].dt.hour
    df['星期'] = df[time_col].dt.dayofweek.map({
        0:'周一',1:'周二',2:'周三',3:'周四',4:'周五',5:'周六',6:'周日'
    })
    df['订单日期'] = df[time_col].dt.date
    return df

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='数据', index=False)
    return output.getvalue()

# --------------------------
# 侧边栏
# --------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align:center'>📊 数据分析工具</h2>", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### 📤 数据导入")
    uploaded_file = st.file_uploader("上传Excel/CSV", type=['xlsx','csv'], label_visibility="collapsed")
    col1, col2 = st.columns([3,1])
    with col1:
        if st.button("📥 导入数据", use_container_width=True):
            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                    st.session_state.df = df
                    st.session_state.data_loaded = True
                    time_candidates = [c for c in df.columns if any(x in c for x in ['时间','日期','time','date'])]
                    st.session_state.time_column = time_candidates[0] if time_candidates else df.columns[0]
                    st.session_state.processed_df = process_order_data(df, st.session_state.time_column)
                    st.success("✅ 导入成功")
                except Exception as e:
                    st.error(f"失败：{e}")
    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state.data_loaded = False
            st.session_state.df = None
            st.session_state.processed_df = None
            st.rerun()

    st.divider()
    st.markdown("#### 📋 功能选择")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("销量分析看板", use_container_width=True):
            st.session_state.selected_page = "销量分析看板"
    with c2:
        if st.button("订单分析看板", use_container_width=True):
            st.session_state.selected_page = "订单分析看板"

# --------------------------
# 主界面
# --------------------------
st.markdown("<h1 style='text-align:center'>跨境电商数据分析平台</h1>", unsafe_allow_html=True)

if not st.session_state.data_loaded:
    st.markdown("""
    <div class='ios-card' style='text-align:center;padding:40px'>
        <h3>👋 请从左侧导入订单数据</h3>
        <p style='color:#8E8E93'>支持 Excel / CSV</p>
    </div>""", unsafe_allow_html=True)
else:
    df_full = st.session_state.processed_df
    min_date = df_full['订单日期'].min()
    max_date = df_full['订单日期'].max()

    # ==========================
    # 销量分析看板（运营终极版）
    # ==========================
    if st.session_state.selected_page == "销量分析看板":
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 📈 销量分析看板")

        # 时间筛选
        bc1,bc2,bc3,bc4,bc5 = st.columns(5)
        with bc1: btn_today = st.button("今日", use_container_width=True)
        with bc2: btn_yesterday = st.button("昨日", use_container_width=True)
        with bc3: btn_7d = st.button("近7天", use_container_width=True)
        with bc4: btn_14d = st.button("近14天", use_container_width=True)
        with bc5: btn_30d = st.button("近30天", use_container_width=True)

        c_start, c_end = st.columns(2)
        with c_start: s_date = st.date_input("开始", max_date, min_value=min_date, max_value=max_date)
        with c_end: e_date = st.date_input("结束", max_date, min_value=min_date, max_value=max_date)

        if btn_today: s_date, e_date = max_date, max_date
        elif btn_yesterday: s_date = e_date = max_date - timedelta(1)
        elif btn_7d: s_date = max_date - timedelta(6)
        elif btn_14d: s_date = max_date - timedelta(13)
        elif btn_30d: s_date = max_date - timedelta(29)

        s_date = validate_date(s_date)
        e_date = validate_date(e_date)
        df = df_full[(df_full['订单日期'] >= s_date) & (df_full['订单日期'] <= e_date)].copy()
        days = (e_date - s_date).days + 1

        st.markdown(f"✅ `{s_date}` ~ `{e_date}`｜共 {len(df)} 条｜{days} 天")
        st.markdown("</div>", unsafe_allow_html=True)

        # --------------
        # 1. 运营总览
        # --------------
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 运营总览")
        total_orders = df['订单号'].nunique()
        total_qty = df['数量'].sum()
        total_revenue = df['销售总额'].sum()
        avg_price = total_revenue / total_qty if total_qty else 0
        avg_orders = total_orders / days
        avg_qty = total_qty / days

        c1,c2,c3,c4 = st.columns(4)
        with c1: st.markdown(f"<div class='metric-card'><p>总订单</p><h2>{total_orders}</h2></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><p>总销量</p><h2>{total_qty}</h2></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><p>总销售额</p><h2>${total_revenue:.2f}</h2></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='metric-card'><p>日均销量</p><h2>{avg_qty:.1f}</h2></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # --------------
        # 2. 异常预警（新增）
        # --------------
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### ⚠️ 异常订单预警")
        if days >= 3:
            day_sum = df.groupby('订单日期')['数量'].sum().sort_index()
            if len(day_sum) >= 3:
                recent = day_sum.iloc[-1]
                prev = day_sum.iloc[-2]
                change = (recent - prev) / prev * 100 if prev != 0 else 0
                if change >= 30:
                    st.markdown(f"""<div class='alert-card'>🚨 销量暴涨：昨日销量 ↑ {change:.1f}%</div>""", unsafe_allow_html=True)
                elif change <= -30:
                    st.markdown(f"""<div class='alert-card'>⚠️ 销量暴跌：昨日销量 ↓ {abs(change):.1f}%</div>""", unsafe_allow_html=True)
                else:
                    st.success("✅ 销量平稳，无异常波动")
        else:
            st.info("ℹ️ 数据天数不足，无法预警")
        st.markdown("</div>", unsafe_allow_html=True)

        # --------------
        # 3. 日销量趋势（新增）
        # --------------
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 📅 日销量趋势")
        day_trend = df.groupby('订单日期')['数量'].sum().reset_index()
        fig = px.line(day_trend, x='订单日期', y='数量', markers=True, color_discrete_sequence=['#007AFF'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # --------------
        # 4. 小时趋势
        # --------------
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### ⏰ 小时销量峰值")
        hour_df = df.groupby('小时')['数量'].sum().reindex(range(24), fill_value=0).reset_index()
        fig = px.line(hour_df, x='小时', y='数量', markers=True, color_discrete_sequence=['#007AFF'])
        fig.update_traces(texttemplate='%{y}', textposition='top center')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # --------------
        # 5. SKU 分析 + 导出（新增）
        # --------------
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 🏆 SKU 销售分析")
        sort_col1, sort_col2, exp_col = st.columns([2,2,1])
        with sort_col1: btn_qty = st.button("按销量排序", use_container_width=True)
        with sort_col2: btn_rev = st.button("按销售额排序", use_container_width=True)
        with exp_col:
            excel_data = to_excel(df)
            st.download_button("📥 导出", data=excel_data, file_name=f"筛选数据_{s_date}_{e_date}.xlsx", mime="application/vnd.ms-excel", use_container_width=True)

        sku_df = df.groupby('SKU').agg(
            销量=('数量','sum'),
            订单量=('订单号','nunique'),
            销售额=('销售总额','sum')
        ).reset_index()

        sku_df['销量占比'] = (sku_df['销量'] / sku_df['销量'].sum() * 100).round(1).astype(str) + '%'
        sku_df['销售额占比'] = (sku_df['销售额'] / sku_df['销售额'].sum() * 100).round(1).astype(str) + '%'

        if btn_qty: sku_df = sku_df.sort_values('销量', ascending=False)
        elif btn_rev: sku_df = sku_df.sort_values('销售额', ascending=False)
        else: sku_df = sku_df.sort_values('销量', ascending=False)

        total_row = pd.DataFrame([{
            'SKU':'合计',
            '销量':sku_df['销量'].sum(),
            '订单量':sku_df['订单量'].sum(),
            '销售额':sku_df['销售额'].sum(),
            '销量占比':'100%',
            '销售额占比':'100%'
        }])
        sku_df = pd.concat([sku_df, total_row], ignore_index=True)
        st.dataframe(sku_df, use_container_width=True, height=420)
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================
    # 订单分析看板
    # ==========================
    elif st.session_state.selected_page == "订单分析看板":
        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 📋 订单分析看板")
        bc1,bc2,bc3,bc4,bc5 = st.columns(5)
        with bc1: btn_7d = st.button("近7天", use_container_width=True)
        with bc2: btn_14d = st.button("近14天", use_container_width=True)
        with bc3: btn_30d = st.button("近30天", use_container_width=True)
        with bc4: btn_last = st.button("上个月", use_container_width=True)
        with bc5: btn_all = st.button("全部", use_container_width=True)

        c_start,c_end = st.columns(2)
        with c_start: s_date = st.date_input("开始", min_date, min_value=min_date, max_value=max_date)
        with c_end: e_date = st.date_input("结束", max_date, min_value=min_date, max_value=max_date)

        if btn_7d: s_date = max_date - timedelta(6)
        if btn_14d: s_date = max_date - timedelta(13)
        if btn_30d: s_date = max_date - timedelta(29)
        if btn_all: s_date,e_date = min_date,max_date

        s_date = validate_date(s_date)
        e_date = validate_date(e_date)
        df = df_full[(df_full['订单日期'] >= s_date) & (df_full['订单日期'] <= e_date)]
        st.success(f"✅ {s_date} ~ {e_date}｜共 {len(df)} 条")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        cw, ch = st.columns(2)
        with cw:
            wdf = df.groupby('星期').size().reindex(WEEK_ORDER, fill_value=0).reset_index(name='订单数')
            fig = px.bar(wdf,x='星期',y='订单数',color_discrete_sequence=['#007AFF'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig,use_container_width=True)
        with ch:
            hdf = df.groupby('小时').size().reindex(range(24), fill_value=0).reset_index(name='订单数')
            fig = px.line(hdf,x='小时',y='订单数',markers=True,color_discrete_sequence=['#007AFF'])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)',paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig,use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='ios-card'>", unsafe_allow_html=True)
        st.markdown("### 🏆 SKU 排行榜")
        rank = df.groupby('SKU').agg(
            销量=('数量','sum'),
            订单量=('订单号','nunique'),
            销售额=('销售总额','sum')
        ).reset_index()
        rank['销量占比'] = (rank['销量']/rank['销量'].sum()*100).round(1).astype(str)+'%'
        rank['销售额占比'] = (rank['销售额']/rank['销售额'].sum()*100).round(1).astype(str)+'%'
        rank = rank.sort_values('销量', ascending=False)
        tr = pd.DataFrame([{'SKU':'合计',
                             '销量':rank['销量'].sum(),
                             '订单量':rank['订单量'].sum(),
                             '销售额':rank['销售额'].sum(),
                             '销量占比':'100%',
                             '销售额占比':'100%'}])
        rank = pd.concat([rank, tr], ignore_index=True)
        st.dataframe(rank, use_container_width=True, height=400)
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='text-align:center;color:#8E8E93;margin-top:30px;font-size:13px'>© 2026 跨境数据分析工具｜iOS 运营终极版</div>", unsafe_allow_html=True)
