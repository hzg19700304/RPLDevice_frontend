"""
参数设置页面
Parameter Settings Page
"""
# flake8: noqa
import logging
from nicegui import ui
from typing import Dict, List

logger = logging.getLogger(__name__)


class ParameterSettingsPage:
    """参数设置页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.param_inputs = {}  # 存储所有参数输入框的引用
        self.param_mapping = {}  # 存储参数地址到名称的映射

        # 注册WebSocket回调
        if self.websocket_client:
            self.websocket_client.register_data_callback(
                'param_read_ack', 
                self._handle_param_read_response
            )
            self.websocket_client.register_data_callback(
                'param_write_ack', 
                self._handle_param_write_response
            )

    async def _handle_param_read_response(self, data):
        """处理参数读取响应"""
        try:
            if 'params' in data:
                await self.update_param_values(data['params'])
            elif 'data' in data and 'params' in data['data']:
                await self.update_param_values(data['data']['params'])
        except Exception as e:
            logger.error(f"处理参数读取响应失败: {e}")

    async def _handle_param_write_response(self, data):
        """处理参数写入响应"""
        try:
            if data.get('exec_status') == 'success':
                ui.notify('参数写入成功', type='positive')
            else:
                error_msg = data.get('exec_msg', '未知错误')
                ui.notify(f'参数写入失败: {error_msg}', type='negative')
        except Exception as e:
            logger.error(f"处理参数写入响应失败: {e}")
        
    def create_page(self) -> ui.column:
        """创建参数设置页面"""
        # 从配置文件加载参数映射
        self._load_param_mapping()
        
        with ui.card().classes('w-full').style('height: calc(100vh - 120px); overflow-y: auto;'):
            ui.label('控制参数设置').classes('text-h5 q-mb-md')
            
            # 顶部操作按钮
            with ui.row().classes('w-full q-mb-md justify-end'):
                ui.button('读取', color='primary', on_click=self._on_read_params).style('min-width: 100px;')
                ui.button('写入', color='positive', on_click=self._on_write_params).style('min-width: 100px;')
            
            # 按参数类型分组显示
            self._create_protection_value_section()
            self._create_protection_delay_section()
            self._create_km_delay_section()
            self._create_continuous_time_section()
            self._create_continuous_count_section()
            self._create_other_params_section()
            
            # 添加底部间距，确保最后一个卡片的边框可见
            ui.element('div').classes('q-pb-md')
        
        return ui.column()
    
    def _load_param_mapping(self):
        """从配置文件加载参数映射"""
        try:
            self.param_mapping = self.config.get_control_parameters_mapping()
            logger.info(f"加载了 {len(self.param_mapping)} 个控制参数")
        except Exception as e:
            logger.error(f"加载参数映射失败: {e}")
            self.param_mapping = {}
    
    def _create_protection_value_section(self):
        """创建保护值参数区域"""
        # 筛选保护值参数（1-11段）
        protection_params = [(addr, name) for addr, name in self.param_mapping.items() 
                            if '段保护值' in name and not '延时' in name]
        
        if not protection_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('保护值设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            with ui.grid(columns=4).classes('w-full gap-2'):
                for addr, name in sorted(protection_params, key=lambda x: self._extract_stage_number(x[1])):
                    self._create_param_input(name, addr, default_value='0')
    
    def _create_protection_delay_section(self):
        """创建保护延时参数区域"""
        delay_params = [(addr, name) for addr, name in self.param_mapping.items() 
                       if '段保护延时' in name]
        
        if not delay_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('保护延时设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            with ui.grid(columns=4).classes('w-full gap-2'):
                for addr, name in sorted(delay_params, key=lambda x: self._extract_stage_number(x[1])):
                    self._create_param_input(name, addr, default_value='0')
    
    def _create_km_delay_section(self):
        """创建KM闭合延时参数区域"""
        km_params = [(addr, name) for addr, name in self.param_mapping.items() 
                    if 'KM闭合延时' in name]
        
        if not km_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('KM闭合延时设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            with ui.grid(columns=4).classes('w-full gap-2'):
                for addr, name in sorted(km_params, key=lambda x: self._extract_stage_number(x[1])):
                    self._create_param_input(name, addr, default_value='0')
    
    def _create_continuous_time_section(self):
        """创建连续动作时间参数区域"""
        time_params = [(addr, name) for addr, name in self.param_mapping.items() 
                       if '连续动作时间' in name]
        
        if not time_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('连续动作时间设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            # 使用响应式网格布局，确保所有控件都能完整显示
            with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-4 gap-4 w-full'):
                for addr, name in sorted(time_params, key=lambda x: self._extract_stage_number(x[1])):
                    self._create_param_input(name, addr, default_value='0')
    
    def _create_continuous_count_section(self):
        """创建连续动作次数参数区域"""
        count_params = [(addr, name) for addr, name in self.param_mapping.items() 
                       if '连续动作次数' in name]
        
        if not count_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('连续动作次数设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            # 使用响应式网格布局，确保所有控件都能完整显示
            with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-4 gap-4 w-full'):
                for addr, name in sorted(count_params, key=lambda x: self._extract_stage_number(x[1])):
                    self._create_param_input(name, addr, default_value='0')
    
    def _create_other_params_section(self):
        """创建其他参数区域"""
        # 筛选不在上述分组中的参数
        other_params = [(addr, name) for addr, name in self.param_mapping.items() 
                       if not any(keyword in name for keyword in 
                                 ['段保护值', '段保护延时', 'KM闭合延时', 
                                  '连续动作时间', '连续动作次数'])]
        
        if not other_params:
            return
        
        with ui.card().classes('w-full q-mb-md'):
            ui.label('其他参数设置').classes('text-subtitle1 text-weight-medium q-mb-sm')
            
            # 使用响应式网格布局，确保所有控件都能完整显示
            with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-4 gap-4 w-full'):
                for addr, name in sorted(other_params):
                    if '保留' not in name:  # 跳过保留参数
                        self._create_param_input(name, addr, default_value='0')
    
    def _extract_stage_number(self, param_name: str) -> int:
        """从参数名称中提取段号，用于排序"""
        try:
            # 提取类似 "1段"、"2段" 的数字
            import re
            match = re.search(r'(\d+)段', param_name)
            if match:
                return int(match.group(1))
            return 999  # 没有段号的放最后
        except:
            return 999
    
    def _create_param_input(self, label: str, register_addr: str, default_value: str = '0'):
        """创建参数输入框
        
        Args:
            label: 参数标签文本
            register_addr: 寄存器地址
            default_value: 默认值
        """
        with ui.column().classes('q-pa-xs').style('min-width: 200px; max-width: 240px; height: 95px;'):
            # 标签 - 单行显示，自适应宽度
            ui.label(label).classes('text-caption text-grey-8').style(
                'font-size: 12px; font-weight: 500; white-space: normal; word-break: break-word; line-height: 1.3; width: 100%; max-height: 48px; overflow: hidden;'
            )
            
            # 输入框 - 使用响应式设计
            input_field = ui.input(value=default_value).props('outlined dense').classes('q-mt-xs').style(
                'width: 100%; max-width: 220px; min-width: 180px; font-size: 14px; height: 32px;'
            )
            
            # 初始化关闭标记
            input_field._vk_closing = False
            input_field._vk_last_show_time = 0
            
            # 点击输入框时弹出虚拟键盘（可选）
            # 使用多种事件确保在不同设备上都能正常触发
            input_field.on('click', lambda e, field=input_field: self._show_virtual_keyboard(field))
            input_field.on('focus', lambda e, field=input_field: self._show_virtual_keyboard(field))
            input_field.on('touchstart', lambda e, field=input_field: self._show_virtual_keyboard(field))
            input_field.on('mousedown', lambda e, field=input_field: self._show_virtual_keyboard(field))
            
            # 保存输入框引用
            self.param_inputs[register_addr] = input_field
    
    async def _on_read_params(self):
        """读取参数按钮点击事件"""
        try:
            logger.info("发送读取参数请求")
            
            if not self.websocket_client or not self.websocket_client.is_connected:
                ui.notify('WebSocket未连接', type='warning')
                return
            
            # 发送读取参数请求
            await self.websocket_client.send_message('param_read', {
                'read_type': 'control_params',
                'start_address': '0x2200',
                'count': len(self.param_mapping)
            })
            
            ui.notify('正在读取参数...', type='info')
            
        except Exception as e:
            logger.error(f"读取参数失败: {e}")
            ui.notify(f'读取参数失败: {str(e)}', type='negative')
    
    async def _on_write_params(self):
        """写入参数按钮点击事件"""
        try:
            # 收集所有输入框的值
            param_values = {}
            invalid_params = []
            
            for addr, input_field in self.param_inputs.items():
                try:
                    value = float(input_field.value)
                    # 验证数值范围（可根据实际需求调整）
                    if value < 0 or value > 65535:
                        invalid_params.append(f"{self.param_mapping.get(addr, addr)}: 超出范围(0-65535)")
                        continue
                    param_values[addr] = int(value)
                except ValueError:
                    invalid_params.append(f"{self.param_mapping.get(addr, addr)}: 非法数值")
            
            if invalid_params:
                ui.notify(f'以下参数无效:\n' + '\n'.join(invalid_params), type='warning')
                return
            
            if not self.websocket_client or not self.websocket_client.is_connected:
                ui.notify('WebSocket未连接', type='warning')
                return
            
            logger.info(f"发送写入参数请求: {len(param_values)} 个参数")
            
            # 发送写入参数请求
            await self.websocket_client.send_message('param_write', {
                'write_type': 'control_params',
                'params': param_values
            })
            
            ui.notify('正在写入参数...', type='info')
            
        except Exception as e:
            logger.error(f"写入参数失败: {e}")
            ui.notify(f'写入参数失败: {str(e)}', type='negative')
    
    def _show_virtual_keyboard(self, input_field):
        """显示虚拟数字键盘"""
        try:
            import time
            current_time = time.time()
            
            # 检查是否正在关闭过程中
            if hasattr(input_field, '_vk_closing') and input_field._vk_closing:
                logger.info("虚拟键盘正在关闭中，不重新显示")
                return
            
            # 检查是否太快重新触发（防止事件冒泡导致的重复触发）
            if hasattr(input_field, '_vk_last_show_time'):
                time_diff = current_time - input_field._vk_last_show_time
                if time_diff < 1.0:  # 1秒内不重复显示
                    logger.info(f"虚拟键盘触发太快({time_diff:.2f}s)，忽略")
                    return
            
            # 更新最后显示时间
            input_field._vk_last_show_time = current_time
            
            logger.info(f"虚拟键盘触发 - 输入框值: {input_field.value}")
            from ui_components import VirtualKeyboard
            keyboard = VirtualKeyboard(input_field, allow_negative=True)
            keyboard.show()
            logger.info("虚拟键盘显示成功")
        except Exception as e:
            logger.error(f"虚拟键盘加载失败: {e}")
            ui.notify(f'虚拟键盘加载失败: {str(e)}', type='negative')
    
    async def update_param_values(self, param_data: dict):
        """更新参数值显示
        
        Args:
            param_data: 从服务器读取的参数数据，格式如 {'0x2200': 300, '0x2201': 350, ...}
        """
        try:
            updated_count = 0
            for addr, value in param_data.items():
                # 处理地址格式
                addr_key = addr if addr.startswith('0x') else f'0x{addr}'
                
                if addr_key in self.param_inputs:
                    self.param_inputs[addr_key].value = str(value)
                    updated_count += 1
            
            logger.info(f"更新了 {updated_count} 个参数值")
            ui.notify(f'参数读取成功 ({updated_count} 个)', type='positive')
            
        except Exception as e:
            logger.error(f"更新参数值失败: {e}")
            ui.notify(f'更新参数值失败: {str(e)}', type='negative')