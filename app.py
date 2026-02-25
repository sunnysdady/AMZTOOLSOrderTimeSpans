import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import base64

# --------------------------
# 页面基础配置 & IOS风格样式
# --------------------------
st.set_page_config(
    page_title="跨境电商数据分析工具",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义IOS风格CSS
def add_ios_style():
    st.markdown("""
    <style>
    /* 全局样式 */
    .stApp {
        background-color: #f5f5f7;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
    }
    
    /* 侧边栏IOS风格 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e6e6e8;
    }
    
    /* IOS磨砂玻璃卡片 */
    .ios-card {
        background: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* IOS按钮样式 */
    .stButton > button {
        background-color: #007aff;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #0066e0;
        transform: translateY(-1px);
    }
    .stButton > button:active {
        background-color: #0052cc;
        transform: translateY(0);
    }
    
    /* 按钮组样式 */
    .btn-group {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin: 10px 0;
    }
    .btn-group > button {
        flex: 1;
        min-width: 80px;
    }
    
    /* 指标卡片样式 */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    
    /* 标题样式 */
    h1, h2, h3, h4 {
        color: #1d1d1f;
        font-weight: 600;
    }
    .stCaption {
        color: #86868b;
        font-size: 12px;
    }
    
    /* 数据框样式 */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    
    /* 去除Streamlit默认边框 */
    .stSelectbox > div > div {
        border-radius: 10px;
        border: 1px solid #e6e6e8;
    }
    .stDateInput > div > div {
        border-radius: 10px;
        border: 1px solid #e6e6e8;
    }
    </style>
    """, unsafe_allow_html=True)

add_ios_style()

# --------------------------
# 全局常量
# --------------------------
WEEK_ORDER = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

# --------------------------
# 会话状态初始化
# --------------------------
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'processed_df' not in st.session_state:
    st.session_state.processed_df = None
if 'time_column' not in st.session_state:
    st.session_state.time_column = None

# --------------------------
# 辅助函数：数据处理 & 日期校验
# --------------------------
def validate_date(input_date):
    """校验并转换日期为统一格式"""
    if isinstance(input_date, date):
        return input_date
    elif isinstance(input_date, datetime):
        return input_date.date()
    elif isinstance(input_date, str):
        try:
            return datetime.strptime(input_date, "%Y-%m-%d").date()
        except:
            return date.today()
    else:
        return date.today()

def process_order_data(df, time_column):
    """处理订单数据，增加日期校验"""
    # 安全转换时间字段
    df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
    df = df.dropna(subset=[time_column])
    
    # 提取维度字段
    df['小时'] = df[time_column].dt.hour
    df['星期'] = df[time_column].dt.dayofweek
    week_mapping = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
    df['星期'] = df['星期'].map(week_mapping)
    
    # 统一转换为date格式，避免datetime/date混用
    df['订单日期'] = df[time_column].dt.date
    
    return df

def get_hourly_stats(df):
    hourly_stats = df.groupby('小时').size().reset_index(name='订单数')
    all_hours = pd.DataFrame({'小时': range(24)})
    hourly_stats = pd.merge(all_hours, hourly_stats, on='小时', how='left').fillna(0)
    return hourly_stats

def get_weekly_stats(df):
    weekly_stats = df.groupby('星期').size().reset_index(name='订单数')
    weekly_stats['星期'] = pd.Categorical(weekly_stats['星期'], categories=WEEK_ORDER, ordered=True)
    weekly_stats = weekly_stats.sort_values('星期').reset_index(drop=True)
    return weekly_stats

def get_week_hour_cross_stats(df):
    cross_stats = df.groupby(['星期', '小时']).size().reset_index(name='订单数')
    all_week_hour = pd.MultiIndex.from_product([WEEK_ORDER, range(24)], names=['星期', '小时']).to_frame(index=False)
    cross_stats = pd.merge(all_week_hour, cross_stats, on=['星期', '小时'], how='left').fillna(0)
    return cross_stats

def get_sku_ranking(df):
    required_cols = ['SKU', '数量', '采购总额', '销售总额']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"数据中缺少必要字段：{col}，无法生成SKU排行榜")
            return pd.DataFrame()
    sku_stats = df.groupby('SKU').agg(
        销量=('数量', 'sum'),
        订单量=('订单号', 'nunique'),
        采购总额=('采购总额', 'sum'),
        销售额=('销售总额', 'sum')
    ).reset_index()
    sku_stats['净销售额'] = sku_stats['销售额'] - sku_stats['采购总额']
    sku_stats['平均价格'] = sku_stats['销售额'] / sku_stats['销量']
    sku_stats[['采购总额', '销售额', '净销售额', '平均价格']] = sku_stats[['采购总额', '销售额', '净销售额', '平均价格']].round(2)
    sku_stats = sku_stats.sort_values('销量', ascending=False).reset_index(drop=True)
    sku_stats.insert(0, '序号', range(1, len(sku_stats)+1))
    return sku_stats

