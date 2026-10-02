//! Supervises the local Exan engine (the frozen Python sidecar).
//!
//! Contract (see `sidecar/exan_sidecar/__main__.py`):
//! * the shell passes a random secret, the data and log directories through the environment,
//! * the engine binds `127.0.0.1` on a free port and prints `EXAN_PORT=<port>` on stdout,
//! * every API call must send that secret as a bearer token (Authorization header),
//! * writing `shutdown` to stdin (or closing stdin) stops the engine.

use std::collections::VecDeque;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

pub const STATUS_EVENT: &str = "sidecar-status";
const SIDECAR_NAME: &str = "exan-sidecar";
const STARTUP_TIMEOUT: Duration = Duration::from_secs(120);
const SHUTDOWN_GRACE: Duration = Duration::from_secs(4);
const CRASH_WINDOW: Duration = Duration::from_secs(120);
const MAX_AUTO_RESTARTS: usize = 3;
const STDERR_LINES: usize = 40;

#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum EngineState {
    #[default]
    Starting,
    Ready,
    Failed,
    Stopped,
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct SidecarStatus {
    pub state: EngineState,
    pub port: Option<u16>,
    pub token: Option<String>,
    pub error: Option<String>,
    pub restarts: u32,
}

#[derive(Default)]
struct Inner {
    status: SidecarStatus,
    child: Option<CommandChild>,
    generation: u64,
    alive: bool,
    shutting_down: bool,
    crashes: VecDeque<Instant>,
    stderr: VecDeque<String>,
}

#[derive(Default)]
pub struct Supervisor {
    inner: Mutex<Inner>,
}

impl Supervisor {
    fn lock(&self) -> std::sync::MutexGuard<'_, Inner> {
        self.inner
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }

    pub fn status(&self) -> SidecarStatus {
        self.lock().status.clone()
    }
}

/// Parses the handshake line printed by the engine once it listens.
pub fn parse_port_line(line: &str) -> Option<u16> {
    line.trim()
        .strip_prefix("EXAN_PORT=")?
        .trim()
        .parse::<u16>()
        .ok()
        .filter(|port| *port != 0)
}

/// A fresh 256-bit secret, hex encoded, for each engine launch.
pub fn new_secret() -> Result<String, String> {
    let mut bytes = [0u8; 32];
    getrandom::fill(&mut bytes).map_err(|err| format!("no secure random source: {err}"))?;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}

/// Remembers the crash and tells whether another automatic restart is allowed.
fn allow_restart(crashes: &mut VecDeque<Instant>, now: Instant) -> bool {
    while crashes
        .front()
        .is_some_and(|t| now.duration_since(*t) > CRASH_WINDOW)
    {
        crashes.pop_front();
    }
    crashes.push_back(now);
    crashes.len() <= MAX_AUTO_RESTARTS
}

fn emit<R: Runtime>(app: &AppHandle<R>, status: &SidecarStatus) {
    if let Err(err) = app.emit(STATUS_EVENT, status) {
        eprintln!("exan: cannot emit engine status: {err}");
    }
}

fn update<R: Runtime>(app: &AppHandle<R>, generation: u64, change: impl FnOnce(&mut Inner)) {
    let supervisor = app.state::<Supervisor>();
    let snapshot = {
        let mut inner = supervisor.lock();
        if inner.generation != generation {
            return;
        }
        change(&mut inner);
        inner.status.clone()
    };
    emit(app, &snapshot);
}

/// Starts a new engine process (stopping a previous one first).
pub fn start<R: Runtime>(app: &AppHandle<R>) -> Result<(), String> {
    stop_current(app, false);
    let secret = new_secret()?;
    let paths = app.path();
    let data_dir = paths
        .app_data_dir()
        .map_err(|err| format!("no data directory: {err}"))?;
    let log_dir = paths
        .app_log_dir()
        .map_err(|err| format!("no log directory: {err}"))?;
    let _ = std::fs::create_dir_all(&data_dir);
    let _ = std::fs::create_dir_all(&log_dir);

    let spawned = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|err| format!("engine binary not found: {err}"))
        .and_then(|command| {
            command
                .env("EXAN_SECRET", &secret)
                .env("EXAN_DATA_DIR", &data_dir)
                .env("EXAN_LOG_DIR", &log_dir)
                .env("EXAN_WATCH_STDIN", "1")
                .spawn()
                .map_err(|err| format!("the engine could not be started: {err}"))
        });

    let supervisor = app.state::<Supervisor>();
    let (generation, snapshot, rx) = {
        let mut inner = supervisor.lock();
        inner.generation += 1;
        inner.shutting_down = false;
        inner.stderr.clear();
        let restarts = inner.status.restarts;
        match spawned {
            Ok((rx, child)) => {
                inner.child = Some(child);
                inner.alive = true;
                inner.status = SidecarStatus {
                    state: EngineState::Starting,
                    restarts,
                    ..Default::default()
                };
                (inner.generation, inner.status.clone(), Some(rx))
            }
            Err(err) => {
                inner.child = None;
                inner.alive = false;
                inner.status = SidecarStatus {
                    state: EngineState::Failed,
                    error: Some(err),
                    restarts,
                    ..Default::default()
                };
                (inner.generation, inner.status.clone(), None)
            }
        }
    };
    emit(app, &snapshot);
    let Some(mut rx) = rx else {
        return Err(snapshot.error.unwrap_or_default());
    };

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        let mut exit_code: Option<i32> = None;
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    if let Some(port) = parse_port_line(&line) {
                        let token = secret.clone();
                        update(&handle, generation, |inner| {
                            inner.status.state = EngineState::Ready;
                            inner.status.port = Some(port);
                            inner.status.token = Some(token);
                            inner.status.error = None;
                        });
                    }
                }
                CommandEvent::Stderr(bytes) => {
                    let line = String::from_utf8_lossy(&bytes).trim_end().to_string();
                    if cfg!(debug_assertions) {
                        eprintln!("[engine] {line}");
                    }
                    let supervisor = handle.state::<Supervisor>();
                    let mut inner = supervisor.lock();
                    if inner.generation == generation {
                        inner.stderr.push_back(line);
                        while inner.stderr.len() > STDERR_LINES {
                            inner.stderr.pop_front();
                        }
                    }
                }
                CommandEvent::Error(err) => eprintln!("exan: engine pipe error: {err}"),
                CommandEvent::Terminated(payload) => {
                    exit_code = payload.code;
                    break;
                }
                _ => {}
            }
        }
        on_exit(&handle, generation, exit_code);
    });

    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        tokio::time::sleep(STARTUP_TIMEOUT).await;
        let child = {
            let supervisor = handle.state::<Supervisor>();
            let mut inner = supervisor.lock();
            if inner.generation != generation || inner.status.state != EngineState::Starting {
                return;
            }
            inner.status.state = EngineState::Failed;
            inner.status.error = Some("The engine did not start in time.".into());
            inner.child.take()
        };
        if let Some(child) = child {
            let _ = child.kill();
        }
        let snapshot = handle.state::<Supervisor>().status();
        emit(&handle, &snapshot);
    });
    Ok(())
}

