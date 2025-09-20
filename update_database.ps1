# PowerShell Script to Update SoilsFert Application Database
# Run this script from the application directory

param(
    [string]$DatabasePath = "soilsfert.db",
    [switch]$BackupFirst = $true,
    [switch]$ShowTables = $false,
    [switch]$ResetDatabase = $false,
    [switch]$AddTestData = $false
)

Write-Host "SoilsFert Database Update Script" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Check if SQLite3 is available
$sqliteCommand = Get-Command sqlite3 -ErrorAction SilentlyContinue
if (-not $sqliteCommand) {
    Write-Host "ERROR: sqlite3 command not found. Please install SQLite3 first." -ForegroundColor Red
    Write-Host "Download from: https://www.sqlite.org/download.html" -ForegroundColor Yellow
    exit 1
}

# Check if database exists
if (-not (Test-Path $DatabasePath)) {
    Write-Host "Database file '$DatabasePath' not found. Creating new database..." -ForegroundColor Yellow
    # Run Python script to initialize database
    python -c "
import sqlite3
import sys
import os
sys.path.append('.')
from app import init_db
init_db()
print('Database initialized successfully!')
"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to initialize database" -ForegroundColor Red
        exit 1
    }
}

# Backup database if requested
if ($BackupFirst) {
    $backupName = "soilsfert_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    Copy-Item $DatabasePath $backupName
    Write-Host "Database backed up to: $backupName" -ForegroundColor Cyan
}

# Show tables if requested
if ($ShowTables) {
    Write-Host "`nCurrent database tables:" -ForegroundColor Yellow
    sqlite3 $DatabasePath ".tables"
    Write-Host "`nTable schemas:" -ForegroundColor Yellow
    sqlite3 $DatabasePath ".schema"
}

# Reset database if requested
if ($ResetDatabase) {
    Write-Host "`nResetting database..." -ForegroundColor Yellow
    Remove-Item $DatabasePath -Force
    python -c "
import sys
sys.path.append('.')
from app import init_db
init_db()
print('Database reset and reinitialized!')
"
    Write-Host "Database has been reset!" -ForegroundColor Green
}

# Database update operations
Write-Host "`nPerforming database updates..." -ForegroundColor Yellow

# Update 1: Add missing columns to users table if they don't exist
Write-Host "Checking users table structure..." -ForegroundColor Cyan
sqlite3 $DatabasePath "
PRAGMA table_info(users);
ALTER TABLE users ADD COLUMN subscription_start_date TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN subscription_end_date TEXT DEFAULT NULL;
ALTER TABLE users ADD COLUMN last_login_date TEXT DEFAULT NULL;
" 2>$null

# Update 2: Add indexes for better performance
Write-Host "Adding database indexes..." -ForegroundColor Cyan
sqlite3 $DatabasePath "
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_soil_analyses_user_id ON soil_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_soil_analyses_created_at ON soil_analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_testimonials_user_id ON testimonials(user_id);
CREATE INDEX IF NOT EXISTS idx_testimonials_status ON testimonials(status);
CREATE INDEX IF NOT EXISTS idx_contacts_created_at ON contacts(created_at);
"

# Update 3: Add new columns for enhanced features
Write-Host "Adding enhanced feature columns..." -ForegroundColor Cyan
sqlite3 $DatabasePath "
ALTER TABLE soil_analyses ADD COLUMN soil_type TEXT DEFAULT 'loamy';
ALTER TABLE soil_analyses ADD COLUMN extraction_method TEXT DEFAULT 'olsen_modified';
ALTER TABLE soil_analyses ADD COLUMN bulk_density REAL DEFAULT 1.3;
ALTER TABLE soil_analyses ADD COLUMN particle_density REAL DEFAULT 2.65;
ALTER TABLE soil_analyses ADD COLUMN product_ecce REAL DEFAULT 100.0;
" 2>$null

# Update 4: Create new tables for advanced features if they don't exist
Write-Host "Creating advanced feature tables..." -ForegroundColor Cyan
sqlite3 $DatabasePath "
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    UNIQUE(user_id, preference_key)
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    report_type TEXT NOT NULL DEFAULT 'pdf',
    file_path TEXT,
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES soil_analyses (id)
);

CREATE TABLE IF NOT EXISTS lime_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    lime_type TEXT NOT NULL,
    target_ae REAL NOT NULL,
    lime_needed_kg_ha REAL NOT NULL,
    lime_needed_total_kg REAL NOT NULL,
    calculation_method TEXT DEFAULT 'enhanced',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES soil_analyses (id)
);
"

# Add test data if requested
if ($AddTestData) {
    Write-Host "Adding test data..." -ForegroundColor Cyan
    sqlite3 $DatabasePath "
INSERT OR IGNORE INTO users (email, password_hash, plan_type, analyses_used) 
VALUES ('test@example.com', 'pbkdf2:sha256:600000\$test\$test', 'pro', 0);

INSERT OR IGNORE INTO testimonials (user_id, user_name, location, rating, comment, status, featured, created_at)
VALUES (1, 'Test User', 'Test Location', 5, 'Great application for soil analysis!', 'approved', 1, datetime('now'));
"
    Write-Host "Test data added successfully!" -ForegroundColor Green
}

# Verify database integrity
Write-Host "`nVerifying database integrity..." -ForegroundColor Yellow
$integrityCheck = sqlite3 $DatabasePath "PRAGMA integrity_check;"
if ($integrityCheck -eq "ok") {
    Write-Host "✅ Database integrity check passed!" -ForegroundColor Green
} else {
    Write-Host "❌ Database integrity check failed: $integrityCheck" -ForegroundColor Red
}

# Show updated table count
$tableCount = sqlite3 $DatabasePath "SELECT COUNT(*) FROM sqlite_master WHERE type='table';"
Write-Host "Database now contains $tableCount tables" -ForegroundColor Cyan

# Show user count
$userCount = sqlite3 $DatabasePath "SELECT COUNT(*) FROM users;"
Write-Host "Total users in database: $userCount" -ForegroundColor Cyan

Write-Host "`n✅ Database update completed successfully!" -ForegroundColor Green
Write-Host "You can now restart the Flask application." -ForegroundColor Yellow

# Usage examples
Write-Host "`nUsage Examples:" -ForegroundColor Magenta
Write-Host "  .\update_database.ps1                    # Basic update with backup" -ForegroundColor White
Write-Host "  .\update_database.ps1 -ShowTables        # Show current tables" -ForegroundColor White
Write-Host "  .\update_database.ps1 -ResetDatabase     # Reset entire database" -ForegroundColor White
Write-Host "  .\update_database.ps1 -AddTestData       # Add test data" -ForegroundColor White
Write-Host "  .\update_database.ps1 -BackupFirst:`$false # Skip backup" -ForegroundColor White
