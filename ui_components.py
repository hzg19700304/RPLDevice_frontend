"""
UI组件模块
UI Components Module
"""
# flake8: noqa
import logging
from datetime import datetime
from nicegui import ui
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class UIComponents:
    """UI组件管理器"""
    
    def __init__(self, config_manager, page_manager=None):
        self.config = config_manager
        self.page_manager = page_manager
        self.connection_status = False
        self.device_info = self.config.get_device_info()
        
        # UI元素引用
        self.header_time_label = None
        self.header_status_icon = None
        self.footer_status_labels = {}
        self.footer_status_icons = {}
        
    def create_header(self) -> None:
        """创建顶部栏"""
        with ui.header().classes('q-pa-md').style('background-color: #2C3E50; color: white;'):
            with ui.row().classes('w-full items-center'):
                # 设备名称
                ui.label(self.device_info.get('设备名称', '钢轨电位限制柜')).classes('text-h5')
                
                ui.space()
                
                # 系统时间
                self.header_time_label = ui.label().classes('text-body1')
                self._update_time()
                # 创建定时器，每秒更新一次时间
                ui.timer(1.0, self._update_time)
                
                ui.space()
                
                # 连接状态指示器
                with ui.row().classes('items-center'):
                    self.header_status_icon = ui.icon('wifi_off', color='red').classes('text-h5')
                    ui.label('未连接').classes('text-body1 q-ml-xs')
                
                # 设置菜单
                with ui.button(icon='settings').classes('touch-friendly'):
                    with ui.menu():
                        ui.menu_item('系统设置', lambda: self._show_system_settings())
                        ui.menu_item('用户管理', lambda: self._show_user_management())
                        ui.separator()
                        ui.menu_item('关于系统', lambda: self._show_about())
    
    def create_left_drawer(self) -> None:
        """创建左侧导航栏"""
        enabled_pages = self.config.get_enabled_pages()
        
        with ui.left_drawer().classes('bg-blue-grey-9').style('width: 120px;'):
            with ui.column().classes('w-full'):
                ui.label('功能菜单').classes('text-h6 text-white q-pa-md')
                ui.separator()
                
                # 根据配置动态生成菜单项
                menu_items = [
                    ('show_main_diagram', '主接线图', 'electrical_services'),
                    ('show_system_status', '系统状态', 'info'),
                    ('show_event_record', '事件记录', 'event_note'),
                    ('show_real_time_curve', '实时曲线', 'show_chart'),
                    ('show_history_curve', '历史曲线', 'timeline'),
                    ('show_parameter_settings', '参数设置', 'settings'),
                    ('show_api_status', 'API状态', 'cloud'),
                    ('show_fault_record', '故障录波', 'bug_report'),
                    ('show_range_settings', '量程设置', 'tune'),
                    ('show_channel_calibration', '通道校正', 'build')
                ]
                
                for page_key, page_name, icon in menu_items:
                    if page_key in enabled_pages:
                        self._create_menu_item(page_name, icon, page_key)
    
    def _create_menu_item(self, name: str, icon: str, page_key: str) -> None:
        """创建菜单项"""
        # 获取字体配置
        font_config = self.config.get_font_config()
        # logger.info(f"菜单项 {name} 的字体配置: {font_config}")  # 注释掉调试信息
        
        enable_responsive = font_config.get('enable_responsive_font', True)
        scale_factor = font_config.get('font_scale_factor', 1.0)
        menu_size = int(font_config.get('menu_font_size', 18) * scale_factor)
        
        # logger.info(f"菜单项 {name} 计算的字体大小: {menu_size}")  # 注释掉调试信息
        
        # 根据配置生成字体样式
        if enable_responsive:
            icon_font = f"max({menu_size+2}px, min(4vw, {menu_size+14}px))"
            text_font = f"max({menu_size-2}px, min(3vw, {menu_size+6}px))"
        else:
            icon_font = f"{menu_size+8}px"
            text_font = f"{menu_size}px"
        
        # logger.info(f"菜单项 {name} 生成的字体样式 - 图标: {icon_font}, 文本: {text_font}")  # 注释掉调试信息
        
        with ui.item(on_click=lambda: self._handle_menu_click(page_key)).classes('text-white touch-friendly').style('min-height: 48px; padding: 8px; width: 100%; box-sizing: border-box;'):
            with ui.row().classes('items-center justify-center w-full').style('gap: 16px;'):
                ui.icon(icon).style(f'font-size: {icon_font}; color: white;')
                ui.label(name).classes('menu-text').style(f'font-size: {text_font}; font-weight: 500; color: white;')
    
    def _handle_menu_click(self, page_key: str) -> None:
        """处理菜单点击事件"""
        if self.page_manager:
            self.page_manager.switch_page(page_key)
        else:
            # 如果没有页面管理器，显示提示
            ui.notify(f'点击了菜单: {page_key}', type='info')
    
    def create_footer(self) -> None:
        """创建底部状态栏"""
        with ui.footer().classes('bg-grey-2 text-grey-8 q-pa-sm').style('height: auto; min-height: 48px;'):  # 改为 auto
            with ui.row().classes('w-full items-center text-caption').style('min-height: 36px; overflow-x: auto; flex-wrap: nowrap;'):  # 添加 flex-wrap: nowrap 和 overflow-x: auto
                # 控制板连接状态
                with ui.row().classes('items-center flex-no-wrap').style('white-space: nowrap; flex-shrink: 0;'):  # 添加 flex-shrink: 0
                    ui.icon('memory', color='grey').classes('q-mr-xs')
                    self.footer_status_labels['control_board'] = ui.label('控制板串口: 未连接').style('font-size: 12px;')
                
                ui.separator().props('vertical').classes('q-mx-sm')
                
                # PSCADA连接状态
                with ui.row().classes('items-center flex-no-wrap').style('white-space: nowrap; flex-shrink: 0;'):
                    ui.icon('router', color='grey').classes('q-mr-xs')
                    self.footer_status_labels['pscada'] = ui.label('PSCADA串口: 未连接').style('font-size: 12px;')
                
                ui.separator().props('vertical').classes('q-mx-sm')
                
                # 服务器连接状态
                with ui.row().classes('items-center flex-no-wrap').style('white-space: nowrap; flex-shrink: 0;'):
                    ui.icon('settings_ethernet', color='grey').classes('q-mr-xs')
                    self.footer_status_labels['server'] = ui.label('服务器: 未连接').style('font-size: 12px;')

                ui.separator().props('vertical').classes('q-mx-sm')

                # WebSocket连接状态
                with ui.row().classes('items-center flex-no-wrap').style('white-space: nowrap; flex-shrink: 0;'):
                    self.footer_status_icons['websocket'] = ui.icon('link_off', color='grey').classes('q-mr-xs')
                    self.footer_status_labels['websocket'] = ui.label('WebSocket: 未连接').style('color: red; font-size: 12px;')
            
                ui.space()
                
                # 系统版本
                version = self.device_info.get('系统版本', '1.0.0')
                ui.label(f'版本: {version}').style('font-size: 12px; white-space: nowrap; flex-shrink: 0;')
    
    def update_connection_status(self, connected: bool, connection_type: str = 'websocket') -> None:
        """更新连接状态
        
        Args:
            connected: 连接状态（True=已连接, False=未连接）
            connection_type: 连接类型 ('control_board', 'pscada', 'server', 'websocket')
        """
        # 获取显示名称
        display_name = self._get_connection_name(connection_type)
        
        self.connection_status = connected
        
        # 更新顶部状态图标（通常用于 WebSocket）
        if connection_type == 'websocket' and self.header_status_icon:
            if connected:
                self.header_status_icon.props('name=wifi color=green')
            else:
                self.header_status_icon.props('name=wifi_off color=red')
        
        # 更新底部状态栏文本
        if connection_type in self.footer_status_labels:
            label = self.footer_status_labels[connection_type]
            if connected:
                label.text = f'{display_name}: 已连接'
                label.style('color: green; font-size: 12px;')
            else:
                label.text = f'{display_name}: 未连接'
                label.style('color: red; font-size: 12px;')
        
        # 更新底部状态栏图标
        if connection_type in self.footer_status_icons:
            icon = self.footer_status_icons[connection_type]
            if connected:
                # 根据不同的连接类型使用不同的图标
                icon_name = self._get_connected_icon(connection_type)
                icon.props(f'name={icon_name} color=green')
            else:
                icon_name = self._get_disconnected_icon(connection_type)
                icon.props(f'name={icon_name} color=grey')

    def _get_connection_name(self, connection_type: str) -> str:
        """获取连接类型的显示名称"""
        name_map = {
            'control_board': '控制板串口',
            'pscada': 'PSCADA串口',
            'server': '服务器',
            'websocket': 'WebSocket'
        }
        return name_map.get(connection_type, connection_type)

    def _get_connected_icon(self, connection_type: str) -> str:
        """获取已连接状态的图标"""
        icon_map = {
            'control_board': 'memory',
            'pscada': 'router',
            'server': 'cloud',
            'websocket': 'link'
        }
        return icon_map.get(connection_type, 'check_circle')

    def _get_disconnected_icon(self, connection_type: str) -> str:
        """获取未连接状态的图标"""
        icon_map = {
            'control_board': 'memory',
            'pscada': 'router',
            'server': 'cloud_off',
            'websocket': 'link_off'
        }
        return icon_map.get(connection_type, 'cancel')


    
    def _update_time(self) -> None:
        """更新时间显示"""
        if self.header_time_label:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.header_time_label.text = current_time
    
    def _show_system_settings(self) -> None:
        """显示系统设置对话框"""
        with ui.dialog() as dialog, ui.card():
            ui.label('系统设置').classes('text-h6')
            ui.separator()
            
            with ui.column().classes('q-pa-md'):
                ui.label('功能开发中...')
                
                with ui.row().classes('q-mt-md'):
                    ui.button('关闭', on_click=dialog.close).classes('touch-friendly')
        
        dialog.open()
    
    def _show_user_management(self) -> None:
        """显示用户管理对话框"""
        with ui.dialog() as dialog, ui.card():
            ui.label('用户管理').classes('text-h6')
            ui.separator()
            
            with ui.column().classes('q-pa-md'):
                ui.label('功能开发中...')
                
                with ui.row().classes('q-mt-md'):
                    ui.button('关闭', on_click=dialog.close).classes('touch-friendly')
        
        dialog.open()
    
    def _show_about(self) -> None:
        """显示关于系统对话框"""
        device_info = self.config.get_device_info()
        
        with ui.dialog() as dialog, ui.card():
            ui.label('关于系统').classes('text-h6')
            ui.separator()
            
            with ui.column().classes('q-pa-md'):
                ui.label(f"设备名称: {device_info.get('设备名称', 'N/A')}")
                ui.label(f"设备ID: {device_info.get('设备ID', 'N/A')}")
                ui.label(f"系统版本: {device_info.get('系统版本', 'N/A')}")
                ui.label(f"设备IP: {device_info.get('设备IP', 'N/A')}")
                
                with ui.row().classes('q-mt-md'):
                    ui.button('关闭', on_click=dialog.close).classes('touch-friendly')
        
        dialog.open()

