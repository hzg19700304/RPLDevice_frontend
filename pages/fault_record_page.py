"""
故障录波查询页面
Fault Record Page
"""
import logging
from datetime import datetime
from nicegui import ui

logger = logging.getLogger(__name__)


class FaultRecordPage:
    """故障录波查询页面"""

    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        
        # UI组件引用
        self.record_count_label = None
        self.record_select = None
        self.fault_time_label = None
        self.fault_code_label = None
        self.fault_desc_label = None
        self.data_table = None
        self.progress_dialog = None
        self.progress_bar = None
        self.progress_text = None
        self.cancel_button = None
        self.main_container = None  # 保存主容器引用，用于UI上下文
        
        # 数据状态
        self.available_records = 0
        self.current_record_id = 0
        self.is_reading = False
        self.current_request_id = None
        
        # 获取配置
        self.analog_mapping = self._load_analog_mapping()
        self.status_bits = self._load_status_bits()
        self.input_bits = self._load_input_bits()
        self.output_bits = self._load_output_bits()
        
        # 注册WebSocket回调
        if self.websocket_client:
            self.websocket_client.register_data_callback(
                'fault_record_list_ack', 
                self._handle_directory_response
            )
            self.websocket_client.register_data_callback(
                'fault_record_read_start', 
                self._handle_read_start
            )
            self.websocket_client.register_data_callback(
                'fault_record_progress', 
                self._handle_read_progress
            )
            self.websocket_client.register_data_callback(
                'fault_record_complete', 
                self._handle_read_complete
            )
            self.websocket_client.register_data_callback(
                'fault_record_error', 
                self._handle_read_error
            )
            self.websocket_client.register_data_callback(
                'fault_record_cancelled', 
                self._handle_read_cancelled
            )
            self.websocket_client.register_data_callback(
                'control_ack', 
                self._handle_clear_response
            )

    def _load_analog_mapping(self):
        """加载模拟量映射配置"""
        mapping = {}
        section = 'HMI系统模拟量地址映射'
        if self.config.config.has_section(section):
            for key, value in self.config.config.items(section):
                mapping[key] = value
        return mapping

    def _load_status_bits(self):
        """加载系统状态点表"""
        bits = {}
        section = 'HMI系统状态点表'
        if self.config.config.has_section(section):
            for key, value in self.config.config.items(section):
                bit_num = key.replace('bit', '')
                bits[int(bit_num)] = value
        return bits

    def _load_input_bits(self):
        """加载开关量输入点表"""
        bits = {}
        section = 'HMI开关量输入点表'
        if self.config.config.has_section(section):
            for key, value in self.config.config.items(section):
                bit_num = key.replace('bit', '')
                bits[int(bit_num)] = value
        return bits

    def _load_output_bits(self):
        """加载开关量输出点表"""
        bits = {}
        section = 'HMI开关量输出点表'
        if self.config.config.has_section(section):
            for key, value in self.config.config.items(section):
                bit_num = key.replace('bit', '')
                bits[int(bit_num)] = value
        return bits

    def create_page(self):
        """创建页面"""
        with ui.card().classes('w-full h-full') as main_card:
            self.main_container = main_card  # 保存主容器引用
            # 顶部控制面板
            self._create_control_panel()          
            ui.separator()       
            # 故障信息显示区域
            self._create_fault_info_area()     
            ui.separator()     
            # 数据表格
            self._create_data_table()

    def _create_control_panel(self):
        """创建顶部控制面板"""
        # 标题行
        with ui.row().classes('w-full items-center p-2'):
            ui.label('故障录波查询').classes('text-h6 text-weight-bold')
        
        # 控制元素行
        with ui.row().classes('w-full items-center justify-between p-2'):
            # 左侧元素
            with ui.row().classes('items-center gap-2 no-wrap'):
                ui.label('记录可读数:').classes('text-body1')
                self.record_count_label = ui.label('0').classes('text-body1 text-primary')
                
                ui.label('记录编号:').classes('text-body1 ml-4')
                self.record_select = ui.select(
                    options=[0],
                    value=0,
                ).classes('w-20').props('dense outlined options-dense').style('padding: 0px; margin: 0px;')
            
            # 右侧按钮组
            with ui.row().classes('items-center gap-2'):
                ui.button('查询目录', on_click=lambda: self._query_directory())\
                    .props('outline color=primary dense')
                
                ui.button('查询详情', on_click=lambda: self._query_detail())\
                    .props('unelevated color=primary dense')
                
                ui.button('取消', on_click=lambda: self._cancel_reading())\
                    .props('outline color=grey-7 dense')
                
                ui.button('清除记录', on_click=lambda: self._show_clear_confirm())\
                    .props('outline color=negative dense')

    def _create_fault_info_area(self):
        """创建故障信息显示区域"""
        # 第一行：故障时间和故障码
        with ui.row().classes('w-full items-center gap-4 p-2 no-wrap'):
            ui.label('故障发生时间:').classes('text-body2')
            self.fault_time_label = ui.label('2000-01-01 00:00:00.000').classes('text-body1')
            
            ui.label('故障码:').classes('text-body2')
            self.fault_code_label = ui.label('0x0000').classes('text-body1')
        
        # 第二行：故障描述
        with ui.row().classes('w-full items-center gap-4 p-2 no-wrap'):
            ui.label('故障描述:').classes('text-body2')
            self.fault_desc_label = ui.label('--').classes('text-body1') 

    def _create_data_table(self):
        """创建数据表格"""
        # 构建表格列定义
        columns = [
            {'name': 'index', 'label': '序号', 'field': 'index', 'align': 'center', 'style': 'width: 60px'},
            {'name': 'system_status', 'label': '系统状态', 'field': 'system_status', 'align': 'center', 'style': 'width: 80px'},
            {'name': 'switch_input', 'label': '开关量输入', 'field': 'switch_input', 'align': 'center', 'style': 'width: 80px'},
            {'name': 'switch_output', 'label': '开关量输出', 'field': 'switch_output', 'align': 'center', 'style': 'width: 80px'},
        ]
        
        # 添加模拟量列（从配置中读取）
        analog_columns = ['SV1', 'SV2', 'SA1', 'SA2']
        for col in analog_columns:
            col_name = self.analog_mapping.get(col.lower(), col)
            columns.append({
                'name': col.lower(),
                'label': col_name,
                'field': col.lower(),
                'align': 'center',
                'style': 'width: 80px'
            })
        
        self.data_table = ui.table(
            columns=columns,
            rows=[],
            row_key='index'
        ).classes('w-full')
        
        # 设置表格点击事件
        self.data_table.on('row-click', self._on_row_click)

    async def _query_directory(self):
        """查询故障录波目录"""
        logger.info("查询故障录波目录")
        
        # 检查WebSocket连接状态
        if not self.websocket_client.is_connected:
            logger.error("WebSocket未连接，无法查询故障录波目录")
            ui.notify('WebSocket未连接，请检查网络连接', type='negative')
            return
        
        # 发送WebSocket请求
        message = {
            'type': 'fault_record_list',
            'device_id': 'HYP_RPLD_001',
            'request_id': f'req_dir_{datetime.now().timestamp()}'
        }
        
        logger.info(f"准备发送故障录波目录查询消息: {message}")
        result = await self.websocket_client.send_message(message['type'], message)
        logger.info(f"消息发送结果: {result}")
        
        if result:
            ui.notify('正在查询故障录波目录...', type='info')
        else:
            ui.notify('发送查询请求失败，请检查网络连接', type='negative')

    async def _query_detail(self):
        """查询故障录波详情"""
        if self.is_reading:
            ui.notify('正在读取中，请稍候...', type='warning')
            return
        
        record_id = self.record_select.value
        logger.info(f"查询故障录波详情，记录编号: {record_id}")
        
        self.is_reading = True
        self.current_request_id = f'req_fault_read_{datetime.now().timestamp()}'
        
        # 发送WebSocket请求
        message = {
            'type': 'fault_record_read',
            'device_id': 'HYP_RPLD_001',
            'record_id': record_id,
            'request_id': self.current_request_id
        }
        
        await self.websocket_client.send_message(message['type'], message)
        
        # 显示进度对话框
        self._show_progress_dialog()

    async def _cancel_reading(self):
        """取消读取"""
        if not self.is_reading:
            return
        
        logger.info("用户取消故障录波读取")
        
        # 发送取消请求
        message = {
            'type': 'fault_record_cancel',
            'device_id': 'HYP_RPLD_001',
            'request_id': self.current_request_id
        }
        
        await self.websocket_client.send_message(message['type'], message)
        
        self.is_reading = False
        if self.progress_dialog:
            self.progress_dialog.close()

    def _show_clear_confirm(self):
        """显示清除记录确认对话框"""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('⚠️ 警告：此操作将清除所有故障录波记录').classes('text-h6 q-mb-md')
            
            ui.separator()
            
            ui.label('是否确认清除所有记录？').classes('text-body1 q-my-md')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('取消', on_click=dialog.close).props('flat')
                ui.button('确认', on_click=lambda: self._clear_records(dialog))\
                    .props('unelevated color=negative')
        
        dialog.open()

    async def _clear_records(self, dialog):
        """清除故障录波记录"""
        logger.info("清除故障录波记录")
        
        # 发送控制命令
        message = {
            'type': 'control_cmd',
            'cmd': 'fault_record_clear',
            'cmd_param': {
                'coil_addr': '0x0110',
                'confirm': True
            }
        }
        
        await self.websocket_client.send_message(message['type'], message)
        dialog.close()
        ui.notify('正在清除故障录波记录...', type='info')

    def _show_progress_dialog(self):
        """显示进度对话框"""
        self.progress_dialog = ui.dialog().props('persistent')
        
        with self.progress_dialog, ui.card().classes('w-96'):
            ui.label('正在读取故障录波...').classes('text-h6 q-mb-md')
            
            self.progress_bar = ui.linear_progress(value=0).classes('w-full')
            
            with ui.row().classes('w-full justify-between q-mt-md'):
                self.progress_text = ui.label('当前批次: 0/0')
                ui.label('预计剩余时间: --')
            
            ui.button('取消查询', on_click=self._cancel_reading)\
                .props('flat color=negative').classes('w-full q-mt-md')
        
        self.progress_dialog.open()

    def _show_bit_parse_dialog(self, title, value, bit_mapping):
        """显示点位数据解析对话框"""
        with ui.dialog() as dialog, ui.card().classes('w-80'):
            ui.label(f'数据解析({value})').classes('text-h6 q-mb-md')
            
            ui.separator()
            
            # 解析每个bit位
            int_value = int(value, 16) if isinstance(value, str) else value
            
            with ui.column().classes('w-full gap-2 q-my-md'):
                for bit_num in range(16):
                    if bit_num in bit_mapping:
                        is_set = (int_value >> bit_num) & 1
                        icon = '🟢' if is_set else '🔴'
                        status = bit_mapping[bit_num]
                        ui.label(f'bit{bit_num}: {icon} {status}').classes('text-body2')
            
            ui.button('关闭', on_click=dialog.close).props('flat').classes('w-full')
        
        dialog.open()

    def _on_row_click(self, event):
        """表格行点击事件"""
        row = event.args[1]
        col = event.args[2]
        
        # 点击系统状态列
        if col == 'system_status':
            self._show_bit_parse_dialog(
                '系统状态',
                row['system_status'],
                self.status_bits
            )
        # 点击开关量输入列
        elif col == 'switch_input':
            self._show_bit_parse_dialog(
                '开关量输入',
                row['switch_input'],
                self.input_bits
            )
        # 点击开关量输出列
        elif col == 'switch_output':
            self._show_bit_parse_dialog(
                '开关量输出',
                row['switch_output'],
                self.output_bits
            )

    async def handle_websocket_message(self, message):
        """处理WebSocket消息"""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        # 根据消息类型调用相应的处理函数
        if msg_type == 'fault_record_list_ack':
            await self._handle_directory_response(message)
        elif msg_type == 'fault_record_read_start':
            await self._handle_read_start(message)
        elif msg_type == 'fault_record_progress':
            await self._handle_read_progress(message)
        elif msg_type == 'fault_record_complete':
            await self._handle_read_complete(message)
        elif msg_type == 'fault_record_error':
            await self._handle_read_error(message)
        elif msg_type == 'fault_record_cancelled':
            await self._handle_read_cancelled(message)
        elif msg_type == 'control_ack':
            if message.get('cmd') == 'fault_record_clear':
                await self._handle_clear_response(message)
        else:
            logger.warning(f"未知的消息类型: {msg_type}")

    async def _handle_directory_response(self, message):
        """处理目录查询响应"""
        try:
            logger.info(f"收到目录查询响应: {message}")
            
            # 从消息中提取故障录波目录信息
            # 注意：message本身就是数据对象，不是包含data字段的对象
            self.available_records = message.get('total_records', 0)
            
            logger.info(f"提取的记录数: {self.available_records}")
            
            # 存储记录信息供后续使用
            self.fault_records_info = message.get('records', [])
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    # 更新UI
                    if self.record_count_label:
                        self.record_count_label.set_text(str(self.available_records))
                        logger.info(f"已更新记录数标签: {self.available_records}")
                    
                    # 更新记录选择下拉框
                    if self.record_select:
                        options = list(range(self.available_records))
                        self.record_select.set_options(options)
                        if options:
                            self.record_select.set_value(0)
                        logger.info(f"已更新记录选择下拉框: {options}")
                    
                    # 使用run_javascript来安全地显示通知
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '查询成功，共有 {self.available_records} 条记录',
                            type: 'positive',
                            position: 'top',
                            timeout: 3000
                        }})
                    ''')
            else:
                # 如果没有主容器，直接使用run_javascript
                await ui.run_javascript(f'''
                    Quasar.Notify.create({{
                        message: '查询成功，共有 {self.available_records} 条记录',
                        type: 'positive',
                        position: 'top',
                        timeout: 3000
                    }})
                ''')
                logger.info("没有主容器，直接使用run_javascript显示通知")
        except Exception as e:
            logger.error(f"处理目录查询响应失败: {e}")

    async def _handle_read_start(self, message):
        """处理读取开始响应"""
        try:
            data = message.get('data', {})
            if data.get('exec_status') == 'success':
                # 重置进度
                self.current_progress = 0
                self.total_records = data.get('total_records', 0)
                
                # 更新进度条
                self._update_progress_ui()
                
                # 确保在主UI上下文中处理响应
                if self.main_container is not None:
                    with self.main_container:
                        # 显示开始读取通知
                        await ui.run_javascript('''
                            Quasar.Notify.create({
                                message: '开始读取故障记录...',
                                type: 'info',
                                position: 'top',
                                timeout: 3000
                            })
                        ''')
                else:
                    # 如果没有主容器，直接使用run_javascript
                    await ui.run_javascript('''
                        Quasar.Notify.create({
                            message: '开始读取故障记录...',
                            type: 'info',
                            position: 'top',
                            timeout: 3000
                        })
                    ''')
            else:
                error_msg = data.get('exec_msg', '未知错误')
                # 确保在主UI上下文中处理响应
                if self.main_container is not None:
                    with self.main_container:
                        await ui.run_javascript(f'''
                            Quasar.Notify.create({{
                                message: '读取故障记录失败: {error_msg}',
                                type: 'negative',
                                position: 'top',
                                timeout: 5000
                            }})
                        ''')
                else:
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '读取故障记录失败: {error_msg}',
                            type: 'negative',
                            position: 'top',
                            timeout: 5000
                        }})
                    ''')
        except Exception as e:
            logger.error(f"处理读取开始响应失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '处理读取开始响应失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')

    async def _handle_read_progress(self, data):
        """处理读取进度"""
        try:
            # 更新进度
            self.current_progress = data.get('progress', 0)
            self.current_record = data.get('current_record', 0)
            
            # 更新进度条
            self._update_progress_ui()
            
            # 记录日志
            logger.info(f"读取进度: {self.current_progress}% ({self.current_record}/{self.total_records})")
        except Exception as e:
            logger.error(f"处理读取进度失败: {e}")
    
    def _update_progress_ui(self):
        """更新进度条UI"""
        try:
            # 确保在主UI上下文中更新UI
            if self.main_container is not None:
                with self.main_container:
                    if hasattr(self, 'progress_bar') and self.progress_bar:
                        self.progress_bar.value = self.current_progress
                    
                    if hasattr(self, 'progress_text') and self.progress_text:
                        self.progress_text.text = f"{self.current_progress}% ({self.current_record}/{self.total_records})"
            else:
                # 如果没有主容器，直接更新UI
                if hasattr(self, 'progress_bar') and self.progress_bar:
                    self.progress_bar.value = self.current_progress
                
                if hasattr(self, 'progress_text') and self.progress_text:
                    self.progress_text.text = f"{self.current_progress}% ({self.current_record}/{self.total_records})"
        except Exception as e:
            logger.error(f"更新进度UI失败: {e}")

    async def _handle_read_complete(self, data):
        """处理读取完成响应"""
        try:
            self.is_reading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    if data.get('exec_status') == 'success':
                        # 获取故障记录数据
                        fault_records = data.get('fault_records', [])
                        
                        # 更新数据表格
                        self._update_data_table(fault_records)
                        
                        # 更新进度条到100%
                        self.current_progress = 100
                        self.current_record = self.total_records
                        self._update_progress_ui()
                        
                        # 显示完成通知
                        await ui.run_javascript('''
                            Quasar.Notify.create({
                                message: '故障记录读取完成',
                                type: 'positive',
                                position: 'top',
                                timeout: 3000
                            })
                        ''')
                    else:
                        error_msg = data.get('exec_msg', '未知错误')
                        await ui.run_javascript(f'''
                            Quasar.Notify.create({{
                                message: '读取故障记录失败: {error_msg}',
                                type: 'negative',
                                position: 'top',
                                timeout: 5000
                            }})
                        ''')
            else:
                # 如果没有主容器，直接使用run_javascript
                if data.get('exec_status') == 'success':
                    # 获取故障记录数据
                    fault_records = data.get('fault_records', [])
                    
                    # 更新数据表格
                    self._update_data_table(fault_records)
                    
                    # 更新进度条到100%
                    self.current_progress = 100
                    self.current_record = self.total_records
                    self._update_progress_ui()
                    
                    # 显示完成通知
                    await ui.run_javascript('''
                        Quasar.Notify.create({
                            message: '故障记录读取完成',
                            type: 'positive',
                            position: 'top',
                            timeout: 3000
                        })
                    ''')
                else:
                    error_msg = data.get('exec_msg', '未知错误')
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '读取故障记录失败: {error_msg}',
                            type: 'negative',
                            position: 'top',
                            timeout: 5000
                        }})
                    ''')
        except Exception as e:
            logger.error(f"处理读取完成响应失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '处理读取完成响应失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')
    
    def _update_complete_ui(self, fault_info, data_points):
        """更新完成UI（非异步函数）"""
        try:
            # 更新故障信息
            self._update_fault_info(fault_info)
            
            # 更新数据表格
            self._update_data_table(data_points)
        except Exception as e:
            logger.error(f"更新完成UI失败: {e}")

    async def _handle_read_error(self, data):
        """处理读取错误"""
        try:
            self.is_reading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.close()
            
            error_msg = data.get('error_msg', '未知错误')
            current_batch = data.get('current_batch', 0)
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    # 显示错误对话框
                    with ui.dialog() as dialog, ui.card().classes('w-96'):
                        ui.label('❌ 读取故障录波数据失败').classes('text-h6 q-mb-md')
                        
                        ui.separator()
                        
                        ui.label(f'错误信息: {error_msg}').classes('text-body2 q-my-md')
                        ui.label(f'失败批次: {current_batch}').classes('text-body2')
                        
                        with ui.row().classes('w-full justify-end gap-2 q-mt-md'):
                            ui.button('取消', on_click=dialog.close).props('flat')
                            ui.button('重试', on_click=lambda: [dialog.close(), ui.timer(0.1, self._query_detail, once=True)])\
                                .props('unelevated color=primary')
                    
                    dialog.open()
            else:
                # 如果没有主容器，使用run_javascript显示错误通知
                await ui.run_javascript(f'''
                    Quasar.Notify.create({{
                        message: '读取故障录波数据失败: {error_msg}',
                        type: 'negative',
                        position: 'top',
                        timeout: 5000
                    }})
                ''')
        except Exception as e:
            logger.error(f"处理读取错误失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '处理读取错误失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')

    async def _handle_read_cancelled(self, data):
        """处理取消确认"""
        try:
            cancelled_at_batch = data.get('cancelled_at_batch', 0)
            logger.info(f"故障录波读取已取消，取消于第 {cancelled_at_batch} 批")
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    # 使用run_javascript来安全地显示通知
                    await ui.run_javascript('''
                        Quasar.Notify.create({
                            message: '已取消读取',
                            type: 'info',
                            position: 'top',
                            timeout: 3000
                        })
                    ''')
            else:
                # 如果没有主容器，直接使用run_javascript
                await ui.run_javascript('''
                    Quasar.Notify.create({
                        message: '已取消读取',
                        type: 'info',
                        position: 'top',
                        timeout: 3000
                    })
                ''')
        except Exception as e:
            logger.error(f"处理取消确认失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({
                    message: '处理取消确认失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                })
            ''')

    async def _handle_clear_response(self, data):
        """处理清除记录响应"""
        try:
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    if data.get('exec_status') == 'success':
                        # 获取清除的记录数量
                        cleared_count = data.get('cleared_count', 0)
                        exec_msg = data.get('exec_msg', '清除成功')
                        
                        # 清除表格数据
                        self._clear_data_table()
                        
                        # 显示成功通知
                        await ui.run_javascript(f'''
                            Quasar.Notify.create({{
                                message: '{exec_msg}，已清除 {cleared_count} 条记录',
                                type: 'positive',
                                position: 'top',
                                timeout: 3000
                            }})
                        ''')
                        
                        # 重新查询目录
                        ui.timer(0.1, self._query_directory, once=True)
                    else:
                        error_msg = data.get('exec_msg', '未知错误')
                        await ui.run_javascript(f'''
                            Quasar.Notify.create({{
                                message: '清除故障记录失败: {error_msg}',
                                type: 'negative',
                                position: 'top',
                                timeout: 5000
                            }})
                        ''')
            else:
                # 如果没有主容器，直接使用run_javascript
                if data.get('exec_status') == 'success':
                    # 获取清除的记录数量
                    cleared_count = data.get('cleared_count', 0)
                    exec_msg = data.get('exec_msg', '清除成功')
                    
                    # 清除表格数据
                    self._clear_data_table()
                    
                    # 显示成功通知
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '{exec_msg}，已清除 {cleared_count} 条记录',
                            type: 'positive',
                            position: 'top',
                            timeout: 3000
                        }})
                    ''')
                    
                    # 重新查询目录
                    ui.timer(0.1, self._query_directory, once=True)
                else:
                    error_msg = data.get('exec_msg', '未知错误')
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '清除故障记录失败: {error_msg}',
                            type: 'negative',
                            position: 'top',
                            timeout: 5000
                        }})
                    ''')
        except Exception as e:
            logger.error(f"处理清除记录响应失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '处理清除记录响应失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')

    def _clear_data_table(self):
        """清除表格数据"""
        try:
            if self.data_table:
                self.data_table.rows = []
                self.data_table.update()
        except Exception as e:
            logger.error(f"清除表格数据失败: {e}")

    def _update_fault_info(self, fault_info):
        """更新故障信息显示"""
        try:
            # 确保在主UI上下文中更新UI
            if self.main_container is not None:
                with self.main_container:
                    fault_time = fault_info.get('fault_time', '--')
                    fault_bits = fault_info.get('fault_bits', '--')
                    
                    if self.fault_time_label:
                        self.fault_time_label.set_text(fault_time)
                    
                    if self.fault_code_label:
                        self.fault_code_label.set_text(fault_bits)
                    
                    # 根据故障码生成故障描述
                    fault_desc = self._generate_fault_description(fault_bits)
                    if self.fault_desc_label:
                        self.fault_desc_label.set_text(fault_desc)
            else:
                # 如果没有主容器，直接更新UI
                fault_time = fault_info.get('fault_time', '--')
                fault_bits = fault_info.get('fault_bits', '--')
                
                if self.fault_time_label:
                    self.fault_time_label.set_text(fault_time)
                
                if self.fault_code_label:
                    self.fault_code_label.set_text(fault_bits)
                
                # 根据故障码生成故障描述
                fault_desc = self._generate_fault_description(fault_bits)
                if self.fault_desc_label:
                    self.fault_desc_label.set_text(fault_desc)
        except Exception as e:
            logger.error(f"更新故障信息显示失败: {e}")

    def _generate_fault_description(self, fault_bits):
        """根据故障码生成故障描述"""
        # 这里可以根据实际的故障码映射生成描述
        # 简化实现，返回示例描述
        if fault_bits == '--':
            return '--'
        return '1段电压保护、2段电流保护、系统异常'

    def _update_data_table(self, data_points):
        """更新数据表格"""
        try:
            if not self.data_table:
                return
            
            # 确保在主UI上下文中更新UI
            if self.main_container is not None:
                with self.main_container:
                    rows = []
                    for i, point in enumerate(data_points):
                        row = {
                            'index': i,
                            'system_status': point.get('system_status', '0x0000'),
                            'switch_input': point.get('switch_input', '0x0000'),
                            'switch_output': point.get('switch_output', '0x0000'),
                            'sv1': f"{point.get('rail_potential_max', 0)} V",
                            'sv2': f"{point.get('max_polarization', 0)} mV",
                            'sa1': f"{point.get('branch_currents', [0])[0]} A",
                            'sa2': f"{point.get('branch_voltages', [0])[0]} V",
                        }
                        rows.append(row)
                    
                    self.data_table.rows = rows
                    self.data_table.update()
            else:
                # 如果没有主容器，直接更新UI
                rows = []
                for i, point in enumerate(data_points):
                    row = {
                        'index': i,
                        'system_status': point.get('system_status', '0x0000'),
                        'switch_input': point.get('switch_input', '0x0000'),
                        'switch_output': point.get('switch_output', '0x0000'),
                        'sv1': f"{point.get('rail_potential_max', 0)} V",
                        'sv2': f"{point.get('max_polarization', 0)} mV",
                        'sa1': f"{point.get('branch_currents', [0])[0]} A",
                        'sa2': f"{point.get('branch_voltages', [0])[0]} V",
                    }
                    rows.append(row)
                
                self.data_table.rows = rows
                self.data_table.update()
        except Exception as e:
            logger.error(f"更新数据表格失败: {e}")
