use std::sync::Mutex;

use tauri::{Emitter, Manager, State};
use log::{info, warn, error};
use tauri_plugin_log::{Builder, Target};

#[derive(Default)]
struct DeepLinkState {
    url: Mutex<Option<String>>,
}

// ----------------------
// COMMAND: frontend can fetch last link
// ----------------------
#[tauri::command]
fn get_deep_link(state: State<DeepLinkState>) -> Option<String> {
    let value = state.url.lock().unwrap().clone();
    info!("📦 get_deep_link called → {:?}", value);
    value
}

// ----------------------
// Helper: save + emit
// ----------------------
fn save_and_emit(app: &tauri::AppHandle, state: &DeepLinkState, url: String) {
    info!("💾 Saving deep link: {}", url);

    *state.url.lock().unwrap() = Some(url.clone());

    if let Some(window) = app.get_webview_window("main") {
        let _ = window.emit("deep-link", url.clone());
        info!("📡 Emitted deep-link event to frontend");
    } else {
        error!("❌ Main window not found");
    }
}

// ----------------------
// ENTRY POINT
// ----------------------
pub fn run() {
    tauri::Builder::default()
        .manage(DeepLinkState::default())

        // ----------------------
        // LOGGING PLUGIN (FIXED)
        // ----------------------
        .plugin(
    Builder::default()
        .targets([
            Target::Stdout,
            Target::Webview,
            Target::LogDir,
        ])
        .level(log::LevelFilter::Info)
        .build(),
)

        // ----------------------
        // DEEP LINK PLUGIN
        // ----------------------
        .plugin(tauri_plugin_deep_link::init())

        // ----------------------
        // SINGLE INSTANCE PLUGIN
        // ----------------------
        .plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            info!("🔁 SINGLE INSTANCE TRIGGERED: {:?}", argv);

            let state = app.state::<DeepLinkState>();

            if let Some(url) = argv.iter().find(|a| a.starts_with("proctoride://")) {
                info!("🔥 Deep link from single instance: {}", url);

                save_and_emit(app, &state, url.clone());

                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.set_focus();
                    info!("🎯 Focused main window");
                }
            } else {
                warn!("⚠️ No deep link found in single instance args");
            }
        }))

        // ----------------------
        // SETUP (cold start)
        // ----------------------
        .setup(|app| {
            let state = app.state::<DeepLinkState>();

            let args: Vec<String> = std::env::args().collect();
            info!("🚀 APP START ARGS: {:?}", args);

            if let Some(url) = args.iter().find(|a| a.starts_with("proctoride://")) {
                info!("🔥 FOUND DEEP LINK ON START: {}", url);

                save_and_emit(&app.handle(), &state, url.clone());
            } else {
                info!("ℹ️ No deep link found on startup");
            }

            Ok(())
        })

        // ----------------------
        // COMMAND HANDLER
        // ----------------------
        .invoke_handler(tauri::generate_handler![get_deep_link])

        .run(tauri::generate_context!())
        .expect("error running app");
}