def get_sales_metrics(df, today_date, yesterday_date, last_week_today_date):
    # 日期校验
    today_date = validate_date(today_date)
    yesterday_date = validate_date(yesterday_date)
    last_week_today_date = validate_date(last_week_today_date)
    
    today_data = df[df['订单日期'] == today_date]
    yesterday_data = df[df['订单日期'] == yesterday_date]
    last_week_today_data = df[df['订单日期'] == last_week_today_date]

    metrics = {
        'today_sales': today_data['数量'].sum(),
        'today_revenue': today_data['销售总额'].sum(),
        'today_orders': today_data['订单号'].nunique(),
        'today_avg_price': today_data['销售总额'].sum() / today_data['数量'].sum() if today_data['数量'].sum() > 0 else 0,
        'today_cancel': 0,
        'yesterday_sales': yesterday_data['数量'].sum(),
        'yesterday_revenue': yesterday_data['销售总额'].sum(),
        'yesterday_orders': yesterday_data['订单号'].nunique(),
        'yesterday_avg_price': yesterday_data['销售总额'].sum() / yesterday_data['数量'].sum() if yesterday_data['数量'].sum() > 0 else 0,
        'yesterday_cancel': 0,
        'last_week_today_sales': last_week_today_data['数量'].sum(),
        'last_week_today_revenue': last_week_today_data['销售总额'].sum(),
        'last_week_today_orders': last_week_today_data['订单号'].nunique(),
        'last_week_today_avg_price': last_week_today_data['销售总额'].sum() / last_week_today_data['数量'].sum() if last_week_today_data['数量'].sum() > 0 else 0,
        'last_week_today_cancel': 0
    }
    return metrics

def get_hourly_trend(df, today_date, yesterday_date):
    today_date = validate_date(today_date)
    yesterday_date = validate_date(yesterday_date)
    
    today_hourly = df[df['订单日期'] == today_date].groupby('小时')['数量'].sum().reset_index(name='今日销量')
    yesterday_hourly = df[df['订单日期'] == yesterday_date].groupby('小时')['数量'].sum().reset_index(name='昨日销量')
    all_hours = pd.DataFrame({'小时': range(24)})
    hourly_trend = pd.merge(all_hours, today_hourly, on='小时', how='left').fillna(0)
    hourly_trend = pd.merge(hourly_trend, yesterday_hourly, on='小时', how='left').fillna(0)
    return hourly_trend

