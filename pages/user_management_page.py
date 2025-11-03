#!/usr/bin/env python3
"""
用户管理页面
User Management Page
"""

from nicegui import ui
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class UserManagementPage:
    """用户管理页面类"""
    
    def __init__(self, config_manager, page_manager):
        """
        初始化用户管理页面
        
        Args:
            config_manager: 配置管理器
            page_manager: 页面管理器
        """
        self.config_manager = config_manager
        self.page_manager = page_manager
        self.current_user = page_manager.current_user if hasattr(page_manager, 'current_user') else None
        self.logout_callback: Optional[Callable] = None
        
    def set_logout_callback(self, callback: Callable) -> None:
        """设置登出回调函数"""
        self.logout_callback = callback
        
    def show(self) -> None:
        """显示用户管理页面"""
        # 主容器 - 使用白色背景
        with ui.column().classes('w-full h-full').style('background: #f5f7fa; min-height: 100vh;'):
            # 顶部装饰条
            ui.element('div').style('height: 4px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);')
            
            # 内容区域
            with ui.column().classes('w-full items-center').style('padding: 18px 20px;'):
                # 页面标题区域
                with ui.column().classes('items-center').style('margin-bottom: 24px;'):
                    ui.icon('manage_accounts', size='2.5rem').style('color: #667eea;')
                    ui.label('用户管理').classes('text-h5 text-weight-bold q-mt-sm').style('color: #2c3e50; margin-top: 8px;')
                    ui.label('管理您的账户信息和安全设置').classes('text-body2 text-grey-6').style('margin-top: 4px;')  
                
                # 主要内容区域 - 最大宽度容器
                with ui.column().classes('gap-6').style('max-width: 900px; width: 100%; gap: 20px;'):
                    # 用户信息卡片
                    self._create_user_info_card()
                    
                    # 操作按钮区域 - 使用两列布局
                    with ui.row().classes('w-full').style('gap: 16px; display: flex;'):
                        # 修改密码
                        with ui.element('div').style('flex: 1;'):
                            self._create_action_card(
                                icon='lock',
                                title='修改密码',
                                description='更改您的登录密码以保护账户安全',
                                color='#667eea',
                                button_text='修改密码',
                                callback=self.show_change_password_dialog
                            )
                        
                        # 退出登录
                        with ui.element('div').style('flex: 1;'):
                            self._create_action_card(
                                icon='logout',
                                title='退出登录',
                                description='安全退出当前账户',
                                color='#e74c3c',
                                button_text='退出',
                                callback=self.logout
                            )
    
    def _create_user_info_card(self) -> None:
        """创建用户信息卡片"""
        with ui.card().classes('w-full').style(
            'background: white; '
            'border-radius: 12px; '
            'box-shadow: 0 2px 12px rgba(0,0,0,0.08); '
            'padding: 18px;'
        ):
            # 卡片标题
            with ui.row().classes('w-full items-center q-mb-md'):
                ui.icon('account_circle', size='lg').style('color: #667eea;')
                ui.label('账户信息').classes('text-h6 text-weight-bold q-ml-sm').style('color: #2c3e50;')
            
            # ui.separator().classes('q-mb-md')
            
            # 用户信息 - 使用两列网格布局
            if self.current_user:
                with ui.grid(columns='1fr 1fr').classes('w-full').style('gap: 16px;'):
                    # 用户名
                    self._create_info_row('person', '用户名', self.current_user.get('username', '未知'))
                    
                    # 用户角色
                    role = self.current_user.get('role', '未知')
                    role_display = '管理员' if role == 'admin' else '普通用户'
                    self._create_info_row('verified_user', '用户角色', role_display)
            else:
                with ui.column().classes('w-full items-center q-pa-lg'):
                    ui.icon('warning', size='lg', color='orange')
                    ui.label('未获取到用户信息').classes('text-body2 text-grey-6 q-mt-sm')
    
    def _create_info_row(self, icon: str, label: str, value: str) -> None:
        """创建信息行"""
        with ui.row().classes('items-center').style('padding: 12px; background: #f8f9fa; border-radius: 8px;'):
            ui.icon(icon, size='sm').style('color: #667eea;')
            with ui.column().classes('q-ml-sm').style('gap: 2px;'):
                ui.label(label).classes('text-caption').style('color: #7f8c8d;')
                ui.label(value).classes('text-body2 text-weight-medium').style('color: #2c3e50;')
    
    def _create_action_card(self, icon: str, title: str, description: str, color: str, button_text: str, callback) -> None:
        """创建操作卡片"""
        with ui.card().classes('w-full').style(
            'background: white; '
            'border-radius: 12px; '
            'box-shadow: 0 2px 12px rgba(0,0,0,0.08); '
            'padding: 24px; '
            'height: 100%; '
            'transition: all 0.3s ease;'
        ).on('mouseenter', lambda e: e.sender.style(
            'box-shadow: 0 8px 24px rgba(0,0,0,0.12); transform: translateY(-4px);'
        )).on('mouseleave', lambda e: e.sender.style(
            'box-shadow: 0 2px 12px rgba(0,0,0,0.08); transform: translateY(0);'
        )):
            with ui.column().classes('w-full items-center').style('gap: 16px;'):
                # 图标
                with ui.element('div').style(
                    f'width: 64px; '
                    f'height: 64px; '
                    f'background: {color}15; '
                    f'border-radius: 50%; '
                    f'display: flex; '
                    f'align-items: center; '
                    f'justify-content: center;'
                ):
                    ui.icon(icon, size='lg').style(f'color: {color};')
                
                # 标题和描述
                with ui.column().classes('items-center').style('gap: 4px;'):
                    ui.label(title).classes('text-h6 text-weight-bold').style('color: #2c3e50;')
                    ui.label(description).classes('text-caption text-center').style('color: #7f8c8d; max-width: 200px;')
                
                # 按钮
                ui.button(button_text, icon=icon, on_click=callback).props('no-caps').style(
                    f'background: {color}; '
                    f'color: white; '
                    f'padding: 8px 24px; '
                    f'border-radius: 8px; '
                    f'font-weight: 500;'
                )
    
    def show_change_password_dialog(self) -> None:
        """显示修改密码对话框"""
        with ui.dialog() as dialog, ui.card().classes('q-pa-lg').style('min-width: 450px; border-radius: 12px;'):
            # 标题
            with ui.row().classes('w-full items-center q-mb-md'):
                ui.icon('lock', size='md').style('color: #667eea;')
                ui.label('修改密码').classes('text-h6 text-weight-bold q-ml-sm').style('color: #2c3e50;')
            
            ui.separator().classes('q-mb-lg')
            
            # 表单
            with ui.column().classes('w-full').style('gap: 16px;'):
                old_password = ui.input('原密码', password=True, password_toggle_button=True).props('outlined').classes('w-full')
                new_password = ui.input('新密码', password=True, password_toggle_button=True).props('outlined').classes('w-full')
                confirm_password = ui.input('确认新密码', password=True, password_toggle_button=True).props('outlined').classes('w-full')
                
                # 提示信息
                with ui.card().classes('w-full').style('background: #f0f7ff; border-left: 3px solid #667eea; padding: 12px;'):
                    ui.label('密码要求').classes('text-caption text-weight-bold').style('color: #2c3e50;')
                    ui.label('• 长度不少于6位').classes('text-caption').style('color: #5a6c7d;')
                    ui.label('• 建议包含字母和数字').classes('text-caption').style('color: #5a6c7d;')
                
                # 按钮
                with ui.row().classes('w-full justify-end q-mt-md').style('gap: 8px;'):
                    ui.button('取消', on_click=dialog.close).props('flat no-caps').style('color: #7f8c8d;')
                    ui.button('确认修改', icon='check', on_click=lambda: self.change_password(
                        old_password.value, 
                        new_password.value, 
                        confirm_password.value, 
                        dialog
                    )).props('no-caps').style(
                        'background: #667eea; '
                        'color: white; '
                        'padding: 8px 24px;'
                    )
            
            dialog.open()
    
    async def change_password(self, old_password: str, new_password: str, confirm_password: str, dialog) -> None:
        """修改密码"""
        # 验证输入
        if not old_password or not new_password or not confirm_password:
            ui.notify('请填写所有字段', type='warning', position='top')
            return
            
        if new_password != confirm_password:
            ui.notify('新密码与确认密码不匹配', type='warning', position='top')
            return
            
        if len(new_password) < 6:
            ui.notify('新密码长度不能少于6位', type='warning', position='top')
            return
            
        # 调用后端API修改密码
        try:
            from api_client import get_api_client
            api_client = get_api_client()
            result = await api_client.change_password(old_password, new_password)
            
            if result.get("code") == 200:
                logger.info(f"密码修改成功")
                ui.notify('密码修改成功！', type='positive', position='top', icon='check_circle')
                dialog.close()
            else:
                error_msg = result.get("msg", "修改密码失败")
                logger.error(f"修改密码失败: {error_msg}")
                ui.notify(f'密码修改失败: {error_msg}', type='negative', position='top')
            
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            error_msg = str(e)
            
            if "认证失败" in error_msg or "Token" in error_msg or "token" in error_msg or "401" in error_msg:
                self._handle_auth_failure(error_msg)
            else:
                ui.notify(f'密码修改失败: {error_msg}', type='negative', position='top')
    
    def _handle_auth_failure(self, error_msg: str = "") -> None:
        """处理认证失败"""
        try:
            self.current_user = None
            if hasattr(self.page_manager, 'current_user'):
                self.page_manager.current_user = None
            
            from api_client import get_api_client
            api_client = get_api_client()
            api_client.token = None
            api_client.user_info = None
            if "Authorization" in api_client.client.headers:
                del api_client.client.headers["Authorization"]
            
            if "当前密码不正确" in error_msg:
                ui.notify('当前密码不正确，请重新登录', type='negative', position='top')
            elif "Token" in error_msg or "token" in error_msg or "认证" in error_msg:
                ui.notify('登录已过期，请重新登录', type='negative', position='top')
            else:
                ui.notify('认证失败，请重新登录', type='negative', position='top')
            
            if hasattr(self.page_manager, 'show_login_page'):
                self.page_manager.show_login_page()
                
        except Exception as e:
            logger.error(f"处理认证失败时出错: {e}")
            ui.notify('认证失败，请重新登录', type='negative', position='top')
            
    def logout(self) -> None:
        """登出操作"""
        try:
            self.current_user = None
            if hasattr(self.page_manager, 'current_user'):
                self.page_manager.current_user = None
                
            if self.logout_callback:
                self.logout_callback()
                
            ui.notify('已成功登出', type='positive', position='top', icon='waving_hand')
            
            if hasattr(self.page_manager, 'show_login_page'):
                self.page_manager.show_login_page()
                
        except Exception as e:
            logger.error(f"登出失败: {e}")
            ui.notify(f'登出失败: {str(e)}', type='negative', position='top')