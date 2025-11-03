"""
配置管理模块
Configuration Manager Module
"""
# flake8: noqa
import configparser
import logging
import socket
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    def __init__(self, config_file: str = "config.ini"):
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        self._config_data = {}
        
    def load_config_sync(self) -> None:
        """同步加载配置文件"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            # 保持键的原始大小写
            self.config.optionxform = str
            
            # 读取配置文件，指定编码为utf-8
            self.config.read(self.config_file, encoding='utf-8')
            
            # 将配置转换为字典格式便于使用
            self._parse_config()
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            raise
        
    async def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            
            # 保持键的原始大小写
            self.config.optionxform = str
            
            # 读取配置文件，指定编码为utf-8
            self.config.read(self.config_file, encoding='utf-8')
            
            # 将配置转换为字典格式便于使用
            self._parse_config()
            
            logger.info(f"配置文件加载成功: {self.config_file}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            raise
    
    def _parse_config(self) -> None:
        """解析配置文件"""
        for section_name in self.config.sections():
            self._config_data[section_name] = {}
            for key, value in self.config.items(section_name):
                # 尝试转换数据类型
                self._config_data[section_name][key] = self._convert_value(value)
    
    def _convert_value(self, value: str) -> Any:
        """转换配置值的数据类型"""
        # 去除首尾空格和注释
        value = value.strip()
        
        # 处理行内注释（分号或井号）
        if ';' in value:
            value = value.split(';')[0].strip()
        if '#' in value:
            value = value.split('#')[0].strip()
        
        # 布尔值转换
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数字转换
        try:
            # 尝试转换为整数
            if '.' not in value:
                return int(value)
            # 尝试转换为浮点数
            return float(value)
        except ValueError:
            pass
        
        # 返回字符串
        return value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """获取配置值"""
        try:
            return self._config_data.get(section, {}).get(key, default)
        except Exception:
            return default
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取整个配置段"""
        return self._config_data.get(section, {})
    
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        return self.get_section("设备配置")
    
    def get_websocket_config(self) -> Dict[str, Any]:
        """获取WebSocket配置"""
        return self.get_section("Web Socket配置")
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self.get_section("服务器配置")
    
    def get_ui_labels_config(self) -> Dict[str, Any]:
        """获取界面标签配置"""
        return self.get_section("界面标签配置")
    
    def get_image_display_config(self) -> Dict[str, Any]:
        """获取图片显示配置"""
        return self.get_section("图片显示配置")
    
    def get_system_status_bits(self) -> Dict[str, str]:
        """获取系统状态位配置"""
        return self.get_section("HMI系统状态点表")
    
    def get_input_bits(self) -> Dict[str, str]:
        """获取开关量输入位配置"""
        return self.get_section("HMI开关量输入点表")
    
    def get_output_bits(self) -> Dict[str, str]:
        """获取开关量输出位配置"""
        return self.get_section("HMI开关量输出点表")
    
    def get_fault_bits(self) -> Dict[str, str]:
        """获取故障位配置"""
        return self.get_section("HMI故障点表")
    
    def get_fault_code_mapping(self) -> Dict[str, str]:
        """获取故障码映射配置"""
        return self.get_section("HMI故障点表")
    
    def get_alarm_bits(self) -> Dict[str, str]:
        """获取报警位配置"""
        return self.get_section("HMI报警点表")
    
    def get_system_status_bits(self) -> Dict[str, str]:
        """获取系统状态位配置"""
        return self.get_section("HMI系统状态点表")
    
    def get_input_bits(self) -> Dict[str, str]:
        """获取开关量输入位配置"""
        return self.get_section("HMI开关量输入点表")
    
    def get_output_bits(self) -> Dict[str, str]:
        """获取开关量输出位配置"""
        return self.get_section("HMI开关量输出点表")
    
    def get_igbt_bits(self) -> Dict[str, str]:
        """获取IGBT光纤状态位配置"""
        return self.get_section("HMI IGBT光纤状态点表")
    
    def get_control_parameters_mapping(self) -> Dict[str, str]:
        """获取控制参数地址映射"""
        return self.get_section("HMI系统控制参数地址映射")
    
    def get_fault_record_config(self) -> Dict[str, Any]:
        """获取故障录波配置"""
        return self.get_section("HMI故障录波读取配置")
    
    def is_page_enabled(self, page_key: str) -> bool:
        """检查页面是否启用"""
        ui_config = self.get_ui_labels_config()
        return ui_config.get(page_key, True)  # 默认启用
    
    def get_enabled_pages(self) -> Dict[str, bool]:
        """获取所有启用的页面"""
        ui_config = self.get_ui_labels_config()
        pages = {
            'show_main_diagram': '主接线图',
            'show_system_status': '系统状态',
            'show_event_record': '事件记录',
            'show_real_time_curve': '实时曲线',
            'show_history_curve': '历史曲线',
            'show_parameter_settings': '参数设置',
            'show_api_status': 'API状态',
            'show_fault_record': '故障录波',
            'show_range_settings': '量程设置',
            'show_channel_calibration': '通道校正',
            'show_user_management': '用户管理'
        }
        
        enabled_pages = {}
        for key, name in pages.items():
            if ui_config.get(key, True):  # 默认启用
                enabled_pages[key] = name
        
        return enabled_pages
    
    def get_font_config(self) -> Dict[str, Any]:
        """获取字体配置"""
        return self.get_section("字体配置")
    
    def get_layout_config(self) -> Dict[str, Any]:
        """获取界面布局配置"""
        return self.get_section("界面布局配置")
    
    def get_analog_channel_config(self) -> Dict[str, Any]:
        """获取模拟量通道配置"""
        return self.get_section("HMI模拟量通道配置")
    
    def reload_config(self) -> None:
        """重新加载配置文件"""
        self._config_data.clear()
        self.load_config()
        logger.info("配置文件已重新加载")
    
    def get_local_ip(self) -> str:
        """获取本机IP地址"""
        try:
            # 创建一个UDP套接字连接到公共DNS服务器
            # 这不会发送实际数据，只是获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 连接到Google的DNS服务器（不实际发送数据）
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logger.warning(f"获取本机IP地址失败: {e}")
            # 如果获取失败，返回回环地址
            return "127.0.0.1"
    
    def get_device_ip(self) -> str:
        """获取设备IP地址，优先使用配置文件中的值，如果配置文件中的值为空或不存在，则自动获取本机IP"""
        config_ip = self.get("设备配置", "设备IP", "")
        if config_ip and config_ip.strip():
            return config_ip
        
        # 如果配置文件中没有设置IP，则自动获取本机IP
        local_ip = self.get_local_ip()
        logger.info(f"自动获取本机IP地址: {local_ip}")
        return local_ip