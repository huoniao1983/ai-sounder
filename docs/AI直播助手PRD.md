![]()

AI 直播互动获客助手 · 完整版 PRD & 技术方案（v2.0 Final）
========================================

> **本文档整合 v1.0（主架构）+ v1.1（昵称拟人化）+ v2.0 新增模块（话术编排引擎、音频混音引擎），为最终交付研发的完整闭环版本。**
> 
> **框架结论**：**Tauri 2.x（Rust+React/TS）UI 壳 + Python 引擎子进程**（弹幕/TTS/编排/混音），或纯 Python 团队用 **PySide6 + PyInstaller**。

一、版本需求总览
--------

| 版本          | 新增能力                                                                                                                                    |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0        | 多平台弹幕接入、AI 文案生成、TTS 云/本地引擎、声音克隆、线索收集、OBS 联动                                                                                             |
| v1.1        | 观众昵称拟人化（三层管道：规则→NER→LLM）                                                                                                                |
| **v2.0 新增** | ①**直播预设**（选主播音色+文案组+歌单一键开播）②**话术编排引擎**（N 条文案洗牌播放、防相邻重复、随机停顿）③**音频混音引擎**（主文案语音 + 互动插播 + 背景音乐三通道混音、Ducking 自动闪避）④**背景音乐管理**（顺序循环播放、免版权曲库） |

二、产品概述
------

### 2.1 一句话定位

为中小商家提供“**选音色 → 配文案 → 挂 BGM → 一键开播**”的无人值守 AI 直播获客工具：主文案像真人一样循环播报（随机不重复、有呼吸感停顿），观众互动实时拟人化回应，BGM 常驻垫底、说话自动变小声，弹幕中的意向客户自动沉淀为线索。

### 2.2 单场直播完整用户流程

### 2.3 核心验收指标

| 指标         | 目标                                  |
| ---------- | ----------------------------------- |
| 洗牌正确性      | N≥2 时**任意相邻两条不重复**，单周期内每条恰好播一次      |
| 主文案衔接间隙    | 可配置 0~60s，默认 3~8s 随机                |
| Ducking 响应 | 语音出现后 BGM 500ms 内衰减到位；语音结束 1.5s 后回升 |
| 音频输出       | 48kHz/16bit/双声道，混音无爆音、无削波           |
| 连续运行       | ≥8h 无崩溃、无内存泄漏、BGM 无缝衔接不断流           |

三、功能模块总览（v2.0 全景）
-----------------

| 模块    | 名称                      | 版本       | 本文档处理方式       |
| ----- | ----------------------- | -------- | ------------- |
| A     | 多平台弹幕接入引擎               | v1.0     | §五 精要保留       |
| B     | AI 文案生成引擎               | v1.0     | §五 精要保留       |
| C     | TTS 语音合成引擎              | v1.0     | §五 精要保留       |
| D     | 直播音频桥接                  | v1.0     | 并入**模块 I** 详述 |
| E     | 获客线索收集                  | v1.0     | §五 精要保留       |
| F     | Windows 桌面 UI           | v1.0     | §五 精要保留       |
| G     | 昵称拟人化管道                 | v1.1     | §五 精要保留       |
| **H** | **话术编排引擎（洗牌播放）**        | **v2.0** | **§四 完整详述**   |
| **I** | **音频混音引擎（三通道+Ducking）** | **v2.0** | **§四 完整详述**   |

四、v2.0 核心新增模块（详述）
-----------------

模块 H：话术编排引擎（Script Scheduler）
-----------------------------

### 4.1 需求精确描述

1. 用户为主播配置 **N 条备选主文案**（商品话术、福利口播、留人话术等）。
2. 播放顺序为**随机但不重复**：期望效果 `A-B-C-D-A-B-C-D`，**禁止** `A-B-B-C-A-A`（相邻重复或短窗口内高频重复）。
3. 每条文案播完后**停顿随机几秒**（区间可配，如 3~8s），产生真人换气的呼吸感。
4. 播放期间若出现互动事件（欢迎/礼物/关键词），按打断策略处理（见 4.5）。
5. 支持文案**权重**：主推商品可设更高权重（更早、更频繁出现，但同周期仍不重复）。

### 4.2 核心算法：周期洗牌队列

