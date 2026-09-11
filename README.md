# AISounder

[简体中文](#简体中文) | [English](#english)

AI 直播互动获客助手 / AI Live-Streaming Assistant

---

## 简体中文

### 项目简介

AISounder 是一个面向无人值守直播场景的桌面应用。用户可以创建多个直播专场，为每个专场配置平台、文案、音色、背景音乐和播放参数，然后一键开播。系统会生成拟真的带货话术，调用 CosyVoice v3.5 Flash 合成语音，并在文案播放时自动压低背景音乐。

当前实现状态：

- 直播专场管理与两步创建流程
- 专场独立文案、音色、BGM、播放模式
- AI 文案生成、确认保存、表演指令与 SSML
- CosyVoice v3.5 Flash 在线语音合成
- API 声音复刻、音色命名与描述
- 顺序循环与随机首尾不重复
- 语音与 BGM 双通道播放、Ducking
- 抖音、快手、B站接入配置与统一互动事件
- 线索识别、分级与 CSV 导出

### 系统架构

```text
React + TypeScript UI
        |
        | Tauri IPC / localhost capability API
        v
Tauri 2 Desktop Shell (Rust)
        |
        | spawns and supervises
        v
Python Engine Sidecar
  |- Content generation -> OpenAI-compatible LLM API
  |- Voice synthesis    -> Qianwen DashScope CosyVoice v3.5 Flash
  |- Voice cloning      -> DashScope customization API
  |- Live events        -> Douyin / Kuaishou WebSocket or callback bridge
  |- Script scheduler   -> shuffle, pause, pre-synthesis
  |- Audio mixer        -> voice, BGM, Ducking
  |- Persistence        -> SQLite / local runtime files
```

开发模式下，前端通过 `http://127.0.0.1:8765` 访问 Python capability service。Tauri 主程序会优先启动或复用 `aisounder-engine.exe`，应用退出时停止由它创建的子进程。

### 技术栈

- Desktop: Tauri 2, Rust, NSIS
- Frontend: React 18, TypeScript, Vite, lucide-react
- Engine: Python 3.11+, asyncio, SQLAlchemy, SQLite
- Platform: aiohttp WebSocket
- Audio: NumPy; optional `sounddevice` and `miniaudio`
- Packaging: PyInstaller sidecar + Tauri bundle

### 目录结构

```text
.
├─ desktop/                 Tauri + React desktop application
│  ├─ src/                  React UI
│  ├─ src-tauri/            Rust shell, config and sidecar binary
│  ├─ public/               Offline platform icons
│  └─ scripts/              Sidecar build script
├─ engine/                  Python engine
│  ├─ content/              LLM prompts, script generation and SSML
│  ├─ tts/                  CosyVoice synthesis and voice cloning
│  ├─ scheduler/            Shuffle queue and playback loop
│  ├─ audio/                Mixer, Ducking and music buffering
│  ├─ platform/             Douyin/Kuaishou adapters and event service
│  ├─ leads/                Lead extraction and scoring
│  ├─ nlp/                  Nickname personalization
│  └─ db/                   SQLAlchemy models
├─ assets/music/            Real playable BGM files
├─ assets/voices/           Voice asset documentation
├─ tests/                   pytest suite
└─ docs/                    PRD and technical documents
```

### 外部接口和配置

#### 1. AI 文案大模型

支持任何 OpenAI-compatible `chat/completions` 接口：

```text
Base URL: https://your-provider.example/v1
Model:    your-model
API Key:  your-api-key
```

在应用中选择“设置 → 模型设置”配置。生成的文案包含：

- `content`: 可朗读的口语台词
- `instruction`: CosyVoice 情绪、语速、重音和呼吸指令
- `ssml`: 受控的停顿和发音标签

#### 2. CosyVoice

默认使用千问平台 `cosyvoice-v3.5-flash`：

```text
Base URL: https://dashscope.aliyuncs.com/api/v1
Model:    cosyvoice-v3.5-flash
```

主要接口：

- `POST /services/audio/tts/SpeechSynthesizer`
- `POST /services/audio/tts/customization`

声音复刻需要公网可访问的 WAV、MP3 或 M4A 样本 URL。API Key 只保存在本地运行目录，不写入源码或公开安装包。

#### 3. 直播平台

抖音、快手和 B站支持两种接入方式：

- 官方 WebSocket：配置 `ws_url`、Headers JSON 和 Query Params JSON
- 回调桥接：将平台回调转发到 `POST /platform/callback`

详细字段见 [docs/platform-integration.md](docs/platform-integration.md)。

### 安装和运行

#### 环境要求

- Windows 10/11 x64
- Python 3.11+
- Node.js 20+
- Rust stable 和 MSVC C++ Build Tools
- WebView2
- 可选：VB-Cable、Voicemeeter、OBS

#### 开发模式

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
npm --prefix desktop install

# Terminal 1: local capability service
python -m engine.api_server --host 127.0.0.1 --port 8765

# Terminal 2: browser preview
npm --prefix desktop run dev
```

打开 `http://127.0.0.1:1420`。

完整 Tauri 开发模式需要先生成 Python sidecar：

```powershell
cd desktop
.\scripts\build-sidecar.ps1
npm run tauri dev
```

### 测试

```powershell
python -m pytest
npm --prefix desktop run build
```

测试覆盖洗牌队列、播放调度、SSML 白名单、CosyVoice 参数、Ducking、混音、互动事件、平台适配、线索和数据库结构。

### 打包发布

```powershell
cd desktop
.\scripts\build-sidecar.ps1 -SkipInstall
npm run tauri build
```

主要产物：

```text
desktop/src-tauri/target/release/aisounder.exe
desktop/src-tauri/target/release/aisounder-engine.exe
desktop/src-tauri/target/release/bundle/nsis/AISounder_0.1.0_x64-setup.exe
```

安装包会包含 Tauri 主程序、Python sidecar 和 `assets/` 资源。API Key 不随包发布，首次启动后在“设置 → 模型设置”中配置。

### 安全和限制

- **外部模型依赖**：AI 文案通过用户配置的 OpenAI 兼容 `chat/completions` 接口生成；提示词、专场信息和商品描述会发送给对应模型服务商，请评估数据与隐私风险。
- **语音合成**：音色克隆与合成使用千问 DashScope CosyVoice v3.5 Flash，需要联网和有效 API Key；复刻样本必须是公网可访问的音频 URL，且用户应确认拥有声音授权。
- **平台接入**：抖音、快手和 B站事件获取受开放平台权限、OAuth 审核、签名规则和频控限制；二进制 Protobuf 网关需先通过官方 SDK 或桥接服务解码。
- **音频输出**：应用在本地完成文案语音、BGM 混音和 Ducking，并输出 48kHz/16bit 立体声到虚拟声卡；不采集麦克风，也不控制系统或其他应用音频。
- **内容合规**：AI 话术、昵称互动和克隆音色需人工审核；使用前应确认营销内容、声音授权和 BGM 版权，避免虚假宣传或侵权。

---

## English

### Overview

AISounder is a Windows desktop assistant for unattended live-streaming. It manages multiple live scenes and lets each scene define its platforms, scripts, voice, background music, playback mode, and launch settings.

The application generates natural spoken sales scripts, synthesizes voice through CosyVoice v3.5 Flash, and automatically ducks background music while speech is playing.

Current capabilities:

- Multi-scene dashboard and two-step scene creation
- Scene-specific scripts, voice, BGM, and playback mode
- AI script generation with explicit confirmation before saving
- Performance instructions and CosyVoice-compatible SSML
- Online voice synthesis and voice cloning
- Sequential playback and shuffle without adjacent repeats
- Separate voice/BGM playback with Ducking
- Douyin, Kuaishou, and Bilibili integration settings
- Lead detection, scoring, and CSV export

### Architecture

```text
React + TypeScript UI
        |
        v
Tauri 2 Shell (Rust)
        |
        v
Python Engine Sidecar
  ├─ OpenAI-compatible LLM
  ├─ DashScope CosyVoice v3.5 Flash
  ├─ Platform WebSocket / callback bridge
  ├─ Script scheduler and audio mixer
  └─ SQLite and local runtime files
```

During development the frontend uses `http://127.0.0.1:8765`. In the packaged desktop application, the Rust shell launches and manages `aisounder-engine.exe`.

### Stack

- Desktop: Tauri 2, Rust, NSIS
- Frontend: React 18, TypeScript, Vite, lucide-react
- Engine: Python 3.11+, asyncio, SQLAlchemy, SQLite, aiohttp
- Audio: NumPy, optional sounddevice/miniaudio
- Packaging: PyInstaller + Tauri bundle

### External Services

- LLM: any OpenAI-compatible `chat/completions` API
- TTS and cloning: Qianwen DashScope CosyVoice v3.5 Flash
- Live events: Douyin/Kuaishou official WebSocket or callback bridge

Configure provider URLs, models, and API keys in the application settings. Secrets stay in the local runtime directory and are never committed.

### Development

```powershell
pip install -e ".[dev]"
npm --prefix desktop install
python -m engine.api_server --host 127.0.0.1 --port 8765
npm --prefix desktop run dev
```

Run the complete desktop shell:

```powershell
cd desktop
.\scripts\build-sidecar.ps1
npm run tauri dev
```

Run tests and frontend build:

```powershell
python -m pytest
npm --prefix desktop run build
```

### Release Build

```powershell
cd desktop
.\scripts\build-sidecar.ps1 -SkipInstall
npm run tauri build
```

The NSIS installer is generated under:

```text
desktop/src-tauri/target/release/bundle/nsis/
```

### Security & Limitations

- **External model dependency**: AI scripts are generated through a user-configured OpenAI-compatible `chat/completions` endpoint. Prompts, session details, and product descriptions are sent to that provider, so review its privacy policy before processing sensitive data.
- **Voice synthesis**: Voice cloning and synthesis use Qianwen DashScope CosyVoice v3.5 Flash and require network access and a valid API key. Cloning references must be publicly accessible audio URLs, and users are responsible for obtaining voice authorization.
- **Platform access**: Douyin, Kuaishou, and Bilibili event access is subject to open-platform permissions, OAuth review, signing rules, and rate limits. Binary Protobuf gateways require an official SDK or decoding bridge.
- **Audio output**: The app mixes voice and BGM locally with Ducking, then outputs 48 kHz/16-bit stereo to a virtual audio device. It does not capture a microphone or control audio from other applications.
- **Content compliance**: AI-generated scripts, nickname interactions, and cloned voices require human review. Users must verify advertising claims, voice permissions, and BGM licensing before going live.

See [docs/platform-integration.md](docs/platform-integration.md) and [docs/packaging.md](docs/packaging.md) for more details.

