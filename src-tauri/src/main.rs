#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Arc, Mutex};
use std::time::Duration;
use tauri::Manager;
mod storage;
#[cfg(windows)]
use std::os::windows::process::CommandExt;
#[cfg(windows)]
use std::os::windows::io::{AsRawHandle, FromRawHandle, OwnedHandle};

#[derive(Clone, Serialize)]
struct ConnectionInfo { port: u16, token: String }
struct Backend {
    child: Mutex<Option<Child>>,
    connection: ConnectionInfo,
    #[cfg(windows)]
    _job: OwnedHandle,
}
enum Startup { Pending, Ready(Backend), Failed(String) }
struct BackendSlot(Arc<Mutex<Startup>>);

const PREFERENCE_KEYS: [&str; 5] = ["calix-digits","calix-workers","calix-language","calix-theme","calix-notebook-zoom"];

fn preference_directory(app: &tauri::AppHandle) -> Result<PathBuf,String> {
    if let Some(profile) = std::env::var_os("WEBVIEW2_USER_DATA_FOLDER") { return Ok(PathBuf::from(profile)); }
    app.path().app_config_dir().map_err(|e|e.to_string())
}

#[tauri::command]
fn read_preferences(app: tauri::AppHandle) -> Result<std::collections::BTreeMap<String,String>,String> {
    let path = preference_directory(&app)?.join("preferences.json");
    if !path.exists() { return Ok(Default::default()); }
    let content = std::fs::read_to_string(path).map_err(|e|e.to_string())?;
    serde_json::from_str(&content).map_err(|e|e.to_string())
}

#[tauri::command]
fn write_preferences(app: tauri::AppHandle, preferences: std::collections::BTreeMap<String,String>) -> Result<(),String> {
    if preferences.iter().any(|(key,value)| !PREFERENCE_KEYS.contains(&key.as_str()) || value.len()>64) {
        return Err("Invalid preference key or value".into());
    }
    let directory = preference_directory(&app)?;
    std::fs::create_dir_all(&directory).map_err(|e|e.to_string())?;
    let path = directory.join("preferences.json");
    let content = serde_json::to_vec(&preferences).map_err(|e|e.to_string())?;
    storage::atomic_write(&path, &content)
}

#[tauri::command]
fn write_recovery(app: tauri::AppHandle, content: String, checkpoint: bool) -> Result<(), String> {
    let value: serde_json::Value = serde_json::from_str(&content).map_err(|e| e.to_string())?;
    if value["version"] != 1 || !value["documents"].is_array() { return Err("Invalid recovery workspace".into()); }
    storage::snapshot(&preference_directory(&app)?.join("recovery"), &content, checkpoint)
}

#[tauri::command]
fn list_recovery(app: tauri::AppHandle) -> Result<Vec<storage::Revision>, String> {
    storage::list(&preference_directory(&app)?.join("recovery"))
}

#[tauri::command]
fn read_recovery(app: tauri::AppHandle, id: String) -> Result<String, String> {
    storage::read(&preference_directory(&app)?.join("recovery"), &id)
}

fn file_history(path: &str) -> Result<PathBuf, String> {
    let target = notebook_file(path)?;
    Ok(target.parent().ok_or("Missing parent directory")?.join(".calix-history").join(target.file_name().ok_or("Missing file name")?))
}

#[tauri::command]
fn list_file_versions(path: String) -> Result<Vec<storage::Revision>, String> { storage::list(&file_history(&path)?) }

#[tauri::command]
fn read_file_version(path: String, id: String) -> Result<String, String> { storage::read(&file_history(&path)?, &id) }

#[cfg(windows)]
fn own_backend(child: &Child) -> Result<OwnedHandle, String> {
    use windows_sys::Win32::System::JobObjects::*;
    unsafe {
        let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if handle.is_null() { return Err(std::io::Error::last_os_error().to_string()); }
        let job = OwnedHandle::from_raw_handle(handle);
        let mut limits: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK;
        if SetInformationJobObject(handle, JobObjectExtendedLimitInformation, &limits as *const _ as *const _, std::mem::size_of_val(&limits) as u32) == 0
            || AssignProcessToJobObject(handle, child.as_raw_handle()) == 0 {
            return Err(std::io::Error::last_os_error().to_string());
        }
        Ok(job)
    }
}

