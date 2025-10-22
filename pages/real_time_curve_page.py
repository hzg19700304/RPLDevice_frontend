"""
实时曲线页面 - 修复版
Real-time Curve Page - Fixed Version
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from nicegui import ui
from collections import deque

logger = logging.getLogger(__name__)


class RealTimeCurvePage:
    """实时曲线页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        
        # 曲线数据管理
        self.curve_data: Dict[str, deque] = {}  # 参数名 -> 数据队列
        self.time_stamps: deque = deque(maxlen=120)  # 时间戳队列，2分钟数据（每秒1个点）
        
        # 参数配置 - 根据配置文件中的SA1/SA2/SV1/SV2模拟量
        self.available_parameters = [
            {"name": "轨地电流SA1", "unit": "A", "color": "#FF6B6B"},
            {"name": "可控硅电流SA2", "unit": "A", "color": "#9B59B6"},
            {"name": "轨地电压SV1", "unit": "V", "color": "#3498DB"},
            {"name": "轨地电压SV2", "unit": "V", "color": "#E67E22"}
        ]
        
        # 选中的参数 - 默认选择SA1和SV1
        self.selected_parameters: List[str] = ["轨地电流SA1", "轨地电压SV1"]
        
        # 图表相关
        self.chart = None
        self.chart_container = None
        self.is_running = False
        self.update_timer = None
        self.chart_initialized = False
        
        # UI客户端引用 - 用于后台任务中的UI更新
        self.ui_client = None
        
        # 数据接收状态
        self.last_data_time = None
        self.data_count = 0
        
        # 注册WebSocket回调
        self._setup_data_callbacks()
        
    def _setup_data_callbacks(self):
        """设置数据回调"""
        if self.websocket_client:
            self.websocket_client.register_data_callback('analog_data', self._handle_analog_data)
            # logger.info("已注册模拟量数据回调")
        else:
            logger.warning("WebSocket客户端未初始化")
    
    async def _handle_analog_data(self, data: List[Dict]):
        """处理模拟量数据"""
        try:
            if not isinstance(data, list):
                logger.warning(f"接收到非列表数据: {type(data)}")
                return
                
            current_time = datetime.now()
            
            # 更新时间戳
            self.time_stamps.append(current_time)
            
            # 第一次接收数据时打印结构
            if self.data_count == 0:
                # logger.info(f"首次接收数据，样例: {data[0] if data else 'empty'}")
                pass
            
            # 处理每个参数
            for param_data in data:
                param_name = param_data.get('name', '')
                value = param_data.get('physical_value')
                
                # 如果physical_value不存在，尝试其他字段
                if value is None:
                    value = param_data.get('value', 0)
                
                if not param_name:
                    continue
                
                # 初始化所有参数的数据队列（即使未选中，也要保持数据同步）
                if param_name not in self.curve_data:
                    self.curve_data[param_name] = deque(maxlen=120)
                    # logger.info(f"初始化参数队列: {param_name}")
                
                # 添加数据点
                self.curve_data[param_name].append(float(value))
            
            # 更新最后数据时间
            self.last_data_time = current_time
            self.data_count += 1
            
            # 每10个数据点打印一次调试信息
            if self.data_count % 10 == 0:
                sample_values = {k: list(v)[-1] if v else None for k, v in self.curve_data.items()}
                # logger.info(f"数据更新 #{self.data_count} - 选中: {self.selected_parameters}, "
                          # f"最新值: {sample_values}")
            
            # 等待图表初始化完成再更新
            if self.chart_initialized:
                await self._update_chart()
            
        except Exception as e:
            logger.error(f"处理模拟量数据失败: {e}", exc_info=True)
    
    def create_page(self) -> ui.column:
        """创建实时曲线页面"""
        # 保存当前客户端引用
        from nicegui import context
        self.ui_client = context.client
        
        with ui.column().classes('w-full h-full p-4'):
            with ui.card().classes('w-full p-4'):
                # 标题和控制区域
                with ui.row().classes('w-full items-center justify-between mb-4'):
                    ui.label('实时曲线').classes('text-h6')
                    
                # 参数选择
                with ui.row().classes('items-center gap-4'):
                    ui.label('显示参数:').classes('text-subtitle2')
                    
                    # 保存复选框引用
                    self.param_checkboxes = {}
                    
                    for param in self.available_parameters:
                        is_selected = param['name'] in self.selected_parameters
                        with ui.row().classes('items-center gap-2 p-2 rounded-lg').style(f'background-color: {param["color"]}20;'):
                            checkbox = ui.checkbox(
                                param['name'], 
                                value=is_selected
                            )
                            self.param_checkboxes[param['name']] = checkbox
                        
                        def make_handler(param_name, checkbox_ref):
                            def on_param_toggle():
                                # 获取复选框的当前值
                                checked = checkbox_ref.value
                                # logger.info(f"参数切换: {param_name}, 勾选状态: {checked}")
                                
                                if checked:
                                    if param_name not in self.selected_parameters:
                                        self.selected_parameters.append(param_name)
                                        logger.info(f"添加参数: {param_name}")
                                else:
                                    if param_name in self.selected_parameters:
                                        self.selected_parameters.remove(param_name)
                                        logger.info(f"移除参数: {param_name}")
                                
                                # logger.info(f"当前选中参数: {self.selected_parameters}")
                                
                                # 重新创建图表
                                self._recreate_chart()
                            return on_param_toggle
                        
                        checkbox.on('update:model-value', make_handler(param['name'], checkbox))
                
                # # 状态信息显示
                # with ui.row().classes('w-full items-center mb-4 gap-4'):
                #     self.status_label = ui.label('状态: 等待数据...').classes('text-sm text-grey-7')
                #     self.data_count_label = ui.label('数据点: 0').classes('text-sm text-grey-7')
                #     self.last_time_label = ui.label('最后数据: --').classes('text-sm text-grey-7')
            
            # 图表容器
            self.chart_container = ui.card().classes('w-full p-4').style('height: 520px;')
            
            # 创建图表
            self._create_chart()
            
            # 启动数据更新
            self.is_running = True
            # self.update_timer = ui.timer(1.0, self._update_status_display)  # 状态显示已注释掉 - 不需要
    
    def _create_chart(self):
        """创建图表"""
        try:
            self.chart_container.clear()
            
            with self.chart_container:
                chart_id = f"chart_{id(self)}"
                
                # 创建canvas容器 - 使用div包裹canvas
                with ui.element('div').style('height: 450px; width: 100%; position: relative;'):
                    ui.element('canvas').props(f'id="{chart_id}"')
                
                # 构建图表配置 - 只包含选中的参数
                datasets = []
                for param_name in self.selected_parameters:
                    param_info = next((p for p in self.available_parameters if p['name'] == param_name), None)
                    if param_info:
                        dataset = {
                            'label': f"{param_name} ({param_info['unit']})",
                            'data': [],
                            'borderColor': param_info['color'],
                            'backgroundColor': param_info['color'] + '20',
                            'borderWidth': 2,
                            'fill': False,
                            'tension': 0.4,
                            'pointRadius': 2,
                            'pointHoverRadius': 5
                        }
                        datasets.append(dataset)
                
                logger.info(f"创建图表，选中参数: {self.selected_parameters}, 数据集数量: {len(datasets)}")
                
                chart_config = {
                    'type': 'line',
                    'data': {
                        'labels': [],
                        'datasets': datasets
                    },
                    'options': {
                        'responsive': True,
                        'maintainAspectRatio': False,
                        'animation': {
                            'duration': 0
                        },
                        'scales': {
                            'x': {
                                'title': {
                                    'display': True,
                                    'text': '时间'
                                },
                                'ticks': {
                                    'maxRotation': 45,
                                    'minRotation': 45,
                                    'maxTicksLimit': 10
                                }
                            },
                            'y': {
                                'title': {
                                    'display': True,
                                    'text': '数值'
                                },
                                'beginAtZero': False
                            }
                        },
                        'plugins': {
                            'legend': {
                                'display': True,
                                'position': 'top'
                            },
                            'tooltip': {
                                'mode': 'index',
                                'intersect': False
                            }
                        },
                        'interaction': {
                            'mode': 'nearest',
                            'axis': 'x',
                            'intersect': False
                        }
                    }
                }
                
                # 初始化Chart.js
                ui.run_javascript(f'''
                    (function() {{
                        function initChart() {{
                            const ctx = document.getElementById('{chart_id}');
                            if (!ctx) {{
                                console.error('Canvas not found: {chart_id}');
                                return;
                            }}
                            
                            // 销毁旧图表
                            if (window.chart_{chart_id}) {{
                                window.chart_{chart_id}.destroy();
                            }}
                            
                            // 创建新图表
                            try {{
                                window.chart_{chart_id} = new Chart(ctx, {json.dumps(chart_config)});
                                console.log('Chart created successfully');
                            }} catch (e) {{
                                console.error('Chart creation error:', e);
                            }}
                        }}
                        
                        // 检查Chart.js是否已加载
                        if (typeof Chart === 'undefined') {{
                            const script = document.createElement('script');
                            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
                            script.onload = initChart;
                            script.onerror = function() {{
                                console.error('Failed to load Chart.js');
                            }};
                            document.head.appendChild(script);
                        }} else {{
                            initChart();
                        }}
                    }})();
                ''')
                
                # 保存图表ID
                self.chart = type('ChartWrapper', (), {'id': chart_id})()
                
                # 延迟设置初始化标志
                async def mark_initialized():
                    await asyncio.sleep(0.5)
                    self.chart_initialized = True
                    logger.info("图表初始化完成")
                
                asyncio.create_task(mark_initialized())
                
        except Exception as e:
            logger.error(f"创建图表失败: {e}", exc_info=True)
            with self.chart_container:
                ui.label(f'创建图表失败: {str(e)}').classes('text-negative')
    
    def _recreate_chart(self):
        """重新创建图表"""
        # logger.info(f"重新创建图表，选中参数: {self.selected_parameters}")
        
        # 暂停图表更新
        self.chart_initialized = False
        
        # 延迟一点再重建，避免竞态条件
        async def rebuild():
            await asyncio.sleep(0.1)
            self._create_chart()
        
        asyncio.create_task(rebuild())
    
    async def _update_chart(self):
        """更新图表数据"""
        try:
            if not self.chart or not self.chart_initialized or not self.ui_client:
                return
            
            # 准备时间标签（只显示最近的时间点）
            time_labels = [t.strftime('%H:%M:%S') for t in self.time_stamps]
            
            # 构建新的数据集 - 只包含选中的参数
            datasets = []
            for param_name in self.selected_parameters:
                param_info = next((p for p in self.available_parameters if p['name'] == param_name), None)
                if param_info and param_name in self.curve_data:
                    values = list(self.curve_data[param_name])
                    
                    # 确保数据长度一致
                    if len(values) < len(time_labels):
                        values = [None] * (len(time_labels) - len(values)) + values
                    elif len(values) > len(time_labels):
                        values = values[-len(time_labels):]
                    
                    dataset = {
                        'label': f"{param_name} ({param_info['unit']})",
                        'data': values,
                        'borderColor': param_info['color'],
                        'backgroundColor': param_info['color'] + '20',
                        'borderWidth': 2,
                        'fill': False,
                        'tension': 0.4,
                        'pointRadius': 2,
                        'pointHoverRadius': 5
                    }
                    datasets.append(dataset)
                    
                    # 调试：第一次更新时打印数据样本
                    if self.data_count == 1:
                        logger.info(f"参数 {param_name} 数据样本: {values[:5]}...")
            
            # 只有在有数据集时才更新
            if not datasets:
                logger.warning(f"没有可显示的数据集，选中参数: {self.selected_parameters}, "
                             f"可用数据: {list(self.curve_data.keys())}")
                return
            
            # 更新图表 - 使用保存的客户端上下文
            chart_id = self.chart.id
            update_code = f'''
                (function() {{
                    const chart = window.chart_{chart_id};
                    if (chart) {{
                        chart.data.labels = {json.dumps(time_labels)};
                        chart.data.datasets = {json.dumps(datasets)};
                        chart.update('none');
                    }} else {{
                        console.warn('Chart not found: {chart_id}');
                    }}
                }})();
            '''
            
            # 使用客户端上下文执行JavaScript
            self.ui_client.run_javascript(update_code)
            
        except Exception as e:
            logger.error(f"更新图表失败: {e}", exc_info=True)
    
    async def _update_status_display(self):
        """更新状态显示"""
        try:
            # 检查组件是否仍然存在
            if not self.status_label or not hasattr(self.status_label, 'set_text'):
                return
                
            if self.last_data_time:
                time_diff = (datetime.now() - self.last_data_time).total_seconds()
                if time_diff < 5:
                    self.status_label.set_text("状态: 正常接收数据")
                    self.status_label.classes(remove='text-warning text-grey-7', add='text-positive')
                else:
                    self.status_label.set_text(f"状态: 数据中断 {int(time_diff)}秒")
                    self.status_label.classes(remove='text-positive text-grey-7', add='text-warning')
            else:
                self.status_label.set_text("状态: 等待数据...")
                self.status_label.classes(remove='text-positive text-warning', add='text-grey-7')
            
            self.data_count_label.set_text(f"数据点: {self.data_count}")
            
            if self.last_data_time:
                self.last_time_label.set_text(f"最后数据: {self.last_data_time.strftime('%H:%M:%S')}")
            else:
                self.last_time_label.set_text("最后数据: --")
                
        except Exception as e:
            logger.error(f"更新状态显示失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        self.is_running = False
        if self.update_timer:
            self.update_timer.cancel()
        
        # 销毁图表
        if self.chart:
            chart_id = self.chart.id
            ui.run_javascript(f'''
                if (window.chart_{chart_id}) {{
                    window.chart_{chart_id}.destroy();
                    delete window.chart_{chart_id};
                }}
            ''')
        
        # 注销回调
        if self.websocket_client:
            self.websocket_client.unregister_data_callback('analog_data', self._handle_analog_data)
        
        logger.info("实时曲线页面已清理")