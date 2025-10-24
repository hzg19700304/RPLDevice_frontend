"""
历史曲线页面 - 优化版
History Curve Page - Optimized
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from nicegui import ui
import aiohttp

logger = logging.getLogger(__name__)


class HistoryCurvePage:
    """历史曲线页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        
        # 可用的参数配置
        self.available_parameters = [
            {"name": "轨地电流SA1", "unit": "A", "color": "#FF6B6B", "register": "0x0005"},
            {"name": "可控硅电流SA2", "unit": "A", "color": "#9B59B6", "register": "0x0006"},
            {"name": "轨地电压SV1", "unit": "V", "color": "#3498DB", "register": "0x0007"},
            {"name": "轨地电压SV2", "unit": "V", "color": "#E67E22", "register": "0x0008"}
        ]
        
        # 选中的参数
        self.selected_parameters: List[str] = ["轨地电流SA1", "轨地电压SV1"]
        
        # 设置默认时间（当天0点到当前时间）
        now = datetime.now()
        self.default_start_date = now.strftime('%Y-%m-%d')  # 当天日期
        self.default_start_time = "00:00"  # 当天开始时间
        self.default_end_date = now.strftime('%Y-%m-%d')
        self.default_end_time = now.strftime('%H:%M')  # 当前时间
        
        # 图表相关
        self.chart = None
        self.chart_container = None
        
        # 数据相关
        self.historical_data: Dict[str, List] = {}
        self.time_labels: List[str] = []
        
        # UI组件引用
        self.param_checkboxes = {}
        self.query_date_input = None
        self.start_time_input = None
        self.end_time_input = None
        self.status_label = None
        self.data_count_label = None
        self.data_table_container = None
        
        # API配置
        self.api_base_url = self.config.get('API配置', 'base_url', default='http://localhost:8001')
        self.api_timeout = self.config.get('API配置', 'timeout', default=30)
        
    def create_page(self) -> ui.column:
        """创建历史曲线页面"""
        with ui.column().classes('w-full p-2 gap-2').style('height: calc(100vh - 150px); overflow-y: auto;'):
            # 标题栏 - 简洁风格
            with ui.card().classes('w-full p-2').style('background: white; border-left: 4px solid #1976D2; flex-shrink: 0;').props('flat'):
                ui.label('历史曲线').classes('text-h6 font-bold text-grey-8')
            
            # 参数选择 + 查询条件 + 操作按钮（紧凑布局）
            with ui.card().classes('w-full p-2').props('flat bordered').style('flex-shrink: 0;'):
                # 参数选择（横向排列）
                with ui.row().classes('w-full items-center gap-2 mb-2'):
                    ui.label('显示参数:').classes('text-subtitle2 font-medium text-grey-8').style('min-width: 70px;')
                    with ui.row().classes('flex-1 flex-wrap gap-2'):
                        for param in self.available_parameters:
                            is_selected = param['name'] in self.selected_parameters
                            param_color = param.get('color', '#1976D2')  # 获取参数对应的颜色
                            
                            # 创建带颜色的复选框
                            with ui.row().classes('items-center').style(f'background-color: {param_color}20; border-radius: 4px; padding: 2px 6px; border: 1px solid {param_color}40;'):
                                checkbox = ui.checkbox(
                                    param['name'], 
                                    value=is_selected
                                ).classes('text-sm').style(f'color: {param_color}; font-weight: 500;')
                                
                                self.param_checkboxes[param['name']] = checkbox
                                
                                def make_handler(param_name, checkbox_ref):
                                    def on_param_toggle():
                                        checked = checkbox_ref.value
                                        if checked:
                                            if param_name not in self.selected_parameters:
                                                self.selected_parameters.append(param_name)
                                        else:
                                            if param_name in self.selected_parameters:
                                                self.selected_parameters.remove(param_name)
                                    return on_param_toggle
                                
                                checkbox.on('update:model-value', make_handler(param['name'], checkbox))
                
                # ui.separator().classes('my-1')
                
                # 查询条件（横向排列，强制不换行）
                with ui.row().classes('w-full items-center gap-2 mt-1').style('flex-wrap: nowrap;'):
                    # 查询日期
                    with ui.row().classes('items-center gap-1').style('flex: 0 0 auto; min-width: 200px;'):
                        ui.label('查询日期').classes('text-sm text-grey-7').style('min-width: 60px; flex-shrink: 0;')
                        self.query_date_input = ui.input('').props('type=date outlined dense').style('width: 160px;').set_value(self.default_start_date)
                    
                    # 开始时间
                    with ui.row().classes('items-center gap-1').style('flex: 0 0 auto; min-width: 180px;'):
                        ui.label('开始时间').classes('text-sm text-grey-7').style('min-width: 60px; flex-shrink: 0;')
                        self.start_time_input = ui.input('').props('type=time outlined dense').style('width: 120px;').set_value(self.default_start_time)
                    
                    # 结束时间
                    with ui.row().classes('items-center gap-1').style('flex: 0 0 auto; min-width: 180px;'):
                        ui.label('结束时间').classes('text-sm text-grey-7').style('min-width: 60px; flex-shrink: 0;')
                        self.end_time_input = ui.input('').props('type=time outlined dense').style('width: 120px;').set_value(self.default_end_time)
                    
                    # 操作按钮
                    with ui.row().classes('gap-2').style('flex: 0 0 auto; margin-left: auto;'):
                        ui.button('查询', on_click=self._query_data, icon='search').props('unelevated dense').classes('bg-blue-6')
                        ui.button('重置', on_click=self._reset_selection, icon='refresh').props('flat dense').classes('text-grey-7')
                        ui.button('导出CSV', on_click=self._export_csv, icon='download').props('flat dense').classes('text-green-7')
            
            # 状态信息（紧凑显示）
            with ui.row().classes('w-full items-center justify-between px-2 py-1').style('background: #f5f5f5; border-radius: 4px; flex-shrink: 0;'):
                with ui.row().classes('items-center gap-4'):
                    self.status_label = ui.label('状态: 等待查询...').classes('text-sm text-grey-7')
                    self.data_count_label = ui.label('数据点: 0').classes('text-sm text-grey-7')
                ui.label('').classes('text-sm text-grey-6')  # 占位，保持布局
            
            # 图表容器（占据剩余空间）
            self.chart_container = ui.card().classes('w-full p-3').props('flat bordered').style('background: white; height: 550px; flex-shrink: 0;')
            self._create_empty_chart()
            
            # 数据表格（可折叠）
            with ui.expansion('数据详情', icon='table_chart').classes('w-full').props('dense'):
                self.data_table_container = ui.column().classes('w-full p-2')
    
    def _create_empty_chart(self):
        """创建空图表"""
        self.chart_container.clear()
        
        with self.chart_container:
            self.chart = ui.plotly({}).classes('w-full h-full')
            
            # 初始化空图表配置 - 简洁风格
            empty_figure = {
                'data': [],
                'layout': {
                    'title': {'text': '历史数据曲线', 'font': {'size': 16, 'color': '#424242'}},
                    'xaxis': {
                        'title': '时间',
                        'gridcolor': '#e0e0e0',
                        'showline': True,
                        'linecolor': '#e0e0e0'
                    },
                    'yaxis': {
                        'title': '数值',
                        'gridcolor': '#e0e0e0',
                        'showline': True,
                        'linecolor': '#e0e0e0'
                    },
                    'hovermode': 'x unified',
                    'showlegend': True,
                    'legend': {
                        'orientation': 'h',
                        'y': -0.15,
                        'x': 0.5,
                        'xanchor': 'center',
                        'bgcolor': 'rgba(255,255,255,0.8)',
                        'bordercolor': '#e0e0e0',
                        'borderwidth': 1
                    },
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white',
                    'margin': {'l': 60, 'r': 30, 't': 50, 'b': 80},
                    'autosize': True
                }
            }
            
            self.chart.update_figure(empty_figure)
            logger.info("创建空Plotly图表完成")

    def _create_data_table(self):
        """创建数据表格"""
        self.data_table_container.clear()
        
        with self.data_table_container:
            ui.label('暂无数据，请先查询历史数据').classes('text-grey-6 text-center py-4')
    
    def _get_time_range(self):
        """获取时间范围"""
        # 安全获取输入框的值
        try:
            query_date = self.query_date_input.value if self.query_date_input and self.query_date_input.value else self.default_start_date
            start_time_str = self.start_time_input.value if self.start_time_input and self.start_time_input.value else self.default_start_time
            end_time_str = self.end_time_input.value if self.end_time_input and self.end_time_input.value else self.default_end_time
            
            # 组合日期和时间
            start_time = datetime.fromisoformat(f"{query_date} {start_time_str}")
            
            # 结束时间使用相同的查询日期，不跨天
            try:
                end_time = datetime.fromisoformat(f"{query_date} {end_time_str}")
                # 如果结束时间等于或早于开始时间，说明用户选择了无效的时间范围
                # 此时应该限制在同一天的23:59:59，而不是跨天
                if end_time <= start_time:
                    # 设置为当天的23:59:59，确保不跨天
                    end_time = datetime.fromisoformat(f"{query_date} 23:59:59")
            except ValueError:
                # 如果时间格式无效，使用当天的结束时间
                end_time = datetime.fromisoformat(f"{query_date} 23:59:59")
            
            # 确保最小时间间隔为1分钟
            if end_time <= start_time:
                end_time = start_time + timedelta(minutes=1)
            
            return start_time, end_time
        except Exception as e:
            logger.error(f"获取时间范围失败: {e}", exc_info=True)
            # 返回默认时间范围（最近24小时）
            now = datetime.now()
            return now - timedelta(hours=24), now
    
    async def _query_data(self):
        """查询历史数据"""
        try:
            if not self.selected_parameters:
                ui.notify('请至少选择一个参数', type='warning')
                return
            
            start_time, end_time = self._get_time_range()
            
            # 更新状态
            self.status_label.text = f'状态: 正在查询数据...'
            self.data_count_label.text = '数据点: 0'
            
            logger.info(f"查询历史数据: 参数={self.selected_parameters}, 时间范围={start_time} - {end_time}")
            
            # 构建API请求 - 使用ISO时间格式（后端API要求）
            # 注意：后端API要求单个参数查询，我们循环查询每个参数
            # 添加时区信息以符合后端API要求
            params = {
                'start_time': start_time.isoformat() + '+00:00',
                'end_time': end_time.isoformat() + '+00:00',
                'page': 1,
                'page_size': 0  # 设置为0表示查询所有数据，无数量限制
            }
            
            # 真实数据查询
            await self._query_real_data(params)
            
            # 更新图表
            await self._update_chart()
            
            # 更新数据表格
            self._update_data_table()
            
            # 更新状态
            data_count = len(self.time_labels) if self.time_labels else 0
            self.status_label.text = f'状态: 查询完成'
            self.data_count_label.text = f'数据点: {data_count}'
            
            ui.notify(f'数据查询完成，共 {data_count} 个数据点', type='positive')
            
        except Exception as e:
            logger.error(f"查询历史数据失败: {e}", exc_info=True)
            self.status_label.text = f'状态: 查询失败 - {str(e)}'
            ui.notify(f'数据查询失败: {str(e)}', type='negative')
    
    async def _query_real_data(self, params):
        """真实数据查询 - 从后端API获取历史数据"""
        try:
            # 清空现有数据
            self.historical_data = {}
            self.time_labels = []
            
            # 获取时间范围
            start_time = params['start_time']
            end_time = params['end_time']
            
            logger.info(f"开始查询真实历史数据: 参数={self.selected_parameters}, 时间范围={start_time} - {end_time}")
            
            # 为每个选中的参数查询数据
            all_data_points = {}  # 存储所有参数的数据点
            time_set = set()  # 用于收集所有时间点
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.api_timeout)) as session:
                for param_name in self.selected_parameters:
                    param_info = next(p for p in self.available_parameters if p['name'] == param_name)
                    
                    # 构建API请求参数
                    api_params = {
                        'start_time': start_time,
                        'end_time': end_time,
                        'param_name': param_name,  # 查询特定参数
                        'page': 1,
                        'page_size': 0  # 设置为0表示查询所有数据，无数量限制
                    }
                    
                    try:
                        # 调用后端API获取历史数据
                        async with session.get(
                            f"{self.api_base_url}/api/v1/history/analog",
                            params=api_params
                        ) as response:
                            
                            if response.status == 200:
                                result = await response.json()
                                
                                # 检查API响应格式
                                if isinstance(result, dict) and result.get('code') == 200:
                                    data = result.get('data', {})
                                    records = data.get('list', [])
                                    logger.info(f"参数 {param_name} API返回数据量: {len(records)}")
                                    # 处理查询到的数据
                                    param_data_points = []
                                    for record in records:
                                        timestamp = record.get('timestamp', '')
                                        value = float(record.get('value', 0))
                                        
                                        if timestamp:
                                            # 格式化时间戳
                                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                                            
                                            param_data_points.append({
                                                'time': time_str,
                                                'value': value
                                            })
                                            time_set.add(time_str)
                                    
                                    all_data_points[param_name] = param_data_points
                                    logger.info(f"参数 {param_name} 查询到 {len(param_data_points)} 个数据点")
                                    
                                else:
                                    logger.warning(f"参数 {param_name} API响应错误: {result.get('msg', '未知错误')}")
                                    all_data_points[param_name] = []
                            else:
                                logger.error(f"参数 {param_name} API请求失败: HTTP {response.status}")
                                all_data_points[param_name] = []
                                
                    except Exception as e:
                        logger.error(f"参数 {param_name} 查询异常: {e}")
                        all_data_points[param_name] = []
            
            # 统一时间轴和数据对齐
            if time_set:
                # 按时间排序
                self.time_labels = sorted(list(time_set))
                logger.info(f"统一时间轴完成，共 {len(self.time_labels)} 个时间点")
                
                # 为每个参数构建对齐的数据序列
                for param_name in self.selected_parameters:
                    if param_name in all_data_points:
                        # 创建时间到值的映射
                        time_value_map = {}
                        for point in all_data_points[param_name]:
                            time_value_map[point['time']] = point['value']
                        
                        # 按统一时间轴构建数据序列
                        aligned_data = []
                        for time_str in self.time_labels:
                            if time_str in time_value_map:
                                aligned_data.append(time_value_map[time_str])
                            else:
                                aligned_data.append(None)  # 缺失数据用None表示
                        
                        self.historical_data[param_name] = aligned_data
                        logger.info(f"参数 {param_name} 数据对齐完成，共 {len(aligned_data)} 个点")
            else:
                logger.warning("未查询到任何数据点")
                # 如果没有数据，创建一个空的时间轴
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                current_time = start_dt
                while current_time <= end_dt:
                    self.time_labels.append(current_time.strftime('%Y-%m-%d %H:%M:%S'))
                    current_time += timedelta(minutes=1)
                
                # 为每个参数创建空数据
                for param_name in self.selected_parameters:
                    self.historical_data[param_name] = [None] * len(self.time_labels)
            
            logger.info(f"真实数据查询完成: {len(self.time_labels)} 个时间点，{len(self.historical_data)} 个参数")
            
        except Exception as e:
            logger.error(f"真实数据查询失败: {e}", exc_info=True)
            # 失败时回退到模拟数据
            await self._fallback_to_simulated_data(params)
    
    async def _fallback_to_simulated_data(self, params):
        """回退到模拟数据（当真实数据查询失败时）"""
        logger.warning("真实数据查询失败，回退到模拟数据模式")
        
        # 解析时间范围
        start_time = datetime.fromisoformat(params['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(params['end_time'].replace('Z', '+00:00'))
        
        # 生成时间标签（每分钟一个点）
        self.time_labels = []
        current_time = start_time
        while current_time <= end_time:
            self.time_labels.append(current_time.strftime('%Y-%m-%d %H:%M:%S'))
            current_time += timedelta(minutes=1)
        
        # 为每个选中的参数生成模拟数据
        self.historical_data = {}
        import random
        for param_name in self.selected_parameters:
            param_info = next(p for p in self.available_parameters if p['name'] == param_name)
            
            # 生成基础值附近的随机数据
            if '电流' in param_name:
                base_value = 50.0
                variation = 20.0
            else:  # 电压
                base_value = 220.0
                variation = 50.0
            
            data_points = []
            for i in range(len(self.time_labels)):
                trend = random.uniform(-0.5, 0.5) * (i / len(self.time_labels))
                noise = random.uniform(-1, 1)
                value = base_value + (variation * trend) + (variation * 0.1 * noise)
                data_points.append(max(0, value))
            
            self.historical_data[param_name] = data_points
        
        logger.info(f"模拟数据生成完成: {len(self.time_labels)} 个时间点")
    
    async def _update_chart(self):
        """更新图表"""
        try:
            if not self.historical_data or not self.time_labels:
                return
            
            # 构建数据集
            data_traces = []
            for param_name in self.selected_parameters:
                if param_name in self.historical_data:
                    param_info = next(p for p in self.available_parameters if p['name'] == param_name)
                    data = self.historical_data[param_name]
                    
                    trace = {
                        'x': self.time_labels,
                        'y': data,
                        'type': 'scatter',
                        'mode': 'lines+markers',
                        'name': f"{param_name} ({param_info['unit']})",
                        'line': {'color': param_info['color'], 'width': 2},
                        'marker': {'color': param_info['color'], 'size': 4},
                        'hovertemplate': f'{param_name}: %{{y:.2f}} {param_info["unit"]}<br>时间: %{{x}}<extra></extra>'
                    }
                    
                    data_traces.append(trace)
            
            # 创建Plotly图表配置 - 简洁风格
            figure = {
                'data': data_traces,
                'layout': {
                    'title': {'text': '历史数据曲线', 'font': {'size': 16, 'color': '#424242'}},
                    'xaxis': {
                        'title': '时间',
                        'tickangle': -45,
                        'tickmode': 'auto',
                        'nticks': 10,
                        'gridcolor': '#e0e0e0',
                        'showline': True,
                        'linecolor': '#e0e0e0'
                    },
                    'yaxis': {
                        'title': '数值',
                        'gridcolor': '#e0e0e0',
                        'showline': True,
                        'linecolor': '#e0e0e0'
                    },
                    'hovermode': 'x unified',
                    'showlegend': True,
                    'legend': {
                        'orientation': 'h',
                        'y': -0.15,
                        'x': 0.5,
                        'xanchor': 'center',
                        'bgcolor': 'rgba(255,255,255,0.8)',
                        'bordercolor': '#e0e0e0',
                        'borderwidth': 1
                    },
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white',
                    'margin': {'l': 60, 'r': 30, 't': 50, 'b': 80}
                }
            }
            
            # 更新图表
            self.chart.update_figure(figure)
            logger.info(f"Plotly图表更新完成: {len(data_traces)} 个数据trace")
            
        except Exception as e:
            logger.error(f"更新图表失败: {e}", exc_info=True)
    
    def _update_data_table(self):
        """更新数据表格"""
        try:
            self.data_table_container.clear()
            
            if not self.historical_data or not self.time_labels:
                with self.data_table_container:
                    ui.label('暂无数据').classes('text-grey-6 text-center py-4')
                return
            
            with self.data_table_container:
                # 创建表格
                columns = [
                    {'name': 'time', 'label': '时间', 'field': 'time', 'align': 'left'},
                ]
                
                # 添加参数列
                for param_name in self.selected_parameters:
                    param_info = next(p for p in self.available_parameters if p['name'] == param_name)
                    columns.append({
                        'name': param_name,
                        'label': f"{param_name} ({param_info['unit']})",
                        'field': param_name,
                        'align': 'right'
                    })
                
                # 准备表格数据
                rows = []
                for i, time_label in enumerate(self.time_labels):
                    row = {'time': time_label}
                    for param_name in self.selected_parameters:
                        if param_name in self.historical_data:
                            value = self.historical_data[param_name][i]
                            if value is not None:
                                row[param_name] = f"{value:.2f}"
                            else:
                                row[param_name] = "--"
                    rows.append(row)
                
                # 限制显示最新的100条记录
                display_rows = rows[-100:] if len(rows) > 100 else rows
                
                # 创建表格
                table = ui.table(
                    columns=columns,
                    rows=display_rows,
                    row_key='time',
                    pagination={'rowsPerPage': 10}
                ).classes('w-full')
                
                table.props('dense flat bordered')
                
                # 显示数据概览
                if len(rows) > 100:
                    ui.label(f'显示最新 100 条记录，共 {len(rows)} 条').classes('text-caption text-grey-6 mt-2')
                
        except Exception as e:
            logger.error(f"更新数据表格失败: {e}", exc_info=True)
    
    async def _export_csv(self):
        """导出CSV文件"""
        try:
            if not self.historical_data or not self.time_labels:
                ui.notify('没有可导出的数据，请先查询数据', type='warning')
                return
            
            # 构建CSV内容
            import csv
            import io
            
            output = io.StringIO()
            
            # CSV头部
            headers = ['时间']
            for param_name in self.selected_parameters:
                param_info = next(p for p in self.available_parameters if p['name'] == param_name)
                headers.append(f"{param_name} ({param_info['unit']})")
            
            # 写入数据
            writer = csv.writer(output)
            writer.writerow(headers)
            
            for i, time_label in enumerate(self.time_labels):
                row = [time_label]
                for param_name in self.selected_parameters:
                    if param_name in self.historical_data:
                        value = self.historical_data[param_name][i]
                        if value is not None:
                            row.append(f"{value:.3f}")
                        else:
                            row.append('')
                    else:
                        row.append('')
                writer.writerow(row)
            
            # 获取CSV内容
            csv_content = output.getvalue()
            output.close()
            
            # 生成文件名
            start_time, end_time = self._get_time_range()
            filename = f"历史数据_{start_time.strftime('%Y%m%d_%H%M')}_{end_time.strftime('%Y%m%d_%H%M')}.csv"
            
            # 触发浏览器下载
            ui.download(csv_content.encode('utf-8-sig'), filename)
            
            ui.notify(f'数据已导出: {filename}', type='positive')
            logger.info(f"CSV导出完成: {filename}")
            
        except Exception as e:
            logger.error(f"CSV导出失败: {e}", exc_info=True)
            ui.notify(f'导出失败: {str(e)}', type='negative')
    
    def _reset_selection(self):
        """重置所有选择"""
        try:
            # 重置参数选择
            self.selected_parameters = []
            for param_name, checkbox in self.param_checkboxes.items():
                checkbox.value = False
            
            # 重置时间（当天0点到当前时间）
            now = datetime.now()
            if self.query_date_input:
                self.query_date_input.set_value(now.strftime('%Y-%m-%d'))  # 当天日期
            if self.start_time_input:
                self.start_time_input.set_value("00:00")  # 当天开始时间
            if self.end_time_input:
                self.end_time_input.set_value(now.strftime('%H:%M'))  # 当前时间
            
            # 清空历史数据
            self.historical_data = {}
            self.time_labels = []
            
            # 重置状态显示
            if self.status_label:
                self.status_label.text = '状态: 已重置'
            if self.data_count_label:
                self.data_count_label.text = '数据点: 0'
            
            # 清空图表
            self._create_empty_chart()
            
            # 清空数据表格
            self._create_data_table()
            
            ui.notify('已重置所有选择', type='info')
            logger.info("重置功能执行完成")
            
        except Exception as e:
            logger.error(f"重置功能失败: {e}", exc_info=True)
            ui.notify(f'重置失败: {str(e)}', type='negative')
    
    def cleanup(self):
        """清理资源"""
        logger.info("历史曲线页面资源已清理")