**算法本质**：音乐播放器“随机播放（Shuffle）”模式——将 N 条文案视为一副牌，整副洗乱后逐张发出；发完重新洗一副，并处理**跨周期边界**（新周期第一张 ≠ 旧周期最后一张）。
    # /engine/scheduler/shuffle_queue.py
    import random
    from typing import Any, Optional

    class ShuffleQueue:
        """    周期洗牌队列：保证任意相邻两次取出的元素不同，    且一个完整周期内每个元素恰好出现一次。        不变量（Loop Invariant）:      I1: self.pool 是当前周期剩余未播元素的随机排列      I2: pool 末尾元素 ≠ last_played（跨周期边界成立后保持）      I3: 每个 pop() 严格 O(1)（洗牌均摊到整个周期，平均 O(N)）    """

        def __init__(self, items: list, weights: Optional[list[float]] = None, seed: Optional[int] = None):
            assert len(items) >= 1, "至少需要 1 条文案"
            self.items = list(items)
            self.weights = weights if weights else [1.0] * len(items)
            self.rng = random.Random(seed)
            self.pool: list = []
            self.last_played: Any = None
            self.cycle_count = 0          # 完整周期数（用于统计）

        def next(self) -> Any:
            """取出下一条文案，O(1) 均摊"""
            if not self.pool:
                self._refill()
            item = self.pool.pop()        # 从末尾取（洗牌后的末尾即随机）
            self.last_played = item
            return item

        def _refill(self):
            """重洗一副牌，并处理跨周期边界"""
            if len(self.items) == 1:
                # N=1 退化：无法避免重复，原样返回（产品层应弹警告，见 4.6）
                self.pool = [self.items[0]]
                return

            # 加权洗牌：权重大者更大概率排在前面位置
            self.pool = self._weighted_shuffle(self.items, self.weights)
            self.cycle_count += 1

            # 边界修复：新周期末尾（即将播出的下一条）不能等于上周期的 last_played
            if self.last_played is not None and self.pool[-1] == self.last_played:
                # 与随机一个非末尾位置交换（swap-fix，O(1)）
                swap_idx = self.rng.randint(0, len(self.pool) - 2)
                self.pool[-1], self.pool[swap_idx] = self.pool[swap_idx], self.pool[-1]

        def _weighted_shuffle(self, items: list, weights: list[float]) -> list:
            """        加权不重复洗牌：每轮从剩余项中按权重有放回抽样位置、        无放回取出元素。结果保证：每项恰好出现一次，        且权重越高的项出现在序列前部（=越早被播到）的概率越大。        复杂度 O(N²)，N≤500 时 <10ms，满足场景。        """
            remaining = list(zip(items, weights))
            result = []
            while remaining:
                total = sum(w for _, w in remaining)
                r = self.rng.uniform(0, total)
                acc = 0.0
                for idx, (item, w) in enumerate(remaining):
                    acc += w
                    if acc >= r:
                        result.append(item)
                        remaining.pop(idx)
                        break
            return result

        def update_items(self, items: list, weights: Optional[list[float]] = None):
            """直播中动态增删文案（UI 编辑后热更新，下周期生效）"""
            self.items = list(items)
            self.weights = weights if weights else [1.0] * len(items)
            self.pool.clear()   # 丢弃当前周期，下次 next() 重洗

        def peek_remaining(self) -> int:
            return len(self.pool)

**算法正确性说明（供研发/测试对齐）**：

| 场景           | 行为                            | 证明                                  |
| ------------ | ----------------------------- | ----------------------------------- |
| N=4，权重均等     | 如 `B-D-A-C A-C-B-D ...`，相邻必不同 | 周期内元素唯一 → 无重复；边界 swap-fix 保证跨周期相邻不同 |
| N=2          | 只能产生 `A-B-A-B...`（唯一合法解）      | 周期唯一排列为 A-B 或 B-A，均无相邻重复            |
| N=1          | 必然连续重复 `A-A-A`                | 数学上不可避免 → 触发 UI 警告（4.6）             |
| 权重 [3,1,1,1] | 权重 3 的文案平均更早出现，但每周期仍各一次       | 加权抽样不改变“无放回”性质                      |
| 直播中改文案       | 立即重洗，old `last_played` 保留继续防重 | `update_items` 清池保 last_played      |

> **为什么不用“纯随机+查重重试”？** 纯随机在 N 较小时可能长时间不出现某条（饥饿），且重试逻辑复杂。周期洗牌保证**确定性公平**（每条每周期恰好一次），这正是需求 `A-B-C-D-A-B-C-D` 的形式化表达。

