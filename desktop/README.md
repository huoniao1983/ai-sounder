# AISounder desktop

Tauri 2 + React/TypeScript 壳，管理 Python `engine/` sidecar 并展示直播运行态。

```powershell
cd desktop
npm install
npm run tauri dev
```

当前开发机 Rust 位于 `D:\app\cargo`；若新终端找不到 `cargo`，先执行：

```powershell
$env:Path = 'D:\app\cargo\bin;' + $env:Path
$env:CARGO_HOME = 'D:\app\cargo'
$env:RUSTUP_HOME = 'D:\app\rustup'
```

纯前端预览也可运行：

```powershell
npm install
npm run dev
```

开发预览还需要在仓库根目录启动本地能力服务（真实音频、TTS 与上传接口）：

```powershell
python -m engine.api_server --host 127.0.0.1 --port 8765
```

F5-TTS 与 OpenVoice V2 属于本地推理引擎，按需安装后才可用于自定义音色合成，接入说明见仓库根目录 `docs/local-tts.md`。
