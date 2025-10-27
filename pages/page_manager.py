"""
页面管理器
Page Manager
"""
# flake8: noqa
import logging
from datetime import datetime
from nicegui import ui
from .main_diagram_page import MainDiagramPage
from .system_status_page import SystemStatusPage
from .event_record_page import EventRecordPage
from .parameter_settings_page import ParameterSettingsPage
from .real_time_curve_page import RealTimeCurvePage
from .history_curve_page import HistoryCurvePage
from .fault_record_page import FaultRecordPage

logger = logging.getLogger(__name__)


class PageManager:
    """页面管理器"""

    def __init__(self, config_manager, websocket_client):
        self.config = config_manager
        self.websocket_client = websocket_client
        self.current_page = None
        self.pages = {}
        self.main_content_area = None
        
        # 初始化各个页面实例
        self.main_diagram_page = MainDiagramPage(config_manager, websocket_client)
        self.system_status_page = SystemStatusPage(config_manager, websocket_client)
        self.event_record_page = EventRecordPage(config_manager, websocket_client)
        self.parameter_settings_page = ParameterSettingsPage(config_manager, websocket_client)
        self.real_time_curve_page = RealTimeCurvePage(config_manager, websocket_client)
        self.history_curve_page = HistoryCurvePage(config_manager, websocket_client)
        self.fault_record_page = FaultRecordPage(config_manager, websocket_client)
        
    def setup_pages(self) -> None:
        """设置页面"""
        enabled_pages = self.config.get_enabled_pages()

        # 创建页面容器
        self.main_content_area = ui.column().classes('w-full h-full')

        with self.main_content_area:
            # 默认显示主接线图页面
            if 'show_main_diagram' in enabled_pages:
                self.current_page = 'show_main_diagram'
                self.main_diagram_page.create_page()
            else:
                # 如果主接线图未启用，显示第一个可用页面
                first_page = next(iter(enabled_pages.keys()), None)
                if first_page:
                    self.current_page = first_page
                    self._create_placeholder_page(enabled_pages[first_page])
                else:
                    self.current_page = 'default'
                    self._create_placeholder_page("系统")

    def _create_placeholder_page(self, page_name: str) -> None:
        """创建占位页面"""
        with ui.card().classes('w-full h-full'):
            ui.label(page_name).classes('text-h5 q-mb-md')

            with ui.column().classes('w-full items-center q-mt-xl'):
                ui.icon('construction', size='xl', color='grey-5')
                ui.label('功能开发中...').classes('text-h6 text-grey-6 q-mt-md')
                ui.label('该页面将在后续任务中实现').classes('text-body2 text-grey-5')

    def switch_page(self, page_key: str) -> None:
        """切换页面"""
        if page_key == self.current_page:
            return  # 已经是当前页面，无需切换

        logger.info(f"切换到页面: {page_key}")

        # 清空当前内容
        if self.main_content_area:
            self.main_content_area.clear()

        # 根据页面键创建对应页面
        enabled_pages = self.config.get_enabled_pages()

        with self.main_content_area:
            if page_key == 'show_main_diagram':
                self.main_diagram_page.create_page()
            elif page_key == 'show_system_status':
                self.system_status_page.create_page()
            elif page_key == 'show_event_record':
                self.event_record_page.create_page()
            elif page_key == 'show_parameter_settings':
                self.parameter_settings_page.create_page()
            elif page_key == 'show_real_time_curve':
                self.real_time_curve_page.create_page()
            elif page_key == 'show_history_curve':
                self.history_curve_page.create_page()
            elif page_key == 'show_fault_record':
                self.fault_record_page.create_page()
            elif page_key == 'show_api_status':
                self._create_placeholder_page("API状态")
            elif page_key == 'show_range_settings':
                self._create_placeholder_page("量程设置")
            elif page_key == 'show_channel_calibration':
                self._create_placeholder_page("通道校正")
            else:
                self._create_placeholder_page("未知页面")

        self.current_page = page_key
        page_name = enabled_pages.get(page_key, page_key)
        ui.notify(f'已切换到: {page_name}', type='positive')
    
    def cleanup(self):
        """清理页面资源"""
        if hasattr(self, 'real_time_curve_page'):
            self.real_time_curve_page.cleanup()
        if hasattr(self, 'history_curve_page'):
            self.history_curve_page.cleanup()
        logger.info("页面管理器已清理")