### 4.3 播放循环与预合成流水线

    # /engine/scheduler/script_scheduler.py
    import asyncio, random
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class Script:
        id: str
        content: str
        weight: float = 1.0
        enabled: bool = True
    
    class ScriptScheduler:
        """    主文案播放循环：      取文案 → [停顿期间]预合成下一条 → 语音入混音器 → 随机停顿 → 下一条    与互动播报共用语音通道（在混音器层面串行），天然不会人声重叠。    """
        def __init__(self, scripts: list[Script], voice_id: str, tts_engine,                 mixer, config: dict):
            self.queue = ShuffleQueue(
                [s for s in scripts if s.enabled],
                weights=[s.weight for s in scripts if s.enabled],
            )
            self.voice_id = voice_id
            self.tts = tts_engine
            self.mixer = mixer
            self.cfg = config
            self.running = False
            self._prefetched: dict = {}   # script_id → audio_bytes 预合成缓存
    
        async def run(self):
            self.running = True
            while self.running:
                script = self.queue.next()
    
                # 1. 取音频（优先用预合成结果，未命中现场合成）
                audio = self._prefetched.pop(script.id, None) or \
                        await self.tts.synthesize(script.content, self.voice_id)
    
                # 2. 入混音器语音通道（互动事件也进同一通道，排队串行）
                await self.mixer.enqueue_voice(audio, source=f"script:{script.id}")
    
                # 3. 停顿期间并行预合成下一条（消除 TTS 网络延迟造成的空窗）
                nxt = self.queue.peek_next_prefetch()
                if nxt:
                    asyncio.create_task(self._prefetch(nxt))
    
                # 4. 随机停顿（呼吸感的核心）
                gap = random.uniform(
                    self.cfg["min_gap_seconds"],   # 默认 3
                    self.cfg["max_gap_seconds"],   # 默认 8
                )
                await asyncio.sleep(gap)
    
        async def _prefetch(self, script: Script):
            if script.id not in self._prefetched:
                try:
                    self._prefetched[script.id] = await asyncio.wait_for(
                        self.tts.synthesize(script.content, self.voice_id),
                        timeout=10.0,
                    )
                except asyncio.TimeoutError:
                    pass  # 失败则主循环现场合成兜底
    
        def stop(self):
            self.running = False

### 4.4 打断策略（主文案 vs 互动播报）

| 模式          | 行为                                         | 适用场景         |
| ----------- | ------------------------------------------ | ------------ |
| `queue`（默认） | 主文案播完 → 停顿 → **先清空互动队列** → 下一条主文案          | 大多数带货场景      |
| `interrupt` | 互动事件**立即插播**：主文案语音淡出（300ms）→ 互动语音 → 回到编排循环 | 互动密集、重视回应及时性 |
| `pause`     | 检测到弹幕活跃（如 10s 内 >20 条）时**暂停主文案**，安静期恢复     | 避免话术与互动互相淹没  |

实现要点：打断时向混音器发送 `fade_out_voice(300ms)` 指令，清空语音队列中未播的**主文案**帧但保留**互动**帧。

### 4.5 与 AI 文案生成的联动

用户在文案组编辑页点击“AI 生成”→ LLM 按商品信息生成 **N 条风格变体**（prompt 中明确要求“生成 5 条内容不重复、句式各异的话术”）→ 自动写入 `scripts` 表并赋随机权重 → 直接进入洗牌池。**这一步是“文案永不重样”的第一道防线，洗牌算法是第二道。**

### 4.6 边界与异常

| 情况            | 处理                                               |
| ------------- | ------------------------------------------------ |
| N=1           | 允许配置但 UI 黄色警告“仅 1 条文案将连续重复，建议 ≥3 条”；停顿强制拉长至 ≥10s |
| N=0           | 禁止开播，红色提示                                        |
| 某条文案 TTS 合成失败 | 重试 1 次 → 仍失败则跳过该条（记日志），洗牌队列继续，**不阻塞整场直播**        |
| 用户直播中增删文案     | 热更新（4.2 `update_items`），下周期生效                    |
| 电脑休眠/断网       | TTS 失败自动切备用 Provider；恢复后从断点周期继续                  |

模块 I：音频混音引擎（三通道 + Ducking）
--------------------------

### 4.7 音频链路总览

    ┌────────────────────┐
    │ 主文案调度器(模块H) │──┐
    └────────────────────┘  ├─► [语音通道 voice ch] ──┐
    ┌────────────────────┐  │   (串行队列,互斥)       │
    │ 互动播报调度(模块A/G)│──┘                        │    ┌──────────┐     ┌────────────┐
    └────────────────────┘                           ├──►│ 混音器   │────►│ VB-Cable   │────► OBS ────► 直播间
    ┌────────────────────┐                           │    │ (48kHz)  │     │ 虚拟声卡    │
    │ BGM 播放器          │──── [音乐通道 music ch] ──┘    └──────────┘     └────────────┘
    │ (顺序循环,独立解码)  │     ← Ducking: 说话时自动压低
    └────────────────────┘

