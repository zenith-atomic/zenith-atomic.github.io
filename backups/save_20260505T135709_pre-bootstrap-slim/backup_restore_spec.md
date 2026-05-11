# OpenClaw Workspace Backup and Restore System Specification

## 1. Problem Statement

The OpenClaw workspace contains critical configuration, memory, user data, and potentially custom models. Loss of this data due to system failures, accidental deletions, or corruption would severely impact the agent's functionality, requiring extensive manual recovery or complete re-setup. A robust backup and restore system is essential to ensure data integrity, minimize downtime, and provide peace of mind for users. Without such a system, the risk of unrecoverable data loss is unacceptably high.

## 2. Scope

This specification covers the backup and restore of the following OpenClaw components within the `/home/ai/.openclaw/workspace/` directory and related system configurations:

*   **Workspace Content:** All files and subdirectories within `/home/ai/.openclaw/workspace/` (excluding temporary or cache directories explicitly defined as exclusions). This includes:
    *   `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `USER.md`, `TOOLS.md`
    *   `memory/` directory (recent notes, inbox, `MEMORY.md`)
    *   `factory/` directory (scripts, tools)
    *   `nemoclaw/`, `wiki/`, `research/` (custom project directories)
    *   Any other user-created files or directories within the workspace.
*   **OpenClaw Configuration:**
    *   `~/.openclaw/openclaw.json` (main runtime configuration)
    *   `~/.openclaw/agents/` session/state metadata as needed for continuity
*   **Installed Models List:** A list of currently installed and configured models. This allows for re-installation of models, not backup of the models themselves.

**Out of Scope:**

*   Operating System backups.
*   Application binaries or OpenClaw core system files (these should be reinstalled).
*   Large language models or other AI model files themselves (only their configuration/list is backed up).
*   System logs (beyond OpenClaw's internal session logs which are part of the workspace).

## 3. Approach

The backup system will consist of a single script that archives the specified directories and files into a compressed timestamped file.

### Backup Script (`backup_openclaw.sh`)

1.  **Preparation:**
    *   Define source directories/files:
        *   `/home/ai/.openclaw/workspace/`
        *   `~/.openclaw/openclaw.json`
        *   `~/.openclaw/agents/` (if continuity artifacts are desired)
    *   Define destination directory for backups (e.g., `/var/backups/openclaw/` or a user-configurable path).
    *   Generate a timestamp for the backup file (e.g., `YYYYMMDD_HHMMSS`).
    *   Define the backup filename (e.g., `openclaw_backup_YYYYMMDD_HHMMSS.tar.gz`).
    *   Create the destination directory if it doesn't exist.
2.  **Model List Capture:**
    *   Run `openclaw models list --json > /tmp/openclaw_models.json` to capture the currently installed models. This file will be included in the backup.
3.  **Archiving:**
    *   Use `tar` with `gzip` compression to create a single archive file.
    *   Include all defined source directories and files.
    *   Exclude known temporary/cache directories if identified (e.g., `.git/`, `node_modules/` if present in workspace sub-projects). A `.backupignore` file could be implemented for fine-grained control if needed.
    *   Include the `/tmp/openclaw_models.json` file.
4.  **Verification (Optional but Recommended):**
    *   Check the exit status of the `tar` command.
    *   Optionally, check the size of the generated archive (e.g., ensure it's not empty).
5.  **Cleanup:**
    *   Remove the temporary `/tmp/openclaw_models.json` file.
    *   Implement a retention policy (e.g., keep last 7 daily backups, last 4 weekly, last 12 monthly). Old backups beyond the policy should be deleted.

### Restore Procedure (`restore_openclaw.sh`)

The restore procedure will be a manual, step-by-step process, guided by a script or clear instructions.

1.  **Prerequisites:**
    *   A fresh installation of OpenClaw is assumed to be present on the target machine.
    *   The backup archive file (`.tar.gz`) must be accessible.
    *   OpenClaw services should be stopped (`openclaw gateway stop`).
2.  **Selection:**
    *   The user selects the desired backup file to restore from.
3.  **Extraction:**
    *   The script will extract the contents of the backup archive to a temporary location.
4.  **Verification:**
    *   Display the contents of the backup to the user for confirmation (e.g., list files in the archive).
5.  **Restoration:**
    *   **Workspace:** Overwrite the existing `/home/ai/.openclaw/workspace/` with the backed-up content.
    *   **Configuration:** Restore `~/.openclaw/openclaw.json` if it was included in the archive, or preserve the local runtime config if you only want workspace recovery.
    *   **Models:** Read the `openclaw_models.json` file from the backup and provide instructions/commands to the user to re-install these models using `openclaw models add <model_id>`. The script should not attempt to automatically re-install models to avoid unintended actions or network issues during restore.
6.  **Post-restore:**
    *   Provide instructions to restart OpenClaw services (`openclaw gateway start`).
    *   Clear temporary files created during restore.

## 4. Automation

The backup script should be designed for automated execution.

*   **Cron Job:** The primary method for automation will be a daily cron job.
    *   Example cron entry: `0 2 * * * /usr/local/bin/backup_openclaw.sh > /var/log/openclaw_backup.log 2>&1` (runs daily at 2:00 AM).
*   **Manual Trigger:** The script should also be runnable manually for immediate backups.
*   **Heartbeat Integration (Future):** Consider a lightweight check during `HEARTBEAT.md` execution to ensure the last backup was successful and within a reasonable timeframe (e.g., less than 24 hours ago). This would not trigger a backup, only report status.

## 5. Limitations

*   **Not a disaster recovery solution for the entire OS:** This only backs up OpenClaw specific data.
*   **Model files not backed up:** Only the list of models is preserved, requiring re-download. This is by design due to potentially large model sizes.
*   **Requires manual intervention for restore:** The restore process is guided but requires user input/confirmation, especially for model re-installation. It's not a fully automated bare-metal restore.
*   **No incremental backups:** The current approach is full backups. For very large workspaces, incremental backups could be considered in a future iteration.
*   **No encryption:** Backups are stored unencrypted on the local filesystem. Users should ensure the backup destination is secure.
*   **Single point of failure for backup storage:** Backups are local. For true disaster recovery, an off-site backup strategy would be needed (e.g., rsync to cloud storage, which is out of scope for this spec but a recommended user action).

## 6. Test Plan

### 6.1. Backup Test Cases

1.  **TC-B-001: Basic Backup Functionality**
    *   **Objective:** Verify that the backup script creates a valid archive.
    *   **Steps:**
        1.  Run `backup_openclaw.sh`.
        2.  Check for the presence of `openclaw_backup_YYYYMMDD_HHMMSS.tar.gz` in the backup destination.
        3.  Verify the script exits with status 0.
2.  **TC-B-002: Archive Content Verification**
    *   **Objective:** Verify that the backup archive contains all specified files and directories.
    *   **Steps:**
        1.  Run `backup_openclaw.sh`.
        2.  Extract the generated archive to a temporary directory.
        3.  Verify that `/home/ai/.openclaw/workspace/` content and `openclaw_models.json` (from inside the archive) are present and readable.
3.  **TC-B-003: Exclusions Verification**
    *   **Objective:** Verify that specified exclusions (e.g., `.git/`) are not included in the backup.
    *   **Steps:**
        1.  Create a `.git/` directory (or other exclusion) within the workspace.
        2.  Run `backup_openclaw.sh`.
        3.  Extract the archive and confirm the excluded directory is NOT present.
4.  **TC-B-004: Retention Policy**
    *   **Objective:** Verify that old backups are pruned according to the retention policy.
    *   **Steps:**
        1.  Create several dummy backup files that would exceed the retention policy.
        2.  Run `backup_openclaw.sh`.
        3.  Verify that only the allowed number of backups remain.
5.  **TC-B-005: Model List Capture**
    *   **Objective:** Verify that `openclaw_models.json` is correctly captured and included.
    *   **Steps:**
        1.  Ensure a few models are installed (`openclaw models add ...`).
        2.  Run `backup_openclaw.sh`.
        3.  Extract the archive and check the content of `openclaw_models.json` against `openclaw models list`.

### 6.2. Restore Test Cases

1.  **TC-R-001: Full Workspace Restore**
    *   **Objective:** Verify that a full restore successfully reinstates the workspace.
    *   **Steps:**
        1.  Perform a backup.
        2.  Make significant changes to `/home/ai/.openclaw/workspace/` (add/delete files, modify `MEMORY.md`).
        3.  Stop OpenClaw gateway (`openclaw gateway stop`).
        4.  Run `restore_openclaw.sh` using the latest backup.
        5.  Restart OpenClaw gateway (`openclaw gateway start`).
        6.  Verify that the workspace content is identical to the backup (e.g., `diff -r` against the extracted backup content).
2.  **TC-R-002: Configuration Files Restore**
    *   **Objective:** Verify that configuration files are correctly restored.
    *   **Steps:**
        1.  Perform a backup.
        2.  Modify `~/.openclaw/openclaw.json`.
        3.  Stop OpenClaw gateway.
        4.  Run `restore_openclaw.sh`.
        5.  Restart OpenClaw gateway.
        6.  Verify that the restored runtime configuration reflects the backup decision.
3.  **TC-R-003: Model Re-installation Guidance**
    *   **Objective:** Verify that the restore script correctly prompts for model re-installation.
    *   **Steps:**
        1.  Install a unique model not present by default.
        2.  Perform a backup.
        3.  Uninstall the unique model.
        4.  Run `restore_openclaw.sh`.
        5.  Verify that the script outputs clear instructions to re-install the model using `openclaw models add ...`.
4.  **TC-R-004: Handling Missing Backup Files**
    *   **Objective:** Verify graceful error handling if the specified backup file does not exist.
    *   **Steps:**
        1.  Attempt to run `restore_openclaw.sh` with a non-existent backup filename.
        2.  Verify that the script provides an informative error message and exits cleanly.
5.  **TC-R-005: Restore on a Clean System (Simulated)**
    *   **Objective:** Verify the restore process works on a system that simulates a fresh OpenClaw installation.
    *   **Steps:**
        1.  Set up a new environment with only OpenClaw installed (no custom workspace content).
        2.  Perform a backup from a functional OpenClaw system.
        3.  Transfer the backup to the clean system.
        4.  Stop OpenClaw gateway.
        5.  Run `restore_openclaw.sh` on the clean system.
        6.  Restart OpenClaw gateway.
        7.  Verify all restored components are functional and accessible (e.g., agent responds correctly, memory files are present).


## 7. Current Implementation Notes

- `scripts/backup_openclaw.sh` now creates timestamped workspace archives and includes `openclaw_models.json`.
- `scripts/restore_openclaw.sh` restores the workspace payload and restarts the gateway.
- `scripts/health_monitor.sh` is intended to alert on service failures and recent cron errors.
