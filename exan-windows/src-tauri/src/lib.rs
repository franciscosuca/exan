mod sidecar;

use std::path::PathBuf;

use sidecar::{SidecarStatus, Supervisor};
use tauri::{AppHandle, RunEvent, State};
use tauri_plugin_dialog::DialogExt;
use tauri_plugin_opener::OpenerExt;

/// Links the UI may open in the default browser. Anything else is refused.
fn help_url(topic: &str) -> Option<&'static str> {
    match topic {
        "ollama" => Some("https://ollama.com/download"),
        "lmstudio" => Some("https://lmstudio.ai/download"),
        "models" => Some("https://huggingface.co/blog/ocr-open-models"),
        _ => None,
    }
}

/// Keeps file names produced by the UI plain (no folders, no control characters).
fn clean_file_name(name: &str) -> String {
    let cleaned: String = name
        .chars()
        .map(|c| {
            if c.is_control() || "/\\:*?\"<>|".contains(c) {
                '_'
            } else {
                c
            }
        })
        .collect();
    let cleaned = cleaned.trim().trim_start_matches('.').to_string();
    if cleaned.is_empty() {
        "exan-export.csv".into()
    } else {
        cleaned
    }
}

#[tauri::command]
fn engine_status(supervisor: State<'_, Supervisor>) -> SidecarStatus {
    supervisor.status()
}

#[tauri::command]
async fn restart_engine(app: AppHandle) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || sidecar::start(&app))
        .await
        .map_err(|err| err.to_string())?
}

#[tauri::command]
async fn save_text_file(
    app: AppHandle,
    file_name: String,
    contents: String,
) -> Result<Option<String>, String> {
    let name = clean_file_name(&file_name);
    let path: Option<PathBuf> = tauri::async_runtime::spawn_blocking(move || {
        app.dialog()
            .file()
            .set_file_name(name)
            .add_filter("CSV", &["csv"])
            .blocking_save_file()
            .and_then(|file| file.into_path().ok())
    })
    .await
    .map_err(|err| err.to_string())?;
    let Some(path) = path else { return Ok(None) };
    std::fs::write(&path, contents.as_bytes())
        .map_err(|err| format!("{}: {err}", path.display()))?;
    Ok(Some(path.display().to_string()))
}

#[tauri::command]
fn open_help(app: AppHandle, topic: String) -> Result<(), String> {
    let url = help_url(&topic).ok_or_else(|| "unknown link".to_string())?;
    app.opener()
        .open_url(url, None::<&str>)
        .map_err(|err| err.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Supervisor::default())
        .invoke_handler(tauri::generate_handler![
            engine_status,
            restart_engine,
            save_text_file,
            open_help
        ])
        .setup(|app| {
            let handle = app.handle().clone();
            tauri::async_runtime::spawn_blocking(move || {
                if let Err(err) = sidecar::start(&handle) {
                    eprintln!("exan: {err}");
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the Exan app");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            sidecar::stop_current(handle, true);
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_known_help_links_open() {
        assert_eq!(help_url("ollama"), Some("https://ollama.com/download"));
        assert!(help_url("https://example.com").is_none());
    }

    #[test]
    fn file_names_are_cleaned() {
        assert_eq!(clean_file_name("../../etc/passwd"), "_.._etc_passwd");
        assert_eq!(
            clean_file_name("Ergebnisse: Klasse 7b.csv"),
            "Ergebnisse_ Klasse 7b.csv"
        );
        assert_eq!(clean_file_name("  "), "exan-export.csv");
    }
}