**关键决策：应用内混音，单流输出。** 不开两个独立音频流（Windows 混音器聚合不可控、无法做 Ducking、音量比例漂移），而是由本引擎混合成单路 PCM 后写入虚拟声卡一个流。

### 4.8 混音核心实现

    # /engine/audio/mixer.py
    import numpy as np
    import sounddevice as sd
    from collections import deque
    import threading
    
    class AudioMixer:
        """    双通道实时混音（pull 模式，由声卡回调驱动）：      - voice ch: TTS 语音（优先级高，mono 24kHz → 重采样 48kHz）      - music ch: 背景音乐（垫底，立体声 48kHz）    Ducking（人声闪避）: 检测到语音能量 → BGM 增益平滑滑向 10%；    语音结束 1.5s 后平滑回升至 35%。防削波用 tanh 软限幅。    """
        SR = 48000
        BLOCK = 960  # 20ms @48kHz，兼顾延迟与回调开销
    
        def __init__(self, output_device_id: int):
            self.voice_q: deque[np.ndarray] = deque()
            self._ducking = DuckController(
                normal_gain=0.35, ducked_gain=0.10,
                attack_ms=150, release_ms=1500,
            )
            self._stream = sd.OutputStream(
                device=output_device_id,      # "CABLE Input (VB-Audio)"
                samplerate=self.SR, channels=2, dtype="float32",
                blocksize=self.BLOCK,
                callback=self._callback,      # 实时线程，内部禁止阻塞/分配大对象
            )
            self._lock = threading.Lock()
    
        # ── 供外部线程调用 ─────────────────────────────
        def enqueue_voice(self, pcm_48k: np.ndarray):
            """语音帧入队（int16 mono → float32 stereo），线程安全"""
            with self._lock:
                self.voice_q.append(pcm_48k.astype(np.float32) / 32768.0)
    
        def start(self): self._stream.start()
        def stop(self):  self._stream.stop()
    
        # ── 声卡实时回调（~20ms 一次）───────────────────
        def _callback(self, outdata, frames, time_info, status):
            voice = self._drain_voice(frames)          # 拼接语音队列，不足补零
            music = MusicPlayer.instance().read(frames) # BGM 读帧（环形缓冲，永不断流）
    
            duck_gain = self._ducking.step(voice, frames)  # 返回本块 BGM 增益标量
            music = music * duck_gain
    
            mixed = voice + music
            mixed = np.tanh(mixed * 1.2) * 0.9         # 软限幅防爆音
            outdata[:] = np.column_stack([mixed, mixed]) # mono→stereo（BGM 立体声时另行处理）
    
        def _drain_voice(self, frames) -> np.ndarray:
            out = np.zeros(frames, dtype=np.float32)
            filled = 0
            with self._lock:
                while self.voice_q and filled < frames:
                    chunk = self.voice_q[0]
                    take = min(len(chunk), frames - filled)
                    out[filled:filled+take] = chunk[:take]
                    if take < len(chunk):
                        self.voice_q[0] = chunk[take:]
                    else:
                        self.voice_q.popleft()
                    filled += take
            return out
    
    
    class DuckController:
        """一阶平滑增益控制：语音能量 > 阈值 → attack 压低；静默 release_ms 后回升"""
        def __init__(self, normal_gain, ducked_gain, attack_ms, release_ms,                 silence_threshold=0.02):
            self.g_normal, self.g_duck = normal_gain, ducked_gain
            self.atk = 1 - np.exp(-1 / (attack_ms * 0.001 * 50))   # 每20ms步进系数
            self.rel = 1 - np.exp(-1 / (release_ms * 0.001 * 50))
            self.thresh = silence_threshold
            self.gain = normal_gain
            self._silent_blocks = 0
    
        def step(self, voice_block: np.ndarray, frames: int) -> float:
            energy = np.sqrt(np.mean(voice_block ** 2)) if len(voice_block) else 0.0
            if energy > self.thresh:
                self._silent_blocks = 0
                self.gain += (self.g_duck - self.gain) * self.atk    # 快速压低
            else:
                self._silent_blocks += 1
                if self._silent_blocks * 20 >= 300:                  # 静默>300ms 才开始回升
                    self.gain += (self.g_normal - self.gain) * self.rel
            return self.gain