def get_sku_multi_period(df, today_date, yesterday_date, last_week_today_date):
    today_date = validate_date(today_date)
    yesterday_date = validate_date(yesterday_date)
    last_week_today_date = validate_date(last_week_today_date)
    
    today_data = df[df['订单日期'] == today_date]
    yesterday_data = df[df['订单日期'] == yesterday_date]
    last_week_today_data = df[df['订单日期'] == last_week_today_date]
    last_7_days = df[(df['订单日期'] >= today_date - timedelta(days=6)) & (df['订单日期'] <= today_date)]
    last_14_days = df[(df['订单日期'] >= today_date - timedelta(days=13)) & (df['订单日期'] <= today_date)]
    last_30_days = df[(df['订单日期'] >= today_date - timedelta(days=29)) & (df['订单日期'] <= today_date)]

    sku_today = today_data.groupby('SKU').agg(
        今日销量=('数量', 'sum'),
        今日订单量=('订单号', 'nunique'),
        今日销售额=('销售总额', 'sum')
    ).reset_index()
    sku_yesterday = yesterday_data.groupby('SKU').agg(
        昨日销量=('数量', 'sum'),
        昨日订单量=('订单号', 'nunique'),
        昨日销售额=('销售总额', 'sum')
    ).reset_index()
    sku_last_week = last_week_today_data.groupby('SKU').agg(
        上周今日销量=('数量', 'sum'),
        上周今日订单量=('订单号', 'nunique'),
        上周今日销售额=('销售总额', 'sum')
    ).reset_index()
    sku_7d = last_7_days.groupby('SKU').agg(
        七天销量=('数量', 'sum')
    ).reset_index()
    sku_14d = last_14_days.groupby('SKU').agg(
        十四天销量=('数量', 'sum')
    ).reset_index()
    sku_30d = last_30_days.groupby('SKU').agg(
        三十天销量=('数量', 'sum')
    ).reset_index()

    sku_multi = sku_today.merge(sku_yesterday, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_last_week, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_7d, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_14d, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_30d, on='SKU', how='outer')
    sku_multi = sku_multi.fillna(0)
    return sku_multi

