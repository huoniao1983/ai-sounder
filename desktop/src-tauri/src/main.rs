use std::net::TcpStream;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::Manager;

struct EngineProcess(Mutex<Option<Child>>);

fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(|path| path.parent())
        .expect("workspace root should sit two levels above src-tauri")
        .to_path_buf()
}

fn data_dir() -> PathBuf {
    let base = std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(std::env::temp_dir);
    base.join("AISounder")
}

fn engine_online() -> bool {
    TcpStream::connect_timeout(
        &"127.0.0.1:8765".parse().expect("valid engine address"),
        Duration::from_millis(150),
    )
    .is_ok()
}

fn spawn_engine() -> Option<Child> {
    if engine_online() {
        return None;
    }
    let exe_dir = std::env::current_exe().ok()?.parent()?.to_path_buf();
    let bundled = exe_dir.join("aisounder-engine.exe");
    let bundled_targeted = exe_dir.join("aisounder-engine-x86_64-pc-windows-msvc.exe");
    let resource_dir = if bundled.exists() || bundled_targeted.exists() {
        exe_dir.clone()
    } else {
        workspace_root()
    };
    let app_data_dir = data_dir();
    let _ = std::fs::create_dir_all(&app_data_dir);
    let mut command = if bundled.exists() {
        Command::new(bundled)
    } else if bundled_targeted.exists() {
        Command::new(bundled_targeted)
    } else {
        let mut python = Command::new("python");
        python
            .args(["-m", "engine.api_server", "--host", "127.0.0.1", "--port", "8765"])
            .current_dir(workspace_root());
        python
    };
    command.env("AISOUNDER_RESOURCE_DIR", &resource_dir);
    command.env("AISOUNDER_DATA_DIR", &app_data_dir);
    command
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .ok()
}

fn stop_engine(state: &EngineProcess) {
    if let Some(mut child) = state.0.lock().expect("engine process lock").take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

#[tauri::command]
fn engine_status() -> Result<bool, String> {
    Ok(engine_online())
}

fn main() {
    let app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![engine_status])
        .setup(|app| {
            let child = spawn_engine();
            app.manage(EngineProcess(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to run AISounder");

    app.run(|app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            if let Some(state) = app_handle.try_state::<EngineProcess>() {
                stop_engine(&state);
            }
        }
    });
}