fn on_exit<R: Runtime>(app: &AppHandle<R>, generation: u64, code: Option<i32>) {
    let supervisor = app.state::<Supervisor>();
    let restart = {
        let mut inner = supervisor.lock();
        if inner.generation != generation {
            return;
        }
        inner.alive = false;
        inner.child = None;
        if inner.shutting_down {
            inner.status = SidecarStatus {
                state: EngineState::Stopped,
                restarts: inner.status.restarts,
                ..Default::default()
            };
            false
        } else if inner.status.state == EngineState::Failed {
            false
        } else if allow_restart(&mut inner.crashes, Instant::now()) {
            inner.status.restarts += 1;
            inner.status.state = EngineState::Starting;
            inner.status.port = None;
            inner.status.token = None;
            true
        } else {
            let details: Vec<String> = inner.stderr.iter().rev().take(6).rev().cloned().collect();
            let code = code.map_or_else(|| "a signal".to_string(), |c| format!("code {c}"));
            inner.status.state = EngineState::Failed;
            inner.status.port = None;
            inner.status.token = None;
            inner.status.error = Some(
                format!(
                    "The engine stopped unexpectedly ({code}). {}",
                    details.join(" | ")
                )
                .trim()
                .to_string(),
            );
            false
        }
    };
    emit(app, &supervisor.status());
    if restart {
        let handle = app.clone();
        tauri::async_runtime::spawn(async move {
            tokio::time::sleep(Duration::from_secs(1)).await;
            if let Err(err) = start(&handle) {
                eprintln!("exan: engine restart failed: {err}");
            }
        });
    }
}

/// Asks the current engine to stop. With `wait`, blocks until it exited (or kills it after a grace period).
pub fn stop_current<R: Runtime>(app: &AppHandle<R>, wait: bool) {
    let supervisor = app.state::<Supervisor>();
    let (child, generation) = {
        let mut inner = supervisor.lock();
        inner.shutting_down = true;
        (inner.child.take(), inner.generation)
    };
    let Some(mut child) = child else { return };
    let graceful = child.write(b"shutdown\n").is_ok();
    if !wait {
        // Kill it later if it ignores the request; the new engine uses another port anyway.
        tauri::async_runtime::spawn(async move {
            tokio::time::sleep(SHUTDOWN_GRACE).await;
            let _ = child.kill();
        });
        return;
    }
    if graceful {
        let deadline = Instant::now() + SHUTDOWN_GRACE;
        while Instant::now() < deadline {
            {
                let inner = supervisor.lock();
                if inner.generation != generation || !inner.alive {
                    return;
                }
            }
            std::thread::sleep(Duration::from_millis(50));
        }
    }
    let _ = child.kill();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn handshake_line_is_parsed() {
        assert_eq!(parse_port_line("EXAN_PORT=51234\n"), Some(51234));
        assert_eq!(parse_port_line("  EXAN_PORT= 8765\r\n"), Some(8765));
        assert_eq!(parse_port_line("EXAN_PORT=0"), None);
        assert_eq!(parse_port_line("EXAN_PORT=99999"), None);
        assert_eq!(parse_port_line("INFO listening"), None);
    }

    #[test]
    fn secrets_are_random_hex() {
        let a = new_secret().unwrap();
        let b = new_secret().unwrap();
        assert_eq!(a.len(), 64);
        assert!(a.chars().all(|c| c.is_ascii_hexdigit()));
        assert_ne!(a, b);
    }

    #[test]
    fn restarts_are_limited_within_the_window() {
        let mut crashes = VecDeque::new();
        let now = Instant::now();
        assert!(allow_restart(&mut crashes, now));
        assert!(allow_restart(&mut crashes, now));
        assert!(allow_restart(&mut crashes, now));
        assert!(!allow_restart(&mut crashes, now));
        assert!(allow_restart(
            &mut crashes,
            now + CRASH_WINDOW + Duration::from_secs(1)
        ));
    }
}
