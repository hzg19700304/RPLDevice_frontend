"""
参数设置页面
Parameter Settings Page
"""
# flake8: noqa
import logging
from nicegui import ui

logger = logging.getLogger(__name__)


class ParameterSettingsPage:
    """参数设置页面类"""
    
    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.param_inputs = {}  # 存储所有参数输入框的引用
        
    def create_page(self) -> ui.column:
        """创建参数设置页面"""
        with ui.card().classes('w-full').style('height: calc(100vh - 100px); overflow-y: auto;'):
            ui.label('控制参数设置').classes('text-h5 q-mb-md')
            
            # 顶部操作按钮
            with ui.row().classes('w-full q-mb-md justify-end'):
                ui.button('读取', color='primary', on_click=self._on_read_params).style('min-width: 100px;')
                ui.button('写入', color='positive', on_click=self._on_write_params).style('min-width: 100px;')
            
            # 分组标题：三段保护电流设置
            with ui.card().classes('w-full q-mb-md'):
                ui.label('三段保护电流设置 (×0.1A)').classes('text-subtitle1 text-weight-medium q-mb-sm')
                
                # 参数网格 - 4列布局
                with ui.grid(columns=4).classes('w-full gap-2'):
                    # 第一行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2200', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2201', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2202', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2203', default_value='450')
                    
                    # 第二行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2204', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2205', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2206', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2207', default_value='450')
                    
                    # 第三行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2208', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2209', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x220A', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x220B', default_value='450')
                    
                    # 第四行
                    self._create_param_input('轨电位控制给定值 (V)', '0x220C', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x220D', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x220E', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x220F', default_value='450')
            
            # 第二组：三段保护电流设置
            with ui.card().classes('w-full q-mb-md'):
                ui.label('三段保护电流设置 (×0.1A)').classes('text-subtitle1 text-weight-medium q-mb-sm')
                
                with ui.grid(columns=4).classes('w-full gap-2'):
                    # 第一行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2210', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2211', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2212', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2213', default_value='450')
                    
                    # 第二行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2214', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2215', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2216', default_value='400')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2217', default_value='450')
                    
                    # 第三行
                    self._create_param_input('轨电位控制给定值 (V)', '0x2218', default_value='300')
                    self._create_param_input('轨电位控制给定值 (V)', '0x2219', default_value='350')
                    self._create_param_input('轨电位控制给定值 (V)', '0x221A', default_value='400')
                    ui.column()  # 占位，保持4列对齐
        
        return ui.column()
    
    def _create_param_input(self, label: str, register_addr: str, default_value: str = '0'):
        """创建参数输入框
        
        Args:
            label: 参数标签文本
            register_addr: 寄存器地址
            default_value: 默认值
        """
        with ui.column().classes('q-pa-xs'):
            # 标签
            ui.label(label).classes('text-caption text-grey-7').style('font-size: 11px; white-space: nowrap;')
            
            # 输入框
            input_field = ui.input(value=default_value).props('outlined dense').classes('q-mt-xs').style(
                'max-width: 180px; font-size: 13px;'
            )
            
            # 点击输入框时弹出虚拟键盘（可选）
            # input_field.on('click', lambda: self._show_virtual_keyboard(input_field))
            
            # 保存输入框引用
            self.param_inputs[register_addr] = input_field
    
    def _on_read_params(self):
        """读取参数按钮点击事件"""
        try:
            # 这里应该通过 WebSocket 发送读取参数的请求
            logger.info("发送读取参数请求")
            
            # TODO: 实现实际的参数读取逻辑
            # await self.websocket_client.send_message('param_read', {
            #     'read_type': 'control_params'
            # })
            
            ui.notify('正在读取参数...', type='info')
            
        except Exception as e:
            logger.error(f"读取参数失败: {e}")
            ui.notify(f'读取参数失败: {str(e)}', type='negative')
    
    def _on_write_params(self):
        """写入参数按钮点击事件"""
        try:
            # 收集所有输入框的值
            param_values = {}
            for addr, input_field in self.param_inputs.items():
                try:
                    value = float(input_field.value)
                    param_values[addr] = value
                except ValueError:
                    ui.notify(f'参数 {addr} 的值无效', type='warning')
                    return
            
            logger.info(f"发送写入参数请求: {param_values}")
            
            # TODO: 实现实际的参数写入逻辑
            # await self.websocket_client.send_message('param_write', {
            #     'params': param_values
            # })
            
            ui.notify('正在写入参数...', type='info')
            
        except Exception as e:
            logger.error(f"写入参数失败: {e}")
            ui.notify(f'写入参数失败: {str(e)}', type='negative')
    
    def _show_virtual_keyboard(self, input_field):
        """显示虚拟数字键盘（可选功能）"""
        # 可以使用 ui_components.py 中的 VirtualKeyboard 组件
        pass
    
    def update_param_values(self, param_data: dict):
        """更新参数值显示
        
        Args:
            param_data: 从服务器读取的参数数据，格式如 {'0x2200': 300, '0x2201': 350, ...}
        """
        for addr, value in param_data.items():
            if addr in self.param_inputs:
                self.param_inputs[addr].value = str(value)
        
        ui.notify('参数读取成功', type='positive')