class VirtualKeyboard:
    """虚拟数字键盘组件"""
    
    def __init__(self, target_input, allow_negative: bool = True):
        self.target_input = target_input
        self.allow_negative = allow_negative
        self.current_value = ""
        
    def show(self) -> None:
        """显示虚拟键盘"""
        with ui.dialog() as dialog, ui.card().classes('q-pa-md'):
            ui.label('数字键盘').classes('text-h6')
            ui.separator()
            
            # 显示当前输入值
            self.display = ui.input(value=self.current_value, readonly=True).classes('text-center text-h5')
            
            # 数字键盘布局
            with ui.grid(columns=3).classes('q-mt-md'):
                for i in range(1, 10):
                    ui.button(str(i), on_click=lambda x=i: self._input_digit(str(x))).classes('touch-friendly')
                
                # 第四行
                if self.allow_negative:
                    ui.button('+/-', on_click=self._toggle_sign).classes('touch-friendly')
                else:
                    ui.button('').props('disable')  # 占位
                
                ui.button('0', on_click=lambda: self._input_digit('0')).classes('touch-friendly')
                ui.button('.', on_click=lambda: self._input_digit('.')).classes('touch-friendly')
            
            # 控制按钮
            with ui.row().classes('q-mt-md'):
                ui.button('清除', on_click=self._clear).classes('touch-friendly')
                ui.button('退格', on_click=self._backspace).classes('touch-friendly')
                ui.button('取消', on_click=dialog.close).classes('touch-friendly')
                ui.button('确定', on_click=lambda: self._confirm(dialog)).classes('touch-friendly')
        
        dialog.open()
    
    def _input_digit(self, digit: str) -> None:
        """输入数字"""
        if digit == '.' and '.' in self.current_value:
            return  # 避免重复小数点
        
        self.current_value += digit
        self.display.value = self.current_value
    
    def _toggle_sign(self) -> None:
        """切换正负号"""
        if self.current_value.startswith('-'):
            self.current_value = self.current_value[1:]
        else:
            self.current_value = '-' + self.current_value
        self.display.value = self.current_value
    
    def _clear(self) -> None:
        """清除输入"""
        self.current_value = ""
        self.display.value = self.current_value
    
    def _backspace(self) -> None:
        """退格"""
        self.current_value = self.current_value[:-1]
        self.display.value = self.current_value
    
    def _confirm(self, dialog) -> None:
        """确认输入"""
        if self.target_input:
            self.target_input.value = self.current_value
        dialog.close()

