"""
事件记录页面 - 整合版
Event Record Page - Integrated
"""
# flake8: noqa
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from nicegui import ui
import httpx
import json

logger = logging.getLogger(__name__)


class EventRecordPage:
    """事件记录页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.query_date = None
        self.query_btn = None
        self.export_btn = None
        self.stats_label = None
        self.data_table = None
        self.loading_spinner = None
        self.loading = False
        
        # API配置
        self.api_base_url = self.config.get('API配置', 'base_url', 'http://localhost:8001')
        self.api_timeout = self.config.get('API配置', 'timeout', 30)
        
    def create_page(self) -> ui.column:
        """创建事件记录页面"""
        with ui.card().classes('w-full').style('height: 80vh; overflow-y: auto;'):
            ui.label('事件记录查询').classes('text-h5 q-mb-md')
            
            # 查询条件区域
            with ui.row().classes('w-full q-gutter-md q-mb-md items-end'):
                # 查询日期
                self.query_date = ui.input(
                    label='查询日期',
                    value=datetime.now().strftime('%Y-%m-%d')
                ).props('readonly').classes('w-40')
                with self.query_date:
                    with ui.menu().props('no-parent-event') as date_menu:
                        with ui.date(value=datetime.now().strftime('%Y-%m-%d')).bind_value(self.query_date):
                            with ui.row().classes('justify-end'):
                                ui.button('关闭', on_click=date_menu.close).props('flat')
                    with self.query_date.add_slot('append'):
                        ui.icon('event').on('click', date_menu.open).classes('cursor-pointer')
                
                # 查询按钮
                self.query_btn = ui.button('查询', color='primary', on_click=self._on_query_click).style('min-width: 100px;')
                
                # 导出按钮
                self.export_btn = ui.button('导出', color='secondary', on_click=self._on_export_click).props('outline').style('min-width: 100px;')
            
            # 统计信息区域
            with ui.row().classes('w-full q-mb-md'):
                self.stats_label = ui.label('共 0 条记录').classes('text-body2 text-grey-7')
            
            # 表格区域 - 整合表格
            with ui.column().classes('w-full').style('flex-grow: 1; min-height: 0;'):
                self.columns = [
                    {'name': 'data_type', 'label': '数据类型', 'field': 'data_type', 'align': 'center', 'sortable': True},
                    {'name': 'timestamp', 'label': '时间', 'field': 'timestamp', 'align': 'left', 'sortable': True},
                    {'name': 'device_id', 'label': '设备ID', 'field': 'device_id', 'align': 'center', 'sortable': True},
                    {'name': 'type', 'label': '类型', 'field': 'type', 'align': 'center', 'sortable': True},
                    {'name': 'content', 'label': '内容', 'field': 'content', 'align': 'left'},
                ]
                
                self.data_table = ui.table(
                    columns=self.columns,
                    rows=[],
                    pagination={'rowsPerPage': 20, 'page': 1}
                ).classes('w-full').style('max-height: 60vh; overflow-y: auto;')
                
                # 移除了自定义分页控件，使用表格内置分页功能
            
            # 加载状态指示器
            self.loading_spinner = ui.spinner(size='lg').classes('absolute-center').set_visibility(False)
        
        return ui.column()
    
    async def _on_query_click(self):
        """查询按钮点击事件"""
        if self.loading:
            return
        
        try:
            self.loading = True
            if self.loading_spinner:
                self.loading_spinner.set_visibility(True)
            if self.query_btn:
                self.query_btn.props('loading')
            
            # 检查必要的UI元素是否存在
            if not self.query_date:
                ui.notify('日期控件未初始化', type='negative')
                return
            
            # 构建查询参数 - 查询整天的数据
            query_date = self.query_date.value
            start_datetime = f"{query_date}T00:00:00"
            end_datetime = f"{query_date}T23:59:59"
            
            # logger.info(f"开始查询，日期范围: {start_datetime} 到 {end_datetime}")
            
            # 验证时间格式
            try:
                datetime.fromisoformat(start_datetime)
                datetime.fromisoformat(end_datetime)
            except ValueError:
                ui.notify('时间格式错误', type='negative')
                return
            
            # all_rows 用于收集事件记录和状态历史的所有数据
            all_rows = []
            
            # 同时查询事件记录和状态历史
            # logger.info("开始查询事件记录...")
            event_rows = await self._query_event_records(start_datetime, end_datetime)
            # logger.info(f"查询到 {len(event_rows)} 条事件记录")
            all_rows.extend(event_rows) # 合并事件记录
            
            # logger.info("开始查询状态历史...")
            status_rows = await self._query_status_history(start_datetime, end_datetime)
            # logger.info(f"查询到 {len(status_rows)} 条状态历史")
            all_rows.extend(status_rows) # 合并状态历史
            
            # 按时间排序
            all_rows.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 更新表格 - 使用表格内置分页，直接显示所有数据
            if self.data_table:
                self.data_table.rows = all_rows
                self.data_table.pagination['page'] = 1  # 重置到第一页
            
            if self.stats_label:
                self.stats_label.text = f'共 {len(all_rows)} 条记录'
            
            if not all_rows:
                ui.notify('未找到符合条件的记录', type='info')
                if self.data_table:
                    self.data_table.rows = []
            else:
                ui.notify(f'查询成功，找到 {len(all_rows)} 条记录', type='positive')
                
        except Exception as e:
            logger.error(f"查询失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            ui.notify(f'查询失败: {str(e)}', type='negative')
        finally:
            self.loading = False
            if self.loading_spinner:
                self.loading_spinner.set_visibility(False)
            if self.query_btn:
                self.query_btn.props(remove='loading')
    
    async def _query_event_records(self, start_time: str, end_time: str) -> List[Dict]:
        """查询事件记录"""
        try:
            all_rows = []
            page = 1
            page_size = 100  # 使用最大页面大小提高性能
            
            while True:
                # 构建查询参数
                params = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'page': page,
                    'page_size': page_size
                }
                
                # 调用API
                async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                    response = await client.get(
                        f"{self.api_base_url}/api/v1/history/events",
                        params=params
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 检查API响应格式
                        if isinstance(result, dict) and 'code' in result:
                            if result.get('code') == 200:
                                data = result.get('data', {})
                                rows = data.get('list', [])
                                total = data.get('total', 0)
                            else:
                                break
                        else:
                            rows = result.get('list', [])
                            total = result.get('total', 0)
                        
                        # 格式化数据为统一格式
                        for row in rows:
                            formatted_row = {
                                'data_type': '事件记录',
                                'timestamp': self._format_datetime(row.get('event_time', '')),
                                'device_id': row.get('device_id', ''),
                                'type': self._format_event_type(row.get('event_type', '')),
                                'content': row.get('description', '')
                            }
                            all_rows.append(formatted_row)
                        
                        # 如果当前页数据少于页面大小，说明已经获取完所有数据
                        if len(rows) < page_size or len(all_rows) >= total:
                            break
                            
                        page += 1
                    else:
                        logger.error(f'事件记录API请求失败: {response.status_code}')
                        break
            
            return all_rows
                    
        except Exception as e:
            logger.error(f"查询事件记录失败: {e}")
            return []
    
    async def _query_status_history(self, start_time: str, end_time: str) -> List[Dict]:
        """查询状态历史"""
        try:
            all_rows = []
            page = 1
            page_size = 100  # 使用最大页面大小提高性能
            
            while True:
                # 构建请求参数
                params = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'page': page,
                    'page_size': page_size
                }
                
                # 调用API
                async with httpx.AsyncClient(timeout=self.api_timeout) as client:
                    response = await client.get(
                        f"{self.api_base_url}/api/v1/history/status",
                        params=params
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 检查API响应格式
                        if isinstance(result, dict) and 'code' in result:
                            if result.get('code') == 200:
                                data = result.get('data', {})
                                rows = data.get('list', [])
                                total = data.get('total', 0)
                            else:
                                break
                        else:
                            rows = result.get('list', [])
                            total = result.get('total', 0)
                        
                        # 格式化数据为统一格式
                        for row in rows:
                            # 构建内容描述
                            status_name = row.get('status_name', '')
                            bit_pos = row.get('bit_position', 0)
                            old_val = row.get('old_value', 0)
                            new_val = row.get('new_value', 0)
                            status_type = row.get('status_type', '')
                            
                            # 根据状态类型获取直观的描述
                            if status_type in ['SystemStatus', 'InputStatus', 'OutputStatus', 'IGBTStatus', 'FaultStatus']:
                                intuitive_name = self._get_status_bit_description(status_type, status_name, bit_pos)
                                content = f"{intuitive_name} (位{bit_pos}): {old_val} → {new_val}"
                            else:
                                content = f"{status_name} (位{bit_pos}): {old_val} → {new_val}"
                            
                            formatted_row = {
                                'data_type': '状态历史',
                                'timestamp': self._format_datetime(row.get('timestamp', '')),
                                'device_id': row.get('device_id', ''),
                                'type': self._format_status_type(status_type),
                                'content': content
                            }
                            all_rows.append(formatted_row)
                        
                        # 如果当前页数据少于页面大小，说明已经获取完所有数据
                        if len(rows) < page_size or len(all_rows) >= total:
                            break
                            
                        page += 1
                    else:
                        logger.error(f'状态历史API请求失败: {response.status_code}')
                        break
            
            return all_rows
            
        except Exception as e:
            logger.error(f"查询状态历史失败: {e}")
            return []
    
    def _on_export_click(self):
        """导出按钮点击事件"""
        if not self.data_table:
            ui.notify('导出控件未初始化', type='warning')
            return
            
        if not self.data_table.rows:
            ui.notify('没有数据可以导出', type='warning')
            return
        
        try:
            # 构建导出数据
            export_data = [['数据类型', '时间', '设备ID', '类型', '内容']]
            
            for row in self.data_table.rows:
                export_data.append([
                    row.get('data_type', ''),
                    row.get('timestamp', ''),
                    row.get('device_id', ''),
                    row.get('type', ''),
                    row.get('content', '')
                ])
            
            # 生成CSV内容
            csv_content = '\n'.join([','.join(row) for row in export_data])
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"历史记录_{timestamp}.csv"
            
            # 创建下载链接
            ui.download(csv_content.encode('utf-8'), filename)
            ui.notify('导出成功', type='positive')
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            ui.notify(f'导出失败: {str(e)}', type='negative')
    
    def _format_datetime(self, dt_str: str) -> str:
        """格式化日期时间字符串"""
        try:
            if 'T' in dt_str:
                dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return dt_str
        except:
            return dt_str
    
    def _format_event_type(self, event_type: str) -> str:
        """格式化事件类型"""
        type_mapping = {
            'system': '系统事件',
            'device': '设备事件',
            'user_operation': '用户操作',
            'alarm': '告警事件',
            'fault': '故障事件',
            'info': '信息事件',
            'warning': '警告事件',
            'error': '错误事件'
        }
        return type_mapping.get(event_type, event_type)
    
    def _format_status_type(self, status_type: str) -> str:
        """格式化状态类型"""
        type_mapping = {
            'FaultStatus': '故障信息',
            'SystemStatus': '系统状态',
            'OutputStatus': '输出状态',
            'InputStatus': '输入状态',
            'IGBTStatus': 'IGBT状态'
        }
        return type_mapping.get(status_type, status_type)
    
    def _get_fault_bit_description(self, status_name: str, bit_position: int) -> str:
        """根据故障位配置获取直观的描述"""
        try:
            # 获取故障位配置
            fault_bits = self.config.get_fault_bits()
            
            # 构建位配置的键名
            bit_key = f"bit{bit_position}"
            
            # 查找对应的配置
            if bit_key in fault_bits:
                # 配置格式通常是 "描述0,描述1" 或 "描述"
                config_value = fault_bits[bit_key]
                if ',' in config_value:
                    # 如果有两个描述，取第一个作为通用描述
                    descriptions = config_value.split(',')
                    return descriptions[0].strip()
                else:
                    # 如果只有一个描述，直接使用
                    return config_value.strip()
            
            # 如果没有找到配置，返回原始状态名
            return status_name
            
        except Exception as e:
            logger.error(f"获取故障位描述失败: {e}")
            return status_name
    
    def _get_status_bit_description(self, status_type: str, status_name: str, bit_position: int) -> str:
        """根据状态类型和位配置获取直观的描述"""
        try:
            # 根据状态类型获取对应的配置
            if status_type == 'SystemStatus':
                status_bits = self.config.get_system_status_bits()
            elif status_type == 'InputStatus':
                status_bits = self.config.get_input_bits()
            elif status_type == 'OutputStatus':
                status_bits = self.config.get_output_bits()
            elif status_type == 'IGBTStatus':
                status_bits = self.config.get_igbt_bits()
            elif status_type == 'FaultStatus':
                status_bits = self.config.get_fault_bits()
            else:
                return status_name
            
            # 构建位配置的键名
            bit_key = f"bit{bit_position}"
            
            # 查找对应的配置
            if bit_key in status_bits:
                # 配置格式通常是 "描述0,描述1" 或 "描述"
                config_value = status_bits[bit_key]
                if ',' in config_value:
                    # 如果有两个描述，取第一个作为通用描述
                    descriptions = config_value.split(',')
                    return descriptions[0].strip()
                else:
                    # 如果只有一个描述，直接使用
                    return config_value.strip()
            
            # 如果没有找到配置，返回原始状态名
            return status_name
            
        except Exception as e:
            logger.error(f"获取状态位描述失败: {e}")
            return status_name
    
    # 移除了自定义分页相关方法，完全使用表格内置分页功能
