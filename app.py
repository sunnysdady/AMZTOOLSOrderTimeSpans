import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta  # 处理月份计算

# --------------------------
# 页面基础配置
# --------------------------
st.set_page_config(
    page_title="订单出单时间统计看板",
    page_icon="📊",
    layout="wide"  # 宽屏布局，适配看板展示
)

# --------------------------
# 全局常量定义（新增：解决week_order未定义问题）
# --------------------------
WEEK_ORDER = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']  # 全局星期排序

# --------------------------
# 辅助函数：数据处理
# --------------------------
def process_order_data(df, time_column):
    """
    处理订单数据，提取小时、星期维度
    :param df: 原始订单DataFrame
    :param time_column: 订单时间字段名
    :return: 处理后的DataFrame
    """
    # 转换时间字段为datetime格式
    df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
    
    # 过滤无效时间数据
    df = df.dropna(subset=[time_column])
    
    # 提取维度字段
    df['小时'] = df[time_column].dt.hour  # 0-23小时
    df['星期'] = df[time_column].dt.dayofweek  # 0=周一，6=周日
    # 映射星期数字为中文
    week_mapping = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
    df['星期'] = df['星期'].map(week_mapping)
    
    return df

def get_hourly_stats(df):
    """按小时统计订单数"""
    hourly_stats = df.groupby('小时').size().reset_index(name='订单数')
    # 补全0-23小时（避免某些小时无数据时图表断层）
    all_hours = pd.DataFrame({'小时': range(24)})
    hourly_stats = pd.merge(all_hours, hourly_stats, on='小时', how='left').fillna(0)
    return hourly_stats

def get_weekly_stats(df):
    """按星期统计订单数"""
    weekly_stats = df.groupby('星期').size().reset_index(name='订单数')
    # 强制按周一到周日排序（使用全局常量）
    weekly_stats['星期'] = pd.Categorical(weekly_stats['星期'], categories=WEEK_ORDER, ordered=True)
    weekly_stats = weekly_stats.sort_values('星期').reset_index(drop=True)
    return weekly_stats

def get_week_hour_cross_stats(df):
    """星期×小时交叉统计（核心看板）"""
    cross_stats = df.groupby(['星期', '小时']).size().reset_index(name='订单数')
    # 补全所有星期×小时组合（使用全局常量）
    all_week_hour = pd.MultiIndex.from_product([WEEK_ORDER, range(24)], names=['星期', '小时']).to_frame(index=False)
    cross_stats = pd.merge(all_week_hour, cross_stats, on=['星期', '小时'], how='left').fillna(0)
    return cross_stats

def calculate_time_range(data_max_date, range_type):
    """
    根据选择的时间范围类型，计算起始日期
    :param data_max_date: 订单数据中的最大日期（最新订单日期）
    :param range_type: 时间范围类型（近7天/14天/30天/上个月/自定义）
    :return: 起始日期（datetime对象）
    """
    if range_type == "近7天":
        start_date = data_max_date - timedelta(days=7)
    elif range_type == "近14天":
        start_date = data_max_date - timedelta(days=14)
    elif range_type == "近30天":
        start_date = data_max_date - timedelta(days=30)
    elif range_type == "上个月":
        # 上个月第一天 到 上个月最后一天
        last_month = data_max_date - relativedelta(months=1)
        start_date = datetime(last_month.year, last_month.month, 1)
    else:  # 自定义，后续由用户选择的日期决定
        start_date = None
    return start_date

# --------------------------
# 页面UI & 核心逻辑
# --------------------------
st.title("📊 订单出单时间统计看板")
st.divider()

# 1. 文件上传区域
st.subheader("1. 上传订单文件")
uploaded_file = st.file_uploader(
    "支持格式：Excel(.xlsx)、CSV(.csv)",
    type=['xlsx', 'csv'],
    help="请确保文件包含订单时间字段（如：出单时间、下单时间等）"
)