class ConfirmDialog:
    """确认对话框组件"""
    
    @staticmethod
    def show(title: str, message: str, on_confirm=None, on_cancel=None) -> None:
        """显示确认对话框"""
        with ui.dialog() as dialog, ui.card():
            ui.label(title).classes('text-h6')
            ui.separator()
            
            with ui.column().classes('q-pa-md'):
                ui.label(message)
                
                with ui.row().classes('q-mt-md'):
                    ui.button('取消', on_click=lambda: (on_cancel() if on_cancel else None, dialog.close())[1]).classes('touch-friendly')
                    ui.button('确定', on_click=lambda: (on_confirm() if on_confirm else None, dialog.close())[1]).classes('touch-friendly')
        
        dialog.open()

class LoadingIndicator:
    """加载指示器组件"""
    
    def __init__(self, message: str = "加载中..."):
        self.message = message
        self.dialog = None
        
    def show(self) -> None:
        """显示加载指示器"""
        with ui.dialog() as self.dialog, ui.card():
            with ui.column().classes('items-center q-pa-lg'):
                ui.spinner(size='lg')
                ui.label(self.message).classes('q-mt-md')
        
        self.dialog.open()
    
    def hide(self) -> None:
        """隐藏加载指示器"""
        if self.dialog:
            self.dialog.close()