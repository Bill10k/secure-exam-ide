// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::Manager;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[tauri::command]
fn get_cli_args() -> Vec<String> {
    std::env::args().collect()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_decorations(false);
                let _ = window.set_resizable(false);
                let _ = window.set_always_on_top(true);

                if let Ok(Some(monitor)) = window.current_monitor() {
                    let monitor_pos = monitor.position();
                    let monitor_size = monitor.size();
                    let _ = window.set_position(tauri::Position::Physical(tauri::PhysicalPosition {
                        x: monitor_pos.x,
                        y: monitor_pos.y,
                    }));
                    let _ = window.set_size(tauri::Size::Physical(tauri::PhysicalSize {
                        width: monitor_size.width,
                        height: monitor_size.height,
                    }));
                }

                let _ = window.maximize();
                let _ = window.set_fullscreen(true);
            }

            Ok(())
        })
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![greet, get_cli_args])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
