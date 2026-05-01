use std::env;
use std::path::PathBuf;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

const STATION_PORTS: [u16; 4] = [7777, 7778, 7780, 7781];

fn main() {
    let repo_root = parse_repo_root()
        .unwrap_or_else(|| env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));

    let git_branch = run_git(&repo_root, &["rev-parse", "--abbrev-ref", "HEAD"]);
    let git_head = run_git(&repo_root, &["rev-parse", "HEAD"]);
    let git_status = run_git(&repo_root, &["status", "--short", "--untracked-files=no"]);
    let tracked_drift = git_status.as_ref().map(|s| !s.trim().is_empty());
    let process_count = local_process_count();
    let listener_ports = local_listener_ports();

    println!("{{");
    println!("  \"schema\": \"station.rust_probe.v1\",");
    println!(
        "  \"emitted_ts_utc\": \"{}\",",
        json_escape(&utc_timestamp())
    );
    println!("  \"authority\": \"advisory_only\",");
    println!("  \"network_behavior\": \"local_observation_only\",");
    println!("  \"observer\": \"rust/station_probe\",");
    println!(
        "  \"repo_root\": \"{}\",",
        json_escape(&repo_root.display().to_string())
    );
    println!("  \"os\": \"{}\",", json_escape(env::consts::OS));
    println!("  \"arch\": \"{}\",", json_escape(env::consts::ARCH));
    println!("  \"hostname\": {},", json_string_or_null(local_hostname()));
    println!("  \"process_count\": {},", json_u64_or_null(process_count));
    println!("  \"station_ports\": {},", json_ports(&listener_ports));
    println!("  \"git\": {{");
    println!("    \"branch\": {},", json_string_or_null(git_branch));
    println!("    \"head\": {},", json_string_or_null(git_head));
    println!(
        "    \"tracked_drift\": {}",
        json_bool_or_null(tracked_drift)
    );
    println!("  }}");
    println!("}}");
}

fn parse_repo_root() -> Option<PathBuf> {
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        if arg == "--repo-root" {
            return args.next().map(PathBuf::from);
        }
    }
    None
}

fn run_git(repo_root: &PathBuf, args: &[&str]) -> Option<String> {
    let output = Command::new("git")
        .args(args)
        .current_dir(repo_root)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn local_hostname() -> Option<String> {
    if let Ok(value) = env::var("COMPUTERNAME") {
        if !value.trim().is_empty() {
            return Some(value.trim().to_string());
        }
    }
    if let Ok(value) = env::var("HOSTNAME") {
        if !value.trim().is_empty() {
            return Some(value.trim().to_string());
        }
    }
    command_stdout("hostname", &[])
}

fn local_process_count() -> Option<u64> {
    if cfg!(windows) {
        let output = command_stdout("tasklist", &["/FO", "CSV", "/NH"])?;
        let count = output
            .lines()
            .filter(|line| !line.trim().is_empty())
            .count();
        return Some(count as u64);
    }
    let output = command_stdout("ps", &["-e", "-o", "pid="])?;
    let count = output
        .lines()
        .filter(|line| !line.trim().is_empty())
        .count();
    Some(count as u64)
}

fn local_listener_ports() -> Vec<(u16, bool)> {
    let output = if cfg!(windows) {
        command_stdout("netstat", &["-ano", "-p", "tcp"])
    } else {
        command_stdout(
            "sh",
            &[
                "-c",
                "netstat -an -p tcp 2>/dev/null || ss -ltn 2>/dev/null",
            ],
        )
    };
    let mut rows = Vec::new();
    for port in STATION_PORTS {
        let needle = format!(":{port}");
        let listening = output
            .as_ref()
            .map(|text| {
                text.lines().any(|line| {
                    line.contains(&needle) && line.to_ascii_uppercase().contains("LISTEN")
                })
            })
            .unwrap_or(false);
        rows.push((port, listening));
    }
    rows
}

fn command_stdout(program: &str, args: &[&str]) -> Option<String> {
    let output = Command::new(program).args(args).output().ok()?;
    if !output.status.success() {
        return None;
    }
    Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
}

fn utc_timestamp() -> String {
    let duration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let total_seconds = duration.as_secs() as i64;
    let days = total_seconds.div_euclid(86_400);
    let seconds_of_day = total_seconds.rem_euclid(86_400);
    let (year, month, day) = civil_from_days(days);
    let hour = seconds_of_day / 3_600;
    let minute = (seconds_of_day % 3_600) / 60;
    let second = seconds_of_day % 60;
    format!(
        "{year:04}-{month:02}-{day:02}T{hour:02}:{minute:02}:{second:02}.{:09}Z",
        duration.subsec_nanos()
    )
}

fn civil_from_days(days_since_epoch: i64) -> (i64, u32, u32) {
    let z = days_since_epoch + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 }.div_euclid(146_097);
    let day_of_era = z - era * 146_097;
    let year_of_era = (day_of_era - day_of_era / 1_460 + day_of_era / 36_524
        - day_of_era / 146_096)
        .div_euclid(365);
    let mut year = year_of_era + era * 400;
    let day_of_year = day_of_era - (365 * year_of_era + year_of_era / 4 - year_of_era / 100);
    let month_prime = (5 * day_of_year + 2).div_euclid(153);
    let day = day_of_year - (153 * month_prime + 2).div_euclid(5) + 1;
    let month = month_prime + if month_prime < 10 { 3 } else { -9 };
    if month <= 2 {
        year += 1;
    }
    (year, month as u32, day as u32)
}

fn json_escape(value: &str) -> String {
    let mut out = String::new();
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c.is_control() => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

fn json_string_or_null(value: Option<String>) -> String {
    match value {
        Some(text) => format!("\"{}\"", json_escape(&text)),
        None => "null".to_string(),
    }
}

fn json_u64_or_null(value: Option<u64>) -> String {
    match value {
        Some(number) => number.to_string(),
        None => "null".to_string(),
    }
}

fn json_bool_or_null(value: Option<bool>) -> String {
    match value {
        Some(true) => "true".to_string(),
        Some(false) => "false".to_string(),
        None => "null".to_string(),
    }
}

fn json_ports(rows: &[(u16, bool)]) -> String {
    let mut parts = Vec::new();
    for (port, listening) in rows {
        parts.push(format!(
            "{{\"port\":{},\"listening\":{}}}",
            port,
            if *listening { "true" } else { "false" }
        ));
    }
    format!("[{}]", parts.join(","))
}
