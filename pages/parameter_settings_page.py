"""
参数设置页面
Parameter Settings Page
"""
# flake8: noqa
import logging
import asyncio
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
        self.main_container = None  # 保存主容器引用，用于UI上下文

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
            logger.info(f"收到参数读取响应: {data}")
            
            # 处理不同的数据格式
            params_data = None
            
            if 'params' in data:
                params_data = data['params']
            elif 'data' in data:
                if 'params' in data['data']:
                    params_data = data['data']['params']
                else:
                    params_data = data['data']
            
            logger.info(f"提取到的参数数据类型: {type(params_data)}")
            if isinstance(params_data, list):
                logger.info(f"参数列表长度: {len(params_data)}")
                if len(params_data) > 0:
                    logger.info(f"第一个参数示例: {params_data[0]}")
            
            if params_data is not None:
                # 如果params_data是列表格式，需要转换为字典格式
                if isinstance(params_data, list):
                    # 将列表格式转换为地址到值的映射
                    param_dict = {}
                    for param in params_data:
                        if isinstance(param, dict) and 'reg_addr' in param and 'current_value' in param:
                            param_dict[param['reg_addr']] = param['current_value']
                        else:
                            logger.warning(f"参数格式不正确: {param}")
                    logger.info(f"转换后的参数字典长度: {len(param_dict)}")
                    logger.info(f"转换后的参数字典示例: {dict(list(param_dict.items())[:5])}")
                    # 使用调度方法确保在正确的UI上下文中更新
                    self.schedule_param_update(param_dict)
                elif isinstance(params_data, dict):
                    # 已经是字典格式，直接使用
                    logger.info(f"直接使用字典格式，长度: {len(params_data)}")
                    # 使用调度方法确保在正确的UI上下文中更新
                    self.schedule_param_update(params_data)
                else:
                    logger.warning(f"未知的参数数据格式: {type(params_data)}")
            else:
                logger.warning("未找到参数数据")
                
        except Exception as e:
            logger.error(f"处理参数读取响应失败: {e}")
            logger.exception("详细错误信息:")

    async def _handle_param_write_response(self, data):
        """处理参数写入响应"""
        try:
            # 确保在主UI上下文中处理响应
            if self.main_container is not None:
                with self.main_container:
                    if data.get('exec_status') == 'success':
                        # 检查是否是模拟模式
                        is_simulation = data.get('simulation_mode', False)
                        if is_simulation:
                            # 使用run_javascript来安全地显示通知
                            await ui.run_javascript('''
                                Quasar.Notify.create({
                                    message: '参数写入成功 (模拟模式: 设备不支持这些地址)',
                                    type: 'info',
                                    position: 'top',
                                    timeout: 5000
                                })
                            ''')
                        else:
                            # 使用run_javascript来安全地显示通知
                            await ui.run_javascript('''
                                Quasar.Notify.create({
                                    message: '参数写入成功',
                                    type: 'positive',
                                    position: 'top',
                                    timeout: 3000
                                })
                            ''')
                    else:
                        error_msg = data.get('exec_msg', '未知错误')
                        # 使用run_javascript来安全地显示错误通知
                        await ui.run_javascript(f'''
                            Quasar.Notify.create({{
                                message: '参数写入失败: {error_msg}',
                                type: 'negative',
                                position: 'top',
                                timeout: 5000
                            }})
                        ''')
            else:
                # 如果没有主容器，直接使用run_javascript
                if data.get('exec_status') == 'success':
                    # 检查是否是模拟模式
                    is_simulation = data.get('simulation_mode', False)
                    if is_simulation:
                        await ui.run_javascript('''
                            Quasar.Notify.create({
                                message: '参数写入成功 (模拟模式: 设备不支持这些地址)',
                                type: 'info',
                                position: 'top',
                                timeout: 5000
                            })
                        ''')
                    else:
                        await ui.run_javascript('''
                            Quasar.Notify.create({
                                message: '参数写入成功',
                                type: 'positive',
                                position: 'top',
                                timeout: 3000
                            })
                        ''')
                else:
                    error_msg = data.get('exec_msg', '未知错误')
                    await ui.run_javascript(f'''
                        Quasar.Notify.create({{
                            message: '参数写入失败: {error_msg}',
                            type: 'negative',
                            position: 'top',
                            timeout: 5000
                        }})
                    ''')
        except Exception as e:
            logger.error(f"处理参数写入响应失败: {e}")
        
    def create_page(self) -> ui.column:
        """创建参数设置页面"""
        # 从配置文件加载参数映射
        self._load_param_mapping()
        
        with ui.card().classes('w-full').style('height: calc(100vh - 120px); overflow-y: auto;') as main_card:
            self.main_container = main_card  # 保存主容器引用
            ui.label('控制参数设置').classes('text-h5')
            
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
            
            # 使用run_javascript来安全地显示通知
            await ui.run_javascript('''
                Quasar.Notify.create({
                    message: '正在读取参数...',
                    type: 'info',
                    position: 'top',
                    timeout: 2000
                })
            ''')
            
        except Exception as e:
            logger.error(f"读取参数失败: {e}")
            # 使用run_javascript来安全地显示错误通知
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '读取参数失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')
    
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
                # 使用run_javascript来安全地显示警告通知
                await ui.run_javascript(f'''
                    Quasar.Notify.create({{
                        message: '以下参数无效: {"; ".join(invalid_params)}',
                        type: 'warning',
                        position: 'top',
                        timeout: 5000,
                        multiLine: true
                    }})
                ''')
                return
            
            if not self.websocket_client or not self.websocket_client.is_connected:
                # 使用run_javascript来安全地显示警告通知
                await ui.run_javascript('''
                    Quasar.Notify.create({
                        message: 'WebSocket未连接',
                        type: 'warning',
                        position: 'top',
                        timeout: 3000
                    })
                ''')
                return
            
            logger.info(f"发送写入参数请求: {len(param_values)} 个参数")
            
            # 发送写入参数请求
            await self.websocket_client.send_message(
                'param_write', 
                {
                    'write_type': 'control_params',
                    'params': param_values
                })
            
            # 使用run_javascript来安全地显示通知
            await ui.run_javascript('''
                Quasar.Notify.create({
                    message: '正在写入参数...',
                    type: 'info',
                    position: 'top',
                    timeout: 2000
                })
            ''')
            
        except Exception as e:
            logger.error(f"写入参数失败: {e}")
            # 使用run_javascript来安全地显示错误通知
            await ui.run_javascript(f'''
                Quasar.Notify.create({{
                    message: '写入参数失败: {str(e)}',
                    type: 'negative',
                    position: 'top',
                    timeout: 5000
                }})
            ''')
    
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
            # 由于这不是异步函数，使用普通方式显示通知
            ui.notify(f'虚拟键盘加载失败: {str(e)}', type='negative')
    
    def update_param_values(self, param_data: dict):
        """更新参数值显示
        
        Args:
            param_data: 从服务器读取的参数数据，格式如 {'0x2200': 300, '0x2201': 350, ...}
        """
        try:
            updated_count = 0
            
            logger.info(f"开始更新参数值，收到 {len(param_data)} 个参数数据")
            logger.info(f"参数数据示例: {dict(list(param_data.items())[:5])}")
            logger.info(f"当前UI中的参数输入框数量: {len(self.param_inputs)}")
            
            # 直接在主线程中执行UI更新，避免异步上下文问题
            for addr, value in param_data.items():
                # 处理地址格式
                addr_key = addr if addr.startswith('0x') else f'0x{addr}'
                
                # 检查地址是否在UI中
                if addr_key in self.param_inputs:
                    input_field = self.param_inputs[addr_key]
                    input_field.value = str(value)
                    updated_count += 1
                    logger.debug(f"更新参数: {addr_key} = {value}")
                else:
                    logger.warning(f"地址 {addr_key} 在UI中未找到对应的输入框")
            
            logger.info(f"成功更新 {updated_count} 个参数值，{len(param_data) - updated_count} 个未找到对应UI")
            
        except Exception as e:
            logger.error(f"更新参数值失败: {e}")

    def schedule_param_update(self, param_data: dict):
        """调度参数更新，确保在正确的UI上下文中执行
        
        Args:
            param_data: 从服务器读取的参数数据
        """
        try:
            if self.main_container is not None:
                # 使用主容器上下文来确保UI更新在正确的位置执行
                with self.main_container:
                    ui.timer(0.1, lambda: self._safe_update_params(param_data), once=True)
            else:
                # 如果没有主容器，直接使用timer
                ui.timer(0.1, lambda: self._safe_update_params(param_data), once=True)
        except Exception as e:
            logger.error(f"调度参数更新失败: {e}")
    
    def _safe_update_params(self, param_data: dict):
        """安全地更新参数值（在正确的UI上下文中）"""
        try:
            updated_count = 0
            missing_addrs = []
            
            logger.info(f"开始安全更新参数，收到 {len(param_data)} 个参数")
            logger.info(f"UI中可用的参数地址数量: {len(self.param_inputs)}")
            logger.info(f"UI中前5个地址: {list(self.param_inputs.keys())[:5]}")
            
            # 添加地址格式调试信息
            if param_data:
                sample_addr = list(param_data.keys())[0]
                logger.info(f"收到的第一个地址格式: {sample_addr}")
                logger.info(f"UI中对应的地址格式: {sample_addr if sample_addr in self.param_inputs else '未找到'}")
            
            # 确保在主容器上下文中执行
            if self.main_container is not None:
                with self.main_container:
                    for addr, value in param_data.items():
                        # 处理地址格式 - 统一转换为小写进行比较
                        addr_key = addr.lower() if addr.startswith('0x') else f'0x{addr}'.lower()
                        
                        # 检查地址是否在UI中（也转换为小写进行比较）
                        ui_addrs_lower = {k.lower(): k for k in self.param_inputs.keys()}
                        if addr_key in ui_addrs_lower:
                            original_addr = ui_addrs_lower[addr_key]
                            input_field = self.param_inputs[original_addr]
                            input_field.value = str(value)
                            updated_count += 1
                            logger.debug(f"更新参数成功: {original_addr} = {value}")
                        else:
                            missing_addrs.append(addr_key)
                            logger.warning(f"地址 {addr_key} 在UI中未找到对应的输入框")
                    
                    # 显示通知 - 现在应该在正确的UI上下文中
                    ui.notify(f'参数读取成功 ({updated_count}/{len(param_data)} 个)', type='positive')
            else:
                # 如果没有主容器，直接更新
                for addr, value in param_data.items():
                    # 处理地址格式 - 统一转换为小写进行比较
                    addr_key = addr.lower() if addr.startswith('0x') else f'0x{addr}'.lower()
                    
                    # 检查地址是否在UI中（也转换为小写进行比较）
                    ui_addrs_lower = {k.lower(): k for k in self.param_inputs.keys()}
                    if addr_key in ui_addrs_lower:
                        original_addr = ui_addrs_lower[addr_key]
                        input_field = self.param_inputs[original_addr]
                        input_field.value = str(value)
                        updated_count += 1
                        logger.debug(f"更新参数成功: {original_addr} = {value}")
                    else:
                        missing_addrs.append(addr_key)
                        logger.warning(f"地址 {addr_key} 在UI中未找到对应的输入框")
                
                # 显示通知
                ui.notify(f'参数读取成功 ({updated_count}/{len(param_data)} 个)', type='positive')
            
            logger.info(f"安全更新完成: {updated_count} 个参数值, 缺失 {len(missing_addrs)} 个地址")
            if missing_addrs:
                logger.info(f"缺失的地址示例: {missing_addrs[:10]}")
            
        except Exception as e:
            logger.error(f"安全更新参数值失败: {e}")
            ui.notify(f'更新参数值失败: {str(e)}', type='negative')