if uploaded_file is not None:
    # 读取文件
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        # 展示原始数据预览
        st.subheader("数据预览")
        st.dataframe(df.head(5), use_container_width=True)
        
        # 让用户选择订单时间字段
        time_column = st.selectbox(
            "请选择订单时间字段",
            options=df.columns.tolist(),
            help="选择包含出单时间的列（如：下单时间、支付时间等）"
        )
        
        # 处理数据
        with st.spinner("正在处理数据..."):
            processed_df = process_order_data(df, time_column)
        
        st.success("数据处理完成！")
        st.divider()
        
        # 2. 时间范围筛选区域
        st.subheader("2. 时间范围筛选")
        
        # 获取订单数据的时间边界
        data_min_date = processed_df[time_column].dt.date.min()
        data_max_date = processed_df[time_column].dt.date.max()
        data_max_datetime = processed_df[time_column].max()  # 带时分秒的最新时间
        
        # 显示数据时间范围提示
        st.info(f"当前订单数据时间范围：{data_min_date} ~ {data_max_date}")
        
        # 快捷时间范围按钮（一行排列）
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            btn_7d = st.button("近7天", use_container_width=True)
        with col2:
            btn_14d = st.button("近14天", use_container_width=True)
        with col3:
            btn_30d = st.button("近30天", use_container_width=True)
        with col4:
            btn_last_month = st.button("上个月", use_container_width=True)
        with col5:
            btn_all = st.button("全部数据", use_container_width=True)
        
        # 自定义日期选择器
        st.markdown("##### 或自定义时间范围")
        col_start, col_end = st.columns(2)
        with col_start:
            custom_start_date = st.date_input(
                "开始日期",
                value=data_min_date,
                min_value=data_min_date,
                max_value=data_max_date
            )
        with col_end:
            custom_end_date = st.date_input(
                "结束日期",
                value=data_max_date,
                min_value=data_min_date,
                max_value=data_max_date
            )
        
        # 确定最终筛选的时间范围
        filter_start_date = None
        filter_end_date = data_max_date  # 默认结束日期为最新
        
        if btn_7d:
            filter_start_date = (data_max_datetime - timedelta(days=7)).date()
        elif btn_14d:
            filter_start_date = (data_max_datetime - timedelta(days=14)).date()
        elif btn_30d:
            filter_start_date = (data_max_datetime - timedelta(days=30)).date()
        elif btn_last_month:
            # 上个月的时间范围：上个月1号 到 上个月最后一天
            last_month = data_max_datetime - relativedelta(months=1)
            filter_start_date = datetime(last_month.year, last_month.month, 1).date()
            # 计算上个月最后一天
            first_day_current_month = datetime(data_max_datetime.year, data_max_datetime.month, 1)
            filter_end_date = (first_day_current_month - timedelta(days=1)).date()
        elif btn_all:
            filter_start_date = data_min_date
        else:
            # 自定义日期
            filter_start_date = custom_start_date
            filter_end_date = custom_end_date
        
        # 过滤数据（转换为date比较，避免时分秒干扰）
        processed_df['订单日期'] = processed_df[time_column].dt.date
        filtered_df = processed_df[
            (processed_df['订单日期'] >= filter_start_date) & 
            (processed_df['订单日期'] <= filter_end_date)
        ]
        
        # 验证过滤后的数据是否为空
        if len(filtered_df) == 0:
            st.warning(f"所选时间范围（{filter_start_date} ~ {filter_end_date}）内无订单数据！")
        else:
            st.success(f"筛选出 {filter_start_date} ~ {filter_end_date} 的订单数据，共 {len(filtered_df)} 条")
            
            # 重新统计筛选后的数据
            hourly_stats = get_hourly_stats(filtered_df)
            weekly_stats = get_weekly_stats(filtered_df)
            cross_stats = get_week_hour_cross_stats(filtered_df)
            
            # 3. 数据看板区域
            st.divider()
            st.subheader("3. 数据看板")
            
            # 分栏展示：左侧星期维度，右侧小时维度
            col_week, col_hour = st.columns(2)
            
            # 3.1 星期维度统计
            with col_week:
                st.markdown("#### 按星期统计")
                # 可视化：柱状图
                fig_week = px.bar(
                    weekly_stats,
                    x='星期',
                    y='订单数',
                    title=f'各星期订单数量（{filter_start_date} ~ {filter_end_date}）',
                    color='订单数',
                    color_continuous_scale='Blues',
                    height=400
                )
                fig_week.update_layout(showlegend=False)
                st.plotly_chart(fig_week, use_container_width=True)
                # 数据表格
                with st.expander("查看星期统计数据"):
                    st.dataframe(weekly_stats, use_container_width=True)
            
            # 3.2 小时维度统计
            with col_hour:
                st.markdown("#### 按24小时统计")
                # 可视化：折线图（更适合小时趋势）
                fig_hour = px.line(
                    hourly_stats,
                    x='小时',
                    y='订单数',
                    title=f'24小时订单数量趋势（{filter_start_date} ~ {filter_end_date}）',
                    markers=True,
                    height=400
                )
                fig_hour.update_xaxes(tick0=0, dtick=1)  # 小时轴显示0-23
                st.plotly_chart(fig_hour, use_container_width=True)
                # 数据表格
                with st.expander("查看小时统计数据"):
                    st.dataframe(hourly_stats, use_container_width=True)
            
            # 3.3 星期×24小时交叉分析（热力图）- 修复week_order未定义问题
            st.markdown("#### 星期×24小时交叉分析（热力图）")
            # 转换为透视表适配热力图（使用全局常量WEEK_ORDER）
            pivot_table = cross_stats.pivot(index='星期', columns='小时', values='订单数')
            # 按周一到周日排序（使用全局常量）
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
                height=500
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)
            
            # 4. 数据下载区域
            st.divider()
            st.subheader("4. 数据下载")
            col_download1, col_download2 = st.columns(2)
            with col_download1:
                # 导出小时统计数据
                csv_hour = hourly_stats.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="下载24小时统计数据",
                    data=csv_hour,
                    file_name=f"订单小时统计_{filter_start_date}_{filter_end_date}.csv",
                    mime="text/csv"
                )
            with col_download2:
                # 导出星期统计数据
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
