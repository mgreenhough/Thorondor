#!/bin/bash
# Install Thorondor daily digest cron job
# Run this on the server after cloning/pulling the repo

set -e

LOG_DIR="/var/log/thorondor"
REPO_DIR="/opt/thorondor"
CRON_CMD="30 4 * * * cd ${REPO_DIR} && source venv/bin/activate && python3 run_digest.py >> ${LOG_DIR}/digest.log 2>&1"
CRON_FILE="/tmp/thorondor_cron"

# Ensure log directory exists
sudo mkdir -p "${LOG_DIR}"

# Write out the current crontab (or empty if none)
crontab -l 2>/dev/null > "${CRON_FILE}" || true

# Remove any existing Thorondor entry
grep -v "run_digest.py" "${CRON_FILE}" > "${CRON_FILE}.tmp" || true
mv "${CRON_FILE}.tmp" "${CRON_FILE}"

# Add the new entry
echo "${CRON_CMD}" >> "${CRON_FILE}"

# Install the updated crontab
crontab "${CRON_FILE}"
rm -f "${CRON_FILE}"

echo "Cron job installed:"
echo "  ${CRON_CMD}"
echo ""
echo "Current crontab:"
crontab -l