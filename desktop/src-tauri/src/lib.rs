use std::sync::{Arc, Mutex};
use tauri_plugin_shell::{process::CommandEvent, ShellExt};

#[derive(Clone, serde::Serialize)]
struct ApiConfig {
    base_url: String,
    secret: String,
}

type SharedConfig = Arc<Mutex<Option<ApiConfig>>>;

#[tauri::command]
fn api_config(state: tauri::State<'_, SharedConfig>) -> Result<ApiConfig, String> {
    state
        .lock()
        .map_err(|_| "sidecar state unavailable".to_string())?
        .clone()
        .ok_or_else(|| "inference sidecar is not ready".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let config: SharedConfig = Arc::new(Mutex::new(None));
    tauri::Builder::default()
        .manage(config.clone())
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            let secret = uuid_like_secret();
            let (mut rx, _child) = app
                .shell()
                .sidecar("exan-inference")
                .map_err(|error| error.to_string())?
                .env("STARTUP_SECRET", &secret)
                .env("LOG_ROOT", app.path().app_data_dir()?.join("logs"))
                .spawn()
                .map_err(|error| error.to_string())?;
            let state = config.clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = rx.recv().await {
                    if let CommandEvent::Stdout(line) = event {
                        if let Some(port) = line.strip_prefix("EXAN_PORT=") {
                            if let Ok(mut current) = state.lock() {
                                *current = Some(ApiConfig {
                                    base_url: format!("http://127.0.0.1:{port}/api"),
                                    secret: secret.clone(),
                                });
                            }
                            break;
                        }
                    }
                }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![api_config])
        .run(tauri::generate_context!())
        .expect("error while running Exan desktop");
}

fn uuid_like_secret() -> String {
    format!("{:x}{:x}", std::process::id(), std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos())
}
