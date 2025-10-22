"""
页面模块
Pages Module
"""

from .page_manager import PageManager
from .main_diagram_page import MainDiagramPage
from .system_status_page import SystemStatusPage
from .event_record_page import EventRecordPage
from .parameter_settings_page import ParameterSettingsPage
from .real_time_curve_page import RealTimeCurvePage

__all__ = [
    'PageManager',
    'MainDiagramPage', 
    'SystemStatusPage',
    'EventRecordPage',
    'ParameterSettingsPage',
    'RealTimeCurvePage'
]