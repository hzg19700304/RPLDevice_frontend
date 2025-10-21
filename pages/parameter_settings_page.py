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
        
    def create_page(self) -> ui.column:
        """创建参数设置页面"""
        with ui.card().classes('w-full h-full'):
            ui.label('参数设置').classes('text-h5 q-mb-md')
            
            # 保护参数设置
            with ui.card().classes('w-full q-mb-md'):
                ui.label('保护参数').classes('text-h6 q-mb-sm')
                with ui.grid(columns=2).classes('w-full q-gutter-md'):
                    ui.number('电压上限 (V)', value=250, min=0, max=500, step=1)
                    ui.number('电压下限 (V)', value=180, min=0, max=500, step=1)
                    ui.number('电流上限 (A)', value=10, min=0, max=50, step=0.1)
                    ui.number('电流下限 (A)', value=0, min=0, max=50, step=0.1)
            
            # 通信参数设置
            with ui.card().classes('w-full q-mb-md'):
                ui.label('通信参数').classes('text-h6 q-mb-sm')
                with ui.grid(columns=2).classes('w-full q-gutter-md'):
                    ui.input('IP地址', value='192.168.1.100')
                    ui.number('端口号', value=8080, min=1, max=65535)
                    ui.number('超时时间 (s)', value=5, min=1, max=60)
                    ui.select(['9600', '19200', '38400', '115200'], 
                             label='波特率', value='115200')
            
            # 系统参数设置
            with ui.card().classes('w-full q-mb-md'):
                ui.label('系统参数').classes('text-h6 q-mb-sm')
                with ui.grid(columns=2).classes('w-full q-gutter-md'):
                    ui.number('数据采集周期 (ms)', value=100, min=10, max=10000)
                    ui.number('数据存储周期 (s)', value=60, min=1, max=3600)
                    ui.checkbox('启用自动备份', value=True)
                    ui.checkbox('启用远程监控', value=True)
            
            # 操作按钮
            with ui.row().classes('w-full justify-end q-mt-md'):
                ui.button('恢复默认', color='grey')
                ui.button('保存设置', color='primary')
        
        return ui.column()  # 返回一个空的column作为占位符