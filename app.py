import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# --------------------------
# 页面基础配置
# --------------------------
st.set_page_config(
    page_title="跨境电商数据分析工具",
    page_icon="📊",
    layout="wide"
)

# --------------------------
# 全局常量
# --------------------------
WEEK_ORDER = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

# --------------------------
# 辅助函数：数据处理
# --------------------------
def process_order_data(df, time_column):
    df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
    df = df.dropna(subset=[time_column])
    df['小时'] = df[time_column].dt.hour
    df['星期'] = df[time_column].dt.dayofweek
    week_mapping = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
    df['星期'] = df['星期'].map(week_mapping)
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

# --------------------------
# 销量分析看板核心函数
# --------------------------
def get_sales_metrics(df, today_date, yesterday_date, last_week_today_date):
    today_data = df[df['订单日期'] == today_date]
    yesterday_data = df[df['订单日期'] == yesterday_date]
    last_week_today_data = df[df['订单日期'] == last_week_today_date]

    metrics = {
        'today_sales': today_data['数量'].sum(),
        'today_revenue': today_data['销售总额'].sum(),
        'today_orders': today_data['订单号'].nunique(),
        'today_avg_price': today_data['销售总额'].sum() / today_data['数量'].sum() if today_data['数量'].sum() > 0 else 0,
        'today_cancel': 0,  # 可根据实际数据调整
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
    today_hourly = df[df['订单日期'] == today_date].groupby('小时')['数量'].sum().reset_index(name='今日销量')
    yesterday_hourly = df[df['订单日期'] == yesterday_date].groupby('小时')['数量'].sum().reset_index(name='昨日销量')
    all_hours = pd.DataFrame({'小时': range(24)})
    hourly_trend = pd.merge(all_hours, today_hourly, on='小时', how='left').fillna(0)
    hourly_trend = pd.merge(hourly_trend, yesterday_hourly, on='小时', how='left').fillna(0)
    return hourly_trend

def get_sku_multi_period(df, today_date, yesterday_date, last_week_today_date):
    today_data = df[df['订单日期'] == today_date]
    yesterday_data = df[df['订单日期'] == yesterday_date]
    last_week_today_data = df[df['订单日期'] == last_week_today_date]
    last_7_days = df[(df['订单日期'] >= today_date - timedelta(days=6)) & (df['订单日期'] <= today_date)]
    last_14_days = df[(df['订单日期'] >= today_date - timedelta(days=13)) & (df['订单日期'] <= today_date)]
    last_30_days = df[(df['订单日期'] >= today_date - timedelta(days=29)) & (df['订单日期'] <= today_date)]

    # 修复：将数字开头的列名改为纯中文（七天销量 而非 7天销量）
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
        七天销量=('数量', 'sum')  # 修复：7天销量 → 七天销量
    ).reset_index()
    sku_14d = last_14_days.groupby('SKU').agg(
        十四天销量=('数量', 'sum')  # 修复：14天销量 → 十四天销量
    ).reset_index()
    sku_30d = last_30_days.groupby('SKU').agg(
        三十天销量=('数量', 'sum')  # 修复：30天销量 → 三十天销量
    ).reset_index()

    sku_multi = sku_today.merge(sku_yesterday, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_last_week, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_7d, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_14d, on='SKU', how='outer')
    sku_multi = sku_multi.merge(sku_30d, on='SKU', how='outer')
    sku_multi = sku_multi.fillna(0)
    return sku_multi

# --------------------------
# 左侧导航栏
# --------------------------
with st.sidebar:
    st.title("📊 功能导航")
    st.divider()
    selected_page = st.radio(
        "选择看板",
        ["销量分析看板", "订单分析看板"],
        index=0
    )

# --------------------------
# 主页面逻辑
# --------------------------
st.title("跨境电商数据分析工具")
st.divider()

