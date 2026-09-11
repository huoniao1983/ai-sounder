# Tauri 打包与本地引擎架构

## 开发运行

`npm run tauri dev` 时 Rust 主进程会自动启动 Python 能力服务：

```powershell
python -m engine.api_server --host 127.0.0.1 --port 8765
```

Rust 会先检查 `127.0.0.1:8765`，未运行才启动子进程；桌面应用退出时停止该子进程。网页预览仍需手动运行 API 服务。

## 构建 Python Sidecar

```powershell
cd desktop
.\scripts\build-sidecar.ps1
```

产物：

```text
desktop/src-tauri/binaries/aisounder-engine.exe
```

Rust 启动顺序：优先运行 `aisounder-engine.exe`，否则退回 `python -m engine.api_server`（开发环境）。Sidecar 的资源目录通过 `AISOUNDER_RESOURCE_DIR` 注入。

## 统一发布包

最终发布采用单一 NSIS 安装包，Tauri 主程序、Python Sidecar、真实音频资源与运行目录统一安装，用户无需手工拼装目录：

```text
AISounder/
├─ aisounder.exe
├─ aisounder-engine.exe
├─ assets/
│  ├─ music/
│  └─ voices/
└─ data/
   ├─ aisounder.db
   └─ uploads/
```

应用运行时通过环境变量读取统一安装目录：

```text
AISOUNDER_RESOURCE_DIR=<程序资源目录>
AISOUNDER_DATA_DIR=<用户数据目录>
```

## 安装器

Tauri 安装器包含：

- 桌面壳 + Python Sidecar + 本地数据库 + 内置 BGM + 音色样本。
- CosyVoice v3.5 Flash 在线合成配置；API Key 在安装后由用户保存到本地运行配置。
- 驱动页：检测不到 VB-Cable 时引导用户单独安装驱动，不静默装驱动。
