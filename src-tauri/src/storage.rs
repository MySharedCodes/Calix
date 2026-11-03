use serde::Serialize;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

static SEQUENCE: AtomicU64 = AtomicU64::new(0);
pub const LIMIT: usize = 20_000_000;

fn stamp() -> u128 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis()
}

pub fn atomic_write(target: &Path, content: &[u8]) -> Result<(), String> {
    if content.len() > LIMIT { return Err("Recovery data exceeds 20 MB".into()); }
    let parent = target.parent().ok_or("Missing parent directory")?;
    let name = target.file_name().ok_or("Missing file name")?.to_string_lossy();
    let temporary = parent.join(format!(".{name}.{}-{}.tmp", std::process::id(), SEQUENCE.fetch_add(1, Ordering::Relaxed)));
    let result = (|| {
        let mut file = OpenOptions::new().write(true).create_new(true).open(&temporary).map_err(|e| e.to_string())?;
        file.write_all(content).map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        drop(file);
        fs::rename(&temporary, target).map_err(|e| e.to_string())
    })();
    if result.is_err() { let _ = fs::remove_file(&temporary); }
    result
}

fn revisions(directory: &Path) -> Result<Vec<PathBuf>, String> {
    if !directory.exists() { return Ok(Vec::new()); }
    let mut files: Vec<_> = fs::read_dir(directory).map_err(|e| e.to_string())?
        .filter_map(Result::ok).map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|ext| ext == "json") && path.file_stem().is_some_and(|stem| stem.to_string_lossy().chars().all(|c| c.is_ascii_digit() || c == '-')))
        .collect();
    files.sort();
    files.reverse();
    Ok(files)
}

pub fn snapshot(directory: &Path, content: &str, force: bool) -> Result<(), String> {
    if content.len() > LIMIT { return Err("Recovery data exceeds 20 MB".into()); }
    fs::create_dir_all(directory).map_err(|e| e.to_string())?;
    let latest = directory.join("latest.data");
    let previous = fs::read(&latest).ok();
    if previous.as_deref() == Some(content.as_bytes()) { return Ok(()); }
    let files = revisions(directory)?;
    let due = files.first().and_then(|path| path.file_stem()?.to_str()?.split('-').next()?.parse::<u128>().ok())
        .is_none_or(|time| stamp().saturating_sub(time) >= 60_000);
    if (force || due) && previous.is_some() {
        let path = directory.join(format!("{:020}-{:06}.json", stamp(), SEQUENCE.fetch_add(1, Ordering::Relaxed)));
        atomic_write(&path, previous.as_ref().unwrap())?;
    }
    atomic_write(&latest, content.as_bytes())?;
    for old in revisions(directory)?.into_iter().skip(20) { fs::remove_file(old).map_err(|e| e.to_string())?; }
    Ok(())
}

#[derive(Serialize)]
pub struct Revision { pub id: String, pub modified: u64, pub bytes: u64 }

pub fn list(directory: &Path) -> Result<Vec<Revision>, String> {
    let mut paths = revisions(directory)?;
    let latest = directory.join("latest.data");
    if latest.exists() { paths.insert(0, latest); }
    paths.into_iter().map(|path| {
        let metadata = fs::metadata(&path).map_err(|e| e.to_string())?;
        let modified = metadata.modified().map_err(|e| e.to_string())?.duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64;
        Ok(Revision { id: path.file_name().unwrap().to_string_lossy().into(), modified, bytes: metadata.len() })
    }).collect()
}

pub fn read(directory: &Path, id: &str) -> Result<String, String> {
    if id != "latest.data" && (!id.ends_with(".json") || !id.trim_end_matches(".json").chars().all(|c| c.is_ascii_digit() || c == '-')) {
        return Err("Invalid recovery revision".into());
    }
    let path = directory.join(id);
    let metadata = fs::symlink_metadata(&path).map_err(|e| e.to_string())?;
    if !metadata.is_file() || metadata.file_type().is_symlink() || metadata.len() > LIMIT as u64 { return Err("Invalid recovery file".into()); }
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn revisions_preserve_previous_and_reject_paths() {
        let dir = std::env::temp_dir().join(format!("calix-recovery-{}-{}", std::process::id(), stamp()));
        snapshot(&dir, "first", false).unwrap();
        snapshot(&dir, "second", true).unwrap();
        assert_eq!(read(&dir, "latest.data").unwrap(), "second");
        let history = list(&dir).unwrap();
        assert_eq!(history.len(), 2);
        assert_eq!(read(&dir, &history[1].id).unwrap(), "first");
        assert!(read(&dir, "../latest.data").is_err());
        for n in 0..25 { snapshot(&dir, &n.to_string(), true).unwrap(); }
        assert_eq!(list(&dir).unwrap().len(), 21);
        assert!(atomic_write(&dir.join("missing/target"), b"bad").is_err());
        assert_eq!(read(&dir, "latest.data").unwrap(), "24");
        fs::remove_dir_all(dir).unwrap();
    }
}