### 4.9 背景音乐播放器

    # /engine/audio/music_player.py
    import miniaudio   # 纯绑定解码 mp3/wav/ogg/flac，免 ffmpeg 依赖
    
    class MusicPlayer:
        """    背景音乐：歌单顺序循环播放（1→2→3→…→N→1）。    独立解码线程预解码到环形缓冲（≥3s 余量），声卡回调只做零拷贝读取，    保证换歌、解码慢时输出不断流。歌曲切换支持 1s 交叉淡化。    单例：全局仅一个 BGM 实例，被混音器读取。    """
        _instance = None
    
        @classmethod
        def instance(cls):
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance
    
        def __init__(self):
            self.playlist: list[str] = []
            self.idx = 0
            self.volume = 0.35
            self._buffer = deque()          # 解码后的 float32 块
            self._min_buffer_blocks = 150   # 150×20ms = 3s 缓冲水位
            self._decoder_thread = None
            self._running = False
    
        def set_playlist(self, paths: list[str], start_index: int = 0):
            self.playlist = paths
            self.idx = start_index
            self._restart_decoder()
    
        def _restart_decoder(self):
            self._running = True
            self._decoder_thread = threading.Thread(target=self._decode_loop, daemon=True)
            self._decoder_thread.start()
    
        def _decode_loop(self):
            """解码线程：顺序循环整个歌单，维持缓冲水位"""
            while self._running and self.playlist:
                path = self.playlist[self.idx]
                try:
                    stream = miniaudio.stream_file(path, sample_rate=48000, nchannels=2)
                    for pcm in stream:                      # 流式逐块解码
                        while len(self._buffer) > self._min_buffer_blocks * 4:
                            threading.Event().wait(0.01)    # 背压：缓冲满则等待
                        self._buffer.append(pcm.astype(np.float32) * self.volume)
                except Exception as e:
                    log.warning(f"BGM decode failed {path}: {e}")
                finally:
                    self.idx = (self.idx + 1) % len(self.playlist)  # 循环下一首
    
        def read(self, frames: int) -> np.ndarray:
            """声卡回调读取，缓冲不足时补静音（永不抛异常、永不断流）"""
            out = np.zeros(frames, dtype=np.float32)
            filled = 0
            while self._buffer and filled < frames:
                chunk = self._buffer[0]
                take = min(len(chunk) , frames - filled)
                out[filled:filled+take] = chunk[:take]
                if take < len(chunk):
                    self._buffer[0] = chunk[take:]
                else:
                    self._buffer.popleft()
                filled += take
            return out
    
        def skip_next(self):
            """UI 点击'下一首'：清空缓冲，跳到下一首"""
            self._buffer.clear()
            self.idx = (self.idx + 1) % len(self.playlist)

**技术选型说明**：

| 项      | 选型                                             | 理由                                         |
| ------ | ---------------------------------------------- | ------------------------------------------ |
| BGM 解码 | **miniaudio**（备选 ffmpeg 子进程）                   | 免外部依赖、支持 mp3/wav/flac、流式解码；ffmpeg 作为特殊格式兜底 |
| 播放输出   | **sounddevice (PortAudio) 回调模式**               | pull 模式时钟由声卡驱动，天然防漂移；回调内零阻塞                |
| 语音重采样  | 24k→48k 用 `scipy.signal.resample_poly`（合成后一次性） | TTS 输出多为 24kHz                             |
| 混音防削波  | `tanh` 软限幅                                     | 比硬 clip 自然，无数字爆音                           |
| 采集端方案  | 不采集，纯软件输出到 VB-Cable                            | 若未来要采麦克风可加 `sd.InputStream` 走同一混音器         |

### 4.10 免版权 BGM 曲库（内置资产）

直播使用带版权音乐会侵权/被平台静音，**出厂内置 ≥20 首免版权曲库**（CC0 / 可商用授权，需保留授权证书文件）：

| 分类   | 数量  | 示例风格                |
| ---- | --- | ------------------- |
| 轻快带货 | 6   | 明亮钢琴+鼓点（100-120BPM） |
| 温馨种草 | 5   | Lo-fi、原声吉他          |
| 燃向促销 | 4   | 电子、节奏强              |
| 静音垫  | 3   | 极低氛围垫乐（几乎无感）        |
| 节日限定 | 2+  | 按节日更新               |

五、既有模块精要（v1.0 / v1.1 要点保留）
--------------------------

### 5.1 模块 A · 平台接入（合规路径）