#[tauri::command]
async fn connection_info(state: tauri::State<'_, BackendSlot>) -> Result<ConnectionInfo, String> {
    let slot = state.0.clone();
    tauri::async_runtime::spawn_blocking(move || {
        for _ in 0..400 {
            {
                let startup = slot.lock().map_err(|e| e.to_string())?;
                match &*startup {
                    Startup::Ready(backend) => return Ok(backend.connection.clone()),
                    Startup::Failed(error) => return Err(error.clone()),
                    Startup::Pending => {}
                }
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        Err("Calculation service startup timed out".into())
    }).await.map_err(|e| e.to_string())?
}

#[tauri::command]
fn startup_notebook() -> Result<Option<(String, String)>, String> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if let Some(path) = notebook_argument(&args)? {
        let target = notebook_file(path)?;
        return Ok(Some((path.to_string(), read_notebook(target.to_string_lossy().into())?)));
    }
    Ok(None)
}

fn notebook_argument(args: &[String]) -> Result<Option<&str>, String> {
    if let Some(index) = args.iter().position(|arg| arg == "--notebook") {
        return args.get(index + 1).map(|path| Some(path.as_str())).ok_or("Missing notebook path".into());
    }
    Ok(args.first().filter(|arg| !arg.starts_with('-')).map(String::as_str))
}

#[cfg(test)]
mod startup_tests {
    use super::notebook_argument;
    #[test]
    fn notebook_path_from_shell_or_cli() {
        let shell = vec!["C:\\Users\\Student\\ring notebook.cixnb".into()];
        assert_eq!(notebook_argument(&shell).unwrap(), Some(shell[0].as_str()));
        let cli = vec!["--notebook".into(), shell[0].clone()];
        assert_eq!(notebook_argument(&cli).unwrap(), Some(shell[0].as_str()));
        assert!(notebook_argument(&["--notebook".into()]).is_err());
        assert_eq!(notebook_argument(&[]).unwrap(), None);
        assert_eq!(notebook_argument(&["--other".into()]).unwrap(), None);
    }
}

#[tauri::command]
fn read_notebook(path: String) -> Result<String, String> {
    let metadata = std::fs::metadata(&path).map_err(|e| e.to_string())?;
    if metadata.len() > 10_000_000 { return Err("Notebook exceeds 10 MB".into()); }
    std::fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_notebook(path: String, content: String) -> Result<(), String> {
    if content.len() > 10_000_000 { return Err("Notebook exceeds 10 MB".into()); }
    let target = PathBuf::from(path);
    let extension = target.extension().and_then(|x| x.to_str()).unwrap_or("");
    if !extension.eq_ignore_ascii_case("cixnb") && !extension.eq_ignore_ascii_case("clxnb") && !extension.eq_ignore_ascii_case("calix") { return Err("Use the .cixnb file extension".into()); }
    if target.exists() {
        let previous = read_notebook(target.to_string_lossy().into())?;
        let history = target.parent().ok_or("Missing parent directory")?.join(".calix-history")
            .join(target.file_name().ok_or("Missing file name")?);
        storage::snapshot(&history, &previous, true)?;
    }
    storage::atomic_write(&target, content.as_bytes())
}

fn notebook_file(path: &str) -> Result<PathBuf, String> {
    let target = PathBuf::from(path);
    if !target.is_absolute() { return Err("Notebook path must be absolute".into()); }
    let extension = target.extension().and_then(|x| x.to_str()).unwrap_or("");
    if !extension.eq_ignore_ascii_case("cixnb") && !extension.eq_ignore_ascii_case("clxnb") && !extension.eq_ignore_ascii_case("calix") {
        return Err("Only .cixnb, .clxnb and .calix notebook files are supported".into());
    }
    let metadata = std::fs::symlink_metadata(&target).map_err(|e| e.to_string())?;
    if !metadata.file_type().is_file() { return Err("Notebook must be a regular file".into()); }
    Ok(target)
}

#[tauri::command]
fn delete_notebook(path: String) -> Result<(), String> {
    let target = notebook_file(&path)?;
    std::fs::remove_file(target).map_err(|e| e.to_string())
}

#[tauri::command]
fn reveal_notebook(path: String) -> Result<(), String> {
    let target = notebook_file(&path)?;
    #[cfg(windows)]
    {
        Command::new("explorer.exe").arg("/select,").arg(&target)
            .spawn().map_err(|e| e.to_string())?;
        Ok(())
    }
    #[cfg(not(windows))]
    { let _ = target; Err("Open file location is currently supported on Windows".into()) }
}

fn start_backend(resource: &Path) -> Result<Backend, String> {
    let packaged = resource.join("backend/calix-service.exe");
    let project = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
    let mut command = if packaged.is_file() {
        Command::new(packaged)
    } else if cfg!(debug_assertions) {
        let mut cmd = Command::new(project.join(".venv/Scripts/python.exe"));
        cmd.args(["-m", "backend.service"]).current_dir(&project);
        cmd
    } else { return Err("Bundled calculation service is missing".into()); };
    command.args(["--port", "0", "--publish-connection", "--role", "desktop"]).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(windows)]
    command.creation_flags(0x08000000);
    let mut child = command.spawn().map_err(|e| format!("Cannot start calculation service: {e}"))?;
    #[cfg(windows)]
    let job = match own_backend(&child) {
        Ok(job) => job,
        Err(error) => { let _ = child.kill(); let _ = child.wait(); return Err(format!("Cannot own calculation process: {error}")); }
    };
    let output = child.stdout.take().ok_or("Missing service output")?;
    let (sender, receiver) = mpsc::channel();
    std::thread::spawn(move || {
        for line in BufReader::new(output).lines().map_while(Result::ok) {
            if line.starts_with("CALIX_READY ") { let _ = sender.send(line); break; }
        }
    });
    let ready = match receiver.recv_timeout(Duration::from_secs(30)) {
        Ok(line) => line,
        Err(error) => { let _ = child.kill(); let _ = child.wait(); return Err(format!("Calculation service did not start: {error}")); }
    };
    let parts: Vec<&str> = ready.split_whitespace().collect();
    if parts.len() != 3 { let _ = child.kill(); let _ = child.wait(); return Err("Invalid service handshake".into()); }
    let port = parts[1].parse::<u16>().map_err(|e| e.to_string())?;
    Ok(Backend {
        child: Mutex::new(Some(child)),
        connection: ConnectionInfo { port, token: parts[2].into() },
        #[cfg(windows)]
        _job: job,
    })
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let resource = app.path().resource_dir()?;
            let slot = Arc::new(Mutex::new(Startup::Pending));
            app.manage(BackendSlot(slot.clone()));
            std::thread::spawn(move || {
                let outcome = match start_backend(&resource) {
                    Ok(backend) => Startup::Ready(backend),
                    Err(error) => Startup::Failed(error),
                };
                if let Ok(mut startup) = slot.lock() { *startup = outcome; }
            });
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![connection_info, startup_notebook, read_preferences, write_preferences, write_recovery, list_recovery, read_recovery, list_file_versions, read_file_version, read_notebook, write_notebook, delete_notebook, reveal_notebook])
        .build(tauri::generate_context!())
        .expect("Calix desktop initialization failed");
    app.run(|handle, event| {
        if let tauri::RunEvent::Exit = event {
            let slot = handle.state::<BackendSlot>();
            if let Ok(startup) = slot.0.lock() {
                if let Startup::Ready(backend) = &*startup {
                    if let Ok(mut guard) = backend.child.lock() {
                        if let Some(mut child) = guard.take() {
                            let _ = child.kill();
                            let _ = child.wait();
                        }
                    }
                }
            };
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn saving_preserves_previous_versions_and_failed_save_keeps_source() {
        let dir = std::env::temp_dir().join(format!("calix-save-test-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("笔记 with spaces.cixnb");
        let name = path.to_string_lossy().to_string();
        write_notebook(name.clone(), "first".into()).unwrap();
        write_notebook(name.clone(), "second".into()).unwrap();
        let versions = list_file_versions(name.clone()).unwrap();
        assert_eq!(read_file_version(name.clone(), versions[0].id.clone()).unwrap(), "first");
        assert!(write_notebook(name.clone(), "x".repeat(10_000_001)).is_err());
        assert_eq!(read_notebook(name.clone()).unwrap(), "second");
        write_notebook(name.clone(), "third".into()).unwrap();
        let versions = list_file_versions(name.clone()).unwrap();
        assert_eq!(read_file_version(name.clone(), versions[0].id.clone()).unwrap(), "second");
        assert_eq!(read_file_version(name, versions[1].id.clone()).unwrap(), "first");
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn notebook_deletion_only_removes_the_requested_regular_notebook() {
        let stamp = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        let directory = std::env::temp_dir().join(format!("calix-file-test-{}-{stamp}", std::process::id()));
        std::fs::create_dir(&directory).unwrap();
        let notebook = directory.join("source with spaces.CALIX");
        let other = directory.join("keep.txt");
        let folder = directory.join("folder.clxnb");
        std::fs::write(&notebook, "test notebook").unwrap();
        std::fs::write(&other, "preserve").unwrap();
        std::fs::create_dir(&folder).unwrap();
        assert!(delete_notebook(other.to_string_lossy().into()).is_err());
        assert!(delete_notebook(folder.to_string_lossy().into()).is_err());
        assert!(delete_notebook("relative.calix".into()).is_err());
        assert!(notebook_file(notebook.to_str().unwrap()).is_ok());
        delete_notebook(notebook.to_string_lossy().into()).unwrap();
        assert!(!notebook.exists());
        assert_eq!(std::fs::read_to_string(&other).unwrap(), "preserve");
        assert!(folder.is_dir());
        assert!(delete_notebook(notebook.to_string_lossy().into()).is_err());
        std::fs::remove_file(other).unwrap();
        std::fs::remove_dir(folder).unwrap();
        std::fs::remove_dir(directory).unwrap();
    }
}