# 1. 文件上传区域（全局）
st.subheader("1. 上传订单文件")
uploaded_file = st.file_uploader(
    "支持格式：Excel(.xlsx)、CSV(.csv)",
    type=['xlsx', 'csv'],
    help="请确保文件包含订单时间字段（如：出单时间、下单时间等）"
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.subheader("数据预览")
        total_rows = len(df)
        st.success(f"✅ 成功导入数据，共 {total_rows} 行，以下是完整数据：")
        st.dataframe(df, use_container_width=True, height=300)

        time_column = st.selectbox(
            "请选择订单时间字段",
            options=df.columns.tolist(),
            help="选择包含出单时间的列（如：下单时间、支付时间等）"
        )

        processed_df = process_order_data(df, time_column)
        st.success("数据处理完成！")
        st.divider()

        # --------------------------
        # 销量分析看板
        # --------------------------
        if selected_page == "销量分析看板":
            st.subheader("📈 销量分析看板")
            st.info("复刻你提供的图片样式，包含核心指标、小时趋势、SKU多周期对比")

            # 时间快捷选择
            st.markdown("#### 时间范围选择")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                btn_today = st.button("今日", use_container_width=True)
            with col2:
                btn_yesterday = st.button("昨日", use_container_width=True)
            with col3:
                btn_7d = st.button("近7天", use_container_width=True)
            with col4:
                btn_14d = st.button("近14天", use_container_width=True)
            with col5:
                btn_30d = st.button("近30天", use_container_width=True)

            # 自定义日期
            st.markdown("##### 或自定义时间范围")
            col_start, col_end = st.columns(2)
            data_min_date = processed_df['订单日期'].min()
            data_max_date = processed_df['订单日期'].max()
            with col_start:
                custom_start_date = st.date_input("开始日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date)
            with col_end:
                custom_end_date = st.date_input("结束日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date)

            # 确定当前分析日期
            if btn_today:
                analysis_date = data_max_date
            elif btn_yesterday:
                analysis_date = data_max_date - timedelta(days=1)
            elif btn_7d:
                analysis_date = data_max_date
                start_date = analysis_date - timedelta(days=6)
                end_date = analysis_date
            elif btn_14d:
                analysis_date = data_max_date
                start_date = analysis_date - timedelta(days=13)
                end_date = analysis_date
            elif btn_30d:
                analysis_date = data_max_date
                start_date = analysis_date - timedelta(days=29)
                end_date = analysis_date
            else:
                analysis_date = custom_end_date
                start_date = custom_start_date
                end_date = custom_end_date

            yesterday_date = analysis_date - timedelta(days=1)
            last_week_today_date = analysis_date - timedelta(days=7)

            # 核心指标卡片
            st.markdown("#### 核心指标")
            metrics = get_sales_metrics(processed_df, analysis_date, yesterday_date, last_week_today_date)
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric(
                    "销量",
                    f"{metrics['today_sales']}",
                    delta=f"+{((metrics['today_sales'] - metrics['yesterday_sales']) / metrics['yesterday_sales'] * 100):.2f}%" if metrics['yesterday_sales'] > 0 else "-",
                    delta_color="inverse"
                )
                st.caption(f"昨日同时: {metrics['yesterday_sales']} | 上周今日同时: {metrics['last_week_today_sales']}")
            with col2:
                st.metric(
                    "销售额",
                    f"${metrics['today_revenue']:.2f}",
                    delta=f"+{((metrics['today_revenue'] - metrics['yesterday_revenue']) / metrics['yesterday_revenue'] * 100):.2f}%" if metrics['yesterday_revenue'] > 0 else "-",
                    delta_color="inverse"
                )
                st.caption(f"昨日同时: ${metrics['yesterday_revenue']:.2f} | 上周今日同时: ${metrics['last_week_today_revenue']:.2f}")
            with col3:
                st.metric(
                    "订单量",
                    f"{metrics['today_orders']}",
                    delta=f"+{((metrics['today_orders'] - metrics['yesterday_orders']) / metrics['yesterday_orders'] * 100):.2f}%" if metrics['yesterday_orders'] > 0 else "-",
                    delta_color="inverse"
                )
                st.caption(f"昨日同时: {metrics['yesterday_orders']} | 上周今日同时: {metrics['last_week_today_orders']}")
            with col4:
                st.metric(
                    "销售均价",
                    f"${metrics['today_avg_price']:.2f}",
                    delta=f"{((metrics['today_avg_price'] - metrics['yesterday_avg_price']) / metrics['yesterday_avg_price'] * 100):.2f}%" if metrics['yesterday_avg_price'] > 0 else "-",
                    delta_color="inverse"
                )
                st.caption(f"昨日同时: ${metrics['yesterday_avg_price']:.2f} | 上周今日同时: ${metrics['last_week_today_avg_price']:.2f}")
            with col5:
                st.metric(
                    "取消订单数",
                    f"{metrics['today_cancel']}",
                    delta=f"-100.00%" if metrics['last_week_today_cancel'] > 0 else "-",
                    delta_color="inverse"
                )
                st.caption(f"昨天全天: {metrics['yesterday_cancel']} | 上周今日全天: {metrics['last_week_today_cancel']}")

            # 小时趋势图
            st.divider()
            st.markdown("#### 销量/销售额小时趋势")
            hourly_trend = get_hourly_trend(processed_df, analysis_date, yesterday_date)
            col_trend1, col_trend2 = st.columns(2)
            with col_trend1:
                fig_sales_trend = px.line(
                    hourly_trend,
                    x='小时',
                    y=['今日销量', '昨日销量'],
                    title='销量小时趋势对比',
                    markers=True,
                    height=300
                )
                st.plotly_chart(fig_sales_trend, use_container_width=True)
            with col_trend2:
                today_revenue_hourly = processed_df[processed_df['订单日期'] == analysis_date].groupby('小时')['销售总额'].sum().reset_index(name='今日销售额')
                yesterday_revenue_hourly = processed_df[processed_df['订单日期'] == yesterday_date].groupby('小时')['销售总额'].sum().reset_index(name='昨日销售额')
                revenue_trend = pd.merge(pd.DataFrame({'小时': range(24)}), today_revenue_hourly, on='小时', how='left').fillna(0)
                revenue_trend = pd.merge(revenue_trend, yesterday_revenue_hourly, on='小时', how='left').fillna(0)
                fig_revenue_trend = px.line(
                    revenue_trend,
                    x='小时',
                    y=['今日销售额', '昨日销售额'],
                    title='销售额小时趋势对比',
                    markers=True,
                    height=300
                )
                st.plotly_chart(fig_revenue_trend, use_container_width=True)

            # SKU多周期对比
            st.divider()
            st.markdown("#### SKU多周期销量对比")
            sku_multi = get_sku_multi_period(processed_df, analysis_date, yesterday_date, last_week_today_date)
            if 'SKU' in processed_df.columns:
                sku_multi = sku_multi.merge(processed_df[['SKU', 'ASIN', '产品名称']].drop_duplicates(), on='SKU', how='left')
                # 修复：同步调整显示列名（7天→七天、14天→十四天、30天→三十天）
                display_cols = ['SKU', 'ASIN', '产品名称', '七天销量', '十四天销量', '三十天销量', '今日销量', '今日订单量', '今日销售额', '昨日销量', '昨日订单量', '昨日销售额', '上周今日销量', '上周今日订单量', '上周今日销售额']
                st.dataframe(sku_multi[display_cols], use_container_width=True, height=400)
            else:
                st.warning("数据中缺少SKU字段，无法生成SKU多周期对比表")

        # --------------------------
        # 订单分析看板
        # --------------------------
        elif selected_page == "订单分析看板":
            st.subheader("📋 订单分析看板")
            st.info("整合所有订单分析功能：时间范围筛选、星期/小时统计、热力图、SKU排行榜、数据下载")

            # 时间范围筛选
            st.markdown("#### 时间范围筛选")
            data_min_date = processed_df['订单日期'].min()
            data_max_date = processed_df['订单日期'].max()
            data_max_datetime = processed_df[time_column].max()

            st.info(f"当前订单数据时间范围：{data_min_date} ~ {data_max_date}")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                btn_7d = st.button("近7天", use_container_width=True, key="order_7d")
            with col2:
                btn_14d = st.button("近14天", use_container_width=True, key="order_14d")
            with col3:
                btn_30d = st.button("近30天", use_container_width=True, key="order_30d")
            with col4:
                btn_last_month = st.button("上个月", use_container_width=True, key="order_last_month")
            with col5:
                btn_all = st.button("全部数据", use_container_width=True, key="order_all")

            st.markdown("##### 或自定义时间范围")
            col_start, col_end = st.columns(2)
            with col_start:
                custom_start_date = st.date_input("开始日期", value=data_min_date, min_value=data_min_date, max_value=data_max_date, key="order_start")
            with col_end:
                custom_end_date = st.date_input("结束日期", value=data_max_date, min_value=data_min_date, max_value=data_max_date, key="order_end")

            # 确定筛选范围
            filter_start_date = None
            filter_end_date = data_max_date
            if btn_7d:
                filter_start_date = (data_max_datetime - timedelta(days=7)).date()
            elif btn_14d:
                filter_start_date = (data_max_datetime - timedelta(days=14)).date()
            elif btn_30d:
                filter_start_date = (data_max_datetime - timedelta(days=30)).date()
            elif btn_last_month:
                last_month = data_max_datetime - relativedelta(months=1)
                filter_start_date = datetime(last_month.year, last_month.month, 1).date()
                first_day_current_month = datetime(data_max_datetime.year, data_max_datetime.month, 1)
                filter_end_date = (first_day_current_month - timedelta(days=1)).date()
            elif btn_all:
                filter_start_date = data_min_date
            else:
                filter_start_date = custom_start_date
                filter_end_date = custom_end_date

            filtered_df = processed_df[(processed_df['订单日期'] >= filter_start_date) & (processed_df['订单日期'] <= filter_end_date)]
            if len(filtered_df) == 0:
                st.warning(f"所选时间范围（{filter_start_date} ~ {filter_end_date}）内无订单数据！")
            else:
                st.success(f"筛选出 {filter_start_date} ~ {filter_end_date} 的订单数据，共 {len(filtered_df)} 条")

                # 重新统计
                hourly_stats = get_hourly_stats(filtered_df)
                weekly_stats = get_weekly_stats(filtered_df)
                cross_stats = get_week_hour_cross_stats(filtered_df)
                sku_ranking = get_sku_ranking(filtered_df)

                # 数据看板
                st.divider()
                st.markdown("#### 数据看板")
                col_week, col_hour = st.columns(2)
                with col_week:
                    st.markdown("##### 按星期统计")
                    fig_week = px.bar(
                        weekly_stats,
                        x='星期',
                        y='订单数',
                        title=f'各星期订单数量（{filter_start_date} ~ {filter_end_date}）',
                        color='订单数',
                        color_continuous_scale='Blues',
                        height=350
                    )
                    st.plotly_chart(fig_week, use_container_width=True)
                    with st.expander("查看星期统计数据"):
                        st.dataframe(weekly_stats, use_container_width=True)
                with col_hour:
                    st.markdown("##### 按24小时统计")
                    fig_hour = px.line(
                        hourly_stats,
                        x='小时',
                        y='订单数',
                        title=f'24小时订单数量趋势（{filter_start_date} ~ {filter_end_date}）',
                        markers=True,
                        height=350
                    )
                    st.plotly_chart(fig_hour, use_container_width=True)
                    with st.expander("查看小时统计数据"):
                        st.dataframe(hourly_stats, use_container_width=True)

                # 热力图
                st.divider()
                st.markdown("#### 星期×24小时交叉分析（热力图）")
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
                    title=f'各时段订单分布热力图（{filter_start_date} ~ {filter_end_date}）',
                    xaxis_title='小时',
                    yaxis_title='星期',
                    height=400
                )
                st.plotly_chart(fig_heatmap, use_container_width=True)

                # SKU排行榜
                st.divider()
                st.markdown("#### SKU销量排行榜")
                if not sku_ranking.empty:
                    sort_by = st.selectbox("按以下维度排序", options=['销量', '销售额'], index=0, key="ranking_sort")
                    top_n = st.slider("显示前N名", min_value=10, max_value=len(sku_ranking), value=min(50, len(sku_ranking)), step=10, key="ranking_topn")
                    if sort_by == '销量':
                        sku_ranking_sorted = sku_ranking.sort_values('销量', ascending=False).head(top_n)
                    else:
                        sku_ranking_sorted = sku_ranking.sort_values('销售额', ascending=False).head(top_n)
                    st.dataframe(sku_ranking_sorted, use_container_width=True, height=400)
                    csv_sku = sku_ranking_sorted.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"下载{sort_by}前{top_n}名SKU数据",
                        data=csv_sku,
                        file_name=f"SKU排行榜_{sort_by}_前{top_n}名_{filter_start_date}_{filter_end_date}.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("无法生成SKU排行榜，请检查数据中是否包含SKU、数量、采购总额、销售总额等字段")

                # 数据下载
                st.divider()
                st.markdown("#### 数据下载")
                col_download1, col_download2 = st.columns(2)
                with col_download1:
                    csv_hour = hourly_stats.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载24小时统计数据",
                        data=csv_hour,
                        file_name=f"订单小时统计_{filter_start_date}_{filter_end_date}.csv",
                        mime="text/csv"
                    )
                with col_download2:
                    csv_week = weekly_stats.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载星期统计数据",
                        data=csv_week,
                        file_name=f"订单星期统计_{filter_start_date}_{filter_end_date}.csv",
                        mime="text/csv"
                    )

    except Exception as e:
        st.error(f"数据处理失败：{str(e)}")
        st.info("请检查文件格式是否正确，或时间字段是否包含有效时间数据")
else:
    st.info("请上传订单文件开始分析（支持Excel/CSV格式）")