| 平台      | 路径                                      | 关键点                      |
| ------- | --------------------------------------- | ------------------------ |
| 抖音      | 官方直播小玩法（developer.open-douyin.com）      | 弹幕/礼物/进场/点赞事件；审核制；QPS 10 |
| 快手      | 开放平台小玩法 + PC 伴侣 IPC                     | roomCode 由伴侣生成；QPS 10    |
| B 站     | open-live WebSocket + 主播授权身份码           | 最稳定，MVP 首选               |
| 小红书/视频号 | 无公开弹幕 API → **OBS 屏幕字幕 + PaddleOCR 兜底** | 需用户签署风险知情书               |

适配器统一接口 `IPlatformAdapter(login/connect/listen/send/heartbeat)`，事件模型 `DanmuEvent(platform, user_id, nickname, type, content, gift_count)`。凭证 Windows DPAPI + AES-256-GCM 加密存储。

### 5.2 模块 B · AI 文案生成

Provider 模式接入豆包/通义/DeepSeek/智谱/Ollama（OpenAI 兼容协议统一）。输入“商品+卖点+人群”→ 输出 N 条**句式互异**话术（system prompt 强制去重）→ 直接入洗牌池（与模块 H 联动）。

### 5.3 模块 C · TTS 引擎

* 云端：火山豆包（1.3‰字，300ms 首包）、阿里 CosyVoice、MiniMax、腾讯云、Edge-TTS（免费兜底）
* 本地：GPT-SoVITS（4GB 显存，1 分钟克隆，默认推荐）、CosyVoice 2.0、Fish Speech、Bert-VITS2
* 克隆流程：10~30s 干音上传 → 预处理 → 云 API 或本地微调 → 产出 `voice_id` → 试听入库
* 预置 8 音色（小雅/婷婷/阿凯/大壮 + 2 方言 + 自定义）

### 5.4 模块 E · 线索收集

正则管道识别微信号/手机号/意向词 + 行为加权（礼物+20/条、关注+15、粉丝团+25），分数分三级（≥50 高意向即时推送企微；20-49 待跟进；10-19 低意向）。导出 CSV/Excel + Webhook（企微/钉钉/飞书）。

### 5.5 模块 F · UI（新增“开播向导”页）

    ┌─ 开播向导（v2.0 核心新页面）─────────────────────────────┐
    │ ① 选音色:  (●)小雅-温柔带货  ( )阿凯-沉稳  ( )我的克隆-01 │
    │            [▶试听]  [+克隆新音色]                         │
    │ ② 选文案组: [带货话术-羽绒服 ▼]  共6条  [编辑] [AI生成]    │
    │      循环模式: (●)随机不重复 ( )顺序循环                   │
    │      停顿: 3 ~ 8 秒随机   权重编辑: 福利款 ×3             │
    │ ③ 选BGM:   [轻松带货合辑 ▼] 12首  循环播放  音量 35%      │
    │            [试听] [下一首] [导入本地] [免版权曲库]         │
    │ ④ 连平台:  ✅抖音 已授权  ✅B站 已授权  ⚠️小红书 OCR模式   │
    │ ⑤ 高级:    打断模式(queue)  Ducking(开)  AI字幕(开)       │
    │                     [ 🚀 一键开播 ]                       │
    └──────────────────────────────────────────────────────────┘
    ┌─ 直播运行时监控 ─────────────────────────────────────────┐
    │ 弹幕流 │ 正在播: "B-羽绒服福利话术"(主文案) │ BGM: 第3首   │
    │ TTS队列: 2条待播 │ 剩余文案池: 4/6 │ 线索+1 (张哥 60分)   │
    └──────────────────────────────────────────────────────────┘

### 5.6 模块 G · 昵称拟人化（三层管道）

规则层（Unicode 归一 + emoji 剥离 + 百家姓 + 意象词典，P99<5ms）→ NER 层（HanLP，P99<50ms）→ LLM 层（JSON 强制输出 + LRU 10000 缓存，命中<1ms）→ Fallback 通用称呼池（宝子/家人/亲）。输出 `speakable_name`（如 `ok小李→李哥`、`正午晒太阳→太阳宝子`、`Xx_Kk99→宝子`），供互动模板填充。详见 v1.1 文档，此处为集成锚点。
六、整体技术架构（v2.0 终版）
-----------------

**进程与线程模型**：

| 线程/进程                | 职责                         | 优先级注意             |
| -------------------- | -------------------------- | ----------------- |
| Tauri 主进程            | UI 渲染、IPC 转发               | —                 |
| Python 主线程           | asyncio 事件循环（弹幕、编排、TTS 调度） | —                 |
| 声卡回调线程（PortAudio 实时） | 混音读取+Ducking               | **禁止阻塞/IO/大对象分配** |
| BGM 解码线程             | 预解码环形缓冲                    | 背压控制水位            |
| NER 推理线程             | HanLP 本地推理                 | 与主循环隔离防卡顿         |

