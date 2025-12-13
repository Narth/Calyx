# Kernel-Power 41 Postmortem ? 2025-12-06
Frame: kernel_fault_postmortem_v0 (read-only)

## Event Log Deep Dive (12:30?14:30 -07:00)
- Kernel-Power 41 at 14:17:59: unexpected reboot without clean shutdown.
- Boot sequence began 14:17:52 (Kernel-General 12; Kernel-Boot IDs 18/20/25/27/30/32/153/238).
- Driver load issues immediately post-boot:
  - 14:17:59.855: WudfRd failed for ROOT\\DISPLAY\\0000 (Kernel-PnP 219).
  - 14:18:07.135: WudfRd failed for HID VID_1532 PID_0511 (Kernel-PnP 219).
- EventLog markers at 14:18:10: 6008 unexpected shutdown; 6005 log service start; 6009 OS version; 6013 uptime 19s.
- No ACPI/Disk/Ntfs/storahci/stornvme errors logged in the 12:30?14:30 window; none recorded in the 5 minutes before the reboot (likely abrupt power loss prevented logging).
- Additional system activity: Kernel-General 16 (registry hive access history) at 14:19:19.

Plausible contributing factors: abrupt power interruption or forced reset (no pre-fault errors logged), with post-boot driver reload for display stack (WudfRd display device) indicating recovery rather than root cause.

## Disk Health (read-only)
- Physical disks (Get-PhysicalDisk / reliability counters):
  - ST4000DM000-1F2168 (HDD) ? Healthy; status OK; size 3.7 TB; temp 29?C; wear 0; POH 14,963; errors: read 0 / write 0 / other 0.
  - INTEL SSDPEKNW010T9 (SSD) ? Healthy; status OK; size 953.9 GB; temp 35?C; wear 0; errors: not reported.
- Disk/Ntfs/storahci/stornvme events in ?10 min of reboot (14:07:59?14:27:59): none observed.

## Pre-Fault Conditions (14:07:59?14:27:59)
- Heartbeats at 14:10, 14:12, 14:13, 14:15 (pre) and 14:21, 14:23, 14:25, 14:26 (post) report load(1/5/15)=0.00/0.00/0.00; mem_total unknown in WSL context; disk_free ranged 180.35?187.85 GiB.
- No GPU load, thermal, or power telemetry recorded in available logs; metrics_cron last run at 14:04:47 reported zeroed load/mem values.

## Display Topology Delta
- Current detected monitors (Win32_DesktopMonitor): Generic PnP Monitor `DISPLAY\\AOC2401\\5&18855B5E&0&UID4352` plus two Default Monitor placeholders.
- GPU stack: NVIDIA GeForce RTX 2070 SUPER active at 1920x1080@120Hz; Parsec Virtual Display Adapter present; Intel UHD 630 idle.
- Historical display data around the fault not present in `logs/system_snapshots.jsonl`; no evidence of previously attached displays absent post-reboot.

## Outputs
- Raw events: `logs/postmortem/kernelpower41_events.jsonl` (frame: kernel_fault_postmortem_v0).
- Disk health: `logs/postmortem/disk_health_20251206.jsonl`.
- This report: `reports/postmortem/kernelpower41_20251206.md`.
