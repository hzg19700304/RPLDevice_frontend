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
        self.is_cancelling = False  # 新增：取消标志位
        self.current_request_id = None
        self.total_records = 0  # 总记录数
        self.current_record = 0  # 当前记录
        self.current_progress = 0  # 当前进度
        
        # 获取配置
        self.analog_mapping = self._load_analog_mapping()
        self.status_bits = self._load_status_bits()
        # self.input_bits = self._load_input_bits()
        # self.output_bits = self._load_output_bits()
        
        # 注册WebSocket回调
        if self.websocket_client:
            self.websocket_client.register_message_callback(
                'fault_record_list_ack', 
                self._handle_directory_response
            )
            self.websocket_client.register_message_callback(
                'fault_record_read_start', 
                self._handle_read_start
            )
            self.websocket_client.register_message_callback(
                'fault_record_progress', 
                self._handle_read_progress
            )
            self.websocket_client.register_message_callback(
                'fault_record_complete', 
                self._handle_read_complete
            )
            self.websocket_client.register_message_callback(
                'fault_record_error', 
                self._handle_read_error
            )
            self.websocket_client.register_message_callback(
                'fault_record_cancelled', 
                self._handle_read_cancelled
            )
            self.websocket_client.register_message_callback(
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

    # def _load_input_bits(self):
    #     """加载开关量输入点表"""
    #     bits = {}
    #     section = 'HMI开关量输入点表'
    #     if self.config.config.has_section(section):
    #         for key, value in self.config.config.items(section):
    #             bit_num = key.replace('bit', '')
    #             bits[int(bit_num)] = value
    #     return bits

    # def _load_output_bits(self):
    #     """加载开关量输出点表"""
    #     bits = {}
    #     section = 'HMI开关量输出点表'
    #     if self.config.config.has_section(section):
    #         for key, value in self.config.config.items(section):
    #             bit_num = key.replace('bit', '')
    #             bits[int(bit_num)] = value
    #     return bits

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
        # 构建表格列定义 - 适配新4寄存器格式（系统状态 + SA1 + SA2 + SV1）
        columns = [
            {'name': 'index', 'label': '序号', 'field': 'index', 'align': 'center', 'style': 'width: 60px'},
            {'name': 'system_status', 'label': '系统状态', 'field': 'system_status', 'align': 'center', 'style': 'width: 80px'},
        ]
        
        # 添加模拟量列（从配置中读取）- 只包含实际支持的3个模拟量
        analog_columns = ['SA1', 'SA2', 'SV1']  # 移除SV2，只保留实际支持的3个模拟量
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
        ).classes('w-full h-96')  # 设置固定高度，启用滚动条
        
        # 重写 body 插槽，添加单元格点击事件
        self.data_table.add_slot('body', r'''
            <q-tr :props="props">
                <q-td v-for="col in props.cols" 
                      :key="col.name" 
                      :props="props"
                      @click="$parent.$emit('cell-click', {row: props.row, col: col.name, colIndex: props.cols.indexOf(col)})"
                >
                    {{ col.value }}
                </q-td>
            </q-tr>
        ''')
        
        # 设置表格事件 - 只保留单元格点击事件
        self.data_table.on('cell-click', self._on_cell_click)

    async def _query_directory(self):
        """查询故障录波目录"""   
        # 检查WebSocket连接状态
        if not self.websocket_client.is_connected:
            logger.error("WebSocket未连接，无法查询故障录波目录")
            ui.notify('WebSocket未连接，请检查网络连接', type='negative')
            return
        
        # 从配置文件获取设备ID
        device_id = self.config.get('设备配置', '设备ID', 'HYP_RPLD_001')
        
        # 发送WebSocket请求
        message = {
            'type': 'fault_record_list',
            'device_id': device_id,
            'request_id': f'req_dir_{datetime.now().timestamp()}'
        }
        
        result = await self.websocket_client.send_message(message['type'], message)
        logger.info(f"消息发送结果: {result}")
        
        # if result:
        #     ui.notify('正在查询故障录波目录...', type='info')
        # else:
        #     ui.notify('发送查询请求失败，请检查网络连接', type='negative')

    async def _query_detail(self):
        """查询故障录波详情"""
        if self.is_reading:
            ui.notify('正在读取中，请稍候...', type='warning')
            return
        
        # 🔥🔥🔥 新增检查：先判断记录可读数是否为0
        if self.available_records == 0:
            ui.notify('设备中没有故障录波记录，无法查询详情', type='negative')
            return
        
        record_id = self.record_select.value
        
        self.is_reading = True
        self.current_request_id = f'req_fault_read_{datetime.now().timestamp()}'
        
        # 先显示进度对话框，再发送请求
        self._show_progress_dialog()
        
        # 从配置文件获取设备ID
        device_id = self.config.get('设备配置', '设备ID', 'HYP_RPLD_001')
        
        # 发送WebSocket请求
        message = {
            'type': 'fault_record_read',
            'device_id': device_id,
            'record_id': record_id,
            'request_id': self.current_request_id
        }
        
        result = await self.websocket_client.send_message(message['type'], message)
        logger.info(f"故障录波详情消息发送结果: {result}")
        
        # 如果发送失败，立即关闭进度对话框并显示错误
        if not result:
            self.is_reading = False
            if self.progress_dialog:
                self.progress_dialog.close()
            ui.notify('发送查询请求失败，请检查网络连接', type='negative')

    async def _cancel_reading(self):
        """取消读取"""
        if not self.is_reading:
            return
        
        logger.info("用户取消故障录波读取")
        
        # 设置取消标志位
        self.is_cancelling = True
        self.is_reading = False
        
        # 从配置文件获取设备ID
        device_id = self.config.get('设备配置', '设备ID', 'HYP_RPLD_001')
        
        # 发送取消请求
        message = {
            'type': 'fault_record_cancel',
            'device_id': device_id,
            'request_id': self.current_request_id
        }
        
        await self.websocket_client.send_message(message['type'], message)
        
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
        
        # 生成请求ID
        import uuid
        request_id = str(uuid.uuid4())
        
        # 发送控制命令 - 只发送数据部分，不包含type字段
        message_data = {
            'cmd': 'fault_record_clear',
            'request_id': request_id,
            'cmd_param': {
                'coil_addr': '0x0110',
                'confirm': True
            }
        }
        
        await self.websocket_client.send_message('control_cmd', message_data)
        dialog.close()
        # ui.notify('正在清除故障录波记录...', type='info')

    def _show_progress_dialog(self):
        """显示进度对话框"""
        self.progress_dialog = ui.dialog().props('persistent')
        
        with self.progress_dialog, ui.card().classes('w-96'):
            ui.label('正在读取故障录波...').classes('text-h6 q-mb-md')
            
            self.progress_bar = ui.linear_progress(value=0).classes('w-full')
            
            with ui.row().classes('w-full justify-between q-mt-md'):
                self.progress_text = ui.label('当前批次: 0/0')
                # ui.label('预计剩余时间: --')
            
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
                        status_text = bit_mapping[bit_num]
                        # 如果状态文本包含逗号，取右边部分（1状态）
                        if ',' in status_text:
                            status_parts = status_text.split(',')
                            display_status = status_parts[1]
                        else:
                            display_status = status_text
                        
                        # 判断是否为保留位，保留位显示灰色圆点
                        if '保留' in display_status:
                            icon = '⚪'  # 灰色圆点，颜色更深一点
                        else:
                            icon = '🔴' if is_set else '🟢'
                        
                        ui.label(f'bit{bit_num}: {icon} {display_status}').classes('text-body2')
            
            ui.button('关闭', on_click=dialog.close).props('flat').classes('w-full')
        
        dialog.open()

    def _on_cell_click(self, event):
        """表格单元格点击事件"""
        # event.args 结构: {row: 行数据, col: 列名, colIndex: 列索引}
        row_data = event.args['row']
        col_name = event.args['col']
        # col_index = event.args['colIndex']
        
        # logger.info(f"点击单元格: 列'{col_name}' (索引{col_index}), 值: {row_data[col_name]}")
        
        # 根据点击的列处理相应的数据
        if isinstance(row_data, dict):
            # logger.info(f"正在处理列 {col_name} 的点击事件")
            if col_name == 'system_status' and 'system_status' in row_data:
                # logger.info(f"显示系统状态解析框: {row_data['system_status']}")
                self._show_bit_parse_dialog(
                    '系统状态',
                    row_data['system_status'],
                    self.status_bits
                )
            else:
                logger.warning(f"列 {col_name} 没有对应的处理逻辑或数据不存在")
        else:
            logger.warning(f"行数据类型错误: {type(row_data)}")

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
        elif msg_type == 'error':
            # 处理通用错误消息
            await self._handle_general_error(message)
        else:
            logger.warning(f"未知的消息类型: {msg_type}")

    async def _handle_directory_response(self, message):
        """处理目录查询响应"""
        try:
            logger.info(f"收到目录查询响应: {message}")
            
            # 从消息中提取故障录波目录信息
            # 注意：有些情况下消息本身就是数据，需要兼容处理
            if 'total_records' in message and 'data' not in message:
                # 消息本身就是数据格式
                data = message
            else:
                # 标准格式：数据在data字段中
                data = message.get('data', {})
            
            self.available_records = data.get('total_records', 0)
            
            # 存储记录信息供后续使用
            self.fault_records_info = data.get('records', [])
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    # 更新UI
                    if self.record_count_label:
                        self.record_count_label.set_text(str(self.available_records))
                    
                    # 更新记录选择下拉框
                    if self.record_select:
                        options = list(range(self.available_records))
                        self.record_select.set_options(options)
                        if options:
                            self.record_select.set_value(0)
                    
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

        logger.info(f"收到读取开始响应: {message}")

        # 如果正在取消，忽略开始消息
        if self.is_cancelling:
            logger.info("收到开始消息但正在取消中，忽略")
            return

        try:
            # 兼容处理不同的消息格式
            if 'exec_status' in message and 'data' not in message:
                data = message
            else:
                data = message.get('data', {})
                
            if data.get('exec_status') == 'success':
                # 重置进度和取消标志位
                self.current_progress = 0
                self.is_cancelling = False  # 重置取消标志位
                # 适配后端格式：使用 total_batches 作为 total_records
                self.total_records = data.get('total_batches', 301)  # 默认301批
                
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
                            # 显示完成通知 - 使用ui.notify避免JavaScript超时
                            ui.notify('开始读取故障记录...', type='info', position='top', timeout=3000)
                        })
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

    async def _handle_read_progress(self, message):
        """处理读取进度"""
        # 如果正在取消，忽略进度消息
        if self.is_cancelling:
            # logger.info("收到进度消息但正在取消中，忽略")
            return
            
        try:
            # 适配后端实际发送的数据格式
            if 'percentage' in message:
                # 后端格式：包含 percentage, current_batch, total_batches
                self.current_progress = message.get('percentage', 0)
                self.current_record = message.get('current_batch', 0)
                self.total_records = message.get('total_batches', 301)  # 默认301批
                # logger.info(f"检测到后端标准格式进度消息 - percentage: {self.current_progress}%, current_batch: {self.current_record}, total_batches: {self.total_records}")
            elif 'progress' in message and 'data' not in message:
                # 另一种可能的格式
                self.current_progress = message.get('progress', 0)
                self.current_record = message.get('current_record', 0)
                self.total_records = message.get('total_records', 301)
                # logger.info(f"检测到读取进度消息本身就是数据格式 - progress: {self.current_progress}%, current_record: {self.current_record}, total_records: {self.total_records}")
            else:
                # 标准格式：data 中包含进度信息
                data = message.get('data', {})
                self.current_progress = data.get('progress', 0)
                self.current_record = data.get('current_record', 0)
                self.total_records = data.get('total_records', 301)
                # logger.info(f"检测到读取进度标准格式 - progress: {self.current_progress}%, current_record: {self.current_record}, total_records: {self.total_records}")
            
            # 更新进度条
            self._update_progress_ui()
            
            # 记录日志
            # logger.info(f"读取进度: {self.current_progress}% ({self.current_record}/{self.total_records})")
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

    async def _handle_read_complete(self, message):
        """处理读取完成响应"""
        # 如果正在取消，忽略完成消息
        if self.is_cancelling:
            # logger.info("收到完成消息但正在取消中，忽略")
            self.is_cancelling = False  # 重置取消标志位
            return
            
        try:
            self.is_reading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # 从消息中提取数据 - 兼容处理不同格式
            if 'fault_info' in message and 'data' not in message:
                data = message
                # logger.info("检测到读取完成消息本身就是数据格式")
            else:
                data = message.get('data', {})
                # logger.info("检测到读取完成标准格式")
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    if data:  # 检查是否有数据
                        # 获取故障记录数据
                        fault_info = data.get('fault_info', {})
                        data_points = data.get('data_points', [])
                        
                        # 更新故障信息
                        self._update_fault_info(fault_info)
                        
                        # 更新数据表格
                        self._update_data_table(data_points)
                        
                        # 更新进度条到100% - 确保完成时总是显示100%
                        self.current_progress = 100
                        self.current_record = self.total_records
                        logger.info(f"读取完成，设置最终进度: {self.current_progress}% ({self.current_record}/{self.total_records})")
                        self._update_progress_ui()
                        
                        # 显示完成通知
                        await ui.run_javascript('''
                            Quasar.Notify.create({
                                message: '故障记录读取完成',
                                type: 'positive',
                                position: 'top',
                                timeout: 3000
                            }')
                        ''')
                    else:
                        error_msg = '未收到故障记录数据'
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
                if data:  # 检查是否有数据
                    # 获取故障记录数据
                    fault_info = data.get('fault_info', {})
                    data_points = data.get('data_points', [])
                    
                    # 记录数据点数量用于调试
                    # logger.info(f"从完成响应中提取到 {len(data_points)} 个数据点")
                    if len(data_points) > 0:
                        logger.info(f"第一个数据点示例: {data_points[0] if data_points else '无'}")
                        logger.info(f"最后一个数据点示例: {data_points[-1] if data_points else '无'}")
                    
                    # 更新故障信息
                    self._update_fault_info(fault_info)
                    
                    # 更新数据表格
                    self._update_data_table(data_points)
                    
                    # 更新进度条到100% - 确保完成时总是显示100%
                    self.current_progress = 100
                    self.current_record = self.total_records
                    # logger.info(f"读取完成，设置最终进度: {self.current_progress}% ({self.current_record}/{self.total_records})")
                    self._update_progress_ui()
                    
                    # 显示完成通知
                    await ui.run_javascript('''
                        Quasar.Notify.create({
                            message: '故障记录读取完成',
                            type: 'positive',
                            position: 'top',
                            timeout: 3000
                        }')
                    ''')
                else:
                    error_msg = '未收到故障记录数据'
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

    async def _handle_read_error(self, message):
        """处理读取错误"""
        try:
            self.is_reading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # 从消息中提取错误信息 - 兼容处理不同格式
            if 'error_msg' in message and 'data' not in message:
                data = message
                logger.info("检测到读取错误消息本身就是数据格式")
            else:
                data = message.get('data', {})
                logger.info("检测到读取错误标准格式")
            
            error_msg = data.get('error_msg', '未知错误')
            error_code = data.get('error_code', 0)
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    # 显示错误对话框
                    with ui.dialog() as dialog, ui.card().classes('w-96'):
                        ui.label('❌ 读取故障录波数据失败').classes('text-h6 q-mb-md')
                        
                        ui.separator()
                        
                        ui.label(f'错误信息: {error_msg}').classes('text-body2 q-my-md')
                        ui.label(f'错误代码: {error_code}').classes('text-body2')
                        
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

    async def _handle_general_error(self, message):
        """处理通用错误消息"""
        try:
            self.is_reading = False
            
            # 关闭进度对话框
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # 提取错误信息
            error_code = message.get('error_code', 0)
            error_msg = message.get('error_msg', '未知错误')
            
            logger.error(f"收到通用错误消息: 错误代码={error_code}, 错误信息={error_msg}")
            
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    ui.notify(f'读取故障录波失败: {error_msg}', type='negative')
            else:
                # 如果没有主容器，直接使用run_javascript
                await ui.run_javascript(f'''
                    Quasar.Notify.create({{
                        message: '读取故障录波失败: {error_msg}',
                        type: 'negative',
                        position: 'top',
                        timeout: 5000
                    }})
                ''')
        except Exception as e:
            logger.error(f"处理通用错误消息失败: {e}")
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '处理错误消息失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')

    async def _handle_read_cancelled(self, message):
        """处理取消确认"""
        try:
            # 从消息中提取数据 - 兼容处理不同格式
            if 'cancelled_at_batch' in message and 'data' not in message:
                data = message
                logger.info("检测到取消消息本身就是数据格式")
            else:
                data = message.get('data', {})
                logger.info("检测到取消消息标准格式")
                
            cancelled_at_batch = data.get('cancelled_at_batch', 0)
            logger.info(f"故障录波读取已取消，取消于第 {cancelled_at_batch} 批")
            
            # 重置取消标志位
            self.is_cancelling = False
            self.is_reading = False
            
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
                Quasar.Notify.create({{
                    message: '处理取消确认失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
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
                        logger.info(f"故障码 {fault_bits} 生成描述: {fault_desc}")
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
        try:
            # 处理十六进制字符串格式的故障码
            if fault_bits == '--' or not fault_bits:
                return '--'
            
            # 将十六进制字符串转换为整数
            if isinstance(fault_bits, str) and fault_bits.startswith('0x'):
                fault_code = int(fault_bits, 16)
            elif isinstance(fault_bits, str):
                fault_code = int(fault_bits, 16) if all(c in '0123456789abcdefABCDEF' for c in fault_bits) else 0
            else:
                fault_code = int(fault_bits)
            
            # 使用页面配置管理器获取故障码映射
            fault_mapping = self.config.get_fault_code_mapping()
            
            # 解析故障码映射表，提取故障描述
            fault_map = {}
            for key, value in fault_mapping.items():
                if key.startswith('bit') and ',' in value:
                    # 提取逗号后面的故障描述（1=故障状态）
                    fault_desc = value.split(',')[1].strip()
                    if fault_desc and fault_desc != '保留':
                        # 根据bit位计算对应的十六进制值
                        bit_num = int(key.replace('bit', ''))
                        hex_code = 1 << bit_num
                        fault_map[hex_code] = fault_desc
            
            # 解析故障码
            descriptions = []
            for code, desc in fault_map.items():
                if fault_code & code:
                    descriptions.append(desc)
            
            return '、'.join(descriptions) if descriptions else '无故障'
            
        except (ValueError, TypeError) as e:
            logger.error(f"解析故障码失败: {fault_bits}, 错误: {e}")
            return f'故障码解析错误: {fault_bits}'

    def _update_data_table(self, data_points):
        """更新数据表格"""
        try:
            if not self.data_table:
                return
            
            # 记录实际数据点数量
            # actual_count = len(data_points)
            # logger.info(f"收到 {actual_count} 个数据点用于更新表格")
            
            # 确保在主UI上下文中更新UI
            if self.main_container is not None:
                with self.main_container:
                    rows = []
                    for i, point in enumerate(data_points):
                        row = {
                        'index': i,
                        'system_status': point.get('system_status', '0x0000'),
                        # 移除switch_input和switch_output，后端4寄存器格式不包含这些数据
                        'sv1': f"{point.get('channel3_sv1', 0)} V",      # SV1: 通道3轨地电压
                        'sa1': f"{point.get('channel1_sa1', 0)} A",      # SA1: 通道1轨地电流
                        'sa2': f"{point.get('channel2_sa2', 0)} A",      # SA2: 通道2轨地电流
                    }
                        rows.append(row)
                    
                    # logger.info(f"生成表格行数: {len(rows)}")
                    self.data_table.rows = rows
                    self.data_table.update()
                    logger.info(f"表格更新完成，显示 {len(self.data_table.rows)} 行")
            else:
                # 如果没有主容器，直接更新UI
                rows = []
                for i, point in enumerate(data_points):
                    row = {
                        'index': i,
                        'system_status': point.get('system_status', '0x0000'),
                        # 移除switch_input和switch_output，后端4寄存器格式不包含这些数据
                        'sv1': f"{point.get('channel3_sv1', 0)} V",      # SV1: 通道3轨地电压
                        'sa1': f"{point.get('channel1_sa1', 0)} A",      # SA1: 通道1轨地电流
                        'sa2': f"{point.get('channel2_sa2', 0)} A",      # SA2: 通道2轨地电流
                    }
                    rows.append(row)
                
                # logger.info(f"生成表格行数: {len(rows)}")
                self.data_table.rows = rows
                self.data_table.update()
                logger.info(f"表格更新完成，显示 {len(self.data_table.rows)} 行")
        except Exception as e:
            logger.error(f"更新数据表格失败: {e}")