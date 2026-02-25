import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --------------------------
# 页面基础配置
# --------------------------
st.set_page_config(
    page_title="订单出单时间统计看板",
    page_icon="📊",
    layout="wide"  # 宽屏布局，适配看板展示
)

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
    # 强制按周一到周日排序
    week_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekly_stats['星期'] = pd.Categorical(weekly_stats['星期'], categories=week_order, ordered=True)
    weekly_stats = weekly_stats.sort_values('星期').reset_index(drop=True)
    return weekly_stats

def get_week_hour_cross_stats(df):
    """星期×小时交叉统计（核心看板）"""
    cross_stats = df.groupby(['星期', '小时']).size().reset_index(name='订单数')
    # 补全所有星期×小时组合
    week_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    all_week_hour = pd.MultiIndex.from_product([week_order, range(24)], names=['星期', '小时']).to_frame(index=False)
    cross_stats = pd.merge(all_week_hour, cross_stats, on=['星期', '小时'], how='left').fillna(0)
    return cross_stats

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
            hourly_stats = get_hourly_stats(processed_df)
            weekly_stats = get_weekly_stats(processed_df)
            cross_stats = get_week_hour_cross_stats(processed_df)
        
        st.success("数据处理完成！")
        st.divider()
        
        # 2. 数据看板区域
        st.subheader("2. 数据看板")
        
        # 分栏展示：左侧星期维度，右侧小时维度
        col1, col2 = st.columns(2)
        
        # 2.1 星期维度统计
        with col1:
            st.markdown("#### 按星期统计")
            # 可视化：柱状图
            fig_week = px.bar(
                weekly_stats,
                x='星期',
                y='订单数',
                title='各星期订单数量',
                color='订单数',
                color_continuous_scale='Blues',
                height=400
            )
            fig_week.update_layout(showlegend=False)
            st.plotly_chart(fig_week, use_container_width=True)
            # 数据表格
            with st.expander("查看星期统计数据"):
                st.dataframe(weekly_stats, use_container_width=True)
        
        # 2.2 小时维度统计
        with col2:
            st.markdown("#### 按24小时统计")
            # 可视化：折线图（更适合小时趋势）
            fig_hour = px.line(
                hourly_stats,
                x='小时',
                y='订单数',
                title='24小时订单数量趋势',
                markers=True,
                height=400
            )
            fig_hour.update_xaxes(tick0=0, dtick=1)  # 小时轴显示0-23
            st.plotly_chart(fig_hour, use_container_width=True)
            # 数据表格
            with st.expander("查看小时统计数据"):
                st.dataframe(hourly_stats, use_container_width=True)
        
        # 2.3 星期×小时交叉热力图（核心看板）
        st.markdown("#### 星期×24小时交叉分析（热力图）")
        # 转换为透视表适配热力图
        pivot_table = cross_stats.pivot(index='星期', columns='小时', values='订单数')
        # 按周一到周日排序
        pivot_table = pivot_table.reindex(week_order)
        
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
            height=500
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # 3. 数据下载区域
        st.divider()
        st.subheader("3. 数据下载")
        col_download1, col_download2 = st.columns(2)
        with col_download1:
            # 导出小时统计数据
            csv_hour = hourly_stats.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="下载24小时统计数据",
                data=csv_hour,
                file_name=f"订单小时统计_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        with col_download2:
            # 导出星期统计数据
            csv_week = weekly_stats.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="下载星期统计数据",
                data=csv_week,
                file_name=f"订单星期统计_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.error(f"数据处理失败：{str(e)}")
        st.info("请检查文件格式是否正确，或时间字段是否包含有效时间数据")
else:
    st.info("请上传订单文件开始分析（支持Excel/CSV格式）")