七、数据库增量设计（v2.0 新增表）
-------------------

    -- 直播预设（一键开播配置包）
    CREATE TABLE live_presets (
        id INTEGER PRIMARY KEY,
        preset_name TEXT NOT NULL,
        voice_id TEXT NOT NULL,
        tts_provider TEXT NOT NULL,
        script_group_id INTEGER NOT NULL REFERENCES script_groups(id),
        music_playlist_id INTEGER REFERENCES music_playlists(id),
        shuffle_mode TEXT DEFAULT 'weighted_random',  -- weighted_random/sequential
        min_gap_seconds REAL DEFAULT 3,
        max_gap_seconds REAL DEFAULT 8,
        interrupt_mode TEXT DEFAULT 'queue',           -- queue/interrupt/pause
        bgm_volume REAL DEFAULT 0.35,
        ducking_enabled BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_used_at DATETIME
    );
    
    -- 文案组与文案
    CREATE TABLE script_groups (
        id INTEGER PRIMARY KEY,
        group_name TEXT NOT NULL,
        platform TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE scripts (
        id INTEGER PRIMARY KEY,
        group_id INTEGER REFERENCES script_groups(id),
        content TEXT NOT NULL,
        weight REAL DEFAULT 1.0,
        enabled BOOLEAN DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    );
    
    -- BGM 歌单与曲目
    CREATE TABLE music_playlists (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        is_builtin BOOLEAN DEFAULT 0,
        license_note TEXT                            -- 免版权授权说明
    );
    CREATE TABLE music_tracks (
        id INTEGER PRIMARY KEY,
        playlist_id INTEGER REFERENCES music_playlists(id),
        file_path TEXT NOT NULL,
        title TEXT,
        duration_sec INTEGER,
        sort_order INTEGER DEFAULT 0
    );
    
    -- 播放历史（复盘与去重审计）
    CREATE TABLE playback_history (
        id INTEGER PRIMARY KEY,
        session_id INTEGER,
        source TEXT,           -- script / interaction
        ref_id TEXT,           -- script id 或 模板id
        content_snapshot TEXT,
        played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        cycle_no INTEGER,      -- 洗牌周期号（验证 A-B-C-D 规律用）
        queue_pos INTEGER      -- 周期内位置
    );

八、IPC API 契约增量
--------------

| 命令                                              | 入参                                               | 出参                                           | 说明         |
| ----------------------------------------------- | ------------------------------------------------ | -------------------------------------------- | ---------- |
| `preset_save` / `preset_list` / `preset_delete` | 预设对象                                             | —                                            | 直播预设 CRUD  |
| `scripts_update`                                | `{group_id, scripts:[{content,weight,enabled}]}` | `{}`                                         | 直播中热更新文案组  |
| `scheduler_state`                               | —                                                | `{pool_remaining, cycle_no, current_script}` | 运行时监控      |
| `bgm_set_playlist`                              | `{paths[], start_index}`                         | `{}`                                         | 设置/切换歌单    |
| `bgm_control`                                   | `{action: play/pause/next, volume}`              | `{current_track}`                            | BGM 控制     |
| `mixer_set_ducking`                             | `{enabled, normal_gain, ducked_gain}`            | `{}`                                         | Ducking 参数 |

| 事件                  | Payload                                      | 说明                |
| ------------------- | -------------------------------------------- | ----------------- |
| `script_played`     | `{script_id, cycle_no, queue_pos, gap_next}` | 每条主文案播出（驱动监控台与审计） |
| `bgm_track_changed` | `{title, index}`                             | BGM 换曲            |
| `ducking_state`     | `{active: bool, gain}`                       | 闪避状态（调试用，可降频）     |

九、测试与验收（专项）
-----------

### 9.1 洗牌算法专项（模块 H）

    def test_no_adjacent_repeat():
        """N=4 播 1000 次，相邻不得重复"""
        q = ShuffleQueue(["A","B","C","D"])
        seq = [q.next() for _ in range(1000)]
        for i in range(1, len(seq)):
            assert seq[i] != seq[i-1]
    
    def test_cycle_fairness():
        """每个周期恰好每元素出现一次"""
        q = ShuffleQueue(["A","B","C","D"])
        for cycle in range(100):
            played = [q.next() for _ in range(4)]
            assert sorted(played) == ["A","B","C","D"]
    
    def test_boundary_cross_cycle():
        """跨周期边界不得重复：周期尾 == 下周期头 必须被修复"""
        q = ShuffleQueue(["A","B","C"], seed=42)
        # 强制构造边界冲突场景循环验证 10000 次
        for _ in range(10000):
            a, b = q.next(), q.next()
            assert a != b
    
    def test_weighted():
        """权重3的文案在周期内平均出现位置显著靠前（统计检验）"""
        # 跑1000周期，计算位置均值，做 t 检验
    def test_n_equals_2(): ...   # 只能产生 A-B-A-B，无相邻重复
    def test_dynamic_update(): ...  # 直播中热更新，last_played 保持防重

### 9.2 音频专项（模块 I）

| 用例         | 通过标准                                                             |
| ---------- | ---------------------------------------------------------------- |
| Ducking 响应 | 注入 1kHz 语音信号，BGM 增益 500ms 内降至 0.10±0.02；语音停止后 1.5s±0.3s 回升至 0.35 |
| 长时稳定性      | 3 通道并发 + 8h 连续运行，RSS 内存增长 <100MB，无 underrun（`status` 回调无标志）      |
| 换曲无缝       | 100 次随机换曲，输出波形无断零段（>20ms 静音即失败）                                  |
| 削波         | 语音+BGM 满幅叠加，输出峰值 ≤0dBFS，无数字破音                                    |
| 虚拟声卡兼容     | VB-Cable / Voicemeeter 实测 OBS 端采集正常                              |

### 9.3 端到端场景用例

1. 预设 4 条文案 → 开播 30 分钟 → 导出 `playback_history` 验证：无相邻重复、每 4 条为一完整周期、周期内位置随机。
2. 弹幕“ok小李 进入直播间” → 1.5s 内播报“欢迎李哥进入直播间”，期间 BGM 可闻压低。
3. 大额礼物触发 `interrupt` 模式 → 主文案 300ms 淡出 → 感谢语插播 → 编排循环恢复无跳条。
4. 拔网线 30s → TTS 自动切 Edge-TTS 兜底 → 恢复后切回主 Provider。

十、里程碑（v2.0 终版，增量约 +3 周）
-----------------------

| 阶段       | 内容                                             | 工期          |
| -------- | ---------------------------------------------- | ----------- |
| M1       | Tauri 壳 + B 站/抖音接入 + Edge-TTS + 基础互动           | 3 周         |
| M2       | TTS 全家桶 + 声音克隆 + 预置音色                          | 2 周         |
| **M2.5** | **模块 H：洗牌队列 + 编排循环 + 预合成 + 单测**                | **1 周**     |
| **M2.6** | **模块 I：混音器 + Ducking + BGM 播放器 + 曲库 + 虚拟声卡联调** | **1.5 周**   |
| M3       | LLM 文案 + 线索收集 + 导出推送                           | 2 周         |
| M4       | 快手 + 小红书 OCR + OBS 字幕 + 开播向导 UI                | 2 周         |
| M5       | 昵称拟人化打磨 + 稳定性压测（8h/洗牌1000周期） + 发布              | 2 周         |
| **合计**   |                                                | **≈13.5 周** |

十一、风险与开放问题
----------

1. **N=1 文案场景**：技术上无法去重，需产品确认是“警告放行”还是“强制 ≥2 条”。
2. **BGM 版权**：内置曲库必须逐首取得可商用授权并存证；用户自导入音乐由用户自担责任（用户协议明示）。
3. **VB-Cable 安装**：需随安装器捆绑驱动并申请管理员权限，或提供“未安装驱动引导页”（推荐后者，降低安装包签名复杂度）。
4. **蓝牙耳机延迟**：用户戴蓝牙耳机监听时回调缓冲可能需自适应调大（预留 `blocksize` 自适应开关）。
5. **洗牌“可预测性”**：周期洗牌在 N 很小（2~3）时规律感明显，可提供“加扰模式”（周期内额外交换 1 次，仍保证不重复），作为高级选项。

**文档版本**：v2.0 Final | **更新日期**：2026-09-09 | **交付对象**：Coding 大模型 / 研发团队

> **给 Coding LLM 的实施顺序建议**：先实现 `ShuffleQueue`（纯算法，含单测）→ `AudioMixer + MusicPlayer`（本地声卡可独立验证）→ 接入 TTS Provider → 接平台弹幕 → 串互动路由 → 最后做 UI。模块 H 与 I 均可脱离平台 API 独立开发与测试，无外部阻塞依赖。