# --------------------------
# 左侧导航栏（IOS风格）
# --------------------------
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>📊 数据分析工具</h2>", unsafe_allow_html=True)
    st.divider()
    
    # 1. 数据导入模块（移至左侧）
    st.markdown("<h4>📤 数据导入</h4>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "上传Excel/CSV文件",
        type=['xlsx', 'csv'],
        label_visibility="collapsed"
    )
    
    # 数据导入按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("📥 导入数据", use_container_width=True):
            if uploaded_file is not None:
                try:
                    # 读取文件
                    if uploaded_file.name.endswith('.csv'):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                    
                    st.session_state.df = df
                    st.session_state.data_loaded = True
                    st.success("✅ 数据导入成功！")
                    
                    # 自动选择第一个时间相关字段
                    time_cols = [col for col in df.columns if '时间' in col or '日期' in col or 'date' in col.lower() or 'time' in col.lower()]
                    if time_cols:
                        st.session_state.time_column = time_cols[0]
                        # 预处理数据
                        st.session_state.processed_df = process_order_data(df, st.session_state.time_column)
                except Exception as e:
                    st.error(f"数据导入失败：{str(e)}")
                    st.session_state.data_loaded = False
            else:
                st.warning("请先选择文件！")
    
    with col2:
        if st.button("🗑️ 清空", use_container_width=True):
            st.session_state.data_loaded = False
            st.session_state.df = None
            st.session_state.processed_df = None
            st.session_state.time_column = None
            st.rerun()
    
    st.divider()
    
    # 2. 看板选择（按钮组替代单选框）
    st.markdown("<h4>📋 功能选择</h4>", unsafe_allow_html=True)
    st.markdown('<div class="btn-group">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("销量分析看板", use_container_width=True, key="sales_board"):
            st.session_state.selected_page = "销量分析看板"
    with col2:
        if st.button("订单分析看板", use_container_width=True, key="order_board"):
            st.session_state.selected_page = "订单分析看板"
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 初始化默认看板
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "销量分析看板"
    
    st.divider()
    
    # 3. 数据预览（折叠面板）
    with st.expander("📄 数据预览", expanded=False):
        if st.session_state.data_loaded and st.session_state.df is not None:
            st.dataframe(st.session_state.df.head(10), use_container_width=True, height=200)
            st.caption(f"总行数：{len(st.session_state.df)}")
        else:
            st.info("暂无数据，请先导入")

# --------------------------
# 主页面（IOS风格）
# --------------------------
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>跨境电商数据分析平台</h1>", unsafe_allow_html=True)

# 数据未加载时的提示
if not st.session_state.data_loaded:
    st.markdown("""
    <div class="ios-card" style="text-align: center; padding: 40px;">
        <h3>👋 欢迎使用数据分析工具</h3>
        <p style="color: #86868b;">请从左侧侧边栏上传并导入您的订单数据</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # 时间字段选择（IOS风格）
    st.markdown('<div class="ios-card">', unsafe_allow_html=True)
    st.markdown("<h4>🕒 时间字段设置</h4>", unsafe_allow_html=True)
    new_time_column = st.selectbox(
        "选择订单时间字段",
        options=st.session_state.df.columns.tolist(),
        index=st.session_state.df.columns.tolist().index(st.session_state.time_column) if st.session_state.time_column in st.session_state.df.columns else 0
    )
    
    # 时间字段变更时重新处理数据
    if new_time_column != st.session_state.time_column:
        st.session_state.time_column = new_time_column
        st.session_state.processed_df = process_order_data(st.session_state.df, new_time_column)
        st.success("时间字段已更新，数据重新处理完成！")
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    
    # --------------------------
    # 销量分析看板（IOS风格）
    # --------------------------
    if st.session_state.selected_page == "销量分析看板":
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h3>📈 销量分析看板</h3>", unsafe_allow_html=True)
        
        # 时间范围选择（按钮组替代复选框）
        st.markdown("<h4>📅 时间范围选择</h4>", unsafe_allow_html=True)
        st.markdown('<div class="btn-group">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("今日", use_container_width=True, key="sales_today"):
                st.session_state.time_range = "今日"
        with col2:
            if st.button("昨日", use_container_width=True, key="sales_yesterday"):
                st.session_state.time_range = "昨日"
        with col3:
            if st.button("近7天", use_container_width=True, key="sales_7d"):
                st.session_state.time_range = "近7天"
        with col4:
            if st.button("近14天", use_container_width=True, key="sales_14d"):
                st.session_state.time_range = "近14天"
        with col5:
            if st.button("近30天", use_container_width=True, key="sales_30d"):
                st.session_state.time_range = "近30天"
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 自定义日期
        st.markdown("<h5>自定义时间范围</h5>", unsafe_allow_html=True)
        col_start, col_end = st.columns(2)
        data_min_date = st.session_state.processed_df['订单日期'].min()
        data_max_date = st.session_state.processed_df['订单日期'].max()
        
        with col_start:
            custom_start_date = st.date_input("开始日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date, key="sales_start")
        with col_end:
            custom_end_date = st.date_input("结束日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date, key="sales_end")
        
        # 确定分析日期
        if 'time_range' not in st.session_state:
            st.session_state.time_range = "今日"
        
        if st.session_state.time_range == "今日":
            analysis_date = data_max_date
        elif st.session_state.time_range == "昨日":
            analysis_date = data_max_date - timedelta(days=1)
        elif st.session_state.time_range == "近7天":
            analysis_date = data_max_date
        elif st.session_state.time_range == "近14天":
            analysis_date = data_max_date
        elif st.session_state.time_range == "近30天":
            analysis_date = data_max_date
        else:
            analysis_date = custom_end_date
        
        # 日期校验（核心修复）
        analysis_date = validate_date(analysis_date)
        yesterday_date = validate_date(analysis_date - timedelta(days=1))
        last_week_today_date = validate_date(analysis_date - timedelta(days=7))
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 核心指标卡片（IOS风格）
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h3>📊 核心指标</h3>", unsafe_allow_html=True)
        metrics = get_sales_metrics(st.session_state.processed_df, analysis_date, yesterday_date, last_week_today_date)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #86868b; margin: 0;">销量</p>
                <h3 style="margin: 8px 0;">{metrics['today_sales']}</h3>
                <p style="font-size: 12px; color: #34c759; margin: 0;">+{((metrics['today_sales'] - metrics['yesterday_sales']) / metrics['yesterday_sales'] * 100):.2f}% 昨日</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #86868b; margin: 0;">销售额</p>
                <h3 style="margin: 8px 0;">${metrics['today_revenue']:.2f}</h3>
                <p style="font-size: 12px; color: #34c759; margin: 0;">+{((metrics['today_revenue'] - metrics['yesterday_revenue']) / metrics['yesterday_revenue'] * 100):.2f}% 昨日</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #86868b; margin: 0;">订单量</p>
                <h3 style="margin: 8px 0;">{metrics['today_orders']}</h3>
                <p style="font-size: 12px; color: #34c759; margin: 0;">+{((metrics['today_orders'] - metrics['yesterday_orders']) / metrics['yesterday_orders'] * 100):.2f}% 昨日</p>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #86868b; margin: 0;">销售均价</p>
                <h3 style="margin: 8px 0;">${metrics['today_avg_price']:.2f}</h3>
                <p style="font-size: 12px; color: #34c759; margin: 0;">{((metrics['today_avg_price'] - metrics['yesterday_avg_price']) / metrics['yesterday_avg_price'] * 100):.2f}% 昨日</p>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            st.markdown(f"""
            <div class="metric-card">
                <p style="color: #86868b; margin: 0;">取消订单</p>
                <h3 style="margin: 8px 0;">{metrics['today_cancel']}</h3>
                <p style="font-size: 12px; color: #ff3b30; margin: 0;">-100.00% 上周今日</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 小时趋势图
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h3>📈 小时趋势分析</h3>", unsafe_allow_html=True)
        hourly_trend = get_hourly_trend(st.session_state.processed_df, analysis_date, yesterday_date)
        
        col_trend1, col_trend2 = st.columns(2)
        with col_trend1:
            fig_sales_trend = px.line(
                hourly_trend,
                x='小时',
                y=['今日销量', '昨日销量'],
                title='销量小时趋势对比',
                markers=True,
                height=300,
                template="plotly_white"
            )
            fig_sales_trend.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title_x=0.5,
                title_font=dict(size=16, weight='bold')
            )
            st.plotly_chart(fig_sales_trend, use_container_width=True)
        
        with col_trend2:
            today_revenue_hourly = st.session_state.processed_df[st.session_state.processed_df['订单日期'] == analysis_date].groupby('小时')['销售总额'].sum().reset_index(name='今日销售额')
            yesterday_revenue_hourly = st.session_state.processed_df[st.session_state.processed_df['订单日期'] == yesterday_date].groupby('小时')['销售总额'].sum().reset_index(name='昨日销售额')
            revenue_trend = pd.merge(pd.DataFrame({'小时': range(24)}), today_revenue_hourly, on='小时', how='left').fillna(0)
            revenue_trend = pd.merge(revenue_trend, yesterday_revenue_hourly, on='小时', how='left').fillna(0)
            
            fig_revenue_trend = px.line(
                revenue_trend,
                x='小时',
                y=['今日销售额', '昨日销售额'],
                title='销售额小时趋势对比',
                markers=True,
                height=300,
                template="plotly_white"
            )
            fig_revenue_trend.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title_x=0.5,
                title_font=dict(size=16, weight='bold')
            )
            st.plotly_chart(fig_revenue_trend, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # SKU多周期对比
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h3>📦 SKU多周期对比</h3>", unsafe_allow_html=True)
        sku_multi = get_sku_multi_period(st.session_state.processed_df, analysis_date, yesterday_date, last_week_today_date)
        
        if 'SKU' in st.session_state.processed_df.columns:
            sku_multi = sku_multi.merge(st.session_state.processed_df[['SKU', 'ASIN', '产品名称']].drop_duplicates(), on='SKU', how='left')
            display_cols = ['SKU', 'ASIN', '产品名称', '七天销量', '十四天销量', '三十天销量', '今日销量', '今日订单量', '今日销售额', '昨日销量', '昨日订单量', '昨日销售额', '上周今日销量', '上周今日订单量', '上周今日销售额']
            st.dataframe(sku_multi[display_cols], use_container_width=True, height=400)
        else:
            st.warning("数据中缺少SKU字段，无法生成SKU多周期对比表")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # --------------------------
    # 订单分析看板（IOS风格）
    # --------------------------
    elif st.session_state.selected_page == "订单分析看板":
        st.markdown('<div class="ios-card">', unsafe_allow_html=True)
        st.markdown("<h3>📋 订单分析看板</h3>", unsafe_allow_html=True)
        
        # 时间范围选择（按钮组）
        st.markdown("<h4>📅 时间范围选择</h4>", unsafe_allow_html=True)
        st.markdown('<div class="btn-group">', unsafe_allow_html=True)
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            if st.button("近7天", use_container_width=True, key="order_7d"):
                st.session_state.order_time_range = "近7天"
        with col2:
            if st.button("近14天", use_container_width=True, key="order_14d"):
                st.session_state.order_time_range = "近14天"
        with col3:
            if st.button("近30天", use_container_width=True, key="order_30d"):
                st.session_state.order_time_range = "近30天"
        with col4:
            if st.button("上个月", use_container_width=True, key="order_last_month"):
                st.session_state.order_time_range = "上个月"
        with col5:
            if st.button("全部数据", use_container_width=True, key="order_all"):
                st.session_state.order_time_range = "全部数据"
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 自定义日期
        st.markdown("<h5>自定义时间范围</h5>", unsafe_allow_html=True)
        data_min_date = st.session_state.processed_df['订单日期'].min()
        data_max_date = st.session_state.processed_df['订单日期'].max()
        data_max_datetime = st.session_state.processed_df[st.session_state.time_column].max()
        
        col_start, col_end = st.columns(2)
        with col_start:
            custom_start_date = st.date_input("开始日期", value=data_min_date, min_value=data_min_date, max_value=data_max_date, key="order_start")
        with col_end:
            custom_end_date = st.date_input("结束日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date, key="order_end")
        
        # 初始化时间范围
        if 'order_time_range' not in st.session_state:
            st.session_state.order_time_range = "全部数据"
        
        # 确定筛选范围（增加日期校验）
        filter_start_date = validate_date(data_min_date)
        filter_end_date = validate_date(data_max_date)
        
        if st.session_state.order_time_range == "近7天":
            filter_start_date = validate_date((data_max_datetime - timedelta(days=7)).date())
        elif st.session_state.order_time_range == "近14天":
            filter_start_date = validate_date((data_max_datetime - timedelta(days=14)).date())
        elif st.session_state.order_time_range == "近30天":
            filter_start_date = validate_date((data_max_datetime - timedelta(days=30)).date())
        elif st.session_state.order_time_range == "上个月":
            last_month = data_max_datetime - relativedelta(months=1)
            filter_start_date = validate_date(datetime(last_month.year, last_month.month, 1).date())
            first_day_current_month = datetime(data_max_datetime.year, data_max_datetime.month, 1)
            filter_end_date = validate_date((first_day_current_month - timedelta(days=1)).date())
        elif st.session_state.order_time_range == "全部数据":
            filter_start_date = validate_date(data_min_date)
        else:
            filter_start_date = validate_date(custom_start_date)
            filter_end_date = validate_date(custom_end_date)
        
        # 过滤数据
        filtered_df = st.session_state.processed_df[
            (st.session_state.processed_df['订单日期'] >= filter_start_date) & 
            (st.session_state.processed_df['订单日期'] <= filter_end_date)
        ]
        
        if len(filtered_df) == 0:
            st.warning(f"所选时间范围（{filter_start_date} ~ {filter_end_date}）内无订单数据！")
        else:
            st.success(f"筛选出 {filter_start_date} ~ {filter_end_date} 的订单数据，共 {len(filtered_df)} 条")
            
            # 重新统计
            hourly_stats = get_hourly_stats(filtered_df)
            weekly_stats = get_weekly_stats(filtered_df)
            cross_stats = get_week_hour_cross_stats(filtered_df)
            sku_ranking = get_sku_ranking(filtered_df)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 星期/小时统计
            st.markdown('<div class="ios-card">', unsafe_allow_html=True)
            st.markdown("<h3>📊 订单分布统计</h3>", unsafe_allow_html=True)
            
            col_week, col_hour = st.columns(2)
            with col_week:
                st.markdown("<h5>按星期统计</h5>", unsafe_allow_html=True)
                fig_week = px.bar(
                    weekly_stats,
                    x='星期',
                    y='订单数',
                    title='各星期订单数量',
                    color='订单数',
                    color_continuous_scale='Blues',
                    height=350,
                    template="plotly_white"
                )
                fig_week.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    title_x=0.5,
                    showlegend=False
                )
                st.plotly_chart(fig_week, use_container_width=True)
            
            with col_hour:
                st.markdown("<h5>按24小时统计</h5>", unsafe_allow_html=True)
                fig_hour = px.line(
                    hourly_stats,
                    x='小时',
                    y='订单数',
                    title='24小时订单数量趋势',
                    markers=True,
                    height=350,
                    template="plotly_white"
                )
                fig_hour.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    title_x=0.5
                )
                fig_hour.update_xaxes(tick0=0, dtick=1)
                st.plotly_chart(fig_hour, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 热力图
            st.markdown('<div class="ios-card">', unsafe_allow_html=True)
            st.markdown("<h3>🔥 星期×小时热力图</h3>", unsafe_allow_html=True)
            pivot_table = cross_stats.pivot(index='星期', columns='小时', values='订单数')
            pivot_table = pivot_table.reindex(WEEK_ORDER)
            
            fig_heatmap = go.Figure(data=go.Heatmap(
                z=pivot_table.values,
                x=pivot_table.columns,
                y=pivot_table.index,
                colorscale='YlGnBu',
                hoverongaps=False,
                hovertemplate='星期：%{y}<br>小时：%{x}<br>订单数：%{z}<extra></extra>'
            ))
            fig_heatmap.update_layout(
                title='各时段订单分布热力图',
                xaxis_title='小时',
                yaxis_title='星期',
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                title_x=0.5
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # SKU排行榜
            st.markdown('<div class="ios-card">', unsafe_allow_html=True)
            st.markdown("<h3>🏆 SKU销量排行榜</h3>", unsafe_allow_html=True)
            
            if not sku_ranking.empty:
                # 排序按钮组
                st.markdown('<div class="btn-group">', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("按销量排序", use_container_width=True, key="sort_sales"):
                        st.session_state.sort_by = "销量"
                with col2:
                    if st.button("按销售额排序", use_container_width=True, key="sort_revenue"):
                        st.session_state.sort_by = "销售额"
                st.markdown('</div>', unsafe_allow_html=True)
                
                # 初始化排序方式
                if 'sort_by' not in st.session_state:
                    st.session_state.sort_by = "销量"
                
                # 显示条数
                top_n = st.slider("显示前N名", min_value=10, max_value=len(sku_ranking), value=min(50, len(sku_ranking)), step=10, key="ranking_topn")
                
                # 排序展示
                if st.session_state.sort_by == "销量":
                    sku_ranking_sorted = sku_ranking.sort_values('销量', ascending=False).head(top_n)
                else:
                    sku_ranking_sorted = sku_ranking.sort_values('销售额', ascending=False).head(top_n)
                
                st.dataframe(sku_ranking_sorted, use_container_width=True, height=400)
                
                # 下载按钮
                csv_sku = sku_ranking_sorted.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label=f"📥 下载{st.session_state.sort_by}前{top_n}名SKU数据",
                    data=csv_sku,
                    file_name=f"SKU排行榜_{st.session_state.sort_by}_前{top_n}名_{filter_start_date}_{filter_end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.warning("无法生成SKU排行榜，请检查数据中是否包含SKU、数量、采购总额、销售总额等字段")
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 数据下载
            st.markdown('<div class="ios-card">', unsafe_allow_html=True)
            st.markdown("<h3>💾 数据下载</h3>", unsafe_allow_html=True)
            col_download1, col_download2 = st.columns(2)
            with col_download1:
                csv_hour = hourly_stats.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载24小时统计数据",
                    data=csv_hour,
                    file_name=f"订单小时统计_{filter_start_date}_{filter_end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_download2:
                csv_week = weekly_stats.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载星期统计数据",
                    data=csv_week,
                    file_name=f"订单星期统计_{filter_start_date}_{filter_end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            st.markdown('</div>', unsafe_allow_html=True)

# --------------------------
# 页脚（IOS风格）
# --------------------------
st.markdown("""
<div style="text-align: center; margin-top: 40px; color: #86868b; font-size: 12px;">
    © 2026 跨境电商数据分析工具 | IOS风格版
</div>
""", unsafe_allow_html=True)
