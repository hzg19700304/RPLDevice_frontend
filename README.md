# Rail Potential Limiter HMI

钢轨电位限制柜人机界面 (Rail Potential Limiting Device Human Machine Interface)

> 注意：当前版本不包含串口通信与数据库功能；数据通过 WebSocket 获取。

## 项目结构

```
rail-potential-limiter-hmi/         # 推荐的英文项目根目录
├── main.py                         # 主应用程序
├── config_manager.py               # 配置管理模块
├── websocket_client.py             # WebSocket客户端模块
├── ui_components.py                # UI组件模块
├── pages/                          # 页面模块
│   ├── __init__.py
│   └── page_manager.py             # 页面管理器
├── config.ini                      # 配置文件
├── requirements.txt                # 依赖包列表
├── test_config.py                  # 配置测试脚本
├── run_app.py                     # 应用启动脚本
├── setup_env.bat                  # 环境设置脚本(CMD)
├── setup_env.ps1                  # 环境设置脚本(PowerShell)
├── run_with_venv.bat              # 虚拟环境运行脚本
├── .gitignore                     # Git忽略文件
├── venv/                          # 虚拟环境目录(运行setup后生成)
├── PROJECT_RENAME_GUIDE.md        # 项目重命名指南
└── README.md                      # 项目说明文档
```

## 功能特性

### 已实现功能

1. **项目基础结构**
   - NiceUI框架集成
   - 配置文件读取和解析
   - WebSocket客户端连接
   - 基础UI组件框架

2. **配置管理**
   - 支持中文配置项
   - 自动数据类型转换
   - 配置段分类访问
   - 注释过滤处理

3. **WebSocket通信**
   - 异步连接管理
   - 自动重连机制
   - 心跳保持
   - 消息回调系统

4. **UI组件**
   - 响应式布局设计
   - 触摸屏友好界面
   - 虚拟数字键盘
   - 确认对话框
   - 加载指示器

### 待实现功能

- 主接线图SVG显示
- 系统状态监控
- 实时曲线显示
- 历史数据查询
- 参数设置界面
- 故障录波查询
- 用户权限管理

## 安装和运行

### 环境要求

- Python 3.8+
- Windows 操作系统

### 创建虚拟环境（推荐）

#### 方法1：使用 venv（Python内置）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows CMD
venv\Scripts\activate

# Windows PowerShell
venv\Scripts\Activate.ps1

# 验证虚拟环境已激活（命令提示符前会显示 (venv)）
```

#### 方法2：使用 conda
```bash
# 创建虚拟环境
conda create -n rpl-hmi python=3.9

# 激活虚拟环境
conda activate rpl-hmi
```

### 安装依赖

确保虚拟环境已激活，然后安装依赖：

```bash
pip install -r requirements.txt
```

### 快速设置（推荐）

我们提供了自动化脚本来简化环境设置：

#### Windows CMD
```bash
# 一键设置环境（创建虚拟环境+安装依赖）
setup_env.bat

# 使用虚拟环境运行应用
run_with_venv.bat
```

#### Windows PowerShell
```powershell
# 一键设置环境
.\setup_env.ps1

# 手动激活虚拟环境后运行
venv\Scripts\Activate.ps1
python main.py
```

### 退出虚拟环境

```bash
# venv
deactivate

# conda
conda deactivate
```

### 配置文件

确保 `config.ini` 文件存在并正确配置以下关键参数：

- 设备信息
- WebSocket 连接参数
- 界面显示配置

### 运行应用

#### 方法1：直接运行主程序
```bash
python main.py
```

#### 方法2：使用启动脚本
```bash
python run_app.py
```

#### 方法3：测试配置
```bash
python test_config.py
```

### 访问界面

应用启动后，在浏览器中访问：
```
http://localhost:8080
```

## 开发说明

### 配置管理

`ConfigManager` 类提供了完整的配置文件管理功能：

```python
from config_manager import ConfigManager

config = ConfigManager()
await config.load_config()

# 获取设备信息
device_info = config.get_device_info()

# 获取WebSocket配置
ws_config = config.get_websocket_config()

# 检查页面是否启用
if config.is_page_enabled('show_main_diagram'):
    # 显示主接线图页面
    pass
```

### WebSocket通信

`WebSocketClient` 类提供了异步WebSocket通信功能：

```python
from websocket_client import WebSocketClient

client = WebSocketClient(config_manager)
await client.connect()

# 注册数据回调
client.register_data_callback('real_time_data', handle_real_time_data)

# 发送消息
await client.send_message('get_status', {})
```

### UI组件

`UIComponents` 类提供了通用UI组件：

```python
from ui_components import VirtualKeyboard, ConfirmDialog

# 显示虚拟键盘
keyboard = VirtualKeyboard(input_element)
keyboard.show()

# 显示确认对话框
ConfirmDialog.show("确认操作", "是否继续？", on_confirm=do_action)
```

## 技术栈

- **前端框架**: NiceUI (Python-based web UI)
- **实时通信**: WebSocket
- **配置管理**: ConfigParser
- **数据可视化**: Plotly.js
- **异步处理**: asyncio

## 项目重命名 Project Rename

建议将项目文件夹重命名为英文名称以获得更好的兼容性：

**推荐名称**: `rail-potential-limiter-hmi`

详细的重命名步骤请参考 [PROJECT_RENAME_GUIDE.md](PROJECT_RENAME_GUIDE.md)

## 许可证

本项目为内部开发项目，版权所有。