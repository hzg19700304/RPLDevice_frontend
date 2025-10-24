"""
系统状态页面
System Status Page
"""
# flake8: noqa
import logging
from nicegui import ui

logger = logging.getLogger(__name__)


class SystemStatusPage:
    """系统状态页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.status_groups = {}
        self._load_status_config()
        
    def _load_status_config(self):
        """从config.ini加载状态配置"""
        try:
            # 加载五个状态分组的配置
            self.status_groups = {
                '系统状态': self._parse_status_bits('HMI系统状态点表'),
                'IGBT光纤状态': self._parse_status_bits('HMI IGBT光纤状态点表'),
                '开关量输入': self._parse_status_bits('HMI开关量输入点表'),
                '开关量输出': self._parse_status_bits('HMI开关量输出点表'),
                '故障信息': self._parse_status_bits('HMI故障点表')
            }
            logger.info("状态配置加载成功")
        except Exception as e:
            logger.error(f"加载状态配置失败: {e}")
            # 设置默认配置
            self.status_groups = {
                '系统状态': {},
                'IGBT光纤状态': {},
                '开关量输入': {},
                '开关量输出': {},
                '故障信息': {}
            }
    
    def _parse_status_bits(self, section_name):
        """解析状态位配置"""
        status_bits = {}
        try:
            if self.config.config.has_section(section_name):
                for key, value in self.config.config.items(section_name):
                    if key.startswith('bit'):
                        bit_num = int(key[3:])  # 提取bit后面的数字
                        if ',' in value:
                            zero_text, one_text = value.split(',', 1)
                            status_bits[bit_num] = {
                                'zero_text': zero_text.strip(),
                                'one_text': one_text.strip()
                            }
        except Exception as e:
            logger.error(f"解析状态位配置失败 {section_name}: {e}")
        return status_bits
        
    def create_page(self) -> ui.column:
        """创建系统状态页面"""
        # 获取字体配置
        font_config = self.config.get_font_config()
        enable_responsive = font_config.get('enable_responsive_font', True)
        scale_factor = font_config.get('font_scale_factor', 1.0)
        title_size = int(font_config.get('title_font_size', 20) * scale_factor)
        status_size = int(font_config.get('status_font_size', 12) * scale_factor)
        
        # 获取布局配置
        layout_config = self.config.get_layout_config()
        min_width = layout_config.get('min_window_width', 1200)
        card_min_width = layout_config.get('status_card_min_width', 280)
        item_min_height = layout_config.get('status_item_min_height', 24)
        
        # 根据配置生成字体样式
        if enable_responsive:
            title_font = f"max({title_size-4}px, min(3vw, {title_size+4}px))"
            text_font = f"max({status_size}px, min(1.0vw, {status_size+4}px))"
            icon_font = f"max({status_size-2}px, min(2vw, {status_size+6}px))"
        else:
            title_font = f"{title_size}px"
            text_font = f"{status_size}px"
            icon_font = f"{status_size+4}px"
        
        # 修改 ui.add_head_html，添加渐变圆点样式
        ui.add_head_html(f'''
        <style>
        /* 之前的样式... */
        body {{
            min-width: {min_width}px !important;
        }}
        
        .responsive-title {{
            font-size: {title_font} !important;
            font-weight: 600 !important;
        }}
        .responsive-text {{
            font-size: {text_font} !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}
        .responsive-icon {{
            font-size: {icon_font} !important;
            flex-shrink: 0 !important;
        }}
        
        .q-card .responsive-title {{
            font-size: {title_font} !important;
        }}
        .q-card .responsive-text {{
            font-size: {text_font} !important;
        }}
        
        .status-item-row {{
            display: flex !important;
            align-items: center !important;
            gap: 0px !important;
            min-height: {item_min_height}px !important;
            padding: 0px 4px !important;
            margin: 0px 0 !important;
        }}
        
        .status-text {{
            flex: 1 !important;
            min-width: 0 !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }}
        
        .status-card {{
            min-width: {card_min_width}px !important;
        }}
        
        .status-container {{
            min-width: {min_width}px !important;
            overflow-x: auto !important;
        }}
        
        /* === 渐变立体圆点样式 === */
        .material-icons.status-dot {{
            width: 16px !important;
            height: 16px !important;
            font-size: 16px !important;
            border-radius: 50% !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            position: relative !important;
            box-shadow: 
                0 2px 4px rgba(0,0,0,0.2),
                inset 0 -2px 4px rgba(0,0,0,0.2),
                inset 0 2px 4px rgba(255,255,255,0.4) !important;
            transition: all 0.3s ease !important;
            flex-shrink: 0 !important;
        }}
        
        /* 绿色渐变 - 正常状态 */
        .status-dot.dot-positive {{
            background: linear-gradient(135deg, #4ade80 0%, #16a34a 50%, #15803d 100%) !important;
            color: transparent !important;
        }}
        
        /* 红色渐变 - 告警状态 */
        .status-dot.dot-negative {{
            background: linear-gradient(135deg, #f87171 0%, #dc2626 50%, #b91c1c 100%) !important;
            color: transparent !important;
            animation: pulse-red 2s ease-in-out infinite !important;
        }}
        
        /* 灰色渐变 - 保留状态 */
        .status-dot.dot-grey {{
            background: linear-gradient(135deg, #d1d5db 0%, #9ca3af 50%, #6b7280 100%) !important;
            color: transparent !important;
        }}
        
        /* 红色脉冲动画 */
        @keyframes pulse-red {{
            0%, 100% {{
                box-shadow: 
                    0 2px 4px rgba(0,0,0,0.2),
                    inset 0 -2px 4px rgba(0,0,0,0.2),
                    inset 0 2px 4px rgba(255,255,255,0.4),
                    0 0 0 0 rgba(239, 68, 68, 0.7);
            }}
            50% {{
                box-shadow: 
                    0 2px 4px rgba(0,0,0,0.2),
                    inset 0 -2px 4px rgba(0,0,0,0.2),
                    inset 0 2px 4px rgba(255,255,255,0.4),
                    0 0 0 6px rgba(239, 68, 68, 0);
            }}
        }}
        
        /* 悬停效果 */
        .status-dot:hover {{
            transform: scale(1.15) !important;
            box-shadow: 
                0 3px 6px rgba(0,0,0,0.3),
                inset 0 -2px 4px rgba(0,0,0,0.2),
                inset 0 2px 4px rgba(255,255,255,0.5) !important;
        }}
        </style>
        ''')
        
        # 使用容器包装，确保最小宽度
        with ui.column().classes('w-full h-full').style(f'min-width: {min_width}px;'):
            with ui.row().classes('w-full h-full q-gutter-md justify-evenly status-container'):
                # 创建五个状态分组，水平布局，平均分配空间
                for group_name, status_config in self.status_groups.items():
                    self._create_status_group(group_name, status_config)
        
        # 注册WebSocket数据回调函数
        self._register_websocket_callbacks()
        
        return ui.column()  # 返回一个空的column作为占位符
    
    def _register_websocket_callbacks(self):
        """注册WebSocket数据回调函数"""
        if self.websocket_client:
            # 注册系统状态数据回调
            self.websocket_client.register_data_callback('system_status', self._handle_system_status)
            # switch_io数据类型已合并到system_status中，不再单独注册
            # self.websocket_client.register_data_callback('switch_io', self._handle_switch_io)
            # 注册故障数据回调
            self.websocket_client.register_data_callback('fault', self._handle_fault_data)
            # 注册全量快照数据回调
            self.websocket_client.register_data_callback('full_snapshot', self._handle_full_snapshot)
            # logger.info("WebSocket数据回调函数注册成功")
    
    async def _handle_system_status(self, data):
        """处理系统状态数据"""
        try:
            # logger.info(f"收到系统状态数据: {data}")
            status_data = {}
            
            # 如果data中包含data字段，则提取data字段
            if 'data' in data:
                data = data['data']
                # logger.info(f"提取后的系统状态数据: {data}")
            
            # 处理系统状态
            if 'system_status' in data:
                status_data['系统状态'] = {}
                for key, value in data['system_status'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['系统状态'][bit_num] = value
            
            # 处理IGBT光纤状态
            if 'igbt_fiber_status' in data:
                logger.debug(f"IGBT光纤状态数据: {data['igbt_fiber_status']}")
                status_data['IGBT光纤状态'] = {}
                for key, value in data['igbt_fiber_status'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['IGBT光纤状态'][bit_num] = value
                logger.debug(f"处理后的IGBT光纤状态: {status_data['IGBT光纤状态']}")
            else:
                logger.debug("全量快照数据中未找到IGBT光纤状态")
            
            # 处理开关量输入（switch_input）
            if 'switch_input' in data:
                status_data['开关量输入'] = {}
                for key, value in data['switch_input'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['开关量输入'][bit_num] = value
            
            # 处理开关量输出（switch_output）
            if 'switch_output' in data:
                status_data['开关量输出'] = {}
                for key, value in data['switch_output'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['开关量输出'][bit_num] = value
            
            # 处理故障状态
            if 'fault_status' in data:
                status_data['故障信息'] = {}
                for key, value in data['fault_status'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['故障信息'][bit_num] = value
            
            # logger.info(f"处理后的状态数据: {status_data}")
            if status_data:
                self.update_status_data(status_data)
        except Exception as e:
            logger.error(f"处理系统状态数据失败: {e}")
    
    async def _handle_switch_io(self, data):
        """处理开关量数据（已废弃，switch_io数据已合并到system_status中）"""
        logger.warning("switch_io数据类型已合并到system_status中，此方法不再使用")
        # 保留此方法用于兼容性，但实际数据应通过system_status获取
    
    async def _handle_fault_data(self, data):
        """处理故障数据"""
        try:
            logger.debug(f"收到故障数据: {data}")
            # 将故障数据转换为故障信息格式
            fault_bit = data.get('fault_bit', 0)
            fault_status = data.get('fault_status', 0)
            
            status_data = {'故障信息': {fault_bit: fault_status}}
            self.update_status_data(status_data)
        except Exception as e:
            logger.error(f"处理故障数据失败: {e}")
    
    async def _handle_full_snapshot(self, data):
        """处理全量快照数据"""
        try:
            logger.debug(f"收到全量快照数据: {data}")
            status_data = {}
            
            # 处理系统状态
            if 'system_status' in data:
                status_data['系统状态'] = {}
                for key, value in data['system_status'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['系统状态'][bit_num] = value
            
            # 处理开关量输入
            if 'switch_input' in data:
                status_data['开关量输入'] = {}
                for key, value in data['switch_input'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['开关量输入'][bit_num] = value
            
            # 处理开关量输出
            if 'switch_output' in data:
                status_data['开关量输出'] = {}
                for key, value in data['switch_output'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['开关量输出'][bit_num] = value
            
            # 处理故障信息
            if 'fault_info' in data:
                status_data['故障信息'] = {}
                for key, value in data['fault_info'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['故障信息'][bit_num] = value
            
            # 处理IGBT光纤状态
            if 'igbt_fiber_status' in data:
                status_data['IGBT光纤状态'] = {}
                for key, value in data['igbt_fiber_status'].items():
                    if key.startswith('bit'):
                        bit_num = int(key[3:])
                        status_data['IGBT光纤状态'][bit_num] = value
            
            self.update_status_data(status_data)
            # logger.info("全量快照数据更新完成")
        except Exception as e:
            logger.error(f"处理全量快照数据失败: {e}")
    
    def _load_test_data(self):
        """加载测试数据以展示不同状态效果（已弃用，保留用于测试）"""
        logger.warning("使用测试数据，实际应用中应该从WebSocket获取实时数据")
        # 模拟一些状态数据来展示界面效果
        test_data = {
            '系统状态': {
                0: 0,  # 保留 -> 灰色
                1: 0,  # 保留 -> 灰色  
                5: 1,  # 故障状态 -> 红色
                7: 0,  # 参数正确 -> 绿色
                8: 1,  # KM1闭锁 -> 红色
                9: 0,  # 存储器正常 -> 绿色
            },
            '开关量输入': {
                0: 0,  # 短接接触器分位 -> 绿色
                1: 0,  # SB1分位 -> 绿色
                2: 1,  # SB2合位 -> 红色
                9: 1,  # 门锁关闭 -> 红色
            },
            '开关量输出': {
                0: 1,  # K1合闸 -> 红色
                8: 0,  # K9分闸 -> 绿色
                9: 1,  # 运行指示 -> 红色
            },
            '故障信息': {
                0: 0,  # 1段电压保护恢复 -> 绿色
                1: 0,  # 2段电压保护恢复 -> 绿色
                2: 1,  # 3段电压保护 -> 红色
                10: 1, # 晶闸管动作 -> 红色
                11: 0, # 接触器正常 -> 绿色
            }
        }
        
        # 应用测试数据
        self.update_status_data(test_data)
    
    def _create_status_group(self, group_name, status_config):
        """创建状态分组展示"""
        # 获取布局配置
        layout_config = self.config.get_layout_config()
        card_min_width = layout_config.get('status_card_min_width', 280)
        item_min_height = layout_config.get('status_item_min_height', 24)
        
        with ui.card().classes('flex-1 q-pa-md status-card').style(f'min-width: {card_min_width}px; height: calc(100vh - 170px); display: flex; flex-direction: column'):
            # 卡片标题 - 使用响应式字体大小
            ui.label(group_name).classes('text-center responsive-title').style('margin-bottom: 0px; white-space: nowrap;')
            
            # 状态列表，使用flex布局平均分布
            with ui.column().classes('flex-1').style('display: flex; flex-direction: column; justify-content: space-evenly; overflow-y: auto; padding: 4px;'):
                if not status_config:
                    ui.label('暂无配置数据').classes('text-grey-6 responsive-text')
                else:
                    # 按bit位顺序显示状态
                    for bit_num in sorted(status_config.keys()):
                        bit_config = status_config[bit_num]
                        self._create_status_item(group_name, bit_num, bit_config)
    
    def _create_status_item(self, group_name, bit_num, bit_config):
        """创建单个状态项显示"""
        # 获取布局配置
        layout_config = self.config.get_layout_config()
        item_min_height = layout_config.get('status_item_min_height', 24)
        
        with ui.row().classes('items-center status-item-row').style(f'flex: 1; min-height: {item_min_height}px;'):
            zero_text = bit_config.get('zero_text', '保留')
            one_text = bit_config.get('one_text', '保留')
            
            # 如果是保留位，显示灰色渐变圆点
            if zero_text == '保留' and one_text == '保留':
                status_icon = ui.icon('circle').classes('status-dot dot-grey')
                status_text = ui.label(f'Bit{bit_num}: 保留').classes('text-grey-6 responsive-text status-text')
            else:
                # 默认显示0状态（绿色渐变圆点）
                status_icon = ui.icon('circle').classes('status-dot dot-positive')
                status_text = ui.label(f'Bit{bit_num}: {zero_text}').classes('text-positive responsive-text status-text')
            
            # 存储引用以便后续更新，使用组名和bit位作为唯一标识
            status_key = f'{group_name}_{bit_num}'
            setattr(self, f'status_icon_{status_key}', status_icon)
            setattr(self, f'status_text_{status_key}', status_text)
            setattr(self, f'status_config_{status_key}', bit_config)
    
    def update_status_bit(self, group_name, bit_num, bit_value):
        """更新单个状态位显示
        
        Args:
            group_name: 状态组名称
            bit_num: 位号
            bit_value: 位值 (0 或 1)
        """
        status_key = f'{group_name}_{bit_num}'
        
        # 获取UI组件引用
        status_icon = getattr(self, f'status_icon_{status_key}', None)
        status_text = getattr(self, f'status_text_{status_key}', None)
        bit_config = getattr(self, f'status_config_{status_key}', None)
        
        if not all([status_icon, status_text, bit_config]):
            return
            
        zero_text = bit_config.get('zero_text', '保留')
        one_text = bit_config.get('one_text', '保留')
        
        # 如果是保留位，始终显示灰色
        if zero_text == '保留' and one_text == '保留':
            status_icon.classes('status-dot dot-grey', remove='dot-positive dot-negative')
            status_text.set_text(f'Bit{bit_num}: 保留')
            status_text.classes('text-grey-6 responsive-text status-text', remove='text-positive text-negative')
        else:
            if bit_value == 1:
                # 状态位为1：红色渐变圆点（带脉冲动画）
                status_icon.classes('status-dot dot-negative', remove='dot-positive dot-grey')
                status_text.set_text(f'Bit{bit_num}: {one_text}')
                status_text.classes('text-negative responsive-text status-text', remove='text-positive text-grey-6')
            else:
                # 状态位为0：绿色渐变圆点
                status_icon.classes('status-dot dot-positive', remove='dot-negative dot-grey')
                status_text.set_text(f'Bit{bit_num}: {zero_text}')
                status_text.classes('text-positive responsive-text status-text', remove='text-negative text-grey-6')
    
    def update_status_data(self, status_data):
        """更新状态数据显示
        
        Args:
            status_data: 包含各组状态数据的字典
                格式: {
                    '系统状态': {0: 1, 1: 0, ...},
                    '开关量输入': {0: 0, 1: 1, ...},
                    ...
                }
        """
        for group_name, group_data in status_data.items():
            if group_name in self.status_groups:
                for bit_num, bit_value in group_data.items():
                    self.update_status_bit(group_name, bit_num, bit_value)