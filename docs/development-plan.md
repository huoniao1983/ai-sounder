# AI 直播互动获客助手 · 全量开发计划与任务拆分

## 摘要

依据 `docs/AI直播助手PRD.md` v2.0 Final，覆盖 v1.0/v1.1/v2.0 全部模块：Tauri 2.x + React/TS 桌面壳，Python 引擎子进程承载弹幕、TTS、话术编排、混音、线索与昵称处理。按 2 人以上小组并行估算约 14 周；单人串行执行时按 1.8-2 倍排期。

## 技术决策

- Monorepo：`desktop/` 放 Tauri/React/TS，`engine/` 放 Python 引擎，`assets/music/` 放免版权 BGM，`tests/` 镜像 `engine/`。
- Rust 主进程托管 Python sidecar，使用换行分隔 JSON-RPC；命令与事件契约见 PRD。
- 本地 SQLite + SQLAlchemy 保存预设、文案组、歌单、播放历史、音色与线索。Alembic 作为可选迁移依赖，首轮先用 `Base.metadata.create_all` 保证空库可启动。
- 音频输出为单路 48kHz/16bit/stereo PCM；声卡回调不阻塞，Ducking 在应用内完成。

## 实施清单

| 里程碑 | 状态 | 本轮落地 | 待完成 |
| --- | --- | --- | --- |
| M0 工程底座 | 部分完成 | Python/Tauri 目录与 `pyproject.toml`、sidecar JSON-RPC 与 `health`、SQLite 模型与建表、pytest 通过 | Tauri Rust 编译、正式 Alembic 迁移、CI 模板 |
| M1 平台与壳 | 脚手架 | `DanmuEvent`、`PlatformAdapter`、mock 事件源、桌面端启动页结构 | B 站/抖音真实授权与接入、DPAPI 凭证、事件流 UI |
| M2 TTS 与声音 | 部分 | 千问 CosyVoice v3.5 Flash Provider、声音复刻、音色名称与描述 | 音色审核轮询、试听与运行时播放联调 |
| M2.5 话术编排 H | 主体完成 | `ShuffleQueue`、`ScriptScheduler`、预合成、热更新与边界；专项测试通过 | 接 TTS/混音后的全链路压测 |
| M2.6 音频混音 I | 核心完成 | `DuckController`、`AudioMixer`、`MusicPlayer` 缓冲核心与测试 | sounddevice/miniaudio 实机输出、VB-Cable/OBS 联调、8h 稳定性 |
| M3 文案与线索 | 部分 | OpenAI 兼容 LLM Provider、Base URL/模型/API Key 配置、正则线索提取、打分与分级 | 引擎 IPC 串联、线索持久化 UI、CSV/Excel 与 Webhook |
| M4 进阶平台与 UI | 未开始 | 无 | 快手、OCR、OBS、开播向导与运行时监控 |
| M5 拟人化与发布 | 部分规则层 | `speakable_name` 规则层 | HanLP/NER、LLM 层、安装包与发布 |

## 关键代码位置

- `engine/scheduler/shuffle_queue.py`：周期洗牌、权重、跨周期防重、热更新
- `engine/scheduler/script_scheduler.py`：播放循环、停顿、预合成
- `engine/audio/duck_controller.py`：语音检测与 BGM 增益包络
- `engine/audio/mixer.py`：语音/音乐两通道混音与软限幅
- `engine/platform/`：事件模型与平台适配器接口
- `engine/tts/cosyvoice.py`：千问 CosyVoice v3.5 Flash 合成与声音复刻
- `engine/nlp/nickname.py`：昵称拟人化规则层
- `engine/leads/detector.py`：联系方式与意向识别、行为打分
- `engine/content/llm.py`：OpenAI 兼容大模型文案生成
- `engine/ipc/server.py`：sidecar JSON-RPC 传输
- `engine/db/models.py`：PRD 数据表模型

## 测试与验收

当前专项测试覆盖：

- 1000 次播放无相邻重复、每周期公平、跨周期边界 10000 次无重复
- 权重抽样统计显著靠前、N=1/N=2、热更新防重、peek 不消费
- Ducking 500ms 到位、1.5s 回升、纯静音保持常增益
- 混音输出为双声道且经软限幅不削波
- 昵称示例、线索分级、mock 弹幕、SQLite 建表、IPC health/shutdown
- OpenAI 兼容 LLM 的鉴权头、模型参数与 JSON 解析

运行：

```powershell
python -m pytest
```

实机音频与真实平台需安装可选依赖：

```powershell
pip install -e ".[audio,db,dev]"
```
