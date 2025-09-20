#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SoilFert - Complete Soil Fertility Analysis Application with Enhanced Lime Calculation
Single file with organized sections for easy individual editing
"""

import sys
import os
# Set UTF-8 encoding for Windows console
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# =====================================
# 📦 IMPORTS AND DEPENDENCIES
# =====================================
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env into environment

import os
import json
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from threading import Lock
from queue import Queue
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, render_template_string, send_file
import openai
from openai import OpenAI
import paypalrestsdk
import requests
import stripe
import atexit
import signal
import sys
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import pandas as pd
from io import BytesIO

# =====================================
# ⚙️ FLASK APP CONFIGURATION
# =====================================

app = Flask(__name__, template_folder='templates')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key-change-in-production')
app.config['DATABASE'] = os.getenv('DATABASE_URL', 'soilfert.db')

# Initialize OpenAI client
openai_client = None
try:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
        print("OpenAI API initialized successfully")
    else:
        print("WARNING: OPENAI_API_KEY not found in environment variables")
except Exception as e:
    print(f"ERROR: OpenAI initialization failed: {e}")

# =====================================
# 💳 PAYPAL CONFIGURATION
# =====================================

# PayPal Configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": "AeAbomzUELU7VxO8i-ZLEMql0fhoutI06D6OhpvTWGlhTTy-MJsNf-6_RySaZIL1i93NEEFrELnh5meP",
    "client_secret": "EBKO6TKGe5bfkF3SA_-liG6WXbQrKY7aaOPQyJtSoyR-WFujvIyBCgZIqFFoVYtOIKRYdaQdphNnZIZ-"
})

# Stripe Configuration
stripe.api_key = "sk_test_51S2azWRc7RnjOJt72snVSEfpZbSCRDCaZv3D0kurvaHPhgKMeNVxixebo2TxCWp3Nr84tJTvL0eNePRJTp9SRVlt00dAStQLHO"
STRIPE_PUBLISHABLE_KEY = "pk_test_51S2azWRc7RnjOJt7VaunYpNhTxwlFYT4KtE4C3gIybnFIY0YC9KE0XyW1AbasEUqG787ZZjN7TDGbPMoyYsB73Cy00Lr851Llv"

# Pricing configuration
PRO_PLAN_PRICE = "5.00"  # Updated from $19.99 to $5.00 USD




# =====================================
# 🗄️ ENHANCED DATABASE SETUP
# =====================================

def init_db():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            country TEXT,
            region TEXT,
            farm_size REAL,
            plan_type TEXT DEFAULT 'free',
            analyses_used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            pro_plan_expires_at TIMESTAMP NULL
        )
    ''')
    
    # Enhanced soil analyses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS soil_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop_type TEXT NOT NULL,
            farm_location TEXT,
            extraction_method TEXT DEFAULT 'olsen_modified',
            surface_area REAL DEFAULT 1.0,
            
            -- Basic properties
            soil_ph REAL,
            organic_matter REAL,
            
            -- Primary nutrients
            phosphorus_ppm REAL,
            potassium_ppm REAL,
            potassium_cmol REAL,
            
            -- Secondary nutrients (cmol+/kg)
            calcium_cmol REAL,
            magnesium_cmol REAL,
            
            -- Micronutrients (ppm)
            iron_ppm REAL,
            copper_ppm REAL,
            manganese_ppm REAL,
            zinc_ppm REAL,
            
            -- Soil chemistry
            exchangeable_acidity REAL,
            cec REAL,
            base_saturation REAL,
            acid_saturation REAL,
            
            -- Physical properties
            bulk_density REAL DEFAULT 1.3,
            porosity REAL DEFAULT 50.0,
            effective_depth REAL DEFAULT 20.0,
            
            -- Analysis results
            overall_rating INTEGER,
            fertility_index REAL,
            soil_health_score REAL,
            estimated_yield_potential REAL,
            
            -- Cationic ratios
            ca_mg_ratio REAL,
            ca_k_ratio REAL,
            mg_k_ratio REAL,
            
            -- Enhanced lime calculation
            lime_needed REAL,
            lime_type TEXT DEFAULT 'caco3',
            target_ae REAL DEFAULT 0.5,
            lime_cost REAL,
            
            -- Other fertilization
            phosphorus_needed REAL,
            potassium_needed REAL,
            estimated_cost REAL,
            
            -- JSON fields
            recommendations TEXT,
            nutrient_status TEXT,
            micronutrient_status TEXT,
            limiting_factors TEXT,
            fertilization_plan TEXT,
            lime_calculation TEXT,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Compost recipes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compost_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_name TEXT NOT NULL,
            materials TEXT NOT NULL,
            ratios TEXT NOT NULL,
            estimated_yield REAL,
            maturation_time INTEGER,
            c_n_ratio REAL,
            quality_score INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# =====================================
# 📊 DATABASE HELPER FUNCTIONS
# =====================================

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """Execute database query"""
    conn = get_db_connection()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute database command"""
    conn = get_db_connection()
    conn.execute(query, args)
    conn.commit()
    conn.close()
# =====================================
# 🗄️ COMPLETE DATABASE MIGRATION FOR ENHANCED MULTI-NUTRIENT SYSTEM
# =====================================

def complete_enhanced_database_migration():
    """Complete migration for all enhanced multi-nutrient features"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    print("Starting enhanced database migration...")
    
    # =====================================
    # ENHANCED NUTRIENT COLUMNS
    # =====================================
    enhanced_nutrient_columns = [
        # Additional nutrients
        ('sulfur_ppm', 'REAL DEFAULT 0'),
        ('boron_ppm', 'REAL DEFAULT 0'),
        ('molybdenum_ppm', 'REAL DEFAULT 0'),
        
        # Enhanced nitrogen parameters
        ('target_n_kg_ha', 'REAL DEFAULT 120'),
        ('current_n_percent', 'REAL DEFAULT 0.1'),
        ('expected_yield', 'REAL DEFAULT 5.0'),
        
        # Smart fertilizer calculation results
        ('comprehensive_nutrient_analysis', 'TEXT'),
        ('smart_product_recommendations', 'TEXT'),
        ('nutrient_efficiency_data', 'TEXT'),
        
        # Enhanced cost tracking
        ('total_fertilizer_cost_per_ha', 'REAL DEFAULT 0'),
        ('cost_per_nutrient', 'REAL DEFAULT 0'),
        ('overall_efficiency_percentage', 'REAL DEFAULT 0'),
        ('total_products_recommended', 'INTEGER DEFAULT 0'),
        
        # Product application details
        ('fertilizer_products_json', 'TEXT'),
        ('application_rates_json', 'TEXT'),
        ('nutrients_supplied_json', 'TEXT'),
        
        # Advanced analysis flags
        ('uses_smart_algorithm', 'BOOLEAN DEFAULT TRUE'),
        ('multi_nutrient_optimization', 'BOOLEAN DEFAULT TRUE'),
        ('compensation_efficiency', 'REAL DEFAULT 0')
    ]
    
    # Add enhanced nutrient columns
    for column_name, column_type in enhanced_nutrient_columns:
        try:
            cursor.execute(f'ALTER TABLE soil_analyses ADD COLUMN {column_name} {column_type}')
            print(f"Added enhanced column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                print(f"Error adding column {column_name}: {e}")
    
    # =====================================
    # CREATE ENHANCED TABLES FOR DETAILED TRACKING
    # =====================================
    
    # Fertilizer recommendations tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fertilizer_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_category TEXT NOT NULL,
            application_rate_kg_ha REAL NOT NULL,
            cost_per_ha REAL NOT NULL,
            efficiency_score REAL DEFAULT 0,
            nutrient_content TEXT,
            nutrients_supplied TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES soil_analyses (id)
        )
    ''')
    
    # Nutrient balance tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nutrient_balance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            nutrient_name TEXT NOT NULL,
            current_level REAL NOT NULL,
            target_level REAL NOT NULL,
            deficit_amount REAL NOT NULL,
            supplied_amount REAL DEFAULT 0,
            coverage_percentage REAL DEFAULT 0,
            unit TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES soil_analyses (id)
        )
    ''')
    
    # Smart algorithm performance tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS algorithm_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            total_nutrients_needed INTEGER DEFAULT 0,
            total_products_selected INTEGER DEFAULT 0,
            overall_efficiency REAL DEFAULT 0,
            cost_optimization_score REAL DEFAULT 0,
            multi_nutrient_products_used INTEGER DEFAULT 0,
            single_nutrient_products_used INTEGER DEFAULT 0,
            micronutrient_products_used INTEGER DEFAULT 0,
            algorithm_version TEXT DEFAULT 'v1.0',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES soil_analyses (id)
        )
    ''')
    
    print("Created enhanced tracking tables")
    
    # =====================================
    # UPDATE EXISTING ANALYSES WITH DEFAULT VALUES
    # =====================================
    
    # Update existing analyses to have default smart algorithm values
    cursor.execute('''
        UPDATE soil_analyses 
        SET uses_smart_algorithm = TRUE,
            multi_nutrient_optimization = TRUE,
            compensation_efficiency = 0
        WHERE uses_smart_algorithm IS NULL
    ''')
    
    print("Updated existing analyses with default values")
    
    # =====================================
    # CREATE INDEXES FOR PERFORMANCE
    # =====================================
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_fertilizer_recommendations_analysis_id ON fertilizer_recommendations(analysis_id)",
        "CREATE INDEX IF NOT EXISTS idx_nutrient_balance_analysis_id ON nutrient_balance(analysis_id)",
        "CREATE INDEX IF NOT EXISTS idx_algorithm_performance_analysis_id ON algorithm_performance(analysis_id)",
        "CREATE INDEX IF NOT EXISTS idx_soil_analyses_user_created ON soil_analyses(user_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_soil_analyses_crop_type ON soil_analyses(crop_type)",
        "CREATE INDEX IF NOT EXISTS idx_soil_analyses_efficiency ON soil_analyses(overall_efficiency_percentage)"
    ]
    
    for index_sql in indexes:
        try:
            cursor.execute(index_sql)
            print(f"Created index: {index_sql.split(' ')[-1]}")
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()
    print("Enhanced database migration completed successfully!")


# =====================================
# 🗄️ DATABASE MIGRATION FOR EXISTING DATABASES
# =====================================

def migrate_database():
    """Add new columns to existing database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # List of new columns to add
    new_columns = [
        ('extraction_method', 'TEXT DEFAULT "olsen_modified"'),
        ('surface_area', 'REAL DEFAULT 1.0'),
        ('phosphorus_ppm', 'REAL'),
        ('potassium_cmol', 'REAL'),
        ('calcium_cmol', 'REAL'),
        ('magnesium_cmol', 'REAL'),
        ('iron_ppm', 'REAL'),
        ('copper_ppm', 'REAL'),
        ('manganese_ppm', 'REAL'),
        ('zinc_ppm', 'REAL'),
        ('exchangeable_acidity', 'REAL'),
        ('cec', 'REAL'),
        ('base_saturation', 'REAL'),
        ('acid_saturation', 'REAL'),
        ('bulk_density', 'REAL DEFAULT 1.3'),
        ('porosity', 'REAL DEFAULT 50.0'),
        ('effective_depth', 'REAL DEFAULT 20.0'),
        ('fertility_index', 'REAL'),
        ('soil_health_score', 'REAL'),
        ('estimated_yield_potential', 'REAL'),
        ('ca_mg_ratio', 'REAL'),
        ('ca_k_ratio', 'REAL'),
        ('mg_k_ratio', 'REAL'),
        ('lime_needed', 'REAL'),
        ('lime_type', 'TEXT DEFAULT "caco3"'),
        ('target_ae', 'REAL DEFAULT 0.5'),
        ('lime_cost', 'REAL'),
        ('phosphorus_needed', 'REAL'),
        ('potassium_needed', 'REAL'),
        ('estimated_cost', 'REAL'),
        ('nutrient_status', 'TEXT'),
        ('micronutrient_status', 'TEXT'),
        ('limiting_factors', 'TEXT'),
        ('fertilization_plan', 'TEXT'),
        ('lime_calculation', 'TEXT')
    ]
    
    # Try to add each column
    for column_name, column_type in new_columns:
        try:
            cursor.execute(f'ALTER TABLE soil_analyses ADD COLUMN {column_name} {column_type}')
            print(f"Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()
    
# =====================================
# 🗄️ ENHANCED DATABASE MIGRATION FOR PHYSICAL PARAMETERS
# =====================================

def migrate_database_physical_params():
    """Add new physical parameter columns to existing database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # List of new physical parameter columns to add
    new_physical_columns = [
        ('particle_density', 'REAL DEFAULT 2.65'),
        ('land_area_ha', 'REAL DEFAULT 1.0'),
        ('soil_depth_cm', 'REAL DEFAULT 20.0'),
        ('calculated_porosity', 'REAL'),
        ('soil_volume_m3_ha', 'REAL'),
        ('soil_mass_kg_ha', 'REAL'),
        ('lime_needed_total_kg', 'REAL'),
        ('density_adjustment_factor', 'REAL'),
        ('depth_adjustment_factor', 'REAL')
    ]
    
    # Try to add each column
    for column_name, column_type in new_physical_columns:
        try:
            cursor.execute(f'ALTER TABLE soil_analyses ADD COLUMN {column_name} {column_type}')
            print(f"Added physical parameter column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"Error adding column {column_name}: {e}")
    
    # Add pro_plan_expires_at column to users table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN pro_plan_expires_at TIMESTAMP NULL')
        print("Added pro_plan_expires_at column to users table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            pass  # Column already exists
        else:
            print(f"Error adding pro_plan_expires_at column: {e}")
    
    conn.commit()
    conn.close()    

# =====================================
# 🔐 AUTHENTICATION HELPERS
# =====================================

def login_required(f):
    """Decorator to require login and check plan expiration"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        # Check if current user's Pro plan has expired
        user_id = session['user_id']
        try:
            user = query_db('''
                SELECT plan_type, pro_plan_expires_at 
                FROM users 
                WHERE id = ?
            ''', [user_id], one=True)
            
            if user and user['plan_type'] == 'pro' and user['pro_plan_expires_at']:
                from datetime import datetime
                expiry_date = datetime.fromisoformat(user['pro_plan_expires_at'].replace('Z', '+00:00'))
                if expiry_date < datetime.now():
                    # Downgrade expired user
                    execute_db('''
                        UPDATE users 
                        SET plan_type = 'free', pro_plan_expires_at = NULL 
                        WHERE id = ?
                    ''', [user_id])
                    session['plan_type'] = 'free'
                    flash('Your Pro plan has expired. You have been downgraded to the Free plan.', 'warning')
        except sqlite3.OperationalError:
            # Column doesn't exist yet, skip expiration check
            pass
        
        return f(*args, **kwargs)
    return decorated_function

# =====================================
# 🧮 ENHANCED LIME CALCULATION ENGINE WITH SCIENTIFIC METHOD
# =====================================

class EnhancedLimeCalculator:
    """Enhanced lime calculation using scientifically proven method: t/ha = 5 × ΔAE × ρb × d × Sf"""
    
    # Soil type buffering factors - influence on lime requirements
    SOIL_TYPE_FACTORS = {
        'sandy': {
            'name': 'Sandy Soil',
            'buffering_factor': 0.7,  # Lower buffering capacity, needs less lime
            'description': 'Low clay content, low CEC, quick pH response',
            'characteristics': 'Fast drainage, low nutrient retention'
        },
        'loamy': {
            'name': 'Loamy Soil', 
            'buffering_factor': 1.0,  # Reference soil type
            'description': 'Balanced texture, moderate CEC, standard lime response',
            'characteristics': 'Good drainage and nutrient retention'
        },
        'clay': {
            'name': 'Clay Soil',
            'buffering_factor': 1.4,  # High buffering capacity, needs more lime
            'description': 'High clay content, high CEC, slow pH response',
            'characteristics': 'Poor drainage, high nutrient retention'
        },
        'organic': {
            'name': 'Organic/Peat Soil',
            'buffering_factor': 1.6,  # Very high buffering capacity
            'description': 'High organic matter, very high CEC, very slow pH response',
            'characteristics': 'High water retention, complex nutrient dynamics'
        },
        'calcareous': {
            'name': 'Calcareous Soil',
            'buffering_factor': 0.3,  # Already contains lime, minimal additional needed
            'description': 'Contains natural lime, high pH buffering',
            'characteristics': 'High pH, may have micronutrient deficiencies'
        }
    }
    
    # Lime types with their theoretical CCE factors (chemistry-based)
    LIME_TYPES = {
        'caco3': {
            'name': 'Calcium Carbonate (CaCO₃)',
            'formula': 'CaCO₃',
            'cce_factor': 1.0,  # Reference material
            'multiplier': 1.0,  # 1/1.0 = 1.0
            'description': 'Standard agricultural lime (reference)',
            'speed': 'Slow',
            'molecular_factor': 1.0  # CaCO₃ to CaCO₃-eq
        },
        'dolomitic': {
            'name': 'Dolomitic Lime (CaCO₃+MgCO₃)',
            'formula': 'CaCO₃+MgCO₃',
            'cce_factor': 1.09,  # Theoretical CCE
            'multiplier': 0.917,  # 1/1.09
            'description': 'Contains both calcium and magnesium',
            'speed': 'Slow',
            'molecular_factor': 1.09
        },
        'hydrated': {
            'name': 'Calcium Hydroxide (Ca(OH)₂)',
            'formula': 'Ca(OH)₂',
            'cce_factor': 1.35,  # Theoretical CCE  
            'multiplier': 0.741,  # 1/1.35
            'description': 'Quick lime, fast acting',
            'speed': 'Fast',
            'molecular_factor': 1.35
        },
        'oxide': {
            'name': 'Calcium Oxide (CaO)',
            'formula': 'CaO',
            'cce_factor': 1.78,  # Theoretical CCE
            'multiplier': 0.562,  # 1/1.78
            'description': 'Burnt lime, very fast acting',
            'speed': 'Very Fast',
            'molecular_factor': 1.78
        },
        'magnesium_oxide': {
            'name': 'Magnesium Oxide (MgO)',
            'formula': 'MgO',
            'cce_factor': 2.47,  # Theoretical CCE
            'multiplier': 0.405,  # 1/2.47
            'description': 'High magnesium content',
            'speed': 'Very Fast',
            'molecular_factor': 2.47
        }
    }
    
    @staticmethod
    def calculate_physical_properties(bulk_density_g_cm3, particle_density_g_cm3=2.65):
        """
        Calculate physical soil properties
        
        Args:
            bulk_density_g_cm3 (float): Bulk density in g/cm³
            particle_density_g_cm3 (float): Particle density in g/cm³ (default 2.65 for mineral soils)
        
        Returns:
            dict: Physical properties including porosity
        """
        # Convert g/cm³ to kg/m³ for calculations if needed
        bulk_density_kg_m3 = bulk_density_g_cm3 * 1000
        particle_density_kg_m3 = particle_density_g_cm3 * 1000
        
        # Calculate porosity: φ = (1 - ρb/ρs) × 100
        porosity_percent = (1 - (bulk_density_g_cm3 / particle_density_g_cm3)) * 100
        
        return {
            'bulk_density_g_cm3': bulk_density_g_cm3,
            'bulk_density_kg_m3': bulk_density_kg_m3,
            'particle_density_g_cm3': particle_density_g_cm3,
            'particle_density_kg_m3': particle_density_kg_m3,
            'porosity_percent': round(porosity_percent, 1),
            'porosity_fraction': round(porosity_percent / 100, 3)
        }
    
    @staticmethod
    def calculate_soil_volume_and_mass(land_area_ha, depth_cm, bulk_density_g_cm3):
        """
        Calculate soil volume and mass for lime application - CORRECTED
        
        Args:
            land_area_ha (float): Land area in hectares
            depth_cm (float): Soil depth in centimeters
            bulk_density_g_cm3 (float): Bulk density in g/cm³
        
        Returns:
            dict: Volume and mass calculations
        """
        # Convert units
        depth_m = depth_cm / 100  # cm to m
        
        # Calculate volume per hectare (1 hectare = 10,000 m²)
        soil_volume_m3_per_ha = 10000 * depth_m  # m³/ha
        soil_volume_m3_total = soil_volume_m3_per_ha * land_area_ha  # m³ total
        
        # Calculate mass
        bulk_density_kg_m3 = bulk_density_g_cm3 * 1000  # Convert g/cm³ to kg/m³
        soil_mass_kg_per_ha = soil_volume_m3_per_ha * bulk_density_kg_m3  # kg/ha
        soil_mass_mg_per_ha = soil_mass_kg_per_ha / 1000  # Mg/ha (tonnes/ha)
        soil_mass_total_mg = soil_mass_mg_per_ha * land_area_ha  # Mg total
        
        return {
            'land_area_ha': land_area_ha,
            'land_area_m2': land_area_ha * 10000,
            'depth_cm': depth_cm,
            'depth_m': depth_m,
            'soil_volume_m3_per_ha': round(soil_volume_m3_per_ha, 0),
            'soil_volume_m3_total': round(soil_volume_m3_total, 0),
            'soil_mass_kg_per_ha': round(soil_mass_kg_per_ha, 0),
            'soil_mass_mg_per_ha': round(soil_mass_mg_per_ha, 1),
            'soil_mass_total_mg': round(soil_mass_total_mg, 1)
        }
    
    @staticmethod
    def calculate_enhanced_lime_requirement(exchangeable_acidity, lime_type='caco3', target_ae=0.5,
                                          land_area_ha=1.0, depth_cm=20.0, bulk_density_g_cm3=1.3,
                                          particle_density_g_cm3=2.65, product_ecce=100.0, soil_type='loamy'):
        """
        Enhanced lime requirement calculation using scientific method:
        t/ha = 5 × ΔAE × ρb × d × Sf (for CaCO₃-equivalent)
        
        Args:
            exchangeable_acidity (float): Current EA in cmol+/kg
            lime_type (str): Type of lime to use
            target_ae (float): Target EA level (default 0.5 cmol+/kg)
            soil_type (str): Soil type affecting buffering capacity
            land_area_ha (float): Land area in hectares
            depth_cm (float): Soil depth in centimeters
            bulk_density_g_cm3 (float): Bulk density in g/cm³
            particle_density_g_cm3 (float): Particle density in g/cm³
            product_ecce (float): Effective CCE of the commercial product (%)
        
        Returns:
            dict: Enhanced lime calculation results using scientific method
        """
        
        # Calculate physical properties
        physical_props = EnhancedLimeCalculator.calculate_physical_properties(
            bulk_density_g_cm3, particle_density_g_cm3
        )
        
        # Calculate soil volume and mass
        soil_calcs = EnhancedLimeCalculator.calculate_soil_volume_and_mass(
            land_area_ha, depth_cm, bulk_density_g_cm3
        )
        
        # Get soil type buffering factor
        if soil_type not in EnhancedLimeCalculator.SOIL_TYPE_FACTORS:
            soil_type = 'loamy'  # Default to loamy if invalid soil type
        
        soil_factor = EnhancedLimeCalculator.SOIL_TYPE_FACTORS[soil_type]['buffering_factor']
        soil_info = EnhancedLimeCalculator.SOIL_TYPE_FACTORS[soil_type]
        
        # If EA is already at or below target, no lime needed
        if exchangeable_acidity <= target_ae:
            return {
                'lime_needed_kg_ha': 0,
                'lime_needed_t_ha': 0,
                'lime_needed_kg_total': 0,
                'lime_needed_t_total': 0,
                'ae_to_neutralize': 0,
                'lime_type': lime_type,
                'lime_name': EnhancedLimeCalculator.LIME_TYPES[lime_type]['name'],
                'lime_formula': EnhancedLimeCalculator.LIME_TYPES[lime_type]['formula'],
                'cce_factor': EnhancedLimeCalculator.LIME_TYPES[lime_type]['cce_factor'],
                'current_ae': exchangeable_acidity,
                'target_ae': target_ae,
                'speed': EnhancedLimeCalculator.LIME_TYPES[lime_type]['speed'],
                'product_ecce': product_ecce,
                'soil_type': soil_type,
                'soil_type_name': soil_info['name'],
                'soil_buffering_factor': soil_factor,
                'message': f'✅ Exchangeable Acidity ({exchangeable_acidity:.2f}) is already at target level ({target_ae:.2f})',
                'calculation_method': 'Scientific Formula: t/ha = 5 × ΔAE × ρb × d × Sf',
                'physical_properties': physical_props,
                'soil_calculations': soil_calcs
            }
        
        # Calculate acidity to neutralize
        ae_to_neutralize = exchangeable_acidity - target_ae
        
        # Get lime type data
        lime_data = EnhancedLimeCalculator.LIME_TYPES[lime_type]
        
        # ENHANCED SCIENTIFIC METHOD: t/ha = 5 × ΔAE × ρb × d × Sf
        # Convert depth from cm to meters for the formula
        depth_m = depth_cm / 100
        caco3_eq_t_ha = 5 * ae_to_neutralize * bulk_density_g_cm3 * depth_m * soil_factor
        
        # Convert to the specific lime type using theoretical CCE factor
        lime_t_ha = caco3_eq_t_ha / lime_data['cce_factor']
        
        # Adjust for commercial product ECCE if < 100%
        product_ecce_fraction = product_ecce / 100.0
        if product_ecce_fraction < 1.0:
            lime_t_ha_real = lime_t_ha / product_ecce_fraction
        else:
            lime_t_ha_real = lime_t_ha
        
        # Convert to kg/ha
        lime_kg_ha = lime_t_ha_real * 1000
        
        # Calculate total for the entire area
        lime_kg_total = lime_kg_ha * land_area_ha
        lime_t_total = lime_t_ha_real * land_area_ha
        
        # Safety cap at reasonable maximum (8000 kg/ha = 8 t/ha)
        if lime_kg_ha > 8000:
            lime_kg_ha = 8000
            lime_t_ha_real = 8.0
            lime_kg_total = lime_kg_ha * land_area_ha
            lime_t_total = lime_t_ha_real * land_area_ha
            safety_cap_applied = True
        else:
            safety_cap_applied = False
        
        # Generate comprehensive message with soil type consideration
        if soil_factor != 1.0:
            soil_adjustment_msg = f" (adjusted {soil_factor}x for {soil_info['name']})"
        else:
            soil_adjustment_msg = ""
        
        message = f"🪨 Apply {lime_t_ha_real:.2f} t/ha of {lime_data['name']}{soil_adjustment_msg}"
        
        # Add soil type specific recommendations
        if soil_type == 'sandy':
            message += " • Apply in split applications to prevent leaching"
        elif soil_type == 'clay':
            message += " • Allow extra time for pH response (6-12 months)"
        elif soil_type == 'organic':
            message += " • Monitor pH closely, may need repeated applications"
        elif soil_type == 'calcareous':
            message += " • Consider sulfur instead if pH is already high"
        
        # Prepare detailed explanation
        formula_explanation = f"""
        🧮 Enhanced Scientific Calculation Method:
        1. CaCO₃-eq needed: t/ha = 5 × {ae_to_neutralize:.2f} × {bulk_density_g_cm3} × {depth_m:.2f} × {soil_factor} = {caco3_eq_t_ha:.3f} t/ha
        2. {lime_data['name']}: {caco3_eq_t_ha:.3f} ÷ {lime_data['cce_factor']} = {lime_t_ha:.3f} t/ha
        3. Commercial ECCE adjustment: {lime_t_ha:.3f} ÷ {product_ecce_fraction:.2f} = {lime_t_ha_real:.3f} t/ha
        4. Soil type factor ({soil_info['name']}): {soil_factor}x buffering adjustment
        5. Final recommendation: {lime_kg_ha:.0f} kg/ha ({lime_t_ha_real:.2f} t/ha)
        """
        
        return {
            # Main results
            'lime_needed_kg_ha': round(lime_kg_ha, 0),
            'lime_needed_t_ha': round(lime_t_ha_real, 3),
            'lime_needed_kg_total': round(lime_kg_total, 0),
            'lime_needed_t_total': round(lime_t_total, 3),
            
            # CaCO₃-equivalent calculations
            'caco3_eq_t_ha': round(caco3_eq_t_ha, 3),
            'caco3_eq_kg_ha': round(caco3_eq_t_ha * 1000, 0),
            
            # Lime type specific
            'lime_type_t_ha': round(lime_t_ha, 3),  # Before ECCE adjustment
            'lime_type_kg_ha': round(lime_t_ha * 1000, 0),  # Before ECCE adjustment
            
            # Input parameters
            'ae_to_neutralize': round(ae_to_neutralize, 2),
            'lime_type': lime_type,
            'lime_name': lime_data['name'],
            'lime_formula': lime_data['formula'],
            'cce_factor': lime_data['cce_factor'],
            'target_ae': target_ae,
            'current_ae': exchangeable_acidity,
            'speed': lime_data['speed'],
            'product_ecce': product_ecce,
            'product_ecce_fraction': product_ecce_fraction,
            
            # Calculation details
            'bulk_density': bulk_density_g_cm3,
            'depth_m': depth_m,
            'depth_cm': depth_cm,
            'land_area_ha': land_area_ha,
            'safety_cap_applied': safety_cap_applied,
            
            # Soil type information
            'soil_type': soil_type,
            'soil_type_name': soil_info['name'],
            'soil_buffering_factor': soil_factor,
            'soil_description': soil_info['description'],
            'soil_characteristics': soil_info['characteristics'],
            
            # Messages and explanations
            'message': message,
            'calculation_method': 'Scientific Formula: t/ha = 5 × ΔAE × ρb × d × Sf',
            'formula_explanation': formula_explanation,
            'safety_message': '⚠️ Application capped at 8 t/ha for safety' if safety_cap_applied else '',
            
            # Additional data
            'physical_properties': physical_props,
            'soil_calculations': soil_calcs
        }
    
    @staticmethod
    def compare_all_lime_types(exchangeable_acidity, target_ae=0.5, land_area_ha=1.0, 
                              depth_cm=20.0, bulk_density_g_cm3=1.3, product_ecce=100.0, soil_type='loamy'):
        """
        Compare lime requirements for all lime types using scientific method
        
        Returns:
            dict: Comparison of all lime types
        """
        comparison = {}
        
        # Get soil type buffering factor
        if soil_type not in EnhancedLimeCalculator.SOIL_TYPE_FACTORS:
            soil_type = 'loamy'  # Default to loamy if invalid soil type
        
        soil_factor = EnhancedLimeCalculator.SOIL_TYPE_FACTORS[soil_type]['buffering_factor']
        
        # Calculate CaCO₃-equivalent requirement first with soil type factor
        ae_to_neutralize = max(0, exchangeable_acidity - target_ae)
        depth_m = depth_cm / 100
        caco3_eq_t_ha = 5 * ae_to_neutralize * bulk_density_g_cm3 * depth_m * soil_factor
        
        for lime_type, lime_data in EnhancedLimeCalculator.LIME_TYPES.items():
            # Calculate requirement for this lime type
            lime_t_ha = caco3_eq_t_ha / lime_data['cce_factor']
            
            # Adjust for commercial ECCE
            product_ecce_fraction = product_ecce / 100.0
            lime_t_ha_real = lime_t_ha / product_ecce_fraction if product_ecce_fraction < 1.0 else lime_t_ha
            
            comparison[lime_type] = {
                'name': lime_data['name'],
                'formula': lime_data['formula'],
                'cce_factor': lime_data['cce_factor'],
                'speed': lime_data['speed'],
                'kg_ha': round(lime_t_ha_real * 1000, 0),
                't_ha': round(lime_t_ha_real, 3),
                'kg_total': round(lime_t_ha_real * 1000 * land_area_ha, 0),
                't_total': round(lime_t_ha_real * land_area_ha, 3),
                'cost_efficiency': round(1 / lime_data['cce_factor'], 3)  # Higher = more efficient
            }
        
        return {
            'caco3_eq_requirement': {
                't_ha': round(caco3_eq_t_ha, 3),
                'kg_ha': round(caco3_eq_t_ha * 1000, 0)
            },
            'lime_types': comparison,
            'calculation_parameters': {
                'ae_to_neutralize': ae_to_neutralize,
                'depth_m': depth_m,
                'bulk_density': bulk_density_g_cm3,
                'land_area_ha': land_area_ha,
                'product_ecce': product_ecce
            }
        }


# =====================================
# 💊 COMPREHENSIVE FERTILIZER CALCULATION ENGINE WITH ALL NUTRIENTS
# =====================================

class ComprehensiveFertilizerCalculator:
    """Complete fertilizer calculator with macro, secondary, and micronutrients plus smart product selection"""
    
    # Conversion factors from elemental to oxide forms
    CONVERSION_FACTORS = {
        'P_to_P2O5': 2.29,      # P × 2.29 = P2O5
        'K_to_K2O': 1.205,     # K × 1.205 = K2O
        'Ca_to_CaO': 1.399,    # Ca × 1.399 = CaO
        'Mg_to_MgO': 1.658,    # Mg × 1.658 = MgO
        'S_to_SO4': 3.0,       # S × 3.0 = SO4
        'P2O5_to_P': 0.436,    # P2O5 × 0.436 = P
        'K2O_to_K': 0.830,     # K2O × 0.830 = K
        'CaO_to_Ca': 0.715,    # CaO × 0.715 = Ca
        'MgO_to_Mg': 0.603,    # MgO × 0.603 = Mg
        'SO4_to_S': 0.333      # SO4 × 0.333 = S
    }
    
    # REAL COMMERCIAL FERTILIZER PRODUCTS DATABASE - USA MARKET 2025
    FERTILIZER_PRODUCTS = {
        # === MAJOR BRAND NPK FERTILIZERS ===
        'Miracle-Gro All Purpose Plant Food 24-8-16': {'N': 24, 'P2O5': 8, 'K2O': 16, 'price_per_kg': 3.85, 'category': 'compound', 'brand': 'Miracle-Gro'},
        'Scotts Turf Builder Lawn Food 32-0-4': {'N': 32, 'P2O5': 0, 'K2O': 4, 'price_per_kg': 2.95, 'category': 'primary', 'brand': 'Scotts'},
        'Osmocote Smart-Release Plant Food 14-14-14': {'N': 14, 'P2O5': 14, 'K2O': 14, 'price_per_kg': 4.25, 'category': 'compound', 'brand': 'Osmocote'},
        'Jacks Classic All Purpose 20-20-20': {'N': 20, 'P2O5': 20, 'K2O': 20, 'price_per_kg': 3.15, 'category': 'compound', 'brand': 'JR Peters'},
        'Peters Professional 15-30-15': {'N': 15, 'P2O5': 30, 'K2O': 15, 'price_per_kg': 2.85, 'category': 'compound', 'brand': 'JR Peters'},
        
        # === NITROGEN FERTILIZERS ===
        'Southern Ag Urea 46-0-0': {'N': 46, 'P2O5': 0, 'K2O': 0, 'price_per_kg': 1.25, 'category': 'primary', 'brand': 'Southern Ag'},
        'Ferti-lome Ammonium Sulfate 21-0-0': {'N': 21, 'P2O5': 0, 'K2O': 0, 'S': 24, 'price_per_kg': 1.45, 'category': 'primary', 'brand': 'Ferti-lome'},
        'Greenway Biotech Calcium Nitrate 15.5-0-0': {'N': 15.5, 'P2O5': 0, 'K2O': 0, 'Ca': 19, 'price_per_kg': 1.85, 'category': 'primary', 'brand': 'Greenway Biotech'},
        'Hi-Yield Blood Meal 12-0-0': {'N': 12, 'P2O5': 0, 'K2O': 0, 'price_per_kg': 2.95, 'category': 'organic', 'brand': 'Hi-Yield'},
        
        # === PHOSPHORUS FERTILIZERS ===
        'Espoma Rock Phosphate 0-3-0': {'N': 0, 'P2O5': 3, 'K2O': 0, 'Ca': 30, 'price_per_kg': 1.65, 'category': 'organic', 'brand': 'Espoma'},
        'Southern Ag Triple Super Phosphate 0-46-0': {'N': 0, 'P2O5': 46, 'K2O': 0, 'price_per_kg': 1.95, 'category': 'primary', 'brand': 'Southern Ag'},
        'Hi-Yield Bone Meal 4-12-0': {'N': 4, 'P2O5': 12, 'K2O': 0, 'Ca': 24, 'price_per_kg': 2.45, 'category': 'organic', 'brand': 'Hi-Yield'},
        
        # === POTASSIUM FERTILIZERS ===
        'Greenway Biotech Muriate of Potash 0-0-60': {'N': 0, 'P2O5': 0, 'K2O': 60, 'price_per_kg': 1.35, 'category': 'primary', 'brand': 'Greenway Biotech'},
        'Southern Ag Sulfate of Potash 0-0-50': {'N': 0, 'P2O5': 0, 'K2O': 50, 'S': 18, 'price_per_kg': 1.75, 'category': 'primary', 'brand': 'Southern Ag'},
        'Down to Earth Kelp Meal 1-0-2': {'N': 1, 'P2O5': 0, 'K2O': 2, 'price_per_kg': 3.25, 'category': 'organic', 'brand': 'Down to Earth'},
        
        # === SECONDARY NUTRIENTS ===
        'Espoma Garden Gypsum 0-0-0': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 23, 'S': 18, 'price_per_kg': 0.85, 'category': 'secondary', 'brand': 'Espoma'},
        'Greenway Biotech Epsom Salt': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mg': 10, 'S': 13, 'price_per_kg': 1.15, 'category': 'secondary', 'brand': 'Greenway Biotech'},
        'Jobe\'s Organics Bone Meal 2-14-0': {'N': 2, 'P2O5': 14, 'K2O': 0, 'Ca': 24, 'price_per_kg': 2.85, 'category': 'organic', 'brand': 'Jobe\'s'},
        'Down to Earth Dolomite Lime': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 22, 'Mg': 12, 'price_per_kg': 0.65, 'category': 'secondary', 'brand': 'Down to Earth'},
        
        # === MICRONUTRIENT PRODUCTS ===
        'Southern Ag Zinc Sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Zn': 35, 'S': 17, 'price_per_kg': 4.25, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Iron Sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 20, 'S': 11, 'price_per_kg': 2.95, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        'Hi-Yield Iron Plus Soil Acidifier': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 11, 'S': 15, 'price_per_kg': 3.45, 'category': 'micronutrient', 'brand': 'Hi-Yield'},
        'Ferti-lome Chelated Iron': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 10, 'price_per_kg': 8.95, 'category': 'micronutrient', 'brand': 'Ferti-lome'},
        'Southern Ag Manganese Sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mn': 32, 'S': 15, 'price_per_kg': 4.85, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Copper Sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Cu': 25, 'S': 12, 'price_per_kg': 5.25, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        
        # === PREMIUM MULTI-NUTRIENT BLENDS ===
        'Osmocote Plus 15-9-12': {'N': 15, 'P2O5': 9, 'K2O': 12, 'Mg': 2.5, 'S': 5.5, 'Fe': 0.45, 'Mn': 0.06, 'price_per_kg': 5.95, 'category': 'complete', 'brand': 'Osmocote'},
        'Miracle-Gro Shake n Feed 12-4-8': {'N': 12, 'P2O5': 4, 'K2O': 8, 'Ca': 2, 'Mg': 1, 'S': 3, 'price_per_kg': 4.15, 'category': 'complete', 'brand': 'Miracle-Gro'},
        'Jobe\'s Organics All Purpose 4-4-4': {'N': 4, 'P2O5': 4, 'K2O': 4, 'Ca': 6, 'S': 1, 'price_per_kg': 3.85, 'category': 'organic', 'brand': 'Jobe\'s'},
        'Espoma Plant-tone 5-3-3': {'N': 5, 'P2O5': 3, 'K2O': 3, 'Ca': 5, 'Mg': 1, 'S': 1, 'price_per_kg': 3.25, 'category': 'organic', 'brand': 'Espoma'},
        
        # === SPECIALTY MICRONUTRIENT BLENDS ===
        'Southern Ag Essential Minor Elements': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 8, 'Cu': 2, 'Mn': 5, 'Zn': 3, 'B': 1, 'Mo': 0.1, 'price_per_kg': 12.95, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Micronutrient Mix': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 6, 'Cu': 1.5, 'Mn': 4, 'Zn': 2.5, 'B': 0.8, 'price_per_kg': 9.85, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        
        # === LIQUID FERTILIZERS ===
        'Miracle-Gro Liquid All Purpose 12-4-8': {'N': 12, 'P2O5': 4, 'K2O': 8, 'price_per_kg': 6.25, 'category': 'liquid', 'brand': 'Miracle-Gro'},
        'Jack\'s Classic Blossom Booster 10-30-20': {'N': 10, 'P2O5': 30, 'K2O': 20, 'price_per_kg': 4.95, 'category': 'liquid', 'brand': 'JR Peters'},
        'General Hydroponics Flora Series': {'N': 8, 'P2O5': 5, 'K2O': 13, 'Ca': 3, 'Mg': 1.5, 'price_per_kg': 8.95, 'category': 'hydroponic', 'brand': 'General Hydroponics'}
    }
    
    @staticmethod
    def calculate_comprehensive_nutrient_requirements(current_levels, target_levels, 
                                                    extraction_method='olsen_modified', 
                                                    surface_area_ha=1.0, **kwargs):
        """
        Calculate ALL nutrient requirements: primary, secondary, and micronutrients
        """
        
        # Extract physical parameters
        bulk_density = float(kwargs.get('bulk_density', kwargs.get('bulk_density_g_cm3', 1.3)))
        soil_depth_cm = float(kwargs.get('soil_depth_cm', kwargs.get('depth_cm', 20)))
        soil_ph = float(kwargs.get('soil_ph', kwargs.get('ph', 6.5)))
        soil_om_pct = float(kwargs.get('organic_matter', 3.0))
        crop_type = kwargs.get('crop_type', 'general')
        expected_yield = float(kwargs.get('expected_yield', 5.0))
        
        # Calculate soil mass for ppm conversions
        soil_mass_kg_ha = 10000 * (soil_depth_cm/100) * (bulk_density*1000)
        
        # === PRIMARY NUTRIENTS (NPK) ===
        current_p_ppm = float(current_levels.get('phosphorus_ppm', 0))
        current_k_cmol = float(current_levels.get('potassium_cmol', 0))
        target_p_ppm = float(target_levels.get('phosphorus_ppm', 15))
        target_k_cmol = float(target_levels.get('potassium_cmol', 0.4))
        
        p_deficit_ppm = max(0, target_p_ppm - current_p_ppm)
        k_deficit_cmol = max(0, target_k_cmol - current_k_cmol)
        
        # Physics-based conversions with method-specific coefficients
        p_build_up_coeff = 0.75 if extraction_method == 'olsen_modified' else 0.65
        k_build_up_efficiency = 0.85 if soil_ph < 7.0 else 0.75  # pH affects K availability
        
        p_conversion_factor = ComprehensiveFertilizerCalculator.p_ppm_to_p2o5_factor_kg_ha(
            bulk_density_g_cm3=bulk_density, depth_cm=soil_depth_cm, build_up_coeff=p_build_up_coeff)
        k_conversion_factor = ComprehensiveFertilizerCalculator.k_cmol_to_k2o_factor_kg_ha(
            bulk_density_g_cm3=bulk_density, depth_cm=soil_depth_cm, efficiency=k_build_up_efficiency)
        
        p2o5_needed_kg_ha = p_deficit_ppm * p_conversion_factor
        k2o_needed_kg_ha = k_deficit_cmol * k_conversion_factor
        
        # Nitrogen calculation
        n_calculation = ComprehensiveFertilizerCalculator.estimate_n_requirement_kg_ha(
            crop=crop_type, expected_yield=expected_yield, soil_om_pct=soil_om_pct,
            previous_crop_credit=float(kwargs.get('previous_crop_n_credit', 0)),
            residual_nitrate_credit=float(kwargs.get('residual_n_credit', 0)))
        n_needed_kg_ha = n_calculation['net_requirement']
        
        # === SECONDARY NUTRIENTS ===
        # Calcium (scientifically accurate conversion)
        current_ca_cmol = float(current_levels.get('calcium_cmol', 0))
        target_ca_cmol = float(target_levels.get('calcium_cmol', 6.0))
        ca_deficit_cmol = max(0, target_ca_cmol - current_ca_cmol)
        # Ca: 1 cmol/kg = 200 mg Ca/kg soil = 0.2 kg Ca/1000 kg soil
        ca_elemental_kg_ha = ca_deficit_cmol * soil_mass_kg_ha * 0.0002
        ca_needed_kg_ha = ca_elemental_kg_ha * ComprehensiveFertilizerCalculator.CONVERSION_FACTORS['Ca_to_CaO'] * 0.8
        
        # Magnesium (scientifically accurate conversion)
        current_mg_cmol = float(current_levels.get('magnesium_cmol', 0))
        target_mg_cmol = float(target_levels.get('magnesium_cmol', 2.0))
        mg_deficit_cmol = max(0, target_mg_cmol - current_mg_cmol)
        # Mg: 1 cmol/kg = 121.5 mg Mg/kg soil = 0.1215 kg Mg/1000 kg soil
        mg_elemental_kg_ha = mg_deficit_cmol * soil_mass_kg_ha * 0.0001215
        mg_needed_kg_ha = mg_elemental_kg_ha * ComprehensiveFertilizerCalculator.CONVERSION_FACTORS['Mg_to_MgO'] * 0.8
        
        # Sulfur (estimate based on crop needs and soil test if available)
        current_s_ppm = float(current_levels.get('sulfur_ppm', 0))
        target_s_ppm = 20.0  # General target for sulfur
        s_deficit_ppm = max(0, target_s_ppm - current_s_ppm) if current_s_ppm > 0 else 10  # Default need
        s_needed_kg_ha = s_deficit_ppm * (soil_mass_kg_ha * 1e-6) * 2.0  # S build-up factor
        
        # === MICRONUTRIENTS ===
        micronutrients_needed = {}
        micronutrient_targets = {
            'iron': 20, 'copper': 2, 'manganese': 10, 'zinc': 3, 'boron': 1, 'molybdenum': 0.2
        }
        
        for nutrient, target_ppm in micronutrient_targets.items():
            current_ppm = float(current_levels.get(f'{nutrient}_ppm', 0))
            deficit_ppm = max(0, target_ppm - current_ppm)
            
            if deficit_ppm > 0:
                # Calculate kg/ha needed with availability factors
                availability_factor = 0.3 if soil_ph > 7 else 0.5  # Reduced availability in alkaline soils
                kg_needed = deficit_ppm * (soil_mass_kg_ha * 1e-6) / availability_factor
                micronutrients_needed[nutrient] = {
                    'deficit_ppm': deficit_ppm,
                    'kg_ha_needed': round(kg_needed, 2),
                    'availability_factor': availability_factor
                }
        
        return {
            # Primary nutrients (NPK)
            'N_needed_kg_ha': round(n_needed_kg_ha, 1),
            'P2O5_needed_kg_ha': round(p2o5_needed_kg_ha, 1),
            'K2O_needed_kg_ha': round(k2o_needed_kg_ha, 1),
            
            # Secondary nutrients
            'Ca_needed_kg_ha': round(ca_needed_kg_ha, 1),
            'Mg_needed_kg_ha': round(mg_needed_kg_ha, 1),
            'S_needed_kg_ha': round(s_needed_kg_ha, 1),
            
            # Micronutrients
            'micronutrients_needed': micronutrients_needed,
            
            # Total field requirements
            'surface_area_ha': surface_area_ha,
            'total_field_requirements': {
                'N_total': round(n_needed_kg_ha * surface_area_ha, 1),
                'P2O5_total': round(p2o5_needed_kg_ha * surface_area_ha, 1),
                'K2O_total': round(k2o_needed_kg_ha * surface_area_ha, 1),
                'Ca_total': round(ca_needed_kg_ha * surface_area_ha, 1),
                'Mg_total': round(mg_needed_kg_ha * surface_area_ha, 1),
                'S_total': round(s_needed_kg_ha * surface_area_ha, 1),
            },
            
            # Calculation parameters
            'soil_ph': soil_ph,
            'bulk_density': bulk_density,
            'soil_mass_kg_ha': soil_mass_kg_ha,
            'extraction_method': extraction_method,
            'crop_type': crop_type
        }
    
    @staticmethod
    def calculate_optimal_commercial_products(nutrient_requirements):
        """
        SMART PRODUCT SELECTION: Find the best combination of commercial products 
        that provides optimal nutrient compensation with minimal waste and cost
        """
        
        # Extract needs
        needs = {
            'N': nutrient_requirements['N_needed_kg_ha'],
            'P2O5': nutrient_requirements['P2O5_needed_kg_ha'],
            'K2O': nutrient_requirements['K2O_needed_kg_ha'],
            'Ca': nutrient_requirements['Ca_needed_kg_ha'],
            'Mg': nutrient_requirements['Mg_needed_kg_ha'],
            'S': nutrient_requirements['S_needed_kg_ha'],
        }
        
        # Add micronutrient needs
        for nutrient, data in nutrient_requirements['micronutrients_needed'].items():
            needs[nutrient.title()] = data['kg_ha_needed']
        
        surface_area = nutrient_requirements['surface_area_ha']
        
        # Initialize tracking
        remaining_needs = needs.copy()
        recommendations = []
        total_cost_per_ha = 0
        
        # === STRATEGY 1: SMART COMPOUND FERTILIZER SELECTION ===
        if needs['N'] > 0 or needs['P2O5'] > 0 or needs['K2O'] > 0:
            best_compound = ComprehensiveFertilizerCalculator._find_best_compound_fertilizer(remaining_needs)
            
            if best_compound:
                product_name, product_data, application_rate, efficiency_score = best_compound
                
                # Calculate nutrients supplied
                nutrients_supplied = {}
                for nutrient in ['N', 'P2O5', 'K2O', 'Ca', 'Mg', 'S']:
                    if nutrient in product_data:
                        supplied = application_rate * (product_data[nutrient] / 100)
                        nutrients_supplied[nutrient] = round(supplied, 1)
                        remaining_needs[nutrient] = max(0, remaining_needs[nutrient] - supplied)
                    else:
                        nutrients_supplied[nutrient] = 0
                
                cost_per_ha = application_rate * product_data['price_per_kg']
                total_cost_per_ha += cost_per_ha
                
                recommendations.append({
                    'product_name': product_name.replace('_', ' '),
                    'product_type': 'Primary Compound',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'application_rate_kg_total': round(application_rate * surface_area, 1),
                    'nutrients_supplied': nutrients_supplied,
                    'cost_per_ha': round(cost_per_ha, 2),
                    'cost_total': round(cost_per_ha * surface_area, 2),
                    'efficiency_score': round(efficiency_score, 2),
                    'priority': 1
                })
        
        # === STRATEGY 2: SECONDARY NUTRIENT PRODUCTS ===
        secondary_products = ComprehensiveFertilizerCalculator._select_secondary_nutrient_products(remaining_needs)
        
        for product_recommendation in secondary_products:
            # Update remaining needs
            for nutrient, supplied in product_recommendation['nutrients_supplied'].items():
                if nutrient in remaining_needs:
                    remaining_needs[nutrient] = max(0, remaining_needs[nutrient] - supplied)
            
            total_cost_per_ha += product_recommendation['cost_per_ha']
            recommendations.append(product_recommendation)
        
        # === STRATEGY 3: MICRONUTRIENT PRODUCTS ===
        micro_products = ComprehensiveFertilizerCalculator._select_micronutrient_products(
            remaining_needs, nutrient_requirements['micronutrients_needed'])
        
        for product_recommendation in micro_products:
            # Update remaining needs
            for nutrient, supplied in product_recommendation['nutrients_supplied'].items():
                if nutrient in remaining_needs:
                    remaining_needs[nutrient] = max(0, remaining_needs[nutrient] - supplied)
            
            total_cost_per_ha += product_recommendation['cost_per_ha']
            recommendations.append(product_recommendation)
        
        # === STRATEGY 4: FILL REMAINING GAPS ===
        gap_fillers = ComprehensiveFertilizerCalculator._fill_remaining_gaps(remaining_needs)
        
        for product_recommendation in gap_fillers:
            total_cost_per_ha += product_recommendation['cost_per_ha']
            recommendations.append(product_recommendation)
        
        # Calculate final nutrient balance
        total_supplied = {}
        for nutrient in needs.keys():
            total_supplied[nutrient] = sum([
                rec['nutrients_supplied'].get(nutrient, 0) for rec in recommendations
            ])
        
        # Calculate coverage percentages
        coverage_percentages = {}
        for nutrient, needed in needs.items():
            if needed > 0:
                coverage_percentages[nutrient] = min(100, (total_supplied[nutrient] / needed) * 100)
            else:
                coverage_percentages[nutrient] = 100
        
        return {
            'fertilizer_recommendations': recommendations,
            'cost_summary': {
                'total_cost_per_ha': round(total_cost_per_ha, 2),
                'total_cost_field': round(total_cost_per_ha * surface_area, 2),
                'cost_breakdown': {
                    rec['product_type']: rec['cost_per_ha'] 
                    for rec in recommendations
                }
            },
            'comprehensive_nutrient_balance': {
                'targets': needs,
                'supplied': {k: round(v, 1) for k, v in total_supplied.items()},
                'remaining_deficits': {
                    k: round(max(0, needs[k] - total_supplied[k]), 1) 
                    for k in needs.keys()
                },
                'coverage_percentage': {
                    k: round(v, 1) for k, v in coverage_percentages.items()
                }
            },
            'application_summary': {
                'total_products': len(recommendations),
                'total_fertilizer_kg_ha': round(sum([rec['application_rate_kg_ha'] for rec in recommendations]), 1),
                'total_fertilizer_kg_field': round(sum([rec['application_rate_kg_total'] for rec in recommendations]), 1),
                'product_categories': {
                    'primary': len([r for r in recommendations if 'Primary' in r['product_type']]),
                    'secondary': len([r for r in recommendations if 'Secondary' in r['product_type']]),
                    'micronutrient': len([r for r in recommendations if 'Micro' in r['product_type']])
                }
            },
            'optimization_notes': [
                f"✅ Selected {len(recommendations)} products for complete nutrition",
                f"💰 Cost optimization: ${total_cost_per_ha}/ha",
                f"🎯 Average coverage: {sum(coverage_percentages.values())/len(coverage_percentages):.1f}%",
                f"⚖️ Balanced approach: Primary + Secondary + Micronutrients"
            ]
        }
    
    @staticmethod
    def _find_best_compound_fertilizer(needs):
        """Find the compound fertilizer that provides the best overall nutrient match"""
        
        best_product = None
        best_efficiency = 0
        
        compound_fertilizers = {k: v for k, v in ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS.items() 
                               if v.get('category') in ['compound', 'complete']}
        
        for product_name, product_data in compound_fertilizers.items():
            # Calculate efficiency for each major nutrient
            efficiencies = []
            
            # Check NPK efficiency
            for nutrient in ['N', 'P2O5', 'K2O']:
                if product_data.get(nutrient, 0) > 0 and needs.get(nutrient, 0) > 0:
                    # Calculate application rate needed to meet this nutrient
                    rate_for_nutrient = needs[nutrient] / (product_data[nutrient] / 100)
                    # Efficiency is inverse of over-application
                    efficiency = min(1.0, needs[nutrient] / (rate_for_nutrient * product_data[nutrient] / 100))
                    efficiencies.append(efficiency)
            
            if efficiencies:
                # Overall efficiency is average of individual efficiencies
                overall_efficiency = sum(efficiencies) / len(efficiencies)
                
                # Bonus for providing secondary nutrients
                secondary_bonus = 0
                for nutrient in ['Ca', 'Mg', 'S']:
                    if product_data.get(nutrient, 0) > 0 and needs.get(nutrient, 0) > 0:
                        secondary_bonus += 0.1
                
                # Price efficiency (lower price is better)
                price_efficiency = 0.6 / max(0.3, product_data['price_per_kg'])
                
                total_score = overall_efficiency + secondary_bonus + (price_efficiency * 0.2)
                
                if total_score > best_efficiency:
                    best_efficiency = total_score
                    # Calculate optimal application rate (based on most limiting nutrient)
                    rates = []
                    for nutrient in ['N', 'P2O5', 'K2O']:
                        if product_data.get(nutrient, 0) > 0 and needs.get(nutrient, 0) > 0:
                            rate = needs[nutrient] / (product_data[nutrient] / 100)
                            rates.append(rate)
                    
                    if rates:
                        optimal_rate = min(rates)  # Use minimum to avoid over-application
                        optimal_rate = min(optimal_rate, 500)  # Cap at reasonable maximum
                        best_product = (product_name, product_data, optimal_rate, total_score)
        
        return best_product
    
    @staticmethod
    def _select_secondary_nutrient_products(remaining_needs):
        """Select optimal secondary nutrient products"""
        recommendations = []
        
        # Calcium products
        if remaining_needs.get('Ca', 0) > 5:
            ca_needed = remaining_needs['Ca']
            # Choose between gypsum (Ca+S) or calcium chloride (Ca only)
            if remaining_needs.get('S', 0) > 5:
                # Gypsum provides both Ca and S
                product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Gypsum']
                application_rate = ca_needed / (product_data['Ca'] / 100)
                
                recommendations.append({
                    'product_name': 'Gypsum (Calcium Sulfate)',
                    'product_type': 'Secondary (Ca+S)',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                    'nutrients_supplied': {
                        'Ca': round(application_rate * product_data['Ca'] / 100, 1),
                        'S': round(application_rate * product_data['S'] / 100, 1),
                    },
                    'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                    'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                    'priority': 2
                })
            else:
                # Use calcium chloride for Ca only
                product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Calcium_chloride']
                application_rate = ca_needed / (product_data['Ca'] / 100)
                
                recommendations.append({
                    'product_name': 'Calcium Chloride',
                    'product_type': 'Secondary (Ca)',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                    'nutrients_supplied': {
                        'Ca': round(application_rate * product_data['Ca'] / 100, 1),
                    },
                    'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                    'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                    'priority': 2
                })
        
        # Magnesium products
        if remaining_needs.get('Mg', 0) > 3:
            mg_needed = remaining_needs['Mg']
            product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Magnesium_sulfate']
            application_rate = mg_needed / (product_data['Mg'] / 100)
            
            recommendations.append({
                'product_name': 'Magnesium Sulfate (Epsom Salt)',
                'product_type': 'Secondary (Mg+S)',
                'application_rate_kg_ha': round(application_rate, 1),
                'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                'nutrients_supplied': {
                    'Mg': round(application_rate * product_data['Mg'] / 100, 1),
                    'S': round(application_rate * product_data['S'] / 100, 1),
                },
                'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                'priority': 2
            })
        
        # Sulfur products (if still needed)
        if remaining_needs.get('S', 0) > 8:
            s_needed = remaining_needs['S']
            product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Elemental_sulfur']
            application_rate = s_needed / (product_data['S'] / 100)
            
            recommendations.append({
                'product_name': 'Elemental Sulfur',
                'product_type': 'Secondary (S)',
                'application_rate_kg_ha': round(application_rate, 1),
                'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                'nutrients_supplied': {
                    'S': round(application_rate * product_data['S'] / 100, 1),
                },
                'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                'priority': 3
            })
        
        return recommendations
    
    @staticmethod
    def _select_micronutrient_products(remaining_needs, micronutrient_details):
        """Select optimal micronutrient products"""
        recommendations = []
        
        # Check if we need multiple micronutrients - use blend if economical
        micro_needs = {k: v for k, v in remaining_needs.items() 
                      if k.title() in ['Iron', 'Copper', 'Manganese', 'Zinc', 'Boron', 'Molybdenum']}
        
        if len([k for k, v in micro_needs.items() if v > 0]) >= 3:
            # Use complete micronutrient blend
            product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Complete_micro_blend']
            
            # Calculate application rate based on most needed micronutrient
            max_rate = 0
            for nutrient in ['Fe', 'Cu', 'Mn', 'Zn']:
                if nutrient in product_data and remaining_needs.get(nutrient.title(), 0) > 0:
                    rate = remaining_needs[nutrient.title()] / (product_data[nutrient] / 100)
                    max_rate = max(max_rate, rate)
            
            if max_rate > 0:
                application_rate = min(max_rate, 50)  # Cap micronutrient applications
                
                nutrients_supplied = {}
                for nutrient in ['Fe', 'Cu', 'Mn', 'Zn', 'B', 'Mo']:
                    if nutrient in product_data:
                        supplied = application_rate * (product_data[nutrient] / 100)
                        nutrients_supplied[nutrient] = round(supplied, 2)
                
                recommendations.append({
                    'product_name': 'Complete Micronutrient Blend',
                    'product_type': 'Micronutrient Blend',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                    'nutrients_supplied': nutrients_supplied,
                    'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                    'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                    'priority': 4
                })
        else:
            # Individual micronutrient products
            individual_products = {
                'Iron': 'Iron_sulfate',
                'Copper': 'Copper_sulfate', 
                'Manganese': 'Manganese_sulfate',
                'Zinc': 'Zinc_sulfate'
            }
            
            for nutrient, product_key in individual_products.items():
                if remaining_needs.get(nutrient, 0) > 0.5:  # Only if significant need
                    product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS[product_key]
                    nutrient_symbol = nutrient[:2] if nutrient != 'Zinc' else 'Zn'
                    
                    application_rate = remaining_needs[nutrient] / (product_data[nutrient_symbol] / 100)
                    application_rate = min(application_rate, 25)  # Cap individual micro applications
                    
                    recommendations.append({
                        'product_name': product_data.get('name', product_key.replace('_', ' ')),
                        'product_type': f'Micronutrient ({nutrient_symbol})',
                        'application_rate_kg_ha': round(application_rate, 1),
                        'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                        'nutrients_supplied': {
                            nutrient_symbol: round(application_rate * product_data[nutrient_symbol] / 100, 2),
                        },
                        'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                        'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                        'priority': 4
                    })
        
        return recommendations
    
    @staticmethod
    def _fill_remaining_gaps(remaining_needs):
        """Fill any remaining significant nutrient gaps with targeted products"""
        recommendations = []
        
        # Fill remaining NPK gaps
        if remaining_needs.get('N', 0) > 10:
            product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Urea']
            application_rate = remaining_needs['N'] / (product_data['N'] / 100)
            
            recommendations.append({
                'product_name': 'Urea (Supplemental)',
                'product_type': 'Nitrogen Top-up',
                'application_rate_kg_ha': round(application_rate, 1),
                'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                'nutrients_supplied': {
                    'N': round(application_rate * product_data['N'] / 100, 1),
                },
                'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                'priority': 5
            })
        
        if remaining_needs.get('K2O', 0) > 10:
            product_data = ComprehensiveFertilizerCalculator.FERTILIZER_PRODUCTS['Muriate_KCl']
            application_rate = remaining_needs['K2O'] / (product_data['K2O'] / 100)
            
            recommendations.append({
                'product_name': 'Muriate of Potash (Supplemental)',
                'product_type': 'Potassium Top-up',
                'application_rate_kg_ha': round(application_rate, 1),
                'application_rate_kg_total': round(application_rate * remaining_needs.get('surface_area_ha', 1), 1),
                'nutrients_supplied': {
                    'K2O': round(application_rate * product_data['K2O'] / 100, 1),
                },
                'cost_per_ha': round(application_rate * product_data['price_per_kg'], 2),
                'cost_total': round(application_rate * product_data['price_per_kg'] * remaining_needs.get('surface_area_ha', 1), 2),
                'priority': 5
            })
        
        return recommendations
    
    # Helper methods from the original calculator (keep existing physics-based conversions)
    @staticmethod
    def k_cmol_to_k2o_factor_kg_ha(bulk_density_g_cm3=1.3, depth_cm=20, efficiency=0.8):
        """Physics-based K build-up factor"""
        soil_mass_kg_ha = 10000 * (depth_cm/100) * (bulk_density_g_cm3*1000)
        kgK_per_cmol = 391e-6 * soil_mass_kg_ha
        kgK2O_per_cmol = kgK_per_cmol * ComprehensiveFertilizerCalculator.CONVERSION_FACTORS['K_to_K2O']
        return kgK2O_per_cmol * efficiency

    @staticmethod
    def p_ppm_to_p2o5_factor_kg_ha(bulk_density_g_cm3=1.3, depth_cm=20, build_up_coeff=0.75):
        """Physics-based P build-up factor"""
        soil_mass_kg_ha = 10000 * (depth_cm/100) * (bulk_density_g_cm3*1000)
        phys = 2.29 * soil_mass_kg_ha * 1e-6
        return phys * build_up_coeff

    @staticmethod
    def estimate_n_requirement_kg_ha(crop='general', expected_yield=5.0, soil_om_pct=3.0, 
                                   previous_crop_credit=0, residual_nitrate_credit=0):
        """Crop and yield-based nitrogen requirement calculation"""
        n_index = {
            'corn': 18, 'wheat': 25, 'rice': 15, 'tomatoes': 3, 'potatoes': 4,
            'soybeans': 0, 'lettuce': 8, 'carrots': 6, 'coffee': 20, 'general': 15
        }.get(crop_type.lower(), 15)
        
        gross_need = n_index * expected_yield
        
        if soil_om_pct >= 4:
            mineralization_credit = 30
        elif soil_om_pct >= 3:
            mineralization_credit = 20
        else:
            mineralization_credit = 10
        
        net_n = max(0, gross_need - mineralization_credit - previous_crop_credit - residual_nitrate_credit)
        
        return {
            'gross_need': gross_need,
            'mineralization_credit': mineralization_credit,
            'net_requirement': net_n,
            'n_index_used': n_index,
            'message': message
        }        

                
# =====================================
# 🧪 COMPLETE ENHANCED SOIL ANALYSIS ENGINE WITH COMPREHENSIVE MULTI-NUTRIENT SYSTEM
# =====================================

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math
import json

class ExtractionMethod(Enum):
    """Soil extraction methods"""
    OLSEN_MODIFIED = "olsen_modified"
    MEHLICH_III = "mehlich_iii"

class CropType(Enum):
    """Supported crop types"""
    CORN = "corn"
    WHEAT = "wheat"
    TOMATOES = "tomatoes"
    POTATOES = "potatoes"
    SOYBEANS = "soybeans"
    LETTUCE = "lettuce"
    CARROTS = "carrots"
    RICE = "rice"
    COFFEE = "coffee"
    GENERAL = "general"

@dataclass
class NutrientRange:
    """Optimal nutrient ranges based on extraction method and crop"""
    ph_min: float
    ph_max: float
    p_ppm_min: float
    p_ppm_max: float
    k_cmol_min: float
    k_cmol_max: float
    ca_cmol_min: float
    ca_cmol_max: float
    mg_cmol_min: float
    mg_cmol_max: float
    fe_ppm_min: float
    fe_ppm_max: float
    cu_ppm_min: float
    cu_ppm_max: float
    mn_ppm_min: float
    mn_ppm_max: float
    zn_ppm_min: float
    zn_ppm_max: float
    cec_min: float
    base_saturation_min: float
    base_saturation_max: float
    organic_matter_min: float
    
# =====================================
# 💊 COMPLETE ENHANCED MULTI-NUTRIENT FERTILIZER CALCULATOR
# =====================================

class EnhancedMultiNutrientCalculator:
    """Enhanced fertilizer calculator with comprehensive nutrient analysis and smart product selection"""
    
    # Conversion factors from elemental to oxide forms
    CONVERSION_FACTORS = {
        'P_to_P2O5': 2.29,      # P × 2.29 = P2O5
        'K_to_K2O': 1.205,     # K × 1.205 = K2O
        'Ca_to_CaO': 1.399,    # Ca × 1.399 = CaO
        'Mg_to_MgO': 1.658,    # Mg × 1.658 = MgO
        'S_to_SO3': 2.497,     # S × 2.497 = SO3
        'P2O5_to_P': 0.436,    # P2O5 × 0.436 = P
        'K2O_to_K': 0.830,     # K2O × 0.830 = K
        'CaO_to_Ca': 0.715,    # CaO × 0.715 = Ca
        'MgO_to_Mg': 0.603,    # MgO × 0.603 = Mg
        'SO3_to_S': 0.400      # SO3 × 0.400 = S
    }
    
    # REAL COMMERCIAL FERTILIZER PRODUCTS DATABASE - USA MARKET 2025
    FERTILIZER_PRODUCTS = {
        # === MAJOR BRAND NPK FERTILIZERS ===
        'Miracle-Gro All Purpose Plant Food 24-8-16': {'N': 24, 'P2O5': 8, 'K2O': 16, 'price_per_kg': 3.85, 'category': 'compound', 'brand': 'Miracle-Gro'},
        'Scotts Turf Builder Lawn Food 32-0-4': {'N': 32, 'P2O5': 0, 'K2O': 4, 'price_per_kg': 2.95, 'category': 'primary', 'brand': 'Scotts'},
        'Osmocote Smart-Release Plant Food 14-14-14': {'N': 14, 'P2O5': 14, 'K2O': 14, 'price_per_kg': 4.25, 'category': 'compound', 'brand': 'Osmocote'},
        'Jacks Classic All Purpose 20-20-20': {'N': 20, 'P2O5': 20, 'K2O': 20, 'price_per_kg': 3.15, 'category': 'compound', 'brand': 'JR Peters'},
        'Peters Professional 15-30-15': {'N': 15, 'P2O5': 30, 'K2O': 15, 'price_per_kg': 2.85, 'category': 'compound', 'brand': 'JR Peters'},
        
        # === NITROGEN FERTILIZERS ===
        'Southern Ag Urea 46-0-0': {'N': 46, 'P2O5': 0, 'K2O': 0, 'price_per_kg': 1.25, 'category': 'primary', 'brand': 'Southern Ag'},
        'Ferti-lome Ammonium Sulfate 21-0-0': {'N': 21, 'P2O5': 0, 'K2O': 0, 'S': 24, 'price_per_kg': 1.45, 'category': 'primary', 'brand': 'Ferti-lome'},
        'Greenway Biotech Calcium Nitrate 15.5-0-0': {'N': 15.5, 'P2O5': 0, 'K2O': 0, 'Ca': 19, 'price_per_kg': 1.85, 'category': 'primary', 'brand': 'Greenway Biotech'},
        'Hi-Yield Blood Meal 12-0-0': {'N': 12, 'P2O5': 0, 'K2O': 0, 'price_per_kg': 2.95, 'category': 'organic', 'brand': 'Hi-Yield'},
        
        # === PHOSPHORUS FERTILIZERS ===
        'Espoma Rock Phosphate 0-3-0': {'N': 0, 'P2O5': 3, 'K2O': 0, 'Ca': 30, 'price_per_kg': 1.65, 'category': 'organic', 'brand': 'Espoma'},
        'Southern Ag Triple Super Phosphate 0-46-0': {'N': 0, 'P2O5': 46, 'K2O': 0, 'price_per_kg': 1.95, 'category': 'primary', 'brand': 'Southern Ag'},
        'Hi-Yield Bone Meal 4-12-0': {'N': 4, 'P2O5': 12, 'K2O': 0, 'Ca': 24, 'price_per_kg': 2.45, 'category': 'organic', 'brand': 'Hi-Yield'},
        
        # === POTASSIUM FERTILIZERS ===
        'Greenway Biotech Muriate of Potash 0-0-60': {'N': 0, 'P2O5': 0, 'K2O': 60, 'price_per_kg': 1.35, 'category': 'primary', 'brand': 'Greenway Biotech'},
        'Southern Ag Sulfate of Potash 0-0-50': {'N': 0, 'P2O5': 0, 'K2O': 50, 'S': 18, 'price_per_kg': 1.75, 'category': 'primary', 'brand': 'Southern Ag'},
        'Down to Earth Kelp Meal 1-0-2': {'N': 1, 'P2O5': 0, 'K2O': 2, 'price_per_kg': 3.25, 'category': 'organic', 'brand': 'Down to Earth'},
        
        # === SECONDARY NUTRIENTS ===
        'Espoma Garden Gypsum 0-0-0': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 23, 'S': 18, 'price_per_kg': 0.85, 'category': 'secondary', 'brand': 'Espoma'},
        'Greenway Biotech Epsom Salt': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mg': 10, 'S': 13, 'price_per_kg': 1.15, 'category': 'secondary', 'brand': 'Greenway Biotech'},
        'Jobe\'s Organics Bone Meal 2-14-0': {'N': 2, 'P2O5': 14, 'K2O': 0, 'Ca': 24, 'price_per_kg': 2.85, 'category': 'organic', 'brand': 'Jobe\'s'},
        'Down to Earth Dolomite Lime': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 22, 'Mg': 12, 'price_per_kg': 0.65, 'category': 'secondary', 'brand': 'Down to Earth'},
        
        # === MICRONUTRIENT PRODUCTS ===
        'Southern Ag Zinc Sulfate': {'Zn': 35, 'S': 17, 'price_per_kg': 4.25, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Iron Sulfate': {'Fe': 20, 'S': 11, 'price_per_kg': 2.95, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        'Hi-Yield Iron Plus Soil Acidifier': {'Fe': 11, 'S': 15, 'price_per_kg': 3.45, 'category': 'micronutrient', 'brand': 'Hi-Yield'},
        'Ferti-lome Chelated Iron': {'Fe': 10, 'price_per_kg': 8.95, 'category': 'micronutrient', 'brand': 'Ferti-lome'},
        'Southern Ag Manganese Sulfate': {'Mn': 32, 'S': 15, 'price_per_kg': 4.85, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Copper Sulfate': {'Cu': 25, 'S': 12, 'price_per_kg': 5.25, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        
        # === PREMIUM MULTI-NUTRIENT BLENDS ===
        'Osmocote Plus 15-9-12': {'N': 15, 'P2O5': 9, 'K2O': 12, 'Mg': 2.5, 'S': 5.5, 'Fe': 0.45, 'Mn': 0.06, 'price_per_kg': 5.95, 'category': 'complete', 'brand': 'Osmocote'},
        'Miracle-Gro Shake n Feed 12-4-8': {'N': 12, 'P2O5': 4, 'K2O': 8, 'Ca': 2, 'Mg': 1, 'S': 3, 'price_per_kg': 4.15, 'category': 'complete', 'brand': 'Miracle-Gro'},
        'Jobe\'s Organics All Purpose 4-4-4': {'N': 4, 'P2O5': 4, 'K2O': 4, 'Ca': 6, 'S': 1, 'price_per_kg': 3.85, 'category': 'organic', 'brand': 'Jobe\'s'},
        'Espoma Plant-tone 5-3-3': {'N': 5, 'P2O5': 3, 'K2O': 3, 'Ca': 5, 'Mg': 1, 'S': 1, 'price_per_kg': 3.25, 'category': 'organic', 'brand': 'Espoma'},
        
        # === SPECIALTY MICRONUTRIENT BLENDS ===
        'Southern Ag Essential Minor Elements': {'Fe': 8, 'Cu': 2, 'Mn': 5, 'Zn': 3, 'B': 1, 'Mo': 0.1, 'price_per_kg': 12.95, 'category': 'micronutrient', 'brand': 'Southern Ag'},
        'Greenway Biotech Micronutrient Mix': {'Fe': 6, 'Cu': 1.5, 'Mn': 4, 'Zn': 2.5, 'B': 0.8, 'price_per_kg': 9.85, 'category': 'micronutrient', 'brand': 'Greenway Biotech'},
        
        # === LIQUID FERTILIZERS ===
        'Miracle-Gro Liquid All Purpose 12-4-8': {'N': 12, 'P2O5': 4, 'K2O': 8, 'price_per_kg': 6.25, 'category': 'liquid', 'brand': 'Miracle-Gro'},
        'Jack\'s Classic Blossom Booster 10-30-20': {'N': 10, 'P2O5': 30, 'K2O': 20, 'price_per_kg': 4.95, 'category': 'liquid', 'brand': 'JR Peters'},
        'General Hydroponics Flora Series': {'N': 8, 'P2O5': 5, 'K2O': 13, 'Ca': 3, 'Mg': 1.5, 'price_per_kg': 8.95, 'category': 'hydroponic', 'brand': 'General Hydroponics'}
    }
    
    @staticmethod
    def calculate_comprehensive_nutrient_requirements(current_levels, target_levels, **kwargs):
        """
        Calculate comprehensive nutrient requirements for ALL nutrients including micronutrients
        
        Args:
            current_levels (dict): Current soil nutrient levels
            target_levels (dict): Target nutrient levels
            **kwargs: Additional parameters
            
        Returns:
            dict: Complete nutrient requirements for all elements
        """
        
        # Extract physical parameters
        bulk_density = float(kwargs.get('bulk_density', 1.3))
        soil_depth_cm = float(kwargs.get('soil_depth_cm', 20))
        surface_area_ha = float(kwargs.get('surface_area_ha', 1.0))
        extraction_method = kwargs.get('extraction_method', 'olsen_modified')
        
        # =====================================
        # PRIMARY NUTRIENTS (NPK)
        # =====================================
        primary_nutrients = {
            'N': {
                'current': float(kwargs.get('current_n_percent', 0.1)) * 100,  # Convert to kg/ha equivalent
                'target': float(kwargs.get('target_n_kg_ha', 120)),  # Direct kg/ha input
                'needed': 0
            },
            'P2O5': {
                'current_ppm': float(current_levels.get('phosphorus_ppm', 0)),
                'target_ppm': float(target_levels.get('phosphorus_ppm', 15)),
                'needed': 0
            },
            'K2O': {
                'current_cmol': float(current_levels.get('potassium_cmol', 0)),
                'target_cmol': float(target_levels.get('potassium_cmol', 0.4)),
                'needed': 0
            }
        }
        
        # =====================================
        # SECONDARY NUTRIENTS (Ca, Mg, S)
        # =====================================
        secondary_nutrients = {
            'Ca': {
                'current_cmol': float(current_levels.get('calcium_cmol', 0)),
                'target_cmol': float(target_levels.get('calcium_cmol', 6.0)),
                'needed': 0
            },
            'Mg': {
                'current_cmol': float(current_levels.get('magnesium_cmol', 0)),
                'target_cmol': float(target_levels.get('magnesium_cmol', 1.5)),
                'needed': 0
            },
            'S': {
                'current_ppm': float(current_levels.get('sulfur_ppm', 0)),
                'target_ppm': float(target_levels.get('sulfur_ppm', 20)),
                'needed': 0
            }
        }
        
        # =====================================
        # MICRONUTRIENTS (Fe, Mn, Zn, Cu, B, Mo)
        # =====================================
        micronutrients = {
            'Fe': {
                'current_ppm': float(current_levels.get('iron_ppm', 0)),
                'target_ppm': float(target_levels.get('iron_ppm', 20)),
                'needed': 0
            },
            'Mn': {
                'current_ppm': float(current_levels.get('manganese_ppm', 0)),
                'target_ppm': float(target_levels.get('manganese_ppm', 10)),
                'needed': 0
            },
            'Zn': {
                'current_ppm': float(current_levels.get('zinc_ppm', 0)),
                'target_ppm': float(target_levels.get('zinc_ppm', 3)),
                'needed': 0
            },
            'Cu': {
                'current_ppm': float(current_levels.get('copper_ppm', 0)),
                'target_ppm': float(target_levels.get('copper_ppm', 2)),
                'needed': 0
            },
            'B': {
                'current_ppm': float(current_levels.get('boron_ppm', 0)),
                'target_ppm': float(target_levels.get('boron_ppm', 1)),
                'needed': 0
            },
            'Mo': {
                'current_ppm': float(current_levels.get('molybdenum_ppm', 0)),
                'target_ppm': float(target_levels.get('molybdenum_ppm', 0.2)),
                'needed': 0
            }
        }
        
        # =====================================
        # CALCULATE REQUIREMENTS
        # =====================================
        
        # Soil mass calculation
        soil_mass_kg_ha = 10000 * (soil_depth_cm/100) * (bulk_density * 1000)
        
        # Nitrogen (direct input in kg/ha)
        primary_nutrients['N']['needed'] = max(0, primary_nutrients['N']['target'] - primary_nutrients['N']['current'])
        
        # Phosphorus (ppm to kg/ha P2O5)
        p_deficit_ppm = max(0, primary_nutrients['P2O5']['target_ppm'] - primary_nutrients['P2O5']['current_ppm'])
        p_build_up_coeff = 0.75 if extraction_method == 'olsen_modified' else 0.65
        p_factor = EnhancedMultiNutrientCalculator.p_ppm_to_p2o5_factor_kg_ha(bulk_density, soil_depth_cm, p_build_up_coeff)
        primary_nutrients['P2O5']['needed'] = p_deficit_ppm * p_factor
        
        # Potassium (cmol to kg/ha K2O)
        k_deficit_cmol = max(0, primary_nutrients['K2O']['target_cmol'] - primary_nutrients['K2O']['current_cmol'])
        k_factor = EnhancedMultiNutrientCalculator.k_cmol_to_k2o_factor_kg_ha(bulk_density, soil_depth_cm, 0.8)
        primary_nutrients['K2O']['needed'] = k_deficit_cmol * k_factor
        
        # Secondary nutrients (cmol to kg/ha for Ca/Mg, ppm to kg/ha for S)
        for nutrient, data in secondary_nutrients.items():
            if nutrient in ['Ca', 'Mg']:
                deficit_cmol = max(0, data['target_cmol'] - data['current_cmol'])
                if nutrient == 'Ca':
                    # Ca: 1 cmol/kg = 200 mg/kg = 0.2 kg/ha per 1000 kg soil
                    factor = soil_mass_kg_ha * 0.0002 * EnhancedMultiNutrientCalculator.CONVERSION_FACTORS['Ca_to_CaO']
                else:  # Mg
                    # Mg: 1 cmol/kg = 121.5 mg/kg
                    factor = soil_mass_kg_ha * 0.0001215 * EnhancedMultiNutrientCalculator.CONVERSION_FACTORS['Mg_to_MgO']
                data['needed'] = deficit_cmol * factor
            else:  # Sulfur (ppm)
                deficit_ppm = max(0, data['target_ppm'] - data['current_ppm'])
                # Convert ppm to kg/ha
                data['needed'] = deficit_ppm * soil_mass_kg_ha * 1e-6
        
        # Micronutrients (ppm to kg/ha)
        for nutrient, data in micronutrients.items():
            deficit_ppm = max(0, data['target_ppm'] - data['current_ppm'])
            # Convert ppm to kg/ha with availability factor
            availability_factor = 0.4  # Typical soil availability
            data['needed'] = deficit_ppm * soil_mass_kg_ha * 1e-6 / availability_factor
        
        return {
            'primary_nutrients': primary_nutrients,
            'secondary_nutrients': secondary_nutrients,
            'micronutrients': micronutrients,
            'soil_parameters': {
                'bulk_density': bulk_density,
                'soil_depth_cm': soil_depth_cm,
                'surface_area_ha': surface_area_ha,
                'soil_mass_kg_ha': soil_mass_kg_ha,
                'extraction_method': extraction_method
            }
        }
    
    @staticmethod
    def smart_product_selection_algorithm(nutrient_requirements):
        """
        Advanced algorithm to select optimal fertilizer products based on nutrient compensation efficiency
        
        Args:
            nutrient_requirements (dict): Complete nutrient requirements
            
        Returns:
            dict: Optimized product recommendations with maximum compensation efficiency
        """
        
        primary = nutrient_requirements['primary_nutrients']
        secondary = nutrient_requirements['secondary_nutrients']
        micronutrients = nutrient_requirements['micronutrients']
        surface_area = nutrient_requirements['soil_parameters']['surface_area_ha']
        
        # Create nutrient needs dictionary
        nutrient_needs = {
            'N': primary['N']['needed'],
            'P2O5': primary['P2O5']['needed'],
            'K2O': primary['K2O']['needed'],
            'Ca': secondary['Ca']['needed'],
            'Mg': secondary['Mg']['needed'],
            'S': secondary['S']['needed'],
            'Fe': micronutrients['Fe']['needed'],
            'Mn': micronutrients['Mn']['needed'],
            'Zn': micronutrients['Zn']['needed'],
            'Cu': micronutrients['Cu']['needed'],
            'B': micronutrients.get('B', {}).get('needed', 0),
            'Mo': micronutrients.get('Mo', {}).get('needed', 0)
        }
        
        # Remove zero needs
        nutrient_needs = {k: v for k, v in nutrient_needs.items() if v > 1}  # Only include significant needs
        
        recommendations = []
        remaining_needs = nutrient_needs.copy()
        total_cost_per_ha = 0
        
        # =====================================
        # STEP 1: FIND OPTIMAL MULTI-NUTRIENT PRODUCTS
        # =====================================
        
        if len(remaining_needs) >= 3:  # If we need 3+ nutrients, look for multi-nutrient products
            best_products = EnhancedMultiNutrientCalculator._find_best_multi_nutrient_products(
                remaining_needs, EnhancedMultiNutrientCalculator.FERTILIZER_PRODUCTS
            )
            
            for product_data in best_products:
                if product_data['efficiency_score'] > 0.3:  # Only use if reasonably efficient
                    recommendations.append(product_data)
                    total_cost_per_ha += product_data['cost_per_ha']
                    
                    # Update remaining needs
                    for nutrient, supplied in product_data['nutrients_supplied'].items():
                        if nutrient in remaining_needs:
                            remaining_needs[nutrient] = max(0, remaining_needs[nutrient] - supplied)
        
        # =====================================
        # STEP 2: HANDLE REMAINING PRIMARY NUTRIENTS
        # =====================================
        
        # Handle remaining N, P, K individually
        for nutrient in ['N', 'P2O5', 'K2O']:
            if remaining_needs.get(nutrient, 0) > 5:  # Significant need remains
                best_product = EnhancedMultiNutrientCalculator._find_best_single_nutrient_product(
                    nutrient, remaining_needs[nutrient], EnhancedMultiNutrientCalculator.FERTILIZER_PRODUCTS
                )
                
                if best_product:
                    recommendations.append(best_product)
                    total_cost_per_ha += best_product['cost_per_ha']
                    
                    # Update remaining needs
                    for nut, supplied in best_product['nutrients_supplied'].items():
                        if nut in remaining_needs:
                            remaining_needs[nut] = max(0, remaining_needs[nut] - supplied)
        
        # =====================================
        # STEP 3: HANDLE SECONDARY NUTRIENTS
        # =====================================
        
        for nutrient in ['Ca', 'Mg', 'S']:
            if remaining_needs.get(nutrient, 0) > 2:
                best_product = EnhancedMultiNutrientCalculator._find_best_secondary_nutrient_product(
                    nutrient, remaining_needs[nutrient], EnhancedMultiNutrientCalculator.FERTILIZER_PRODUCTS
                )
                
                if best_product:
                    recommendations.append(best_product)
                    total_cost_per_ha += best_product['cost_per_ha']
                    
                    # Update remaining needs
                    for nut, supplied in best_product['nutrients_supplied'].items():
                        if nut in remaining_needs:
                            remaining_needs[nut] = max(0, remaining_needs[nut] - supplied)
        
        # =====================================
        # STEP 4: HANDLE MICRONUTRIENTS
        # =====================================
        
        micro_needs = {k: v for k, v in remaining_needs.items() if k in ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo'] and v > 0.1}
        
        if len(micro_needs) >= 3:  # Use micronutrient mix if multiple needs
            best_micro_mix = EnhancedMultiNutrientCalculator._find_best_micronutrient_mix(
                micro_needs, EnhancedMultiNutrientCalculator.FERTILIZER_PRODUCTS
            )
            if best_micro_mix:
                recommendations.append(best_micro_mix)
                total_cost_per_ha += best_micro_mix['cost_per_ha']
                
                # Update remaining needs
                for nut, supplied in best_micro_mix['nutrients_supplied'].items():
                    if nut in remaining_needs:
                        remaining_needs[nut] = max(0, remaining_needs[nut] - supplied)
        
        # Handle individual micronutrients
        for nutrient in ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo']:
            if remaining_needs.get(nutrient, 0) > 0.1:
                best_product = EnhancedMultiNutrientCalculator._find_best_micronutrient_product(
                    nutrient, remaining_needs[nutrient], EnhancedMultiNutrientCalculator.FERTILIZER_PRODUCTS
                )
                
                if best_product:
                    recommendations.append(best_product)
                    total_cost_per_ha += best_product['cost_per_ha']
        
        # =====================================
        # CALCULATE NUTRIENT BALANCE AND EFFICIENCY
        # =====================================
        
        total_nutrients_supplied = {}
        for rec in recommendations:
            for nutrient, amount in rec['nutrients_supplied'].items():
                total_nutrients_supplied[nutrient] = total_nutrients_supplied.get(nutrient, 0) + amount
        
        # Calculate coverage percentages
        coverage_percentages = {}
        for nutrient, needed in nutrient_needs.items():
            supplied = total_nutrients_supplied.get(nutrient, 0)
            coverage_percentages[nutrient] = min(100, (supplied / needed * 100)) if needed > 0 else 100
        
        return {
            'smart_recommendations': recommendations,
            'cost_summary': {
                'total_cost_per_ha': round(total_cost_per_ha, 2),
                'total_cost_field': round(total_cost_per_ha * surface_area, 2),
                'average_cost_per_nutrient': round(total_cost_per_ha / max(1, len(nutrient_needs)), 2)
            },
            'nutrient_balance': {
                'original_needs': nutrient_needs,
                'nutrients_supplied': total_nutrients_supplied,
                'coverage_percentages': coverage_percentages,
                'remaining_deficits': {k: max(0, v - total_nutrients_supplied.get(k, 0)) 
                                     for k, v in nutrient_needs.items()},
                'overall_efficiency': round(sum(coverage_percentages.values()) / len(coverage_percentages), 1) if coverage_percentages else 0
            },
            'application_summary': {
                'total_products': len(recommendations),
                'total_fertilizer_kg_ha': round(sum([rec['application_rate_kg_ha'] for rec in recommendations]), 1),
                'categories_used': list(set([rec['category'] for rec in recommendations]))
            }
        }
    
    @staticmethod
    def _find_best_multi_nutrient_products(nutrient_needs, products):
        """Find products that supply multiple needed nutrients efficiently"""
        
        candidates = []
        
        for product_name, product_data in products.items():
            if product_data.get('category') in ['NPK', 'Complete']:
                score = 0
                nutrients_matched = 0
                nutrients_supplied = {}
                
                # Check how many nutrients this product can supply
                for nutrient in nutrient_needs:
                    if nutrient in product_data and product_data[nutrient] > 0:
                        nutrients_matched += 1
                        score += 1
                
                if nutrients_matched >= 2:  # Must supply at least 2 nutrients
                    # Calculate application rate based on most limiting nutrient
                    rates = []
                    for nutrient, needed in nutrient_needs.items():
                        if nutrient in product_data and product_data[nutrient] > 0:
                            rate = needed / (product_data[nutrient] / 100)
                            rates.append(rate)
                    
                    if rates:
                        application_rate = min(rates)  # Use minimum to avoid over-application
                        application_rate = min(application_rate, 800)  # Cap at 800 kg/ha
                        
                        # Calculate nutrients supplied
                        for nutrient in product_data:
                            if nutrient in ['N', 'P2O5', 'K2O', 'Ca', 'Mg', 'S'] and product_data[nutrient] > 0:
                                supplied = application_rate * (product_data[nutrient] / 100)
                                nutrients_supplied[nutrient] = supplied
                        
                        # Calculate efficiency score
                        efficiency_score = nutrients_matched / len(nutrient_needs)
                        cost_per_ha = application_rate * product_data['price_per_kg']
                        
                        candidates.append({
                            'product_name': product_name.replace('_', ' '),
                            'category': product_data['category'],
                            'application_rate_kg_ha': round(application_rate, 1),
                            'nutrients_supplied': nutrients_supplied,
                            'cost_per_ha': round(cost_per_ha, 2),
                            'efficiency_score': efficiency_score,
                            'nutrients_matched': nutrients_matched,
                            'nutrient_content': EnhancedMultiNutrientCalculator._format_nutrient_content(product_data)
                        })
        
        # Sort by efficiency score and cost
        candidates.sort(key=lambda x: (x['efficiency_score'], -x['cost_per_ha']), reverse=True)
        return candidates[:2]  # Return top 2 candidates
    
    @staticmethod
    def _find_best_single_nutrient_product(nutrient, needed_amount, products):
        """Find the best product for a single nutrient"""
        
        candidates = []
        
        for product_name, product_data in products.items():
            if nutrient in product_data and product_data[nutrient] > 0:
                # Calculate application rate
                application_rate = needed_amount / (product_data[nutrient] / 100)
                application_rate = min(application_rate, 600)  # Cap application
                
                cost_per_ha = application_rate * product_data['price_per_kg']
                cost_per_kg_nutrient = cost_per_ha / (application_rate * product_data[nutrient] / 100)
                
                nutrients_supplied = {nutrient: application_rate * (product_data[nutrient] / 100)}
                
                # Add bonus nutrients
                for nut in ['N', 'P2O5', 'K2O', 'Ca', 'Mg', 'S']:
                    if nut != nutrient and nut in product_data and product_data[nut] > 0:
                        nutrients_supplied[nut] = application_rate * (product_data[nut] / 100)
                
                candidates.append({
                    'product_name': product_name.replace('_', ' '),
                    'category': product_data.get('category', 'Single'),
                    'application_rate_kg_ha': round(application_rate, 1),
                    'nutrients_supplied': nutrients_supplied,
                    'cost_per_ha': round(cost_per_ha, 2),
                    'cost_per_kg_nutrient': round(cost_per_kg_nutrient, 2),
                    'efficiency_score': 1.0 / cost_per_kg_nutrient,
                    'nutrient_content': EnhancedMultiNutrientCalculator._format_nutrient_content(product_data)
                })
        
        if candidates:
            candidates.sort(key=lambda x: x['cost_per_kg_nutrient'])
            return candidates[0]
        return None
    
    @staticmethod
    def _find_best_secondary_nutrient_product(nutrient, needed_amount, products):
        """Find the best product for secondary nutrients (Ca, Mg, S)"""
        
        candidates = []
        
        for product_name, product_data in products.items():
            if product_data.get('category') == 'Secondary' and nutrient in product_data and product_data[nutrient] > 0:
                application_rate = needed_amount / (product_data[nutrient] / 100)
                application_rate = min(application_rate, 1000)  # Higher cap for secondary nutrients
                
                cost_per_ha = application_rate * product_data['price_per_kg']
                
                nutrients_supplied = {}
                for nut in ['Ca', 'Mg', 'S']:
                    if nut in product_data and product_data[nut] > 0:
                        nutrients_supplied[nut] = application_rate * (product_data[nut] / 100)
                
                candidates.append({
                    'product_name': product_name.replace('_', ' '),
                    'category': 'Secondary',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'nutrients_supplied': nutrients_supplied,
                    'cost_per_ha': round(cost_per_ha, 2),
                    'nutrient_content': EnhancedMultiNutrientCalculator._format_nutrient_content(product_data)
                })
        
        if candidates:
            candidates.sort(key=lambda x: x['cost_per_ha'])
            return candidates[0]
        return None
    
    @staticmethod
    def _find_best_micronutrient_mix(micro_needs, products):
        """Find the best micronutrient mix product"""
        
        for product_name, product_data in products.items():
            if 'micro_mix' in product_name.lower() or 'chelated' in product_name.lower():
                # Calculate if this mix covers our needs well
                coverage_score = 0
                total_needs = len(micro_needs)
                
                for nutrient in micro_needs:
                    if nutrient in product_data and product_data[nutrient] > 0:
                        coverage_score += 1
                
                if coverage_score >= total_needs * 0.6:  # Covers at least 60% of needed micros
                    # Calculate application rate based on most deficient micronutrient
                    max_rate = 0
                    for nutrient, needed in micro_needs.items():
                        if nutrient in product_data and product_data[nutrient] > 0:
                            rate = needed / (product_data[nutrient] / 100)
                            max_rate = max(max_rate, rate)
                    
                    application_rate = min(max_rate, 50)  # Cap micronutrient applications
                    cost_per_ha = application_rate * product_data['price_per_kg']
                    
                    nutrients_supplied = {}
                    for nutrient in ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo']:
                        if nutrient in product_data and product_data[nutrient] > 0:
                            nutrients_supplied[nutrient] = application_rate * (product_data[nutrient] / 100)
                    
                    return {
                        'product_name': product_name.replace('_', ' '),
                        'category': 'Micronutrient Mix',
                        'application_rate_kg_ha': round(application_rate, 1),
                        'nutrients_supplied': nutrients_supplied,
                        'cost_per_ha': round(cost_per_ha, 2),
                        'nutrient_content': EnhancedMultiNutrientCalculator._format_nutrient_content(product_data)
                    }
        
        return None
    
    @staticmethod
    def _find_best_micronutrient_product(nutrient, needed_amount, products):
        """Find the best individual micronutrient product"""
        
        candidates = []
        
        for product_name, product_data in products.items():
            if product_data.get('category') == 'Micronutrient' and nutrient in product_data and product_data[nutrient] > 0:
                application_rate = needed_amount / (product_data[nutrient] / 100)
                application_rate = min(application_rate, 25)  # Cap micronutrient applications
                
                cost_per_ha = application_rate * product_data['price_per_kg']
                
                nutrients_supplied = {nutrient: application_rate * (product_data[nutrient] / 100)}
                
                # Add any bonus nutrients
                for nut in ['Fe', 'Mn', 'Zn', 'Cu', 'B', 'Mo', 'S']:
                    if nut != nutrient and nut in product_data and product_data[nut] > 0:
                        nutrients_supplied[nut] = application_rate * (product_data[nut] / 100)
                
                candidates.append({
                    'product_name': product_name.replace('_', ' '),
                    'category': 'Micronutrient',
                    'application_rate_kg_ha': round(application_rate, 1),
                    'nutrients_supplied': nutrients_supplied,
                    'cost_per_ha': round(cost_per_ha, 2),
                    'nutrient_content': EnhancedMultiNutrientCalculator._format_nutrient_content(product_data)
                })
        
        if candidates:
            candidates.sort(key=lambda x: x['cost_per_ha'])
            return candidates[0]
        return None
    
    @staticmethod
    def _format_nutrient_content(product_data):
        """Format nutrient content string for display"""
        nutrients = []
        for nutrient, content in product_data.items():
            if nutrient not in ['price_per_kg', 'category'] and content > 0:
                nutrients.append(f"{nutrient}:{content}%")
        return " ".join(nutrients)
    
    @staticmethod
    def p_ppm_to_p2o5_factor_kg_ha(bulk_density_g_cm3=1.3, depth_cm=20, build_up_coeff=0.75):
        """Physics-based P build-up factor"""
        soil_mass_kg_ha = 10000 * (depth_cm/100) * (bulk_density_g_cm3*1000)
        phys = 2.29 * soil_mass_kg_ha * 1e-6
        return phys * build_up_coeff
    
    @staticmethod
    def k_cmol_to_k2o_factor_kg_ha(bulk_density_g_cm3=1.3, depth_cm=20, efficiency=0.8):
        """Physics-based K build-up factor"""
        soil_mass_kg_ha = 10000 * (depth_cm/100) * (bulk_density_g_cm3*1000)
        kgK_per_cmol = 391e-6 * soil_mass_kg_ha
        kgK2O_per_cmol = kgK_per_cmol * EnhancedMultiNutrientCalculator.CONVERSION_FACTORS['K_to_K2O']
        return kgK2O_per_cmol * efficiency    

class ScientificValidation:
    """Scientific validation of calculations using known reference values"""
    
    @staticmethod
    def validate_lime_calculations():
        """Test lime calculations against known scientific values"""
        print("🔬 SCIENTIFIC VALIDATION - LIME CALCULATIONS")
        print("=" * 60)
        
        # Test Case 1: Standard conditions (from soil science literature)
        test_ea = 2.5  # cmol+/kg
        target_ea = 0.5  # cmol+/kg
        bulk_density = 1.3  # g/cm³
        depth_cm = 20  # cm
        
        result = EnhancedLimeCalculator.calculate_enhanced_lime_requirement(
            exchangeable_acidity=test_ea,
            target_ae=target_ea,
            bulk_density_g_cm3=bulk_density,
            depth_cm=depth_cm,
            soil_type='loamy'
        )
        
        expected_caco3_t_ha = 5 * (test_ea - target_ea) * bulk_density * (depth_cm/100) * 1.0
        print(f"Test 1 - Standard Loamy Soil:")
        print(f"  Expected CaCO₃: {expected_caco3_t_ha:.2f} t/ha")
        print(f"  Calculated: {result['caco3_eq_t_ha']:.2f} t/ha")
        print(f"  ✅ Match: {abs(expected_caco3_t_ha - result['caco3_eq_t_ha']) < 0.01}")
        
        # Test Case 2: Clay soil (higher buffering)
        result_clay = EnhancedLimeCalculator.calculate_enhanced_lime_requirement(
            exchangeable_acidity=test_ea,
            target_ae=target_ea,
            bulk_density_g_cm3=bulk_density,
            depth_cm=depth_cm,
            soil_type='clay'
        )
        
        expected_clay = expected_caco3_t_ha * 1.4  # Clay factor
        print(f"\nTest 2 - Clay Soil (1.4x factor):")
        print(f"  Expected: {expected_clay:.2f} t/ha")
        print(f"  Calculated: {result_clay['caco3_eq_t_ha']:.2f} t/ha")
        print(f"  ✅ Match: {abs(expected_clay - result_clay['caco3_eq_t_ha']) < 0.01}")
        
        return True
    
    @staticmethod
    def validate_nutrient_conversions():
        """Test nutrient conversion factors"""
        print("\n🧪 SCIENTIFIC VALIDATION - NUTRIENT CONVERSIONS")
        print("=" * 60)
        
        # Test P conversion (known: P × 2.29 = P₂O₅)
        p_factor = ComprehensiveFertilizerCalculator.CONVERSION_FACTORS['P_to_P2O5']
        print(f"P to P₂O₅ conversion: {p_factor} (Expected: 2.29)")
        print(f"✅ Correct: {abs(p_factor - 2.29) < 0.01}")
        
        # Test K conversion (known: K × 1.205 = K₂O)
        k_factor = ComprehensiveFertilizerCalculator.CONVERSION_FACTORS['K_to_K2O']
        print(f"K to K₂O conversion: {k_factor} (Expected: 1.205)")
        print(f"✅ Correct: {abs(k_factor - 1.205) < 0.01}")
        
        # Test soil mass calculation
        bulk_density = 1.3  # g/cm³
        depth_cm = 20
        expected_mass = 10000 * (depth_cm/100) * (bulk_density * 1000)  # kg/ha
        
        soil_calcs = EnhancedLimeCalculator.calculate_soil_volume_and_mass(1.0, depth_cm, bulk_density)
        calculated_mass = soil_calcs['soil_mass_kg_per_ha']
        
        print(f"\nSoil mass calculation:")
        print(f"  Expected: {expected_mass:,.0f} kg/ha")
        print(f"  Calculated: {calculated_mass:,.0f} kg/ha")
        print(f"  ✅ Match: {abs(expected_mass - calculated_mass) < 1}")
        
        return True

class ProfessionalSoilAnalyzer:
    """Professional soil analysis system with enhanced multi-nutrient fertilizer calculation"""
    
    # Optimal ranges by extraction method and crop type
    NUTRIENT_RANGES = {
        ExtractionMethod.OLSEN_MODIFIED: {
            CropType.GENERAL: NutrientRange(
                ph_min=5.5, ph_max=6.5,
                p_ppm_min=10.0, p_ppm_max=20.0,
                k_cmol_min=0.2, k_cmol_max=0.6,
                ca_cmol_min=4.0, ca_cmol_max=20.0,
                mg_cmol_min=1.0, mg_cmol_max=5.0,
                fe_ppm_min=10, fe_ppm_max=100.0,
                cu_ppm_min=1.0, cu_ppm_max=20,
                mn_ppm_min=5, mn_ppm_max=50.0,
                zn_ppm_min=2, zn_ppm_max=10.0,
                cec_min=15.0,
                base_saturation_min=80.0, base_saturation_max=10000,
                organic_matter_min=5.0
            ),
            CropType.CORN: NutrientRange(
                ph_min=6.0, ph_max=6.8,
                p_ppm_min=15.0, p_ppm_max=25.0,
                k_cmol_min=0.3, k_cmol_max=0.8,
                ca_cmol_min=5.0, ca_cmol_max=25.0,
                mg_cmol_min=1.5, mg_cmol_max=6.0,
                fe_ppm_min=5.0, fe_ppm_max=100.0,
                cu_ppm_min=1.5, cu_ppm_max=3.0,
                mn_ppm_min=5.0, mn_ppm_max=50.0,
                zn_ppm_min=2.0, zn_ppm_max=15.0,
                cec_min=18.0,
                base_saturation_min=85.0, base_saturation_max=95.0,
                organic_matter_min=3.5
            ),
            CropType.TOMATOES: NutrientRange(
                ph_min=5.5, ph_max=6.5,
                p_ppm_min=20.0, p_ppm_max=30.0,
                k_cmol_min=0.4, k_cmol_max=0.9,
                ca_cmol_min=6.0, ca_cmol_max=25.0,
                mg_cmol_min=2.0, mg_cmol_max=6.0,
                fe_ppm_min=10.0, fe_ppm_max=100.0,
                cu_ppm_min=2.0, cu_ppm_max=5.0,
                mn_ppm_min=10.0, mn_ppm_max=50.0,
                zn_ppm_min=3.0, zn_ppm_max=15.0,
                cec_min=20.0,
                base_saturation_min=85.0, base_saturation_max=95.0,
                organic_matter_min=4.0
            )
        },
        ExtractionMethod.MEHLICH_III: {
            CropType.GENERAL: NutrientRange(
                ph_min=5.5, ph_max=6.5,
                p_ppm_min=20.0, p_ppm_max=50.0,
                k_cmol_min=0.5, k_cmol_max=0.8,
                ca_cmol_min=6.0, ca_cmol_max=16.0,
                mg_cmol_min=3.0, mg_cmol_max=6.0,
                fe_ppm_min=50.0, fe_ppm_max=100.0,
                cu_ppm_min=2.0, cu_ppm_max=20.0,
                mn_ppm_min=10.0, mn_ppm_max=50.0,
                zn_ppm_min=2.0, zn_ppm_max=10.0,
                cec_min=15.0,
                base_saturation_min=80.0, base_saturation_max=90.0,
                organic_matter_min=5.0
            )
        }
    }
    
    @classmethod
    def analyze_soil(cls, data):
        """Main comprehensive soil analysis method with enhanced multi-nutrient fertilizer calculation"""
        # Parse input data
        extraction_method = ExtractionMethod(data.get('extraction_method', 'olsen_modified'))
        crop_type = CropType.GENERAL
        
        # Get appropriate nutrient ranges
        if extraction_method not in cls.NUTRIENT_RANGES:
            extraction_method = ExtractionMethod.OLSEN_MODIFIED
        if crop_type not in cls.NUTRIENT_RANGES[extraction_method]:
            crop_type = CropType.GENERAL
            
        ranges = cls.NUTRIENT_RANGES[extraction_method][crop_type]
        
        # Extract and convert data
        ph = float(data.get('ph', data.get('soil_ph', 6.5)))
        organic_matter = float(data.get('organic_matter', 0))
        
        # Primary nutrients
        phosphorus_ppm = float(data.get('phosphorus_ppm', data.get('phosphorus', 0)))
        potassium_cmol = float(data.get('potassium_cmol', 0)) or (float(data.get('potassium_ppm', data.get('potassium', 0))) / 390.98)
        
        # Secondary nutrients
        calcium_cmol = float(data.get('calcium_cmol', 0))
        magnesium_cmol = float(data.get('magnesium_cmol', 0))
        
        # Micronutrients
        iron_ppm = float(data.get('iron_ppm', 0))
        copper_ppm = float(data.get('copper_ppm', 0))
        manganese_ppm = float(data.get('manganese_ppm', 0))
        zinc_ppm = float(data.get('zinc_ppm', 0))
        
        # Additional nutrients (enhanced)
        sulfur_ppm = float(data.get('sulfur_ppm', 0))
        boron_ppm = float(data.get('boron_ppm', 0))
        molybdenum_ppm = float(data.get('molybdenum_ppm', 0))
        
        # Soil chemistry inputs
        exchangeable_acidity = float(data.get('exchangeable_acidity', 0))
        
        # Lime calculation parameters
        lime_type = data.get('lime_type', 'caco3')
        target_ae = float(data.get('target_ae', 0.5))
        
        # =====================================
        # 🧮 AUTOMATIC CALCULATIONS
        # =====================================
        
        # Calculate CEC (Cation Exchange Capacity)
        calculated_cec = calcium_cmol + magnesium_cmol + potassium_cmol + exchangeable_acidity
        
        # Calculate Base Saturation (SB)
        base_cations = calcium_cmol + magnesium_cmol + potassium_cmol
        calculated_base_saturation = (base_cations / calculated_cec * 100) if calculated_cec > 0 else 0
        
        # Calculate Acid Saturation (SA)
        calculated_acid_saturation = (exchangeable_acidity / calculated_cec * 100) if calculated_cec > 0 else 0
        
        # Calculate Cationic Ratios
        ca_mg_ratio = calcium_cmol / magnesium_cmol if magnesium_cmol > 0 else 0
        ca_k_ratio = calcium_cmol / potassium_cmol if potassium_cmol > 0 else 0
        mg_k_ratio = magnesium_cmol / potassium_cmol if potassium_cmol > 0 else 0
        ca_mg_k_ratio = (calcium_cmol + magnesium_cmol) / potassium_cmol if potassium_cmol > 0 else 0
        
        # =====================================
        # 🧪 LIME CALCULATION
        # =====================================
        
        # Physical parameters for consistency with the table
        land_area_ha = float(data.get('surface_area', 1.0))
        soil_depth_cm = float(data.get('soil_depth_cm', data.get('depth_cm', 20.0)))
        bulk_density = float(data.get('bulk_density', data.get('bulk_density_g_cm3', 1.3)))
        particle_density = float(data.get('particle_density', data.get('particle_density_g_cm3', 2.65)))
        product_ecce = float(data.get('product_ecce', data.get('ecce', 100.0)))

        lime_calculation = EnhancedLimeCalculator.calculate_enhanced_lime_requirement(
            exchangeable_acidity=exchangeable_acidity,
            lime_type=lime_type,
            target_ae=target_ae,
            land_area_ha=land_area_ha,
            depth_cm=soil_depth_cm,
            bulk_density_g_cm3=bulk_density,
            particle_density_g_cm3=particle_density,
            product_ecce=product_ecce,
            soil_type=data.get('soil_type', 'loamy')
        )

        # Extract lime needed for the rest of the analysis
        lime_needed = lime_calculation['lime_needed_kg_ha']
        
        # =====================================
        # 💊 ENHANCED COMPREHENSIVE MULTI-NUTRIENT FERTILIZER CALCULATIONS
        # =====================================
        
        # Prepare comprehensive current levels including ALL user inputs
        comprehensive_current_levels = {
            'phosphorus_ppm': phosphorus_ppm,
            'potassium_cmol': potassium_cmol,
            'calcium_cmol': calcium_cmol,
            'magnesium_cmol': magnesium_cmol,
            'iron_ppm': iron_ppm,
            'copper_ppm': copper_ppm,
            'manganese_ppm': manganese_ppm,
            'zinc_ppm': zinc_ppm,
            'sulfur_ppm': sulfur_ppm,
            'boron_ppm': boron_ppm,
            'molybdenum_ppm': molybdenum_ppm
        }
        
        # Set comprehensive target levels based on crop and extraction method
        comprehensive_target_levels = {
            'phosphorus_ppm': ranges.p_ppm_min,
            'potassium_cmol': ranges.k_cmol_min,
            'calcium_cmol': ranges.ca_cmol_min,
            'magnesium_cmol': ranges.mg_cmol_min,
            'iron_ppm': ranges.fe_ppm_min,
            'copper_ppm': ranges.cu_ppm_min,
            'manganese_ppm': ranges.mn_ppm_min,
            'zinc_ppm': ranges.zn_ppm_min,
            # Standard targets for additional nutrients
            'sulfur_ppm': 20,  # Standard S target
            'boron_ppm': 1,    # Standard B target
            'molybdenum_ppm': 0.2  # Standard Mo target
        }
        
        # Calculate comprehensive nutrient requirements using enhanced calculator
        comprehensive_nutrient_requirements = EnhancedMultiNutrientCalculator.calculate_comprehensive_nutrient_requirements(
            current_levels=comprehensive_current_levels,
            target_levels=comprehensive_target_levels,
            bulk_density=bulk_density,
            soil_depth_cm=soil_depth_cm,
            surface_area_ha=float(data.get('surface_area', 1.0)),
            extraction_method=extraction_method.value,
            target_n_kg_ha=float(data.get('target_n_kg_ha', 120)),  # Allow user input
            current_n_percent=float(data.get('current_n_percent', 0.1)),
            expected_yield=float(data.get('expected_yield', 5.0))
        )
        
        # Get smart product recommendations for ALL nutrients
        smart_fertilizer_recommendations = EnhancedMultiNutrientCalculator.smart_product_selection_algorithm(
            comprehensive_nutrient_requirements
        )
        
        # Extract traditional values for backward compatibility
        phosphorus_needed = comprehensive_nutrient_requirements['primary_nutrients']['P2O5']['needed']
        potassium_needed = comprehensive_nutrient_requirements['primary_nutrients']['K2O']['needed']
        
        # =====================================
        # 📊 NUTRIENT STATUS ANALYSIS
        # =====================================
        
        nutrient_status = {}
        micronutrient_status = {}
        
        # Primary nutrients analysis
        if phosphorus_ppm < ranges.p_ppm_min:
            nutrient_status['phosphorus'] = 'Deficient' if phosphorus_ppm < ranges.p_ppm_min * 0.7 else 'Low'
        elif phosphorus_ppm > ranges.p_ppm_max:
            nutrient_status['phosphorus'] = 'High'
        else:
            nutrient_status['phosphorus'] = 'Optimal'
        
        if potassium_cmol < ranges.k_cmol_min:
            nutrient_status['potassium'] = 'Deficient' if potassium_cmol < ranges.k_cmol_min * 0.7 else 'Low'
        elif potassium_cmol > ranges.k_cmol_max:
            nutrient_status['potassium'] = 'High'
        else:
            nutrient_status['potassium'] = 'Optimal'
        
        if calcium_cmol < ranges.ca_cmol_min:
            nutrient_status['calcium'] = 'Low'
        else:
            nutrient_status['calcium'] = 'Optimal'
        
        if magnesium_cmol < ranges.mg_cmol_min:
            nutrient_status['magnesium'] = 'Low'
        else:
            nutrient_status['magnesium'] = 'Optimal'
        
        # Enhanced secondary nutrients
        if sulfur_ppm < 20:
            nutrient_status['sulfur'] = 'Low' if sulfur_ppm > 0 else 'Not Tested'
        else:
            nutrient_status['sulfur'] = 'Optimal'
        
        # Micronutrients analysis (enhanced)
        micronutrients = {
            'iron': (iron_ppm, ranges.fe_ppm_min, ranges.fe_ppm_max),
            'copper': (copper_ppm, ranges.cu_ppm_min, ranges.cu_ppm_max),
            'manganese': (manganese_ppm, ranges.mn_ppm_min, ranges.mn_ppm_max),
            'zinc': (zinc_ppm, ranges.zn_ppm_min, ranges.zn_ppm_max),
            'boron': (boron_ppm, 1.0, 5.0),  # Standard B range
            'molybdenum': (molybdenum_ppm, 0.2, 2.0)  # Standard Mo range
        }
        
        for nutrient, (value, min_val, max_val) in micronutrients.items():
            if value == 0:
                micronutrient_status[nutrient] = 'Not Tested'
            elif value < min_val:
                micronutrient_status[nutrient] = 'Deficient' if value < min_val * 0.5 else 'Low'
            elif value > max_val:
                micronutrient_status[nutrient] = 'High'
            else:
                micronutrient_status[nutrient] = 'Optimal'
        
        # =====================================
        # 📊 SCORING CALCULATIONS
        # =====================================
        
        ph_score = 100 if ranges.ph_min <= ph <= ranges.ph_max else max(0, 100 - abs(ph - (ranges.ph_min + ranges.ph_max)/2) * 30)
        p_score = min(100, (phosphorus_ppm / ranges.p_ppm_min) * 100)
        k_score = min(100, (potassium_cmol / ranges.k_cmol_min) * 100)
        ca_score = min(100, (calcium_cmol / ranges.ca_cmol_min) * 100) if calcium_cmol > 0 else 0
        mg_score = min(100, (magnesium_cmol / ranges.mg_cmol_min) * 100) if magnesium_cmol > 0 else 0
        om_score = min(100, (organic_matter / ranges.organic_matter_min) * 100)
        cec_score = min(100, (calculated_cec / ranges.cec_min) * 100)
        bs_score = 100 if ranges.base_saturation_min <= calculated_base_saturation <= ranges.base_saturation_max else max(0, 100 - abs(calculated_base_saturation - ranges.base_saturation_min) * 2)
        
        overall_rating = (ph_score * 0.15 + p_score * 0.15 + k_score * 0.15 + ca_score * 0.1 + mg_score * 0.1 + om_score * 0.1 + cec_score * 0.15 + bs_score * 0.1)
        fertility_index = min(ph_score/100, p_score/100, k_score/100, om_score/100)
        soil_health_score = (overall_rating + cec_score + bs_score) / 3
        
        # =====================================
        # 💡 ENHANCED RECOMMENDATIONS GENERATION
        # =====================================
        
        recommendations = cls._generate_comprehensive_multi_nutrient_recommendations(
            smart_fertilizer_recommendations,
            comprehensive_nutrient_requirements,
            lime_calculation,
            ph, ranges, nutrient_status, micronutrient_status, 
            phosphorus_needed, potassium_needed, 
            ca_mg_ratio, organic_matter, calculated_cec, calculated_base_saturation, 
            ca_mg_k_ratio
        )
        
        # =====================================
        # ⚠️ LIMITING FACTORS IDENTIFICATION
        # =====================================
        
        limiting_factors = []
        if ph < ranges.ph_min or ph > ranges.ph_max:
            limiting_factors.append("pH")
        if exchangeable_acidity > target_ae:
            limiting_factors.append("Exchangeable Acidity")
        if phosphorus_ppm < ranges.p_ppm_min:
            limiting_factors.append("Phosphorus")
        if potassium_cmol < ranges.k_cmol_min:
            limiting_factors.append("Potassium")
        if calcium_cmol < ranges.ca_cmol_min:
            limiting_factors.append("Calcium")
        if magnesium_cmol < ranges.mg_cmol_min:
            limiting_factors.append("Magnesium")
        if organic_matter < ranges.organic_matter_min:
            limiting_factors.append("Organic Matter")
        if calculated_cec < ranges.cec_min:
            limiting_factors.append("CEC")
        if calculated_base_saturation < ranges.base_saturation_min:
            limiting_factors.append("Base Saturation")
        
        # Enhanced limiting factors for additional nutrients
        if sulfur_ppm > 0 and sulfur_ppm < 20:
            limiting_factors.append("Sulfur")
        if boron_ppm > 0 and boron_ppm < 1:
            limiting_factors.append("Boron")
        if molybdenum_ppm > 0 and molybdenum_ppm < 0.2:
            limiting_factors.append("Molybdenum")
        
        # Cationic ratio issues
        if not (2 <= ca_mg_ratio <= 5):
            limiting_factors.append("Ca/Mg Balance")
        if not (5 <= ca_k_ratio <= 25):
            limiting_factors.append("Ca/K Balance")
        
        # Enhanced cost estimation including comprehensive fertilizers
        lime_cost = lime_needed * 0.15  # $0.15/kg lime
        comprehensive_fertilizer_cost = smart_fertilizer_recommendations['cost_summary']['total_cost_per_ha']
        estimated_cost = lime_cost + comprehensive_fertilizer_cost
        
        return {
            'overall_rating': int(overall_rating),
            'fertility_index': round(fertility_index, 2),
            'soil_health_score': round(soil_health_score, 1),
            'estimated_yield_potential': round(100 - len(limiting_factors) * 12, 1),
            
            # Status
            'nutrient_status': nutrient_status,
            'micronutrient_status': micronutrient_status,
            
            # Calculated values (auto-computed)
            'calculated_cec': round(calculated_cec, 2),
            'calculated_base_saturation': round(calculated_base_saturation, 2),
            'calculated_acid_saturation': round(calculated_acid_saturation, 2),
            
            # Cationic ratios (auto-computed)
            'ca_mg_ratio': round(ca_mg_ratio, 2),
            'ca_k_ratio': round(ca_k_ratio, 2),
            'mg_k_ratio': round(mg_k_ratio, 2),
            'ca_mg_k_ratio': round(ca_mg_k_ratio, 2),
            
            # Enhanced lime calculation
            'lime_needed': lime_needed,
            'lime_calculation': lime_calculation,
            
            # ENHANCED MULTI-NUTRIENT FERTILIZER SECTION
            'comprehensive_nutrient_requirements': comprehensive_nutrient_requirements,
            'smart_fertilizer_recommendations': smart_fertilizer_recommendations,
            
            # Backward compatibility
            'phosphorus_needed': round(phosphorus_needed, 0),
            'potassium_needed': round(potassium_needed, 0),
            'estimated_cost': round(estimated_cost, 2),
            
            # Enhanced cost breakdown
            'detailed_cost_breakdown': {
                'lime_cost_per_ha': round(lime_cost, 2),
                'comprehensive_fertilizer_cost_per_ha': comprehensive_fertilizer_cost,
                'total_cost_per_ha': round(estimated_cost, 2),
                'nutrient_cost_breakdown': {
                    category: sum([rec['cost_per_ha'] for rec in smart_fertilizer_recommendations['smart_recommendations'] 
                                 if rec['category'] == category])
                    for category in set([rec['category'] for rec in smart_fertilizer_recommendations['smart_recommendations']])
                }
            },
            
            # Comprehensive nutrient balance
            'comprehensive_nutrient_balance': smart_fertilizer_recommendations['nutrient_balance'],
            
            # Nutrient efficiency analysis
            'nutrient_efficiency': {
                'overall_efficiency': smart_fertilizer_recommendations['nutrient_balance']['overall_efficiency'],
                'nutrients_covered': len([k for k, v in smart_fertilizer_recommendations['nutrient_balance']['original_needs'].items() if v > 0]),
                'products_optimized': smart_fertilizer_recommendations['application_summary']['total_products'],
                'cost_per_nutrient': round(comprehensive_fertilizer_cost / 
                                         max(1, len([k for k, v in smart_fertilizer_recommendations['nutrient_balance']['original_needs'].items() if v > 0])), 2)
            },
            
            # Summary for easy access
            'summary': {
                'total_nutrients_needed': len([k for k, v in smart_fertilizer_recommendations['nutrient_balance']['original_needs'].items() if v > 0]),
                'total_products_recommended': smart_fertilizer_recommendations['application_summary']['total_products'],
                'overall_efficiency': smart_fertilizer_recommendations['nutrient_balance']['overall_efficiency'],
                'total_cost_per_ha': comprehensive_fertilizer_cost,
                'categories_covered': smart_fertilizer_recommendations['application_summary']['categories_used']
            },
            
            # Recommendations and limiting factors
            'recommendations': recommendations,
            'limiting_factors': limiting_factors,
            
            # Additional data for database storage
            'extraction_method': extraction_method.value,
            'crop_type': crop_type.value,
            'phosphorus_ppm': phosphorus_ppm,
            'potassium_cmol': potassium_cmol,
            'calcium_cmol': calcium_cmol,
            'magnesium_cmol': magnesium_cmol,
            'iron_ppm': iron_ppm,
            'copper_ppm': copper_ppm,
            'manganese_ppm': manganese_ppm,
            'zinc_ppm': zinc_ppm,
            'sulfur_ppm': sulfur_ppm,
            'boron_ppm': boron_ppm,
            'molybdenum_ppm': molybdenum_ppm,
            'exchangeable_acidity': exchangeable_acidity,
            'cec': calculated_cec,
            'base_saturation': calculated_base_saturation,
            'lime_type': lime_type,
            'target_ae': target_ae
        }
    
    @staticmethod
    def _generate_comprehensive_multi_nutrient_recommendations(smart_recommendations, nutrient_requirements, lime_calculation,
                                                             ph, ranges, nutrient_status, micronutrient_status, 
                                                             phosphorus_needed, potassium_needed, 
                                                             ca_mg_ratio, organic_matter, calculated_cec, calculated_base_saturation, 
                                                             ca_mg_k_ratio):
        """Generate comprehensive recommendations including all nutrients and smart product suggestions"""
        recommendations = []
        
        # Enhanced lime recommendations
        if lime_calculation['lime_needed_kg_ha'] > 0:
            recommendations.append(f"🪨 {lime_calculation['message']}")
            recommendations.append(f"   Lime type: {lime_calculation['lime_name']} ({lime_calculation['lime_formula']})")
            
            # Application timing advice
            if lime_calculation['lime_type'] in ['hydrated', 'oxide', 'magnesium_oxide']:
                recommendations.append("   ⏱️ Apply 1-2 months before planting (fast-acting lime)")
            else:
                recommendations.append("   ⏱️ Apply 3-6 months before planting (standard lime)")
            
            # Split application for high amounts
            if lime_calculation['lime_needed_kg_ha'] > 4000:
                recommendations.append("   ⚠️ Consider split application over 2 seasons for high lime rates")
        else:
            recommendations.append("✅ No lime needed - Exchangeable Acidity is within optimal range")
        
        # =====================================
        # SMART FERTILIZER RECOMMENDATIONS
        # =====================================
        
        recommendations.append("💊 SMART MULTI-NUTRIENT FERTILIZER RECOMMENDATIONS:")
        recommendations.append("   🤖 Auto-optimized for maximum nutrient compensation efficiency")
        
        if smart_recommendations['smart_recommendations']:
            for i, product in enumerate(smart_recommendations['smart_recommendations'], 1):
                product_rec = f"   {i}. 🛒 {product['product_name']} ({product['category']}): {product['application_rate_kg_ha']} kg/ha"
                
                # Add nutrient details
                nutrients_list = []
                for nutrient, amount in product['nutrients_supplied'].items():
                    if amount > 0.1:  # Only show significant amounts
                        nutrients_list.append(f"{nutrient}: {amount:.1f}kg")
                
                if nutrients_list:
                    product_rec += f" → Supplies: {', '.join(nutrients_list)}"
                
                product_rec += f" (${product['cost_per_ha']}/ha)"
                recommendations.append(product_rec)
            
            # Overall efficiency summary
            efficiency = smart_recommendations['nutrient_balance']['overall_efficiency']
            recommendations.append(f"   📊 Overall compensation efficiency: {efficiency}% - {ProfessionalSoilAnalyzer._get_efficiency_rating(efficiency)}")
        else:
            recommendations.append("   ✅ No fertilizers needed - all nutrient levels are optimal!")
        
        # =====================================
        # NUTRIENT-SPECIFIC ANALYSIS
        # =====================================
        
        primary = nutrient_requirements['primary_nutrients']
        secondary = nutrient_requirements['secondary_nutrients']
        micronutrients = nutrient_requirements['micronutrients']
        
        # Primary nutrients status
        recommendations.append("🧪 PRIMARY NUTRIENTS STATUS:")
        for nutrient, data in primary.items():
            if data['needed'] > 1:
                recommendations.append(f"   🔴 {nutrient} deficient: {data['needed']:.1f} kg/ha needed")
            else:
                recommendations.append(f"   ✅ {nutrient} adequate")
        
        # Secondary nutrients status
        recommendations.append("⚗️ SECONDARY NUTRIENTS STATUS:")
        for nutrient, data in secondary.items():
            if data['needed'] > 1:
                recommendations.append(f"   🟡 {nutrient} deficient: {data['needed']:.1f} kg/ha needed")
            else:
                recommendations.append(f"   ✅ {nutrient} adequate")
        
        # Micronutrients status
        recommendations.append("🔬 MICRONUTRIENTS STATUS:")
        for nutrient, data in micronutrients.items():
            if data['needed'] > 0.1:
                recommendations.append(f"   🟠 {nutrient} deficient: {data['needed']:.2f} kg/ha needed")
            else:
                recommendations.append(f"   ✅ {nutrient} adequate")
        
        # =====================================
        # SMART OPTIMIZATION INSIGHTS
        # =====================================
        
        if smart_recommendations['smart_recommendations']:
            recommendations.append("🤖 SMART OPTIMIZATION INSIGHTS:")
            
            # Product efficiency
            total_products = len(smart_recommendations['smart_recommendations'])
            nutrients_covered = len([k for k, v in smart_recommendations['nutrient_balance']['original_needs'].items() if v > 0])
            
            if total_products <= nutrients_covered / 2:
                recommendations.append("   🌟 EXCELLENT: Multi-nutrient products selected to minimize applications")
            elif total_products <= nutrients_covered:
                recommendations.append("   👍 GOOD: Efficient product selection with reasonable application complexity")
            else:
                recommendations.append("   ⚠️ COMPLEX: Multiple products needed due to diverse nutrient requirements")
            
            # Cost efficiency
            cost_per_nutrient = smart_recommendations['cost_summary']['average_cost_per_nutrient']
            if cost_per_nutrient < 10:
                recommendations.append(f"   💰 COST EFFICIENT: ${cost_per_nutrient:.2f} per nutrient - excellent value")
            elif cost_per_nutrient < 20:
                recommendations.append(f"   💰 REASONABLE: ${cost_per_nutrient:.2f} per nutrient - good value")
            else:
                recommendations.append(f"   💰 PREMIUM: ${cost_per_nutrient:.2f} per nutrient - high-quality products")
            
            # Application timing
            recommendations.append("⏰ APPLICATION TIMING GUIDANCE:")
            if any('chelated' in prod['product_name'].lower() for prod in smart_recommendations['smart_recommendations']):
                recommendations.append("   • Apply chelated micronutrients during active growing season")
            if any('sulfate' in prod['product_name'].lower() for prod in smart_recommendations['smart_recommendations']):
                recommendations.append("   • Apply sulfate forms early season for soil conditioning")
            
            # Check for heavy applications
            heavy_apps = [p for p in smart_recommendations['smart_recommendations'] if p['application_rate_kg_ha'] > 300]
            if heavy_apps:
                recommendations.append("   • Consider splitting heavy applications (>300 kg/ha) across seasons")
            
            recommendations.append("   • Apply all fertilizers before main nutrient uptake period")
        
        # =====================================
        # TRADITIONAL SOIL HEALTH RECOMMENDATIONS
        # =====================================
        
        # CEC recommendations
        if calculated_cec < ranges.cec_min:
            recommendations.append(f"🔴 Low CEC ({calculated_cec:.1f}). Increase organic matter and clay content")
        else:
            recommendations.append(f"✅ Adequate CEC ({calculated_cec:.1f} cmol+/kg)")
        
        # Base saturation recommendations
        if calculated_base_saturation < ranges.base_saturation_min:
            recommendations.append(f"🔴 Low base saturation ({calculated_base_saturation:.1f}%). Apply lime to increase")
        elif calculated_base_saturation > ranges.base_saturation_max:
            recommendations.append(f"⚠️ High base saturation ({calculated_base_saturation:.1f}%). Monitor nutrient availability")
        else:
            recommendations.append(f"✅ Optimal base saturation ({calculated_base_saturation:.1f}%)")
        
        # Cationic ratios
        if not (2 <= ca_mg_ratio <= 5):
            if ca_mg_ratio < 2:
                recommendations.append(f"⚠️ Ca/Mg ratio is low ({ca_mg_ratio:.2f}) - consider calcium fertilizer")
            else:
                recommendations.append(f"⚠️ Ca/Mg ratio is high ({ca_mg_ratio:.2f}) - consider magnesium fertilizer")
        else:
            recommendations.append(f"✅ Ca/Mg ratio is balanced ({ca_mg_ratio:.2f})")
        
        if not (10 <= ca_mg_k_ratio <= 40):
            recommendations.append(f"⚠️ (Ca+Mg)/K ratio is imbalanced ({ca_mg_k_ratio:.2f}). Optimal: 10-40")
        
        # Organic matter
        if organic_matter < ranges.organic_matter_min:
            recommendations.append("🔴 Increase organic matter through compost, manure, or cover crops")
        else:
            recommendations.append("✅ Organic matter levels are sufficient")
        
        return recommendations
    
    @staticmethod
    def _get_efficiency_rating(efficiency):
        """Get efficiency rating description"""
        if efficiency >= 90:
            return "Excellent optimization"
        elif efficiency >= 80:
            return "Very good optimization"
        elif efficiency >= 70:
            return "Good optimization"
        elif efficiency >= 60:
            return "Moderate optimization"
        else:
            return "Basic coverage"


# Keep the original SoilAnalyzer for backward compatibility
SoilAnalyzer = ProfessionalSoilAnalyzer

# =====================================
# 🗄️ DATABASE MIGRATION FOR TESTIMONIALS (Add this after existing migration functions)
# =====================================

def migrate_testimonials_table():
    """Add testimonials table to database"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    print("Creating testimonials table...")
    
    # Create testimonials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            user_title TEXT,
            comment TEXT NOT NULL,
            rating INTEGER DEFAULT 5,
            is_approved BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create index for better performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_testimonials_approved_created 
        ON testimonials(is_approved, created_at DESC)
    ''')
    
    conn.commit()
    conn.close()
    print("Testimonials table created successfully!")

# =====================================
# ♻️ COMPOST CALCULATION ENGINE
# =====================================

class CompostCalculator:
    """Compost calculation engine"""
    
    MATERIALS = {
        'kitchen_scraps': {'carbon': 30, 'nitrogen': 1, 'description': 'Fruit and vegetable scraps'},
        'grass_clippings': {'carbon': 20, 'nitrogen': 1, 'description': 'Fresh grass clippings'},
        'dry_leaves': {'carbon': 60, 'nitrogen': 1, 'description': 'Dried autumn leaves'},
        'manure': {'carbon': 20, 'nitrogen': 2, 'description': 'Well-aged animal manure'},
        'straw': {'carbon': 80, 'nitrogen': 1, 'description': 'Wheat or rice straw'},
        'wood_chips': {'carbon': 100, 'nitrogen': 1, 'description': 'Small wood chips'}
    }
    
    @staticmethod
    def calculate_recipe(materials, target_volume):
        """Calculate optimal compost recipe"""
        total_carbon = 0
        total_nitrogen = 0
        total_weight = 0
        recipe = {}
        
        for material, percentage in materials.items():
            if material in CompostCalculator.MATERIALS and percentage > 0:
                weight = target_volume * (percentage / 100)
                recipe[material] = weight
                
                material_data = CompostCalculator.MATERIALS[material]
                total_carbon += weight * material_data['carbon'] / 100
                total_nitrogen += weight * material_data['nitrogen'] / 100
                total_weight += weight
        
        c_n_ratio = total_carbon / total_nitrogen if total_nitrogen > 0 else 0
        
        # Calculate quality score and maturation time
        if 25 <= c_n_ratio <= 35:
            quality_score = 100
            maturation_time = 8
        elif 20 <= c_n_ratio <= 40:
            quality_score = 80
            maturation_time = 12
        else:
            quality_score = 60
            maturation_time = 16
        
        return {
            'recipe': recipe,
            'c_n_ratio': round(c_n_ratio, 2),
            'total_weight': round(total_weight, 2),
            'estimated_yield': round(total_weight * 0.3, 2),
            'maturation_time': maturation_time,
            'quality_score': quality_score
        }

# =====================================
# 🤖 AI-POWERED SOIL ANALYSIS
# =====================================

def get_ai_soil_insights(soil_data, analysis_result):
    """
    Generate AI-powered insights and recommendations for soil analysis
    """
    if not openai_client:
        return {
            'ai_summary': "AI analysis unavailable - API key not configured",
            'smart_recommendations': [],
            'contextual_insights': [],
            'risk_assessment': "Unable to perform AI risk assessment"
        }
    
    try:
        # Prepare soil data summary for AI
        soil_summary = f"""
        Soil Analysis Data:
        - pH: {soil_data.get('ph', 'N/A')}
        - Phosphorus: {soil_data.get('phosphorus', 'N/A')} ppm
        - Potassium: {soil_data.get('potassium', 'N/A')} cmol+/kg
        - Organic Matter: {soil_data.get('organic_matter', 'N/A')}%
        - Calcium: {soil_data.get('calcium', 'N/A')} cmol+/kg
        - Magnesium: {soil_data.get('magnesium', 'N/A')} cmol+/kg
        - CEC: {soil_data.get('cec', 'N/A')} cmol+/kg
        - Base Saturation: {analysis_result.get('base_saturation', 'N/A')}%
        - Overall Rating: {analysis_result.get('overall_rating', 'N/A')}/100
        - Crop Type: {soil_data.get('crop_type', 'General farming')}
        - Location: {soil_data.get('location', 'Not specified')}
        """
        
        # Create AI prompt for comprehensive analysis
        prompt = f"""
        As an expert soil scientist and agronomist, analyze this soil test data and provide intelligent insights:

        {soil_summary}

        Please provide:
        1. A concise 2-3 sentence summary of the soil's overall condition
        2. 3-5 specific, actionable recommendations prioritized by importance
        3. 2-3 contextual insights about potential issues or opportunities
        4. A brief risk assessment for crop production

        Focus on practical, farmer-friendly advice. Consider nutrient interactions, soil chemistry, and sustainable practices.
        """
        
        # Call OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using the more cost-effective model
            messages=[
                {"role": "system", "content": "You are a professional soil scientist and agricultural consultant with 20+ years of experience. Provide practical, science-based advice that farmers can understand and implement."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Parse the AI response (simple parsing - could be enhanced)
        lines = ai_response.split('\n')
        
        ai_summary = ""
        smart_recommendations = []
        contextual_insights = []
        risk_assessment = ""
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "summary" in line.lower() or line.startswith("1."):
                current_section = "summary"
                if line.startswith("1."):
                    ai_summary = line[2:].strip()
                continue
            elif "recommendation" in line.lower() or line.startswith("2."):
                current_section = "recommendations"
                continue
            elif "insight" in line.lower() or line.startswith("3."):
                current_section = "insights"
                continue
            elif "risk" in line.lower() or line.startswith("4."):
                current_section = "risk"
                continue
            
            # Add content to appropriate section
            if current_section == "summary" and not ai_summary:
                ai_summary = line
            elif current_section == "recommendations" and line.startswith(('-', '•', '*')) or line[0].isdigit():
                smart_recommendations.append(line.lstrip('-•* ').lstrip('0123456789. '))
            elif current_section == "insights" and line.startswith(('-', '•', '*')) or line[0].isdigit():
                contextual_insights.append(line.lstrip('-•* ').lstrip('0123456789. '))
            elif current_section == "risk":
                risk_assessment += line + " "
        
        # Fallback parsing if structured parsing fails
        if not ai_summary:
            ai_summary = ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
        
        if not smart_recommendations:
            # Extract recommendations from full response
            recommendation_keywords = ["apply", "add", "increase", "decrease", "consider", "recommend", "should", "need"]
            for line in lines:
                if any(keyword in line.lower() for keyword in recommendation_keywords):
                    smart_recommendations.append(line.strip())
                    if len(smart_recommendations) >= 5:
                        break
        
        return {
            'ai_summary': ai_summary.strip(),
            'smart_recommendations': smart_recommendations[:5],  # Limit to 5
            'contextual_insights': contextual_insights[:3],  # Limit to 3
            'risk_assessment': risk_assessment.strip() or "Low to moderate risk with proper management"
        }
        
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        return {
            'ai_summary': f"AI analysis temporarily unavailable ({str(e)[:50]}...)",
            'smart_recommendations': [
                "Apply lime if pH is below 6.0",
                "Add organic matter to improve soil structure",
                "Test soil annually for optimal management"
            ],
            'contextual_insights': [
                "Regular soil testing helps optimize fertilizer use",
                "Soil health improves with consistent organic matter addition"
            ],
            'risk_assessment': "Standard agricultural risk - monitor soil conditions regularly"
        }

# =====================================
# 🏠 LANDING PAGE ROUTE
# =====================================

@app.route('/')
def index():
    """Landing page"""
    return render_template_string(LANDING_PAGE_TEMPLATE)

@app.route('/logo.png')
def serve_logo():
    """Serve the logo image"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, 'logo.png')
    return send_file(logo_path, mimetype='image/png')

# =====================================
# 🔐 AUTHENTICATION ROUTES
# =====================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        data = request.form
        
        # Validation
        if not all([data.get('email'), data.get('password'), data.get('first_name'), data.get('last_name')]):
            flash('All required fields must be filled.', 'error')
            return render_template_string(REGISTER_TEMPLATE)
        
        # Check if user exists
        existing_user = query_db('SELECT id FROM users WHERE email = ?', [data['email']], one=True)
        if existing_user:
            flash('Email already registered.', 'error')
            return render_template_string(REGISTER_TEMPLATE)
        
        # Create user
        password_hash = generate_password_hash(data['password'])
        execute_db('''
            INSERT INTO users (email, password_hash, first_name, last_name, phone, country, 
                             region, farm_size, plan_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            data['email'], password_hash, data['first_name'], data['last_name'],
            data.get('phone', ''), data.get('country', ''), data.get('region', ''),
            float(data.get('farm_size', 0)) if data.get('farm_size') else None, 'free'
        ])
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = f"{user['first_name']} {user['last_name']}"
            session['plan_type'] = user['plan_type']
            
            execute_db('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', [user['id']])
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    
    # Get user data
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    
    # Get recent analyses
    recent_analyses = query_db('''
        SELECT * FROM soil_analyses WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 5
    ''', [user_id])
    
    # Get recent recipes
    recent_recipes = query_db('''
        SELECT * FROM compost_recipes WHERE user_id = ? 
        ORDER BY created_at DESC LIMIT 3
    ''', [user_id])
    
    # Get statistics
    total_analyses = query_db('SELECT COUNT(*) as count FROM soil_analyses WHERE user_id = ?', [user_id], one=True)['count']
    total_recipes = query_db('SELECT COUNT(*) as count FROM compost_recipes WHERE user_id = ?', [user_id], one=True)['count']
    
    # Get user's testimonial if exists
    user_testimonial = query_db('''
        SELECT * FROM testimonials WHERE user_id = ? ORDER BY created_at DESC LIMIT 1
    ''', [user_id], one=True)
    
    # Calculate days remaining for Pro plan
    days_remaining = None
    try:
        if user['plan_type'] == 'pro' and user['pro_plan_expires_at']:
            from datetime import datetime
            try:
                expiry_date = datetime.fromisoformat(user['pro_plan_expires_at'].replace('Z', '+00:00'))
                days_remaining = max(0, (expiry_date - datetime.now()).days)
            except:
                days_remaining = 0
    except (KeyError, TypeError):
        # Column doesn't exist yet
        days_remaining = None
    
    return render_template_string(ENHANCED_DASHBOARD_TEMPLATE,
                                user=user,
                                analyses=recent_analyses,
                                recipes=recent_recipes,
                                total_analyses=total_analyses,
                                total_recipes=total_recipes,
                                user_testimonial=user_testimonial,
                                days_remaining=days_remaining)
    
# =====================================
# KEEP ONLY THE WORKING ROUTE BELOW (around line 3200)
# =====================================

@app.route('/soil-analysis', methods=['GET', 'POST'])
@login_required
def soil_analysis():
    """Enhanced soil analysis page with scientific lime calculation method"""
    if request.method == 'POST':
        user_id = session['user_id']
        user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
        
        # Check usage limits for free users
        if user['plan_type'] == 'free' and user['analyses_used'] >= 3:
            flash('Free plan limit reached (3 analyses). Upgrade for unlimited!', 'warning')
            return redirect(url_for('pricing'))
        
        # Extract form data
        data = request.form.to_dict()
        
        # Extract physical parameters
        land_area_ha = float(data.get('land_area_ha', 1.0))
        soil_depth_cm = float(data.get('soil_depth_cm', 20.0))
        bulk_density = float(data.get('bulk_density', 1.3))
        particle_density = float(data.get('particle_density', 2.65))
        product_ecce = float(data.get('product_ecce', 100.0))
        
        # Run enhanced analysis with ProfessionalSoilAnalyzer
        result = ProfessionalSoilAnalyzer.analyze_soil(data)
        
        # Ensure all required keys exist with defaults
        if 'overall_rating' not in result:
            result['overall_rating'] = 75  # Default rating
        if 'fertility_index' not in result:
            result['fertility_index'] = 0.75
        if 'soil_health_score' not in result:
            result['soil_health_score'] = 75.0
        if 'estimated_yield_potential' not in result:
            result['estimated_yield_potential'] = 85.0
            
        # Calculate cationic ratios if not present
        calcium_cmol = float(data.get('calcium', data.get('calcium_cmol', 0)))
        magnesium_cmol = float(data.get('magnesium', data.get('magnesium_cmol', 0)))
        potassium_cmol = float(data.get('potassium', data.get('potassium_cmol', 0)))
        phosphorus_ppm = float(data.get('phosphorus', data.get('phosphorus_ppm', 0)))
        
        # Ensure all cationic ratios exist
        if 'ca_mg_ratio' not in result:
            result['ca_mg_ratio'] = round(calcium_cmol / magnesium_cmol if magnesium_cmol > 0 else 0, 2)
        if 'ca_k_ratio' not in result:
            result['ca_k_ratio'] = round(calcium_cmol / potassium_cmol if potassium_cmol > 0 else 0, 2)
        if 'mg_k_ratio' not in result:
            result['mg_k_ratio'] = round(magnesium_cmol / potassium_cmol if potassium_cmol > 0 else 0, 2)
            
        # Ensure all nutrient needs exist
        if 'phosphorus_needed' not in result:
            result['phosphorus_needed'] = max(0, 30 - phosphorus_ppm)  # Target 30 ppm
        if 'potassium_needed' not in result:
            result['potassium_needed'] = max(0, 0.3 - potassium_cmol) * 100  # Target 0.3 cmol/kg
        if 'estimated_cost' not in result:
            result['estimated_cost'] = result.get('phosphorus_needed', 0) * 2.5 + result.get('potassium_needed', 0) * 1.8
            
        # Ensure all status dictionaries exist
        if 'recommendations' not in result:
            result['recommendations'] = []
        if 'nutrient_status' not in result:
            result['nutrient_status'] = {}
        if 'micronutrient_status' not in result:
            result['micronutrient_status'] = {}
        if 'limiting_factors' not in result:
            result['limiting_factors'] = []
            
        # Ensure all nutrient values exist with defaults
        if 'phosphorus_ppm' not in result:
            result['phosphorus_ppm'] = phosphorus_ppm
        if 'potassium_cmol' not in result:
            result['potassium_cmol'] = potassium_cmol
        if 'calcium_cmol' not in result:
            result['calcium_cmol'] = calcium_cmol
        if 'magnesium_cmol' not in result:
            result['magnesium_cmol'] = magnesium_cmol
        if 'iron_ppm' not in result:
            result['iron_ppm'] = float(data.get('iron', data.get('iron_ppm', 0)))
        if 'copper_ppm' not in result:
            result['copper_ppm'] = float(data.get('copper', data.get('copper_ppm', 0)))
        if 'manganese_ppm' not in result:
            result['manganese_ppm'] = float(data.get('manganese', data.get('manganese_ppm', 0)))
        if 'zinc_ppm' not in result:
            result['zinc_ppm'] = float(data.get('zinc', data.get('zinc_ppm', 0)))
        if 'exchangeable_acidity' not in result:
            result['exchangeable_acidity'] = float(data.get('exchangeable_acidity', 0))
        if 'calculated_cec' not in result:
            result['calculated_cec'] = calcium_cmol + magnesium_cmol + potassium_cmol + result['exchangeable_acidity']
        if 'calculated_base_saturation' not in result:
            base_cations = calcium_cmol + magnesium_cmol + potassium_cmol
            result['calculated_base_saturation'] = (base_cations / result['calculated_cec'] * 100) if result['calculated_cec'] > 0 else 0
        if 'calculated_acid_saturation' not in result:
            result['calculated_acid_saturation'] = (result['exchangeable_acidity'] / result['calculated_cec'] * 100) if result['calculated_cec'] > 0 else 0
            
        # Ensure smart_fertilizer_recommendations exists for template
        if 'smart_fertilizer_recommendations' not in result:
            result['smart_fertilizer_recommendations'] = {
                'smart_recommendations': [
                    {
                        'product_name': 'Triple Superphosphate (TSP)',
                        'category': 'Phosphorus',
                        'application_rate_kg_ha': max(0, result.get('phosphorus_needed', 0) * 2.2),
                        'cost_per_ha': max(0, result.get('phosphorus_needed', 0) * 2.5),
                        'nutrients_provided': {'P': result.get('phosphorus_needed', 0)},
                        'nutrients_supplied': {'P': result.get('phosphorus_needed', 0)},
                        'efficiency_rating': 85
                    },
                    {
                        'product_name': 'Muriate of Potash (KCl)',
                        'category': 'Potassium', 
                        'application_rate_kg_ha': max(0, result.get('potassium_needed', 0) * 1.6),
                        'cost_per_ha': max(0, result.get('potassium_needed', 0) * 1.8),
                        'nutrients_provided': {'K': result.get('potassium_needed', 0)},
                        'nutrients_supplied': {'K': result.get('potassium_needed', 0)},
                        'efficiency_rating': 90
                    }
                ],
                'cost_summary': {
                    'total_cost_per_ha': result.get('estimated_cost', 0)
                },
                'nutrient_balance': {
                    'overall_efficiency': 85,
                    'original_needs': {
                        'P': result.get('phosphorus_needed', 0),
                        'K': result.get('potassium_needed', 0)
                    }
                },
                'application_summary': {
                    'total_products': 2,
                    'categories_used': ['Phosphorus', 'Potassium']
                }
            }
            
        # Ensure all additional attributes exist for template
        if 'extraction_method' not in result:
            result['extraction_method'] = data.get('extraction_method', 'olsen_modified')
        if 'crop_type' not in result:
            result['crop_type'] = data.get('crop_type', 'general')
        if 'calculation_method' not in result:
            result['calculation_method'] = 'Scientific Formula'
        if 'comprehensive_nutrient_requirements' not in result:
            result['comprehensive_nutrient_requirements'] = {
                'primary_nutrients': {
                    'N': {
                        'current': 0,
                        'target': 120,
                        'needed': 0
                    },
                    'P2O5': {
                        'current_ppm': phosphorus_ppm,
                        'target_ppm': 30,
                        'needed': result.get('phosphorus_needed', 0)
                    },
                    'K2O': {
                        'current_cmol': potassium_cmol,
                        'target_cmol': 0.3,
                        'needed': result.get('potassium_needed', 0)
                    }
                },
                'secondary_nutrients': {
                    'Ca': {
                        'current_cmol': calcium_cmol,
                        'target_cmol': 6.0,
                        'needed': max(0, (6.0 - calcium_cmol) * 20)
                    },
                    'Mg': {
                        'current_cmol': magnesium_cmol,
                        'target_cmol': 1.5,
                        'needed': max(0, (1.5 - magnesium_cmol) * 12)
                    },
                    'S': {
                        'current_ppm': 0,
                        'target_ppm': 20,
                        'needed': 0
                    }
                },
                'micronutrients': {
                    'Fe': {
                        'current_ppm': result.get('iron_ppm', 0),
                        'target_ppm': 20,
                        'needed': max(0, 20 - result.get('iron_ppm', 0)) * 0.001
                    },
                    'Mn': {
                        'current_ppm': result.get('manganese_ppm', 0),
                        'target_ppm': 10,
                        'needed': max(0, 10 - result.get('manganese_ppm', 0)) * 0.001
                    },
                    'Zn': {
                        'current_ppm': result.get('zinc_ppm', 0),
                        'target_ppm': 3,
                        'needed': max(0, 3 - result.get('zinc_ppm', 0)) * 0.001
                    },
                    'Cu': {
                        'current_ppm': result.get('copper_ppm', 0),
                        'target_ppm': 2,
                        'needed': max(0, 2 - result.get('copper_ppm', 0)) * 0.001
                    },
                    'B': {
                        'current_ppm': 0,
                        'target_ppm': 1,
                        'needed': 0.001
                    },
                    'Mo': {
                        'current_ppm': 0,
                        'target_ppm': 0.2,
                        'needed': 0.0002
                    }
                }
            }
        if 'comprehensive_nutrient_balance' not in result:
            result['comprehensive_nutrient_balance'] = {
                'overall_efficiency': 85,
                'nutrients_covered': 2,
                'total_supplied': result.get('phosphorus_needed', 0) + result.get('potassium_needed', 0),
                'coverage_percentages': {
                    'N': 85,
                    'P': 90,
                    'K': 88,
                    'Ca': 75,
                    'Mg': 80,
                    'S': 70,
                    'Fe': 65,
                    'Mn': 60,
                    'Zn': 55,
                    'Cu': 50,
                    'B': 45,
                    'Mo': 40
                }
            }
        if 'nutrient_efficiency' not in result:
            result['nutrient_efficiency'] = {
                'overall_efficiency': 85,
                'nutrients_covered': 2,
                'products_optimized': 2,
                'cost_per_nutrient': round(result.get('estimated_cost', 0) / 2, 2) if result.get('estimated_cost', 0) > 0 else 0
            }
        if 'detailed_cost_breakdown' not in result:
            result['detailed_cost_breakdown'] = {
                'lime_cost_per_ha': 0,
                'comprehensive_fertilizer_cost_per_ha': result.get('estimated_cost', 0),
                'total_cost_per_ha': result.get('estimated_cost', 0),
                'nutrient_cost_breakdown': {
                    'Phosphorus': result.get('phosphorus_needed', 0) * 2.5,
                    'Potassium': result.get('potassium_needed', 0) * 1.8
                }
            }
            
        # Ensure summary object exists for template
        if 'summary' not in result:
            result['summary'] = {
                'overall_efficiency': result.get('smart_fertilizer_recommendations', {}).get('nutrient_balance', {}).get('overall_efficiency', 85),
                'total_nutrients_needed': int(result.get('phosphorus_needed', 0) + result.get('potassium_needed', 0)),
                'total_products_recommended': result.get('smart_fertilizer_recommendations', {}).get('application_summary', {}).get('total_products', 3),
                'total_cost_per_ha': round(result.get('estimated_cost', 0), 2)
            }
        
        # Calculate enhanced lime requirement using SCIENTIFIC METHOD
        enhanced_lime_calculation = EnhancedLimeCalculator.calculate_enhanced_lime_requirement(
            exchangeable_acidity=float(data.get('exchangeable_acidity', 0)),
            lime_type=data.get('lime_type', 'caco3'),
            target_ae=float(data.get('target_ae', 0.5)),
            land_area_ha=float(data.get('surface_area', 1.0)),
            depth_cm=float(data.get('soil_depth_cm', 20.0)),
            bulk_density_g_cm3=bulk_density,
            particle_density_g_cm3=particle_density,
            product_ecce=float(data.get('product_ecce', 100.0)),
            soil_type=data.get('soil_type', 'loamy')
        )
        
        # Generate comparison of all lime types
        lime_comparison = EnhancedLimeCalculator.compare_all_lime_types(
            exchangeable_acidity=float(data.get('exchangeable_acidity', 0)),
            target_ae=float(data.get('target_ae', 0.5)),
            land_area_ha=land_area_ha,
            depth_cm=soil_depth_cm,
            bulk_density_g_cm3=bulk_density,
            product_ecce=product_ecce,
            soil_type=data.get('soil_type', 'loamy')
        )
        
        # Update result with enhanced calculations
        result.update({
            'enhanced_lime_calculation': enhanced_lime_calculation,
            'lime_comparison': lime_comparison,
            'physical_properties': enhanced_lime_calculation['physical_properties'],
            'soil_calculations': enhanced_lime_calculation['soil_calculations'],
            
            # Updated lime values using scientific method
            'lime_needed': enhanced_lime_calculation['lime_needed_kg_ha'],
            'lime_needed_t_ha': enhanced_lime_calculation['lime_needed_t_ha'],
            'lime_needed_total': enhanced_lime_calculation['lime_needed_kg_total'],
            'lime_needed_t_total': enhanced_lime_calculation['lime_needed_t_total'],
            
            # CaCO₃-equivalent values
            'caco3_eq_t_ha': enhanced_lime_calculation['caco3_eq_t_ha'],
            'caco3_eq_kg_ha': enhanced_lime_calculation['caco3_eq_kg_ha'],
            
            # Physical parameters
            'land_area_ha': land_area_ha,
            'soil_depth_cm': soil_depth_cm,
            'bulk_density': bulk_density,
            'particle_density': particle_density,
            'product_ecce': product_ecce,
            'calculated_porosity': enhanced_lime_calculation['physical_properties']['porosity_percent'],
            
            # Scientific method indicators
            'calculation_method': enhanced_lime_calculation['calculation_method'],
            'formula_explanation': enhanced_lime_calculation['formula_explanation'],
            'safety_cap_applied': enhanced_lime_calculation.get('safety_cap_applied', False)
        })
        
        # Prepare values for database insertion
        values_list = [
            user_id, 
            data.get('crop_type', ''), 
            data.get('farm_location', ''),
            result.get('extraction_method', 'olsen_modified'),
            float(data.get('surface_area', 1.0)),
            
            # Basic soil properties
            float(data.get('ph', data.get('soil_ph', 0))),
            float(data.get('organic_matter', 0)),
            result.get('phosphorus_ppm', 0),
            result.get('potassium_cmol', 0),
            result.get('calcium_cmol', 0),
            result.get('magnesium_cmol', 0),
            result.get('iron_ppm', 0),
            result.get('copper_ppm', 0),
            result.get('manganese_ppm', 0),
            result.get('zinc_ppm', 0),
            result.get('exchangeable_acidity', 0),
            result.get('calculated_cec', 0),
            result.get('calculated_base_saturation', 0),
            result.get('calculated_acid_saturation', 0),
            
            # Physical parameters
            bulk_density,
            particle_density,
            enhanced_lime_calculation['physical_properties']['porosity_percent'],
            soil_depth_cm,
            land_area_ha,
            soil_depth_cm,
            enhanced_lime_calculation['physical_properties']['porosity_percent'],
            enhanced_lime_calculation['soil_calculations']['soil_volume_m3_per_ha'],
            enhanced_lime_calculation['soil_calculations']['soil_mass_kg_per_ha'],
            
            # Enhanced lime calculations
            enhanced_lime_calculation['lime_needed_kg_ha'],
            enhanced_lime_calculation['lime_needed_kg_total'],
            enhanced_lime_calculation['lime_type'],
            enhanced_lime_calculation['target_ae'],
            enhanced_lime_calculation['lime_needed_kg_ha'] * 0.15,
            1.0,
            1.0,
            
            # Analysis results
            result['overall_rating'],
            result['fertility_index'],
            result['soil_health_score'],
            result['estimated_yield_potential'],
            result['ca_mg_ratio'],
            result['ca_k_ratio'],
            result['mg_k_ratio'],
            result['phosphorus_needed'],
            result['potassium_needed'],
            result['estimated_cost'],
            
            # JSON fields
            json.dumps(result['recommendations']),
            json.dumps(result['nutrient_status']),
            json.dumps(result['micronutrient_status']),
            json.dumps(result['limiting_factors']),
            json.dumps({
                'scientific_calculation': enhanced_lime_calculation,
                'lime_comparison': lime_comparison,
                'method': 'Scientific Formula: t/ha = 5 × ΔAE × ρb × d'
            })
        ]
        
        # Save comprehensive analysis to database
        execute_db('''
            INSERT INTO soil_analyses (
                user_id, crop_type, farm_location, extraction_method, surface_area,
                soil_ph, organic_matter, phosphorus_ppm, potassium_cmol, 
                calcium_cmol, magnesium_cmol, iron_ppm, copper_ppm, manganese_ppm, zinc_ppm,
                exchangeable_acidity, cec, base_saturation, acid_saturation,
                
                -- Physical parameters
                bulk_density, particle_density, porosity, effective_depth,
                land_area_ha, soil_depth_cm, calculated_porosity,
                soil_volume_m3_ha, soil_mass_kg_ha,
                
                -- Enhanced lime calculations (scientific method)
                lime_needed, lime_needed_total_kg, lime_type, target_ae, lime_cost,
                density_adjustment_factor, depth_adjustment_factor,
                
                overall_rating, fertility_index, soil_health_score, estimated_yield_potential,
                ca_mg_ratio, ca_k_ratio, mg_k_ratio,
                phosphorus_needed, potassium_needed, estimated_cost,
                recommendations, nutrient_status, micronutrient_status, limiting_factors, lime_calculation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', values_list)
        
        # Update usage count
        execute_db('UPDATE users SET analyses_used = analyses_used + 1 WHERE id = ?', [user_id])
        
        # 🤖 Generate AI-powered insights
        ai_insights = get_ai_soil_insights(data, result)
        result['ai_insights'] = ai_insights
        
        return render_template_string(ENHANCED_SOIL_ANALYSIS_RESULT_TEMPLATE, result=result, data=data)
    
    return render_template_string(ENHANCED_SOIL_ANALYSIS_TEMPLATE)


# =====================================
# 🗄️ COMPLETE DATABASE MIGRATION FOR ALL NEW COLUMNS
# =====================================

def complete_database_migration():
    """Complete migration including all physical parameter columns"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    # Complete list of ALL new columns for enhanced functionality
    all_new_columns = [
        # Original enhancements
        ('extraction_method', 'TEXT DEFAULT "olsen_modified"'),
        ('surface_area', 'REAL DEFAULT 1.0'),
        ('phosphorus_ppm', 'REAL'),
        ('potassium_cmol', 'REAL'),
        ('calcium_cmol', 'REAL'),
        ('magnesium_cmol', 'REAL'),
        ('iron_ppm', 'REAL'),
        ('copper_ppm', 'REAL'),
        ('manganese_ppm', 'REAL'),
        ('zinc_ppm', 'REAL'),
        ('exchangeable_acidity', 'REAL'),
        ('cec', 'REAL'),
        ('base_saturation', 'REAL'),
        ('acid_saturation', 'REAL'),
        ('fertility_index', 'REAL'),
        ('soil_health_score', 'REAL'),
        ('estimated_yield_potential', 'REAL'),
        ('ca_mg_ratio', 'REAL'),
        ('ca_k_ratio', 'REAL'),
        ('mg_k_ratio', 'REAL'),
        ('lime_needed', 'REAL'),
        ('lime_type', 'TEXT DEFAULT "caco3"'),
        ('target_ae', 'REAL DEFAULT 0.5'),
        ('lime_cost', 'REAL'),
        ('phosphorus_needed', 'REAL'),
        ('potassium_needed', 'REAL'),
        ('estimated_cost', 'REAL'),
        ('nutrient_status', 'TEXT'),
        ('micronutrient_status', 'TEXT'),
        ('limiting_factors', 'TEXT'),
        ('fertilization_plan', 'TEXT'),
        ('lime_calculation', 'TEXT'),
        
        # NEW: Physical parameter columns
        ('particle_density', 'REAL DEFAULT 2.65'),
        ('land_area_ha', 'REAL DEFAULT 1.0'),
        ('soil_depth_cm', 'REAL DEFAULT 20.0'),
        ('calculated_porosity', 'REAL'),
        ('soil_volume_m3_ha', 'REAL'),
        ('soil_mass_kg_ha', 'REAL'),
        ('lime_needed_total_kg', 'REAL'),
        ('density_adjustment_factor', 'REAL'),
        ('depth_adjustment_factor', 'REAL')
    ]
    
    # Try to add each column
    for column_name, column_type in all_new_columns:
        try:
            cursor.execute(f'ALTER TABLE soil_analyses ADD COLUMN {column_name} {column_type}')
            print(f"Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()
    print("Database migration completed!")



# =====================================
# ♻️ COMPOST CALCULATOR ROUTES
# =====================================

@app.route('/compost-calculator', methods=['GET', 'POST'])
@login_required
def compost_calculator():
    """Compost calculator page"""
    if request.method == 'POST':
        user_id = session['user_id']
        data = request.form
        
        # Extract materials and percentages
        materials = {}
        for key, value in data.items():
            if key.startswith('material_') and value:
                material_name = key.replace('material_', '')
                percentage = float(value)
                if percentage > 0:
                    materials[material_name] = percentage
        
        target_volume = float(data.get('target_volume', 100))
        result = CompostCalculator.calculate_recipe(materials, target_volume)
        
        # Save recipe
        execute_db('''
            INSERT INTO compost_recipes (user_id, recipe_name, materials, ratios, 
                                       estimated_yield, maturation_time, c_n_ratio, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            user_id, data.get('recipe_name', 'My Recipe'),
            json.dumps(list(materials.keys())), json.dumps(materials),
            result['estimated_yield'], result['maturation_time'],
            result['c_n_ratio'], result['quality_score']
        ])
        
        return render_template_string(COMPOST_RESULT_TEMPLATE, result=result, materials=materials)
    
    return render_template_string(COMPOST_CALCULATOR_TEMPLATE, materials=CompostCalculator.MATERIALS)

# =====================================
# 💰 PRICING AND SUBSCRIPTION ROUTES
# =====================================

@app.route('/pricing')
def pricing():
    """Pricing page"""
    plans = {
        'free': {
            'name': 'Free',
            'price': 0,
            'analyses_limit': 3,
            'features': ['3 soil analyses per month', 'Basic recommendations', 'Compost calculator', 'Community support']
        },
        'pro': {
            'name': 'Professional',
            'price': 5.00,
            'analyses_limit': -1,
            'features': ['Unlimited soil analyses', 'Advanced lime calculations', 'All extraction methods', 'PDF reports', 'Priority support']
        }
    }
    return render_template_string(PRICING_TEMPLATE, plans=plans)

@app.route('/upgrade/<plan>')
@login_required
def upgrade_plan(plan):
    """Upgrade user plan (simplified - just updates database)"""
    user_id = session['user_id']
    
    if plan in ['free', 'pro']:
        execute_db('UPDATE users SET plan_type = ? WHERE id = ?', [plan, user_id])
        session['plan_type'] = plan
        flash(f'Successfully upgraded to {plan.title()} plan!', 'success')
    else:
        flash('Invalid plan selected.', 'error')
    
    return redirect(url_for('dashboard'))

def check_and_expire_pro_plans():
    """Check and automatically downgrade expired Pro plans"""
    try:
        # Find users with expired Pro plans
        expired_users = query_db('''
            SELECT id, email FROM users 
            WHERE plan_type = 'pro' 
            AND pro_plan_expires_at IS NOT NULL 
            AND pro_plan_expires_at < datetime('now')
        ''')
        
        for user in expired_users:
            # Downgrade to free plan
            execute_db('''
                UPDATE users 
                SET plan_type = 'free', pro_plan_expires_at = NULL 
                WHERE id = ?
            ''', [user['id']])
            
        return len(expired_users) if expired_users else 0
    except Exception as e:
        print(f"Error checking expired plans: {e}")
        return 0

# =====================================
# 💳 PAYPAL PAYMENT ROUTES
# =====================================

@app.route('/paypal/create-payment')
@login_required
def create_paypal_payment():
    """Create PayPal payment for Pro plan upgrade"""
    try:
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": url_for('paypal_success', _external=True),
                "cancel_url": url_for('paypal_cancel', _external=True)
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": "SoilsFert Pro Plan",
                        "sku": "soilsfert-pro",
                        "price": PRO_PLAN_PRICE,
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": PRO_PLAN_PRICE,
                    "currency": "USD"
                },
                "description": "SoilsFert Professional Plan - Unlimited soil analyses and advanced features"
            }]
        })

        if payment.create():
            # Store payment ID in session for verification
            session['paypal_payment_id'] = payment.id
            
            # Get approval URL
            for link in payment.links:
                if link.rel == "approval_url":
                    return redirect(link.href)
        else:
            flash('Error creating PayPal payment. Please try again.', 'error')
            return redirect(url_for('pricing'))
            
    except Exception as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('pricing'))

@app.route('/paypal/success')
@login_required
def paypal_success():
    """Handle successful PayPal payment"""
    try:
        payment_id = request.args.get('paymentId')
        payer_id = request.args.get('PayerID')
        
        # Verify payment ID matches session
        if payment_id != session.get('paypal_payment_id'):
            flash('Invalid payment session.', 'error')
            return redirect(url_for('pricing'))
        
        # Execute the payment
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Payment successful - upgrade user to Pro with 30-day expiration
            user_id = session['user_id']
            execute_db('''
                UPDATE users 
                SET plan_type = ?, pro_plan_expires_at = datetime('now', '+30 days') 
                WHERE id = ?
            ''', ['pro', user_id])
            session['plan_type'] = 'pro'
            
            # Clear payment session
            session.pop('paypal_payment_id', None)
            
            flash('Payment successful! Welcome to SoilsFert Pro!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Payment execution failed. Please contact support.', 'error')
            return redirect(url_for('pricing'))
            
    except Exception as e:
        flash(f'Payment verification error: {str(e)}', 'error')
        return redirect(url_for('pricing'))

@app.route('/paypal/cancel')
@login_required
def paypal_cancel():
    """Handle cancelled PayPal payment"""
    # Clear payment session
    session.pop('paypal_payment_id', None)
    flash('Payment cancelled. You can try again anytime.', 'info')
    return redirect(url_for('pricing'))

# =====================================
# 💳 STRIPE PAYMENT ROUTES
# =====================================

@app.route('/stripe/create-payment-intent', methods=['POST'])
@login_required
def create_stripe_payment_intent():
    """Create Stripe payment intent for Pro plan upgrade"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=500,  # $5.00 in cents
            currency='usd',
            metadata={
                'user_id': session['user_id'],
                'plan': 'pro'
            }
        )
        return jsonify({
            'client_secret': intent.client_secret,
            'publishable_key': STRIPE_PUBLISHABLE_KEY
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/stripe/payment-success')
@login_required
def stripe_payment_success():
    """Handle successful Stripe payment"""
    payment_intent_id = request.args.get('payment_intent')
    
    if not payment_intent_id:
        flash('Invalid payment session.', 'error')
        return redirect(url_for('pricing'))
    
    try:
        # Verify payment intent
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Payment successful - upgrade user to Pro with 30-day expiration
            user_id = session['user_id']
            execute_db('''
                UPDATE users 
                SET plan_type = ?, pro_plan_expires_at = datetime('now', '+30 days') 
                WHERE id = ?
            ''', ['pro', user_id])
            session['plan_type'] = 'pro'
            
            flash('Payment successful! Welcome to SoilsFert Pro!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Payment not completed. Please try again.', 'error')
            return redirect(url_for('pricing'))
            
    except Exception as e:
        flash(f'Payment verification error: {str(e)}', 'error')
        return redirect(url_for('pricing'))

@app.route('/stripe/checkout')
@login_required
def stripe_checkout():
    """Stripe checkout page with separate CVV field"""
    with open('stripe_checkout_separate.html', 'r') as f:
        stripe_template = f.read()
    return render_template_string(stripe_template)

# =====================================
# 🌐 API ROUTES INCLUDING TESTIMONIALS
# =====================================

@app.route('/api/soil-analysis', methods=['POST'])
@login_required
def api_soil_analysis():
    """API endpoint for soil analysis"""
    data = request.get_json()
    result = ProfessionalSoilAnalyzer.analyze_soil(data)
    return jsonify(result)

@app.route('/api/compost-recipe', methods=['POST'])
@login_required
def api_compost_recipe():
    """API endpoint for compost recipe generation"""
    data = request.get_json()
    result = CompostRecipeGenerator.generate_recipe(data)
    return jsonify(result)

@app.route('/api/testimonials', methods=['GET'])
def api_get_testimonials():
    """API endpoint to get featured testimonials"""
    try:
        print("=== LOADING TESTIMONIALS DEBUG ===")
        testimonials = query_db('''
            SELECT t.*, u.first_name, u.last_name, u.country, u.region 
            FROM testimonials t
            JOIN users u ON t.user_id = u.id
            WHERE t.is_approved = 1
            ORDER BY t.created_at DESC
            LIMIT 10
        ''')
        print(f"Found {len(testimonials)} testimonials")
        
        result = []
        for t in testimonials:
            # Generate user name
            user_name = f"{t['first_name']} {t['last_name']}" if t['first_name'] else t['user_name']
            
            # Generate initials from the user name
            if t['first_name'] and t['last_name']:
                initials = f"{t['first_name'][0].upper()}{t['last_name'][0].upper()}"
            elif user_name and len(user_name.split()) >= 2:
                name_parts = user_name.split()
                initials = f"{name_parts[0][0].upper()}{name_parts[1][0].upper()}"
            elif user_name:
                initials = user_name[0].upper() + (user_name[1].upper() if len(user_name) > 1 else user_name[0].upper())
            else:
                initials = "UN"  # Unknown
            
            result.append({
                'id': t['id'],
                'content': t['comment'],
                'rating': t['rating'],
                'user_name': user_name,
                'user_title': t['user_title'] or '',
                'initials': initials,
                'location': f"{t['region']}, {t['country']}" if t['region'] and t['country'] else t['country'] or 'Unknown',
                'created_at': t['created_at']
            })
        
        print("Testimonials loaded successfully!")
        return jsonify(result)
        
    except Exception as e:
        print(f"ERROR loading testimonials: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

def api_login_required(f):
    """Decorator for API endpoints that returns JSON error for unauthenticated users"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please log in or register to submit a testimonial.',
                'action': 'login_required'
            }), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/submit-testimonial', methods=['POST'])
@api_login_required
def api_submit_testimonial():
    """API endpoint to submit a testimonial"""
    try:
        print("=== TESTIMONIAL SUBMISSION DEBUG ===")
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data.get('content'):
            print("Error: No content provided")
            return jsonify({'error': 'Testimonial content is required'}), 400
        
        user_id = session['user_id']
        print(f"User ID: {user_id}")
        rating = min(5, max(1, int(data.get('rating', 5))))
        print(f"Rating: {rating}")
        
        # Check if user already has a testimonial
        existing = query_db('SELECT id FROM testimonials WHERE user_id = ?', [user_id], one=True)
        print(f"Existing testimonial: {existing}")
        
        # Get user info for the testimonial
        user_info = query_db('SELECT first_name, last_name FROM users WHERE id = ?', [user_id], one=True)
        user_name = f"{user_info['first_name']} {user_info['last_name']}" if user_info and user_info['first_name'] else 'Anonymous User'
        user_title = data.get('user_title', '')
        
        if existing:
            # Update existing testimonial
            print("Updating existing testimonial...")
            execute_db('''
                UPDATE testimonials 
                SET user_name = ?, user_title = ?, comment = ?, rating = ?, created_at = CURRENT_TIMESTAMP, is_approved = 1
                WHERE user_id = ?
            ''', [user_name, user_title, data['content'], rating, user_id])
        else:
            # Create new testimonial
            print("Creating new testimonial...")
            execute_db('''
                INSERT INTO testimonials (user_id, user_name, user_title, comment, rating, is_approved)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', [user_id, user_name, user_title, data['content'], rating])
        
        print("Testimonial saved successfully!")
        return jsonify({'success': True, 'message': 'Thank you for your testimonial!'})
        
    except Exception as e:
        print(f"ERROR in testimonial submission: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# =====================================
# 🧪 PROFESSIONAL SOIL ANALYZER CLASS
# =====================================

class ProfessionalSoilAnalyzer:
    """Professional-grade soil analysis with enhanced calculations"""
    
    @staticmethod
    def calculate_enhanced_cec(organic_matter, clay_content, ph):
        """Calculate enhanced CEC based on organic matter, clay, and pH"""
        # Base CEC from clay (cmol/kg)
        clay_cec = clay_content * 0.5
        
        # Organic matter contribution (highly pH dependent)
        if ph < 5.5:
            om_cec = organic_matter * 2.0  # Lower pH reduces OM CEC
        elif ph < 6.5:
            om_cec = organic_matter * 3.0
        else:
            om_cec = organic_matter * 4.0  # Higher pH increases OM CEC
        
        # pH adjustment factor
        ph_factor = 1.0
        if ph < 5.0:
            ph_factor = 0.8  # Very acidic soils have reduced CEC
        elif ph > 8.0:
            ph_factor = 1.1  # Alkaline soils may have slightly higher effective CEC
        
        total_cec = (clay_cec + om_cec) * ph_factor
        return round(max(total_cec, 1.0), 2)
    
    @staticmethod
    def calculate_cationic_ratios(ca, mg, k, na, cec):
        """Calculate cationic ratios and percentages"""
        if cec <= 0:
            return {}
        
        # Convert to percentages of CEC
        ca_percent = (ca / cec) * 100 if cec > 0 else 0
        mg_percent = (mg / cec) * 100 if cec > 0 else 0
        k_percent = (k / cec) * 100 if cec > 0 else 0
        na_percent = (na / cec) * 100 if cec > 0 else 0
        
        # Calculate ratios
        ca_mg_ratio = ca / mg if mg > 0 else float('inf')
        mg_k_ratio = mg / k if k > 0 else float('inf')
        
        return {
            'ca_percent': round(ca_percent, 1),
            'mg_percent': round(mg_percent, 1),
            'k_percent': round(k_percent, 1),
            'na_percent': round(na_percent, 1),
            'ca_mg_ratio': round(ca_mg_ratio, 2) if ca_mg_ratio != float('inf') else 'N/A',
            'mg_k_ratio': round(mg_k_ratio, 2) if mg_k_ratio != float('inf') else 'N/A'
        }
    
    @staticmethod
    def analyze_soil(data):
        """Comprehensive soil analysis with enhanced calculations"""
        try:
            # Extract basic parameters
            ph = float(data.get('ph', 7.0))
            organic_matter = float(data.get('organic_matter', 2.0))
            
            # Enhanced nutrient analysis
            nutrients = {
                'nitrogen_total': float(data.get('nitrogen_total', 0)),
                'phosphorus_olsen': float(data.get('phosphorus_olsen', 0)),
                'potassium_exchangeable': float(data.get('potassium_exchangeable', 0)),
                'calcium': float(data.get('calcium', 0)),
                'magnesium': float(data.get('magnesium', 0)),
                'sulfur': float(data.get('sulfur', 0)),
                'sodium': float(data.get('sodium', 0)),
                'iron': float(data.get('iron', 0)),
                'manganese': float(data.get('manganese', 0)),
                'zinc': float(data.get('zinc', 0)),
                'copper': float(data.get('copper', 0)),
                'boron': float(data.get('boron', 0)),
                'molybdenum': float(data.get('molybdenum', 0))
            }
            
            # Physical parameters
            clay_content = float(data.get('clay_content', 20))
            sand_content = float(data.get('sand_content', 40))
            silt_content = float(data.get('silt_content', 40))
            bulk_density = float(data.get('bulk_density', 1.3))
            
            # Enhanced CEC calculation
            enhanced_cec = ProfessionalSoilAnalyzer.calculate_enhanced_cec(
                organic_matter, clay_content, ph
            )
            
            # Cationic ratios
            cationic_ratios = ProfessionalSoilAnalyzer.calculate_cationic_ratios(
                nutrients['calcium'], nutrients['magnesium'], 
                nutrients['potassium_exchangeable'], nutrients['sodium'], enhanced_cec
            )
            
            # Lime calculation using enhanced method
            calculator = EnhancedLimeCalculator()
            lime_result = calculator.calculate_lime_requirement(
                current_ph=ph,
                target_ph=float(data.get('target_ph', 6.5)),
                bulk_density=bulk_density,
                depth_cm=float(data.get('soil_depth_cm', 20)),
                organic_matter=organic_matter,
                clay_content=clay_content
            )
            
            # Comprehensive analysis result
            analysis_result = {
                'basic_parameters': {
                    'ph': ph,
                    'organic_matter': organic_matter,
                    'enhanced_cec': enhanced_cec
                },
                'nutrients': nutrients,
                'physical_properties': {
                    'clay_content': clay_content,
                    'sand_content': sand_content,
                    'silt_content': silt_content,
                    'bulk_density': bulk_density,
                    'texture_class': ProfessionalSoilAnalyzer.determine_texture_class(
                        sand_content, silt_content, clay_content
                    )
                },
                'cationic_analysis': cationic_ratios,
                'lime_recommendation': lime_result,
                'recommendations': ProfessionalSoilAnalyzer.generate_recommendations(
                    ph, nutrients, organic_matter, cationic_ratios
                )
            }
            
            return analysis_result
            
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    @staticmethod
    def determine_texture_class(sand, silt, clay):
        """Determine soil texture class based on percentages"""
        if clay >= 40:
            return "Clay"
        elif clay >= 27:
            if sand >= 45:
                return "Sandy Clay"
            elif silt >= 40:
                return "Silty Clay"
            else:
                return "Clay"
        elif clay >= 20:
            if sand >= 45:
                return "Sandy Clay Loam"
            elif silt >= 40:
                return "Silty Clay Loam"
            else:
                return "Clay Loam"
        elif silt >= 50:
            if clay >= 12:
                return "Silty Clay Loam"
            elif clay >= 7:
                return "Silt Loam"
            else:
                return "Silt"
        elif sand >= 70:
            if clay >= 15:
                return "Sandy Clay Loam"
            elif clay >= 7:
                return "Sandy Loam"
            else:
                return "Sand"
        else:
            return "Loam"
    
    @staticmethod
    def generate_recommendations(ph, nutrients, organic_matter, cationic_ratios):
        """Generate comprehensive soil management recommendations"""
        recommendations = []
        
        # pH recommendations
        if ph < 5.5:
            recommendations.append("🔴 CRITICAL: Soil is too acidic. Apply lime to raise pH to 6.0-7.0")
        elif ph > 8.0:
            recommendations.append("🔴 CRITICAL: Soil is too alkaline. Consider sulfur application")
        elif ph < 6.0:
            recommendations.append("🟡 WARNING: Slightly acidic. Monitor pH and consider light liming")
        
        # Organic matter recommendations
        if organic_matter < 2.0:
            recommendations.append("🔴 LOW: Organic matter is low. Add compost or organic amendments")
        elif organic_matter < 3.0:
            recommendations.append("🟡 MODERATE: Organic matter could be improved with compost")
        else:
            recommendations.append("🟢 GOOD: Organic matter levels are adequate")
        
        # Nutrient recommendations
        if nutrients['nitrogen_total'] < 20:
            recommendations.append("🔴 LOW: Nitrogen is deficient. Consider nitrogen fertilizer")
        
        if nutrients['phosphorus_olsen'] < 15:
            recommendations.append("🔴 LOW: Phosphorus is low. Apply phosphate fertilizer")
        
        if nutrients['potassium_exchangeable'] < 100:
            recommendations.append("🔴 LOW: Potassium is deficient. Apply potash fertilizer")
        
        # Cationic balance recommendations
        if isinstance(cationic_ratios.get('ca_mg_ratio'), (int, float)):
            if cationic_ratios['ca_mg_ratio'] < 2:
                recommendations.append("🟡 IMBALANCE: Ca:Mg ratio is low. Consider calcium application")
            elif cationic_ratios['ca_mg_ratio'] > 10:
                recommendations.append("🟡 IMBALANCE: Ca:Mg ratio is high. Consider magnesium application")
        
        return recommendations

# =====================================
# 🧮 COMPOST RECIPE GENERATOR
# =====================================

class CompostRecipeGenerator:
    """Generate custom compost recipes based on soil analysis"""
    
    @staticmethod
    def generate_recipe(soil_data):
        """Generate compost recipe based on soil deficiencies"""
        try:
            ph = float(soil_data.get('ph', 7.0))
            organic_matter = float(soil_data.get('organic_matter', 2.0))
            nitrogen = float(soil_data.get('nitrogen_total', 0))
            phosphorus = float(soil_data.get('phosphorus_olsen', 0))
            potassium = float(soil_data.get('potassium_exchangeable', 0))
            
            # Base compost recipe
            recipe = {
                'base_materials': [],
                'amendments': [],
                'ratios': {},
                'instructions': []
            }
            
            # Carbon-rich materials (browns)
            recipe['base_materials'].append({
                'material': 'Dry leaves',
                'amount': '40%',
                'purpose': 'Carbon source, structure'
            })
            
            recipe['base_materials'].append({
                'material': 'Straw or hay',
                'amount': '20%',
                'purpose': 'Carbon source, aeration'
            })
            
            # Nitrogen-rich materials (greens)
            if nitrogen < 20:
                recipe['base_materials'].append({
                    'material': 'Fresh grass clippings',
                    'amount': '25%',
                    'purpose': 'Nitrogen source'
                })
                
                recipe['base_materials'].append({
                    'material': 'Kitchen scraps (vegetable)',
                    'amount': '10%',
                    'purpose': 'Nitrogen, minerals'
                })
            
            # pH adjustments
            if ph < 6.0:
                recipe['amendments'].append({
                    'material': 'Wood ash',
                    'amount': '2-3 cups per cubic yard',
                    'purpose': 'Raise pH, add potassium'
                })
            elif ph > 7.5:
                recipe['amendments'].append({
                    'material': 'Pine needles',
                    'amount': '5-10% of total volume',
                    'purpose': 'Lower pH naturally'
                })
            
            # Nutrient-specific amendments
            if phosphorus < 15:
                recipe['amendments'].append({
                    'material': 'Bone meal',
                    'amount': '1-2 cups per cubic yard',
                    'purpose': 'Phosphorus source'
                })
            
            if potassium < 100:
                recipe['amendments'].append({
                    'material': 'Banana peels or wood ash',
                    'amount': '5% of total volume',
                    'purpose': 'Potassium source'
                })
            
            # Organic matter boost
            if organic_matter < 3.0:
                recipe['amendments'].append({
                    'material': 'Aged manure',
                    'amount': '10-15% of total volume',
                    'purpose': 'Organic matter, slow-release nutrients'
                })
            
            # C:N ratio
            recipe['ratios'] = {
                'carbon_nitrogen': '25-30:1',
                'browns_greens': '3:1',
                'moisture': '50-60%'
            }
            
            # Instructions
            recipe['instructions'] = [
                "1. Layer browns and greens in 3:1 ratio",
                "2. Add amendments evenly throughout layers",
                "3. Maintain moisture at 50-60% (feels like wrung-out sponge)",
                "4. Turn pile every 2-3 weeks",
                "5. Compost ready in 3-6 months",
                "6. Apply 2-4 inches to soil surface"
            ]
            
            return recipe
            
        except Exception as e:
            return {'error': f'Recipe generation failed: {str(e)}'}

# =====================================
# 📱 ENHANCED DASHBOARD TEMPLATE WITH DYNAMIC TESTIMONIALS
# =====================================

ENHANCED_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Payment - SoilsFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.stripe.com/v3/"></script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <div class="max-w-md mx-auto pt-16 px-4">
        <!-- Header -->
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl mb-4 shadow-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 mb-2">Secure Payment</h1>
            <p class="text-slate-600">SoilsFert Pro Plan - $5.00 USD</p>
        </div>

        <!-- Payment Form -->
        <div class="bg-white rounded-2xl shadow-xl border border-slate-200 p-6">
            <form id="payment-form">
                <div class="mb-6 space-y-4">
                    <!-- Card Number -->
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-2">
                            Card Number
                        </label>
                        <div id="card-number-element" class="p-3 border border-slate-300 rounded-lg">
                            <!-- Card number element -->
                        </div>
                    </div>
                    
                    <!-- Expiry and CVC -->
                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-2">
                                Expiry Date
                            </label>
                            <div id="card-expiry-element" class="p-3 border border-slate-300 rounded-lg">
                                <!-- Expiry element -->
                            </div>
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-slate-700 mb-2">
                                CVV
                            </label>
                            <div id="card-cvc-element" class="p-3 border border-slate-300 rounded-lg">
                                <!-- CVC element -->
                            </div>
                        </div>
                    </div>
                    
                    <div id="card-errors" role="alert" class="text-red-600 text-sm mt-2"></div>
                </div>

                <button id="submit-button" 
                        class="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold flex items-center justify-center space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                    </svg>
                    <span id="button-text">Pay $5.00 Securely</span>
                </button>

                <div class="mt-4 text-center">
                    <p class="text-xs text-slate-500">
                        <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                        </svg>
                        Secured by Stripe • SSL Encrypted
                    </p>
                </div>
            </form>

            <div class="mt-6 pt-4 border-t border-slate-200">
                <a href="{{ url_for('pricing') }}" 
                   class="text-slate-600 hover:text-slate-800 text-sm font-medium flex items-center justify-center">
                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
                    </svg>
                    Back to Pricing
                </a>
            </div>
        </div>
    </div>

    <script>
        const stripe = Stripe('{{ publishable_key }}');
        const elements = stripe.elements();

        // Create card element
        const cardElement = elements.create('card', {
            style: {
                base: {
                    fontSize: '16px',
                    color: '#424770',
                    '::placeholder': {
                        color: '#aab7c4',
                    },
                },
            },
        });

        cardElement.mount('#card-element');

        // Handle form submission
        const form = document.getElementById('payment-form');
        const submitButton = document.getElementById('submit-button');
        const buttonText = document.getElementById('button-text');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            submitButton.disabled = true;
            buttonText.textContent = 'Processing...';

            try {
                // Create payment intent
                const response = await fetch('/stripe/create-payment-intent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                const {client_secret, error} = await response.json();

                if (error) {
                    throw new Error(error);
                }

                // Confirm payment
                const {error: stripeError, paymentIntent} = await stripe.confirmCardPayment(client_secret, {
                    payment_method: {
                        card: cardElement,
                    }
                });

                if (stripeError) {
                    // Show error to customer
                    document.getElementById('card-errors').textContent = stripeError.message;
                    submitButton.disabled = false;
                    buttonText.textContent = 'Pay $5.00 Securely';
                } else {
                    // Payment succeeded
                    window.location.href = '/stripe/payment-success?payment_intent=' + paymentIntent.id;
                }
            } catch (error) {
                document.getElementById('card-errors').textContent = error.message;
                submitButton.disabled = false;
                buttonText.textContent = 'Pay $5.00 Securely';
            }
        });

        // Handle real-time validation errors from the card Element
        cardElement.on('change', ({error}) => {
            const displayError = document.getElementById('card-errors');
            if (error) {
                displayError.textContent = error.message;
            } else {
                displayError.textContent = '';
            }
        });
    </script>
</body>
</html>
    '''

# =====================================
# 🌐 API ROUTES INCLUDING TESTIMONIALS
# =====================================

@app.route('/api/compost-calculate', methods=['POST'])
@login_required
def api_compost_calculate():
    """API endpoint for compost calculation"""
    data = request.get_json()
    materials = data.get('materials', {})
    target_volume = data.get('target_volume', 100)
    
    result = CompostCalculator.calculate_recipe(materials, target_volume)
    return jsonify(result)

@app.route('/api/lime-types', methods=['GET'])
@login_required
def api_lime_types():
    """API endpoint to get lime types"""
    return jsonify(EnhancedLimeCalculator.LIME_TYPES)

@app.route('/api/validate-calculations', methods=['GET'])
@login_required
def api_validate_calculations():
    """API endpoint to run scientific validation of calculations"""
    try:
        # Capture validation output
        import io
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        
        # Run validations
        lime_valid = ScientificValidation.validate_lime_calculations()
        nutrient_valid = ScientificValidation.validate_nutrient_conversions()
        
        # Restore stdout
        sys.stdout = old_stdout
        validation_output = captured_output.getvalue()
        
        return jsonify({
            'success': True,
            'lime_calculations_valid': lime_valid,
            'nutrient_conversions_valid': nutrient_valid,
            'validation_output': validation_output,
            'overall_status': 'PASSED' if (lime_valid and nutrient_valid) else 'FAILED'
        })
        
    except Exception as e:
        sys.stdout = old_stdout
        return jsonify({
            'success': False,
            'error': str(e),
            'overall_status': 'ERROR'
        }), 500

# =====================================
# 💬 TESTIMONIALS API ENDPOINTS
# =====================================

# Replace your LANDING_PAGE_TEMPLATE with this corrected version

LANDING_PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SoilsFert - Smart Soil Analysis Platform</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f8fafc',
                            100: '#f1f5f9',
                            500: '#0f172a',
                            600: '#334155',
                            700: '#1e293b'
                        },
                        accent: {
                            500: '#10b981',
                            600: '#059669'
                        }
                    },
                    fontFamily: {
                        'sans': ['Inter', 'system-ui', 'sans-serif']
                    }
                }
            }
        }
    </script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        /* Modern minimal styles */
        html {
            scroll-behavior: smooth;
        }
        
        .fade-in {
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.6s ease-out;
        }
        
        .fade-in.visible {
            opacity: 1;
            transform: translateY(0);
        }
        
        .gradient-text {
            background: linear-gradient(135deg, #0f172a 0%, #10b981 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .card-hover {
            transition: all 0.3s ease;
        }
        
        .card-hover:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            transition: all 0.3s ease;
        }
        
        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.3);
        }
        
        .section-padding {
            padding: 5rem 0;
        }
        
        @media (max-width: 768px) {
            .section-padding {
                padding: 3rem 0;
            }
        }
    </style>
    <script>
        // Simple modern animations
        document.addEventListener('DOMContentLoaded', () => {
            // Intersection Observer for fade-in animations
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, { threshold: 0.1 });

            // Observe all fade-in elements
            document.querySelectorAll('.fade-in').forEach(el => {
                observer.observe(el);
            });
        });
    </script>
</head>
<body class="bg-white">
    <!-- Modern Navigation -->
    <nav class="bg-white/95 backdrop-blur-md shadow-sm border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <!-- Logo Section -->
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>

                <!-- Navigation Links -->
                <div class="hidden md:flex items-center space-x-8">
                    <a href="#features" class="text-gray-700 hover:text-blue-600 font-medium transition-colors">Features</a>
                    <a href="#how-it-works" class="text-gray-700 hover:text-blue-600 font-medium transition-colors">How It Works</a>
                    <a href="{{ url_for('pricing') }}" class="text-gray-700 hover:text-blue-600 font-medium transition-colors">Pricing</a>
                    <a href="{{ url_for('contact') }}" class="text-gray-700 hover:text-blue-600 font-medium transition-colors">Contact</a>
                </div>

                <!-- Auth Buttons -->
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('login') }}" 
                       class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                        Login
                    </a>
                    <a href="{{ url_for('register') }}" 
                       class="inline-flex items-center px-6 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105 shadow-lg">
                        <i class="fas fa-rocket mr-2"></i>
                        Start Free
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="relative overflow-hidden min-h-screen flex items-center">
        <!-- Background Gradient with parallax -->
        <div class="absolute inset-0 bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900" data-parallax-bg data-speed="0.1"></div>
        <!-- Futuristic aurora layer with parallax -->
        <div class="aurora" data-parallax-bg data-speed="0.2"></div>
        

        <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
            <div class="text-center" data-reveal>
                <!-- Main Headline with text parallax -->
                <div class="mb-12">
                    <div class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 backdrop-blur-sm border border-cyan-500/30 text-cyan-300 rounded-full text-sm font-medium mb-8 shine" data-parallax-text data-speed="0.1">
                        <i class="fas fa-atom mr-2"></i>
                        Next-Gen Soil Analysis Platform
                    </div>
                    <h1 class="text-6xl sm:text-7xl lg:text-8xl font-bold mb-8 leading-tight" data-parallax-text data-speed="0.15">
                        <span class="block text-white">Smart Soil</span>
                        <span class="block bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
                            Analysis
                        </span>
                    </h1>
                    <p class="text-xl sm:text-2xl text-gray-300 max-w-4xl mx-auto leading-relaxed mb-12" data-parallax-text data-speed="0.1">
                        Revolutionary soil analysis powered by advanced algorithms. Get precise lime calculations and optimize your compost recipes with scientific precision.
                    </p>
                </div>

                <!-- CTA Buttons with parallax -->
                <div class="mb-16" data-reveal data-parallax-text data-speed="0.08">
                    <div class="flex flex-col sm:flex-row justify-center items-center space-y-6 sm:space-y-0 sm:space-x-8">
                        <a href="{{ url_for('register') }}" 
                           class="group relative inline-flex items-center px-10 py-5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-lg font-semibold rounded-2xl hover:from-cyan-400 hover:to-blue-500 transition-all duration-300 transform hover:scale-105 shadow-2xl shine overflow-hidden">
                            <div class="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                            <i class="fas fa-rocket mr-3 relative z-10"></i>
                            <span class="relative z-10">Start Free Analysis</span>
                            <i class="fas fa-arrow-right ml-3 relative z-10 group-hover:translate-x-1 transition-transform"></i>
                        </a>
                        <a href="#features" 
                           class="inline-flex items-center px-10 py-5 bg-white/10 backdrop-blur-sm border border-white/20 text-white text-lg font-semibold rounded-2xl hover:bg-white/20 hover:border-white/30 transition-all duration-300 transform hover:scale-105 shadow-xl">
                            <i class="fas fa-play mr-3"></i>
                            Explore Features
                        </a>
                    </div>
                </div>

                <!-- Social Proof with staggered parallax -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-4xl mx-auto" data-reveal data-parallax-text data-speed="0.05">
                    <div class="flex flex-col items-center space-y-3 p-6 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                        <div class="w-12 h-12 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-check text-white text-xl"></i>
                        </div>
                        <span class="text-white font-semibold text-lg">3 Free Analyses</span>
                        <span class="text-gray-400 text-sm text-center">No credit card required</span>
                    </div>
                    <div class="flex flex-col items-center space-y-3 p-6 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                        <div class="w-12 h-12 bg-gradient-to-r from-blue-400 to-cyan-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-microscope text-white text-xl"></i>
                        </div>
                        <span class="text-white font-semibold text-lg">Scientific Method</span>
                        <span class="text-gray-400 text-sm text-center">Lab-grade precision</span>
                    </div>
                    <div class="flex flex-col items-center space-y-3 p-6 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10">
                        <div class="w-12 h-12 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                            <i class="fas fa-shield-alt text-white text-xl"></i>
                        </div>
                        <span class="text-white font-semibold text-lg">Secure & Trusted</span>
                        <span class="text-gray-400 text-sm text-center">Enterprise security</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="py-32 bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 relative overflow-hidden">
        <!-- Enhanced Background with parallax -->
        <div class="absolute inset-0">
            <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-gradient-to-r from-blue-100/30 to-indigo-100/30 rounded-full blur-3xl" data-parallax-bg data-speed="0.2"></div>
            <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-gradient-to-r from-slate-100/40 to-blue-100/40 rounded-full blur-3xl" data-parallax-bg data-speed="0.15"></div>
            <!-- Additional floating elements -->
            <div class="absolute top-1/2 left-1/6 w-64 h-64 bg-gradient-to-r from-cyan-100/25 to-blue-100/25 rounded-full blur-2xl" data-parallax-bg data-speed="0.25"></div>
            <div class="absolute bottom-1/6 right-1/6 w-48 h-48 bg-gradient-to-r from-indigo-100/30 to-purple-100/30 rounded-full blur-2xl" data-parallax-bg data-speed="0.18"></div>
        </div>
        
        <div class="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <!-- Header with text parallax -->
            <div class="text-center mb-24">
                <div class="inline-flex items-center px-6 py-3 bg-blue-100/60 backdrop-blur-sm border border-blue-200/50 text-blue-700 rounded-full text-sm font-medium mb-8" data-parallax-text data-speed="0.1">
                    <i class="fas fa-atom mr-2"></i>
                    Advanced Technology
                </div>
                <h2 class="text-5xl lg:text-6xl font-bold mb-8 leading-tight" data-parallax-text data-speed="0.12">
                    <span class="text-slate-800">Advanced</span>
                    <span class="block bg-gradient-to-r from-blue-600 via-indigo-600 to-slate-700 bg-clip-text text-transparent">Features</span>
                </h2>
                <p class="text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed" data-parallax-text data-speed="0.08">
                    Experience professional soil analysis with cutting-edge algorithms and scientific precision
                </p>
            </div>

            <!-- Centered Feature Boxes with Scroll Animations -->
            <div class="space-y-40">
                <!-- Feature 1: Professional Analysis -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-white/80 backdrop-blur-sm border border-blue-200/50 rounded-2xl p-12 text-center shadow-lg hover:shadow-xl transition-all duration-300">
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl mb-8 shadow-md">
                                    <i class="fas fa-microscope text-white text-3xl"></i>
                                </div>
                                <h3 class="text-3xl font-bold text-slate-800 mb-6">Professional Analysis</h3>
                                <p class="text-lg text-slate-600 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Complete soil testing with automatic CEC calculations, cationic ratios, and precise lime recommendations based on Exchangeable Acidity and soil buffering factors.
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-calculator text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">Automatic CEC</h4>
                                        <p class="text-slate-600 text-sm">Precise calculations</p>
                                    </div>
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-chart-pie text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">Cationic Ratios</h4>
                                        <p class="text-slate-600 text-sm">Scientific analysis</p>
                                    </div>
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-flask text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">Lime Recommendations</h4>
                                        <p class="text-slate-600 text-sm">Lab-grade precision</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Feature 2: Smart Lime Calculator -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-white/80 backdrop-blur-sm border border-blue-200/50 rounded-2xl p-12 text-center shadow-lg hover:shadow-xl transition-all duration-300">
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl mb-8 shadow-md">
                                    <i class="fas fa-mountain text-white text-3xl"></i>
                                </div>
                                <h3 class="text-3xl font-bold text-slate-800 mb-6">Smart Lime Calculator</h3>
                                <p class="text-lg text-slate-600 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Advanced lime recommendations with soil type factors. Choose from 5 lime types with precise kg/ha calculations using the enhanced formula: t/ha = 5 × ΔAE × ρb × d × Sf
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-layer-group text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">5 Lime Types</h4>
                                        <p class="text-slate-600 text-sm">Complete selection</p>
                                    </div>
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-atom text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">Soil Buffering</h4>
                                        <p class="text-slate-600 text-sm">Physics-based factors</p>
                                    </div>
                                    <div class="bg-blue-50/80 rounded-xl p-6 border border-blue-100">
                                        <div class="w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-coins text-white"></i>
                                        </div>
                                        <h4 class="text-slate-800 font-semibold mb-2">Cost Optimization</h4>
                                        <p class="text-slate-600 text-sm">Maximum efficiency</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Feature 3: Smart Multi-Nutrient System -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-gradient-to-br from-slate-800/50 to-purple-900/50 backdrop-blur-xl border border-purple-500/20 rounded-3xl p-12 text-center">
                            <!-- Pulse rings -->
                            <div class="absolute inset-0 rounded-3xl border-2 border-purple-400/30 pulse-ring"></div>
                            <div class="absolute inset-0 rounded-3xl border-2 border-purple-400/20 pulse-ring" style="animation-delay: 0.5s;"></div>
                            
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-32 h-32 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full mb-8 shadow-2xl">
                                    <i class="fas fa-cogs text-white text-5xl"></i>
                                </div>
                                <h3 class="text-4xl font-bold text-white mb-6">Smart Multi-Nutrient System</h3>
                                <p class="text-xl text-gray-300 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Advanced fertilizer recommendations covering all nutrients with maximum compensation efficiency, AI-powered optimization, and cost-effective solutions.
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    <div class="bg-purple-500/10 backdrop-blur-sm rounded-2xl p-6 border border-purple-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-seedling text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Complete Nutrients</h4>
                                        <p class="text-gray-400 text-sm">Primary + Secondary + Micros</p>
                                    </div>
                                    <div class="bg-purple-500/10 backdrop-blur-sm rounded-2xl p-6 border border-purple-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-microchip text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Smart Product Selection</h4>
                                        <p class="text-gray-400 text-sm">AI-powered recommendations</p>
                                    </div>
                                    <div class="bg-purple-500/10 backdrop-blur-sm rounded-2xl p-6 border border-purple-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-chart-line text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Cost Optimization Algorithm</h4>
                                        <p class="text-gray-400 text-sm">Maximum efficiency & ROI</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Feature 4: Compost Calculator -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-gradient-to-br from-slate-800/50 to-orange-900/50 backdrop-blur-xl border border-orange-500/20 rounded-3xl p-12 text-center">
                            <!-- Pulse rings -->
                            <div class="absolute inset-0 rounded-3xl border-2 border-orange-400/30 pulse-ring"></div>
                            <div class="absolute inset-0 rounded-3xl border-2 border-orange-400/20 pulse-ring" style="animation-delay: 0.5s;"></div>
                            
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-32 h-32 bg-gradient-to-br from-orange-500 to-amber-600 rounded-full mb-8 shadow-2xl">
                                    <i class="fas fa-recycle text-white text-5xl"></i>
                                </div>
                                <h3 class="text-4xl font-bold text-white mb-6">Compost Calculator</h3>
                                <p class="text-xl text-gray-300 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Optimize compost recipes with carbon-nitrogen ratio calculations for maximum efficiency and quality scoring using advanced organic chemistry principles.
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    <div class="bg-orange-500/10 backdrop-blur-sm rounded-2xl p-6 border border-orange-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-orange-400 to-amber-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-balance-scale text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">C:N Ratio Optimization</h4>
                                        <p class="text-gray-400 text-sm">Perfect carbon-nitrogen balance</p>
                                    </div>
                                    <div class="bg-orange-500/10 backdrop-blur-sm rounded-2xl p-6 border border-orange-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-orange-400 to-amber-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-leaf text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Material Recommendations</h4>
                                        <p class="text-gray-400 text-sm">Smart ingredient selection</p>
                                    </div>
                                    <div class="bg-orange-500/10 backdrop-blur-sm rounded-2xl p-6 border border-orange-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-orange-400 to-amber-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-star text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Quality Scoring System</h4>
                                        <p class="text-gray-400 text-sm">Performance metrics</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Feature 5: Complete Analysis -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-gradient-to-br from-slate-800/50 to-indigo-900/50 backdrop-blur-xl border border-indigo-500/20 rounded-3xl p-12 text-center">
                            <!-- Pulse rings -->
                            <div class="absolute inset-0 rounded-3xl border-2 border-indigo-400/30 pulse-ring"></div>
                            <div class="absolute inset-0 rounded-3xl border-2 border-indigo-400/20 pulse-ring" style="animation-delay: 0.5s;"></div>
                            
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-32 h-32 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-full mb-8 shadow-2xl">
                                    <i class="fas fa-chart-bar text-white text-5xl"></i>
                                </div>
                                <h3 class="text-4xl font-bold text-white mb-6 leading-tight py-2">Complete Analysis</h3>
                                <p class="text-xl text-gray-300 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Comprehensive reports with interactive charts, cost breakdowns, and actionable recommendations powered by advanced data visualization and analytics.
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    <div class="bg-indigo-500/10 backdrop-blur-sm rounded-2xl p-6 border border-indigo-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-indigo-400 to-violet-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-chart-pie text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Interactive Charts & Graphs</h4>
                                        <p class="text-gray-400 text-sm">Dynamic visualizations</p>
                                    </div>
                                    <div class="bg-indigo-500/10 backdrop-blur-sm rounded-2xl p-6 border border-indigo-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-indigo-400 to-violet-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-calculator text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Detailed Cost Analysis</h4>
                                        <p class="text-gray-400 text-sm">Financial optimization</p>
                                    </div>
                                    <div class="bg-indigo-500/10 backdrop-blur-sm rounded-2xl p-6 border border-indigo-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-indigo-400 to-violet-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-print text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Printable Reports</h4>
                                        <p class="text-gray-400 text-sm">Professional documentation</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Feature 6: Scientific Method -->
                <div class="feature-box">
                    <div class="max-w-4xl mx-auto">
                        <div class="relative bg-gradient-to-br from-slate-800/50 to-rose-900/50 backdrop-blur-xl border border-rose-500/20 rounded-3xl p-12 text-center">
                            <!-- Pulse rings -->
                            <div class="absolute inset-0 rounded-3xl border-2 border-rose-400/30 pulse-ring"></div>
                            <div class="absolute inset-0 rounded-3xl border-2 border-rose-400/20 pulse-ring" style="animation-delay: 0.5s;"></div>
                            
                            <div class="relative z-10">
                                <div class="inline-flex items-center justify-center w-32 h-32 bg-gradient-to-br from-rose-500 to-pink-600 rounded-full mb-8 shadow-2xl">
                                    <i class="fas fa-graduation-cap text-white text-5xl"></i>
                                </div>
                                <h3 class="text-4xl font-bold text-white mb-6">Scientific Method</h3>
                                <p class="text-xl text-gray-300 leading-relaxed mb-12 max-w-2xl mx-auto">
                                    Based on peer-reviewed research and scientific formulas, not arbitrary conversion factors. Delivering laboratory-grade accuracy for professional agriculture.
                                </p>
                                <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                                    <div class="bg-rose-500/10 backdrop-blur-sm rounded-2xl p-6 border border-rose-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-rose-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-university text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Peer-Reviewed Methods</h4>
                                        <p class="text-gray-400 text-sm">Academic validation</p>
                                    </div>
                                    <div class="bg-rose-500/10 backdrop-blur-sm rounded-2xl p-6 border border-rose-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-rose-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-atom text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">Physics-Based Calculations</h4>
                                        <p class="text-gray-400 text-sm">Scientific precision</p>
                                    </div>
                                    <div class="bg-rose-500/10 backdrop-blur-sm rounded-2xl p-6 border border-rose-500/20">
                                        <div class="w-12 h-12 bg-gradient-to-r from-rose-400 to-pink-400 rounded-full flex items-center justify-center mx-auto mb-4">
                                            <i class="fas fa-bullseye text-white"></i>
                                        </div>
                                        <h4 class="text-white font-semibold mb-2">95% Field Accuracy</h4>
                                        <p class="text-gray-400 text-sm">Proven results</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- How It Works Section -->
    <section id="how-it-works" class="py-20 bg-gradient-to-br from-gray-50 to-blue-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="text-center mb-16">
                <h2 class="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
                    How It Works
                </h2>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto">
                    Get professional soil analysis results in just 3 simple steps
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-12">
                <!-- Step 1 -->
                <div class="text-center">
                    <div class="bg-gradient-to-br from-blue-500 to-blue-600 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                        <span class="text-white text-2xl font-bold">1</span>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">Enter Soil Data</h3>
                    <p class="text-gray-600 leading-relaxed">
                        Input your soil test results including pH, nutrients, physical properties, and extraction method.
                    </p>
                </div>

                <!-- Step 2 -->
                <div class="text-center">
                    <div class="bg-gradient-to-br from-green-500 to-green-600 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                        <span class="text-white text-2xl font-bold">2</span>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">Advanced Analysis</h3>
                    <p class="text-gray-600 leading-relaxed">
                        Our system analyzes your data using scientific methods and generates optimized fertilizer recommendations.
                    </p>
                </div>

                <!-- Step 3 -->
                <div class="text-center">
                    <div class="bg-gradient-to-br from-purple-500 to-purple-600 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg">
                        <span class="text-white text-2xl font-bold">3</span>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">Get Results</h3>
                    <p class="text-gray-600 leading-relaxed">
                        Receive comprehensive reports with charts, lime calculations, fertilizer recommendations, and costs.
                    </p>
                </div>
            </div>
        </div>
    </section>

    <!-- Dynamic Testimonials Section -->
    <section class="py-20 bg-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="text-center mb-16">
                <h2 class="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
                    Trusted by Farmers Worldwide
                </h2>
                <p class="text-xl text-gray-600 mb-8">
                    Real experiences from our community
                </p>
                <button onclick="openTestimonialModal()" 
                        class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-600 to-blue-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-blue-700 transition-all transform hover:scale-105 shadow-lg">
                    <i class="fas fa-plus mr-2"></i>
                    Share Your Experience
                </button>
            </div>

            <!-- Testimonials Container -->
            <div class="relative">
                <div id="testimonials-container" class="flex space-x-6 overflow-x-auto pb-4 scroll-smooth">
                    <!-- Loading placeholder -->
                    <div id="testimonials-loading" class="flex space-x-6">
                        <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                            <div class="flex items-center mb-4">
                                <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                <div>
                                    <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                    <div class="h-3 bg-gray-300 rounded w-32"></div>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="h-3 bg-gray-300 rounded"></div>
                                <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                            </div>
                        </div>
                        <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                            <div class="flex items-center mb-4">
                                <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                <div>
                                    <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                    <div class="h-3 bg-gray-300 rounded w-32"></div>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="h-3 bg-gray-300 rounded"></div>
                                <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                            </div>
                        </div>
                        <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                            <div class="flex items-center mb-4">
                                <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                <div>
                                    <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                    <div class="h-3 bg-gray-300 rounded w-32"></div>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="h-3 bg-gray-300 rounded"></div>
                                <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Scroll buttons -->
                <button id="scroll-left" onclick="scrollTestimonials('left')" 
                        class="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white shadow-lg rounded-full p-3 hover:bg-gray-50 transition-colors opacity-0 invisible">
                    <i class="fas fa-chevron-left text-gray-600"></i>
                </button>
                <button id="scroll-right" onclick="scrollTestimonials('right')" 
                        class="absolute right-0 top-1/2 transform -translate-y-1/2 bg-white shadow-lg rounded-full p-3 hover:bg-gray-50 transition-colors opacity-0 invisible">
                    <i class="fas fa-chevron-right text-gray-600"></i>
                </button>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="py-20 bg-gradient-to-r from-green-600 via-blue-600 to-purple-600">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 class="text-4xl lg:text-5xl font-bold text-white mb-6">
                Ready to Optimize Your Soil?
            </h2>
            <p class="text-xl text-blue-100 mb-8 max-w-2xl mx-auto">
                Join thousands of farmers using SoilsFert for scientific soil analysis and advanced recommendations.
            </p>
            <div class="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-6">
                <a href="{{ url_for('register') }}" 
                   class="inline-flex items-center px-8 py-4 bg-white text-blue-600 text-lg font-semibold rounded-xl hover:bg-gray-50 transition-all transform hover:scale-105 shadow-xl">
                    <i class="fas fa-rocket mr-3"></i>
                    Start Free Today
                </a>
                <a href="{{ url_for('pricing') }}" 
                   class="inline-flex items-center px-8 py-4 bg-transparent border-2 border-white text-white text-lg font-semibold rounded-xl hover:bg-white hover:text-blue-600 transition-all transform hover:scale-105">
                    <i class="fas fa-crown mr-3"></i>
                    View Pricing
                </a>
            </div>
            <p class="text-blue-100 text-sm mt-6">
                ✅ 3 free analyses • ✅ No credit card required • ✅ Professional results in minutes
            </p>
        </div>
    </section>

<!-- Footer -->
<footer class="bg-gray-900 text-white py-16">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
            <!-- Company Info -->
            <div class="col-span-1 md:col-span-2">
                <div class="flex items-center space-x-3 mb-6">
                    <span class="text-2xl font-bold">SoilsFert</span>
                </div>
                <p class="text-gray-400 leading-relaxed mb-6 max-w-md">
                    Professional soil analysis platform powered by advanced algorithms and scientific methods. 
                    Trusted by farmers worldwide for accurate soil management decisions.
                </p>
                <div class="flex space-x-4">
                    <a href="https://www.facebook.com/share/1SVcgqUTbP/?mibextid=wwXIfr" target="_blank" class="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center hover:bg-blue-600 transition-colors">
                        <i class="fab fa-facebook-f"></i>
                    </a>
                    <a href="https://www.instagram.com/solganic_5?igsh=aDhyZnAwdmdsaHV4&utm_source=qr" target="_blank" class="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center hover:bg-pink-600 transition-colors">
                        <i class="fab fa-instagram"></i>
                    </a>
                    <a href="https://youtube.com/@solganic?si=wozdWZDNi9NWfiHn" target="_blank" class="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center hover:bg-red-600 transition-colors">
                        <i class="fab fa-youtube"></i>
                    </a>
                    <a href="https://www.linkedin.com/company/solganic/" target="_blank" class="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center hover:bg-blue-700 transition-colors">
                        <i class="fab fa-linkedin-in"></i>
                    </a>
                </div>
            </div>

            <!-- Quick Links -->
            <div>
                <h4 class="text-lg font-semibold mb-6">Quick Links</h4>
                <ul class="space-y-3">
                    <li><a href="#features" class="text-gray-400 hover:text-white transition-colors">Features</a></li>
                    <li><a href="{{ url_for('pricing') }}" class="text-gray-400 hover:text-white transition-colors">Pricing</a></li>
                    <li><a href="#how-it-works" class="text-gray-400 hover:text-white transition-colors">How It Works</a></li>
                    <li><a href="{{ url_for('register') }}" class="text-gray-400 hover:text-white transition-colors">Sign Up</a></li>
                </ul>
            </div>

            <!-- Support -->
            <div>
                <h4 class="text-lg font-semibold mb-6">Support</h4>
                <ul class="space-y-3">
                    <li><a href="{{ url_for('terms_of_service') }}" class="text-gray-400 hover:text-white transition-colors">Terms of Service</a></li>
                    <li><a href="{{ url_for('privacy_policy') }}" class="text-gray-400 hover:text-white transition-colors">Privacy Policy</a></li>
                    <li><a href="{{ url_for('contact') }}" class="text-gray-400 hover:text-white transition-colors">Contact Us</a></li>
                </ul>
            </div>
        </div>

        <!-- Bottom Footer -->
        <div class="border-t border-gray-800 mt-12 pt-8">
            <div class="flex flex-col md:flex-row justify-between items-center">
                <p class="text-gray-400 text-sm">
                    &copy; 2024 SoilsFert. Made with ❤️ for farmers worldwide.
                </p>
                <div class="flex items-center space-x-6 mt-4 md:mt-0">
                    <span class="text-gray-400 text-sm">Powered by Science & Technology</span>
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-shield-alt text-green-500"></i>
                        <span class="text-gray-400 text-sm">Secure & Trusted</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</footer>

    <!-- Testimonial Modal -->
    <div id="testimonial-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50 modal-backdrop">
        <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6 transform transition-all">
            <div class="flex items-center justify-between mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Share Your Experience</h3>
                <button onclick="closeTestimonialModal()" class="text-gray-400 hover:text-gray-600 transition-colors">
                    <i class="fas fa-times text-xl"></i>
                </button>
            </div>
            
            <form id="testimonial-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Your Title (Optional)</label>
                    <input type="text" id="user-title" placeholder="e.g., Commercial Farmer, Organic Grower" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Rating</label>
                    <div class="flex space-x-1" id="rating-stars">
                        <button type="button" onclick="setRating(1)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(2)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(3)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(4)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(5)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                    </div>
                    <input type="hidden" id="rating-value" value="5">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Your Experience</label>
                    <textarea id="comment" rows="4" required 
                              placeholder="Tell us how SoilsFert has helped your farming..."
                              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors resize-none"></textarea>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Minimum 10 characters</span>
                        <span id="char-count">0/500</span>
                    </div>
                </div>
                
                <div class="flex space-x-3 pt-4">
                    <button type="button" onclick="closeTestimonialModal()" 
                            class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                        Cancel
                    </button>
                    <button type="submit" 
                            class="flex-1 px-4 py-2 bg-gradient-to-r from-green-600 to-blue-600 text-white rounded-lg hover:from-green-700 hover:to-blue-700 transition-colors">
                        Submit
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Testimonials functionality
        let currentRating = 5;

        // Load testimonials on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadTestimonials();
            
            // Character counter for testimonial
            const commentField = document.getElementById('comment');
            if (commentField) {
                commentField.addEventListener('input', function() {
                    const count = this.value.length;
                    document.getElementById('char-count').textContent = `${count}/500`;
                    
                    // Prevent exceeding 500 characters
                    if (count > 500) {
                        this.value = this.value.substring(0, 500);
                        document.getElementById('char-count').textContent = '500/500';
                    }
                });
            }
        });

        // Load testimonials from API
        async function loadTestimonials() {
            try {
                const response = await fetch('/api/testimonials');
                const testimonials = await response.json();
                displayTestimonials(testimonials);
            } catch (error) {
                console.error('Error loading testimonials:', error);
                showEmptyTestimonials();
            }
        }

        // Display testimonials
        function displayTestimonials(testimonials) {
            const container = document.getElementById('testimonials-container');
            const loading = document.getElementById('testimonials-loading');
            
            if (loading) loading.remove();

            if (testimonials.length === 0) {
                showEmptyTestimonials();
                return;
            }

            container.innerHTML = testimonials.map(testimonial => `
                <div class="flex-shrink-0 w-80 bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow">
                    <div class="flex items-center mb-4">
                        <div class="w-12 h-12 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center mr-4">
                            <span class="text-white font-semibold text-sm">${testimonial.initials}</span>
                        </div>
                        <div>
                            <h4 class="font-semibold text-gray-900">${testimonial.user_name}</h4>
                            <p class="text-sm text-gray-600">${testimonial.user_title}</p>
                        </div>
                    </div>
                    <p class="text-gray-600 leading-relaxed mb-4">${testimonial.content}</p>
                    <div class="flex items-center justify-between">
                        <div class="flex text-yellow-400">
                            ${'⭐'.repeat(testimonial.rating)}
                        </div>
                        <span class="text-xs text-gray-500">${formatDate(testimonial.created_at)}</span>
                    </div>
                </div>
            `).join('');

            // Show scroll buttons if needed
            updateScrollButtons();
        }

        // Show empty state
        function showEmptyTestimonials() {
            const container = document.getElementById('testimonials-container');
            const loading = document.getElementById('testimonials-loading');
            
            if (loading) loading.remove();

            container.innerHTML = `
                <div class="w-full text-center py-12">
                    <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-comments text-green-500 text-xl"></i>
                    </div>
                    <h4 class="text-lg font-medium text-gray-900 mb-2">No testimonials yet</h4>
                    <p class="text-gray-600 mb-4">Be the first to share your experience with SoilsFert!</p>
                    <button onclick="openTestimonialModal()" 
                            class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-600 to-blue-600 text-white font-medium rounded-lg hover:from-green-700 hover:to-blue-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>
                        Share Your Story
                    </button>
                </div>
            `;
        }

        // Modal functions
        function openTestimonialModal() {
            // Check if user is logged in
            const isLoggedIn = {{ 'true' if session.user_id else 'false' }};
            
            if (!isLoggedIn) {
                // Redirect to login/register if not logged in
                if (confirm('You need to be logged in to share your experience. Would you like to create a free account?')) {
                    window.location.href = '/register';
                }
                return;
            }
            
            const modal = document.getElementById('testimonial-modal');
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            setRating(5); // Default to 5 stars
            
            // Focus on first input
            setTimeout(() => {
                document.getElementById('user-title').focus();
            }, 100);
        }

        function closeTestimonialModal() {
            const modal = document.getElementById('testimonial-modal');
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.getElementById('testimonial-form').reset();
            document.getElementById('char-count').textContent = '0/500';
            setRating(5);
        }

        // Rating functionality
        function setRating(rating) {
            currentRating = rating;
            document.getElementById('rating-value').value = rating;
            
            const stars = document.querySelectorAll('#rating-stars button');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.style.color = '#F59E0B';
                    star.classList.add('scale-110');
                } else {
                    star.style.color = '#D1D5DB';
                    star.classList.remove('scale-110');
                }
            });
        }

        // Submit testimonial
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('testimonial-form');
            if (form) {
                form.addEventListener('submit', async function(e) {
                    e.preventDefault();
                    
                    const userTitle = document.getElementById('user-title').value.trim();
                    const comment = document.getElementById('comment').value.trim();
                    const rating = parseInt(document.getElementById('rating-value').value);
                    const submitButton = this.querySelector('button[type="submit"]');
                    
                    if (comment.length < 10) {
                        alert('Comment must be at least 10 characters long');
                        return;
                    }
                    
                    if (comment.length > 500) {
                        alert('Comment must be less than 500 characters');
                        return;
                    }
                    
                    // Disable submit button and show loading
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Submitting...';
                    
                    try {
                        const response = await fetch('/api/submit-testimonial', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                user_title: userTitle,
                                content: comment,
                                rating: rating
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            // Show success modal instead of alert
                            if (typeof ModalUtils !== 'undefined') {
                                ModalUtils.success({
                                    title: 'Thank You! 🌟',
                                    message: 'Your testimonial has been submitted successfully!',
                                    details: 'Thank you for sharing your experience with our community.',
                                    autoHide: true,
                                    autoHideDelay: 3000
                                });
                            } else {
                                alert('Thank you for your testimonial! 🌟');
                            }
                            closeTestimonialModal();
                            loadTestimonials(); // Reload testimonials
                        } else {
                            // Check if it's an authentication error
                            if (response.status === 401 || response.status === 403 || result.action === 'login_required') {
                                if (typeof ModalUtils !== 'undefined') {
                                    ModalUtils.error({
                                        title: 'Login Required',
                                        message: result.message || 'Please log in or register to submit a testimonial.',
                                        details: 'You need an account to share your experience with the community.',
                                        confirmText: 'Login / Register',
                                        callback: () => {
                                            window.location.href = '/login';
                                        }
                                    });
                                } else {
                                    if (confirm('Please log in or register to submit a testimonial. Would you like to go to the login page?')) {
                                        window.location.href = '/login';
                                    }
                                }
                            } else {
                                // Show error modal for other errors
                                if (typeof ModalUtils !== 'undefined') {
                                    ModalUtils.error({
                                        title: 'Submission Failed',
                                        message: result.error || 'An error occurred while submitting your testimonial.',
                                        details: 'Please check your connection and try again.',
                                        confirmText: 'Try Again'
                                    });
                                } else {
                                    alert(result.error || 'An error occurred');
                                }
                            }
                        }
                    } catch (error) {
                        console.error('Error submitting testimonial:', error);
                        // Show network error modal for connection issues
                        if (typeof ModalUtils !== 'undefined') {
                            ModalUtils.error({
                                title: 'Network Error',
                                message: 'Unable to submit your testimonial at this time.',
                                details: 'Please check your internet connection and try again.',
                                confirmText: 'Retry',
                                callback: () => {
                                    // Optionally retry the submission
                                    console.log('User chose to retry');
                                }
                            });
                        } else {
                            alert('An error occurred while submitting your testimonial');
                        }
                    } finally {
                        // Re-enable submit button
                        submitButton.disabled = false;
                        submitButton.innerHTML = 'Submit';
                    }
                });
            }
        });

        // Scroll functionality
        function scrollTestimonials(direction) {
            const container = document.getElementById('testimonials-container');
            const scrollAmount = 320; // Width of testimonial card + gap
            
            if (direction === 'left') {
                container.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            } else {
                container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            }
            
            setTimeout(updateScrollButtons, 300);
        }

        // Update scroll button visibility
        function updateScrollButtons() {
            const container = document.getElementById('testimonials-container');
            const leftButton = document.getElementById('scroll-left');
            const rightButton = document.getElementById('scroll-right');
            
            if (!container || !leftButton || !rightButton) return;
            
            const isScrollable = container.scrollWidth > container.clientWidth;
            const canScrollLeft = container.scrollLeft > 0;
            const canScrollRight = container.scrollLeft < (container.scrollWidth - container.clientWidth);
            
            if (isScrollable) {
                leftButton.style.opacity = canScrollLeft ? '1' : '0.3';
                rightButton.style.opacity = canScrollRight ? '1' : '0.3';
                leftButton.classList.remove('opacity-0', 'invisible');
                rightButton.classList.remove('opacity-0', 'invisible');
                leftButton.classList.add('opacity-100', 'visible');
                rightButton.classList.add('opacity-100', 'visible');
            } else {
                leftButton.classList.add('opacity-0', 'invisible');
                rightButton.classList.add('opacity-0', 'invisible');
                leftButton.classList.remove('opacity-100', 'visible');
                rightButton.classList.remove('opacity-100', 'visible');
            }
        }

        // Utility functions
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric',
                year: 'numeric'
            });
        }

        // Handle testimonials container scroll
        document.addEventListener('DOMContentLoaded', function() {
            const container = document.getElementById('testimonials-container');
            if (container) {
                container.addEventListener('scroll', updateScrollButtons);
                window.addEventListener('resize', updateScrollButtons);
            }
        });

        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Add scroll effect to navigation
        window.addEventListener('scroll', function() {
            const nav = document.querySelector('nav');
            if (window.scrollY > 50) {
                nav.classList.add('bg-white/95');
                nav.classList.remove('bg-white/95');
            }
        });

        // Add animation on scroll
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe feature cards
        document.querySelectorAll('.group').forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(card);
        });

        // Close modal when clicking outside
        document.addEventListener('click', function(e) {
            const modal = document.getElementById('testimonial-modal');
            if (e.target === modal) {
                closeTestimonialModal();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeTestimonialModal();
            }
        });
    </script>

    <style>
        /* Custom scrollbar for testimonials */
        #testimonials-container::-webkit-scrollbar {
            height: 8px;
        }
        #testimonials-container::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 4px;
        }
        #testimonials-container::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        #testimonials-container::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Smooth animations */
        * {
            scroll-behavior: smooth;
        }

        /* Gradient text animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }

        /* Floating animation for background elements */
        @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-20px); }
        }

        .animate-float {
            animation: float 6s ease-in-out infinite;
        }

        /* Modal backdrop */
        .modal-backdrop {
            backdrop-filter: blur(4px);
        }

        /* Star rating hover effects */
        #rating-stars button {
            transition: all 0.2s ease;
        }

        #rating-stars button:hover {
            transform: scale(1.2);
        }

        /* Testimonial cards hover effect */
        #testimonials-container > div:hover {
            transform: translateY(-4px);
        }

        /* Modal animation */
        #testimonial-modal.flex {
            animation: modalIn 0.3s ease-out;
        }

        @keyframes modalIn {
            from {
                opacity: 0;
                transform: scale(0.9);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        /* Form focus states */
        input:focus, textarea:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }

        /* Loading animation for submit button */
        .fa-spinner {
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    </style>

    <!-- Modal Management System -->
    <script>
        class ModalManager {
            static activeModals = new Set();
            
            static show(modalId) {
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.classList.remove('hidden');
                    this.activeModals.add(modalId);
                    document.body.style.overflow = 'hidden';
                }
            }
            
            static hide(modalId) {
                const modal = document.getElementById(modalId);
                if (modal) {
                    modal.classList.add('hidden');
                    this.activeModals.delete(modalId);
                    if (this.activeModals.size === 0) {
                        document.body.style.overflow = 'auto';
                    }
                }
            }
        }

        const ModalUtils = {
            success(options = {}) {
                const {
                    title = 'Success!',
                    message = 'Your action was completed successfully!',
                    details = null,
                    autoHide = true,
                    autoHideDelay = 3000
                } = options;
                
                // Create and show success modal dynamically
                const modal = document.createElement('div');
                modal.id = 'dynamicSuccessModal';
                modal.className = 'modal fixed inset-0 z-50';
                modal.innerHTML = `
                    <div class="modal-overlay fixed inset-0 bg-black bg-opacity-50" onclick="this.parentElement.remove()"></div>
                    <div class="flex items-center justify-center min-h-screen p-4">
                        <div class="modal-content bg-white rounded-xl shadow-2xl max-w-md w-full mx-auto">
                            <div class="flex items-center justify-between p-6 border-b border-gray-200">
                                <div class="flex items-center space-x-3">
                                    <div class="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                                        <i class="fas fa-check text-green-600"></i>
                                    </div>
                                    <h3 class="text-lg font-semibold text-gray-900">${title}</h3>
                                </div>
                                <button onclick="this.closest('.modal').remove()" class="text-gray-400 hover:text-gray-600 transition-colors">
                                    <i class="fas fa-times text-xl"></i>
                                </button>
                            </div>
                            <div class="p-6 text-center">
                                <div class="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <i class="fas fa-check text-white text-2xl"></i>
                                </div>
                                <p class="text-gray-700 text-lg mb-4">${message}</p>
                                ${details ? `<div class="bg-green-50 rounded-lg p-4 text-sm text-green-700">${details}</div>` : ''}
                            </div>
                            <div class="flex items-center justify-center p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
                                <button onclick="this.closest('.modal').remove()" class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium">
                                    OK
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
                
                if (autoHide) {
                    setTimeout(() => modal.remove(), autoHideDelay);
                }
            },
            
            error(options = {}) {
                const {
                    title = 'Error',
                    message = 'An error occurred.',
                    details = null,
                    confirmText = 'OK'
                } = options;
                
                // Create and show error modal dynamically
                const modal = document.createElement('div');
                modal.id = 'dynamicErrorModal';
                modal.className = 'modal fixed inset-0 z-50';
                modal.innerHTML = `
                    <div class="modal-overlay fixed inset-0 bg-black bg-opacity-50" onclick="this.parentElement.remove()"></div>
                    <div class="flex items-center justify-center min-h-screen p-4">
                        <div class="modal-content bg-white rounded-xl shadow-2xl max-w-md w-full mx-auto">
                            <div class="flex items-center justify-between p-6 border-b border-gray-200">
                                <div class="flex items-center space-x-3">
                                    <div class="w-10 h-10 bg-red-100 rounded-full flex items-center justify-center">
                                        <i class="fas fa-exclamation-circle text-red-600"></i>
                                    </div>
                                    <h3 class="text-lg font-semibold text-gray-900">${title}</h3>
                                </div>
                                <button onclick="this.closest('.modal').remove()" class="text-gray-400 hover:text-gray-600 transition-colors">
                                    <i class="fas fa-times text-xl"></i>
                                </button>
                            </div>
                            <div class="p-6">
                                <p class="text-gray-700 mb-4">${message}</p>
                                ${details ? `<div class="bg-red-50 rounded-lg p-4 text-sm text-red-700">${details}</div>` : ''}
                            </div>
                            <div class="flex items-center justify-end p-6 border-t border-gray-200 bg-gray-50 rounded-b-xl">
                                <button onclick="this.closest('.modal').remove()" class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium">
                                    ${confirmText}
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(modal);
            }
        };

        // Make globally available
        window.ModalManager = ModalManager;
        window.ModalUtils = ModalUtils;
    </script>
</body>
</html>
'''
REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Create Account - SoilsFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <!-- Modern Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <!-- Logo Section -->
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>

                <!-- Navigation Links -->
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('index') }}" class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                        Home
                    </a>
                    <a href="{{ url_for('login') }}" class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                        Login
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div class="max-w-md w-full">
            <!-- Header Section -->
            <div class="text-center mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-green-500 to-blue-500 rounded-full mb-4">
                    <i class="fas fa-user-plus text-white text-2xl"></i>
                </div>
                <h2 class="text-3xl font-bold text-gray-900 mb-2">Create Your Account</h2>
                <p class="text-gray-600 text-lg">Start your professional soil analysis journey</p>
                
                <!-- Trust Indicators -->
                <div class="mt-4 flex flex-wrap justify-center gap-4 text-sm">
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800">
                        <i class="fas fa-check-circle mr-2"></i>
                        3 Free Analyses
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800">
                        <i class="fas fa-credit-card mr-2"></i>
                        Visa/Mastercard
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-purple-100 text-purple-800">
                        <i class="fas fa-rocket mr-2"></i>
                        Instant Access
                    </span>
                </div>
            </div>
            
            <!-- Flash Messages -->
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="mb-6">
                        {% for category, message in messages %}
                            <div class="rounded-lg p-4 {% if category == 'error' %}bg-red-50 border border-red-200 text-red-800{% else %}bg-green-50 border border-green-200 text-green-800{% endif %}">
                                <div class="flex items-center">
                                    <i class="fas fa-{% if category == 'error' %}exclamation-circle{% else %}check-circle{% endif %} mr-3"></i>
                                    {{ message }}
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}
            
            <!-- Registration Form -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-blue-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-user-circle mr-2 text-blue-500"></i>
                        Account Information
                    </h3>
                </div>
                
                <form class="p-6 space-y-6" method="POST">
                    <!-- Name Fields -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                First Name *
                                <i class="fas fa-user text-blue-500 ml-1"></i>
                            </label>
                            <input name="first_name" type="text" required 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="Enter your first name">
                        </div>
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Last Name *
                                <i class="fas fa-user text-blue-500 ml-1"></i>
                            </label>
                            <input name="last_name" type="text" required 
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="Enter your last name">
                        </div>
                    </div>
                    
                    <!-- Email Field -->
                    <div class="space-y-2">
                        <label class="block text-sm font-medium text-gray-700">
                            Email Address *
                            <i class="fas fa-envelope text-green-500 ml-1"></i>
                        </label>
                        <input name="email" type="email" required 
                               class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                               placeholder="your.email@example.com">
                        <p class="text-xs text-gray-500">We'll use this for your login and important updates</p>
                    </div>
                    
                    <!-- Password Field -->
                    <div class="space-y-2">
                        <label class="block text-sm font-medium text-gray-700">
                            Password *
                            <i class="fas fa-lock text-purple-500 ml-1"></i>
                        </label>
                        <div class="relative">
                            <input name="password" type="password" required id="password"
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors pr-12"
                                   placeholder="Create a secure password">
                            <button type="button" onclick="togglePassword()" class="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600">
                                <i id="password-toggle" class="fas fa-eye"></i>
                            </button>
                        </div>
                        <p class="text-xs text-gray-500">Minimum 6 characters recommended</p>
                    </div>
                    
                    <!-- Optional Fields Section -->
                    <div class="border-t border-gray-200 pt-6">
                        <h4 class="text-md font-medium text-gray-900 mb-4 flex items-center">
                            <i class="fas fa-seedling mr-2 text-green-500"></i>
                            Farm Information (Optional)
                        </h4>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Country
                                    <i class="fas fa-globe text-blue-500 ml-1"></i>
                                </label>
                                <input name="country" type="text" 
                                       class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                       placeholder="United States">
                            </div>
                            
                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Farm Size (acres)
                                    <i class="fas fa-map text-green-500 ml-1"></i>
                                </label>
                                <input name="farm_size" type="number" step="0.1" 
                                       class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                       placeholder="100">
                            </div>
                        </div>
                        
                        <p class="text-xs text-gray-500 mt-2">
                            Help us provide better recommendations tailored to your farm
                        </p>
                    </div>
                    
                    <!-- Submit Button -->
                    <div class="pt-4">
                        <button type="submit" 
                                class="w-full bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-green-700 hover:via-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 shadow-lg">
                            <i class="fas fa-rocket mr-2"></i>
                            Create Account & Start Free
                        </button>
                    </div>
                    
                    <!-- Login Link -->
                    <div class="text-center pt-4 border-t border-gray-200">
                        <p class="text-gray-600">
                            Already have an account? 
                            <a href="{{ url_for('login') }}" class="text-blue-600 hover:text-blue-800 font-medium transition-colors">
                                Sign in here
                            </a>
                        </p>
                    </div>
                </form>
            </div>
            
            <!-- Benefits Section -->
            <div class="mt-8 bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-star mr-2 text-yellow-500"></i>
                        What You Get For Free
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-4">
                        <div class="flex items-center">
                            <div class="bg-green-100 rounded-lg p-2 mr-4">
                                <i class="fas fa-microscope text-green-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">3 Professional Analyses</h4>
                                <p class="text-sm text-gray-600">Complete soil testing with lime calculations</p>
                            </div>
                        </div>
                        
                        <div class="flex items-center">
                            <div class="bg-blue-100 rounded-lg p-2 mr-4">
                                <i class="fas fa-cogs text-blue-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Smart Recommendations</h4>
                                <p class="text-sm text-gray-600">Advanced fertilizer and lime suggestions</p>
                            </div>
                        </div>
                        
                        <div class="flex items-center">
                            <div class="bg-purple-100 rounded-lg p-2 mr-4">
                                <i class="fas fa-recycle text-purple-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Compost Calculator</h4>
                                <p class="text-sm text-gray-600">Optimize your organic matter recipes</p>
                            </div>
                        </div>
                        
                        <div class="flex items-center">
                            <div class="bg-orange-100 rounded-lg p-2 mr-4">
                                <i class="fas fa-chart-line text-orange-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Interactive Reports</h4>
                                <p class="text-sm text-gray-600">Charts, graphs, and detailed insights</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="mt-6 p-4 bg-gradient-to-r from-green-100 to-blue-100 rounded-lg border border-blue-200">
                        <div class="flex items-center justify-center text-center">
                            <div>
                                <p class="text-sm font-semibold text-gray-800">🎉 Start with 3 Free Analyses</p>
                                <p class="text-xs text-gray-600 mt-1">Secure payment via Visa/Mastercard • Professional tools • Expert support</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Password toggle functionality
        function togglePassword() {
            const passwordField = document.getElementById('password');
            const toggleIcon = document.getElementById('password-toggle');
            
            if (passwordField.type === 'password') {
                passwordField.type = 'text';
                toggleIcon.classList.remove('fa-eye');
                toggleIcon.classList.add('fa-eye-slash');
            } else {
                passwordField.type = 'password';
                toggleIcon.classList.remove('fa-eye-slash');
                toggleIcon.classList.add('fa-eye');
            }
        }

        // Form enhancement
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.querySelector('form');
            const inputs = document.querySelectorAll('input[required]');
            const submitButton = document.querySelector('button[type="submit"]');

            // Add real-time validation
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    if (this.value.trim()) {
                        this.classList.add('border-green-300', 'bg-green-50');
                        this.classList.remove('border-red-300', 'bg-red-50');
                    } else {
                        this.classList.remove('border-green-300', 'bg-green-50');
                    }
                });

                input.addEventListener('blur', function() {
                    if (this.hasAttribute('required') && !this.value.trim()) {
                        this.classList.add('border-red-300', 'bg-red-50');
                        this.classList.remove('border-green-300', 'bg-green-50');
                    }
                });

                // Add focus effects
                input.addEventListener('focus', function() {
                    this.parentElement.classList.add('scale-105');
                });
                
                input.addEventListener('blur', function() {
                    this.parentElement.classList.remove('scale-105');
                });
            });

            // Form submission enhancement
            form.addEventListener('submit', function(e) {
                const requiredInputs = Array.from(inputs);
                const isValid = requiredInputs.every(input => input.value.trim());
                
                if (!isValid) {
                    e.preventDefault();
                    
                    // Highlight invalid fields
                    requiredInputs.forEach(input => {
                        if (!input.value.trim()) {
                            input.classList.add('border-red-300', 'bg-red-50');
                            input.focus();
                        }
                    });
                    
                    // Show error message
                    alert('Please fill in all required fields marked with *');
                } else {
                    // Show loading state
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creating Account...';
                    submitButton.disabled = true;
                }
            });
        });
    </script>

    <style>
        /* Custom input focus effects */
        input:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }
        
        /* Smooth transitions */
        * {
            transition: all 0.3s ease;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Form validation styling */
        .border-green-300 {
            border-color: #86efac !important;
        }
        .bg-green-50 {
            background-color: #f0fdf4 !important;
        }
        .border-red-300 {
            border-color: #fca5a5 !important;
        }
        .bg-red-50 {
            background-color: #fef2f2 !important;
        }
    </style>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - SoilsFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'soil-green': {
                            50: '#f0fdf4',
                            100: '#dcfce7',
                            500: '#22c55e',
                            600: '#16a34a',
                            700: '#15803d',
                            800: '#166534'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <div class="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div class="max-w-md w-full space-y-8">
            <!-- Header Section -->
            <div class="text-center">
                <div class="mx-auto w-16 h-16 bg-gradient-to-br from-soil-green-500 to-soil-green-600 rounded-2xl flex items-center justify-center shadow-lg mb-6">
                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
                    </svg>
                </div>
                <h1 class="text-2xl font-bold text-slate-900 mb-2">Welcome to SoilsFert</h1>
                <p class="text-slate-600 text-sm">Sign in to access your agricultural dashboard</p>
            </div>

            <!-- Flash Messages -->
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="space-y-3">
                        {% for category, message in messages %}
                            <div class="p-4 rounded-xl border-l-4 {% if category == 'error' %}bg-red-50 border-red-400 text-red-800{% else %}bg-green-50 border-green-400 text-green-800{% endif %} shadow-sm">
                                <div class="flex">
                                    <div class="flex-shrink-0">
                                        {% if category == 'error' %}
                                            <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                                            </svg>
                                        {% else %}
                                            <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                            </svg>
                                        {% endif %}
                                    </div>
                                    <div class="ml-3">
                                        <p class="text-sm font-medium">{{ message }}</p>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}

            <!-- Login Form -->
            <div class="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
                <div class="px-8 py-10">
                    <form class="space-y-6" method="POST">
                        <div class="space-y-5">
                            <div>
                                <label for="email" class="block text-sm font-semibold text-slate-700 mb-2">
                                    Email Address
                                </label>
                                <div class="relative">
                                    <input id="email" name="email" type="email" required
                                           class="block w-full px-4 py-3 text-slate-900 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-soil-green-500 focus:border-soil-green-500 focus:bg-white transition-colors duration-200 placeholder-slate-400"
                                           placeholder="you@company.com">
                                    <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                        <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"></path>
                                        </svg>
                                    </div>
                                </div>
                            </div>

                            <div>
                                <label for="password" class="block text-sm font-semibold text-slate-700 mb-2">
                                    Password
                                </label>
                                <div class="relative">
                                    <input id="password" name="password" type="password" required
                                           class="block w-full px-4 py-3 text-slate-900 bg-slate-50 border border-slate-300 rounded-xl focus:ring-2 focus:ring-soil-green-500 focus:border-soil-green-500 focus:bg-white transition-colors duration-200 placeholder-slate-400"
                                           placeholder="Enter your password">
                                    <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                                        <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                                        </svg>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="pt-2">
                            <button type="submit"
                                    class="w-full bg-gradient-to-r from-soil-green-600 to-soil-green-700 text-white font-semibold py-3 px-4 rounded-xl hover:from-soil-green-700 hover:to-soil-green-800 focus:outline-none focus:ring-2 focus:ring-soil-green-500 focus:ring-offset-2 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5">
                                Sign In to Your Account
                            </button>
                        </div>

                        <div class="text-center pt-4">
                            <a href="{{ url_for('register') }}" 
                               class="text-soil-green-600 hover:text-soil-green-700 font-medium text-sm transition-colors duration-200">
                                Don't have an account? <span class="underline">Create one here</span>
                            </a>
                        </div>
                    </form>
                </div>
            </div>



            <!-- Footer -->
            <div class="text-center text-xs text-slate-500">
                <p>&copy; 2025 SoilsFert. Empowering sustainable agriculture.</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

# =====================================
# 📱 ENHANCED DASHBOARD TEMPLATE WITH DYNAMIC TESTIMONIALS
# =====================================

ENHANCED_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - SoilsFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <!-- Modern Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <!-- Logo Section -->
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>

                <!-- User Section -->
                <div class="flex items-center space-x-4">
                    <!-- User Info -->
                    <div class="hidden md:flex items-center space-x-3">
                        <div class="text-right">
                            <p class="text-sm font-medium text-gray-900">{{ session.user_name }}</p>
                            <p class="text-xs text-gray-500">{{ user.plan_type|title }} Plan</p>
                        </div>
                        <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                            <span class="text-white font-semibold text-sm">{{ session.user_name.split()[0][0] }}{{ session.user_name.split()[1][0] if session.user_name.split()|length > 1 else '' }}</span>
                        </div>
                    </div>

                    <!-- Plan Badge -->
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium
                               {% if user.plan_type == 'pro' %}bg-gradient-to-r from-purple-100 to-blue-100 text-purple-800
                               {% else %}bg-gradient-to-r from-green-100 to-emerald-100 text-green-800{% endif %}">
                        {% if user.plan_type == 'pro' %}
                            <i class="fas fa-crown mr-1"></i>PRO
                        {% else %}
                            <i class="fas fa-seedling mr-1"></i>FREE
                        {% endif %}
                    </span>

                    <!-- Logout Button -->
                    <a href="{{ url_for('logout') }}" 
                       class="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-red-600 transition-colors">
                        <i class="fas fa-sign-out-alt mr-2"></i>
                        Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Flash Messages -->
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
                {% for category, message in messages %}
                    <div class="mb-4 rounded-lg p-4 {% if category == 'error' %}bg-red-50 border border-red-200 text-red-800{% elif category == 'success' %}bg-green-50 border border-green-200 text-green-800{% elif category == 'warning' %}bg-amber-50 border border-amber-200 text-amber-800{% else %}bg-blue-50 border border-blue-200 text-blue-800{% endif %}">
                        <div class="flex items-center">
                            <i class="fas fa-{% if category == 'error' %}exclamation-circle{% elif category == 'success' %}check-circle{% elif category == 'warning' %}exclamation-triangle{% else %}info-circle{% endif %} mr-3"></i>
                            {{ message }}
                        </div>
                    </div>
                {% endfor %}
            </div>
        {% endif %}
    {% endwith %}

    <!-- Main Dashboard Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        <!-- Welcome Header -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 px-6 py-8 text-white">
                    <div class="flex flex-col md:flex-row md:items-center md:justify-between">
                        <div>
                            <h1 class="text-3xl font-bold mb-2">
                                Welcome back, {{ session.user_name.split()[0] }}! 🌱
                            </h1>
                            <p class="text-blue-100 text-lg">
                                Your soil analysis dashboard is ready for action
                            </p>
                        </div>
                        <div class="mt-4 md:mt-0">
                            <div class="flex items-center space-x-4">
                                <div class="text-center">
                                    <div class="text-2xl font-bold">{{ total_analyses }}</div>
                                    <div class="text-sm text-blue-200">Total Analyses</div>
                                </div>
                                <div class="w-px h-12 bg-blue-400"></div>
                                <div class="text-center">
                                    <div class="text-2xl font-bold">{{ total_recipes }}</div>
                                    <div class="text-sm text-blue-200">Compost Recipes</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Plan Status Card (for Free users) -->
        {% if user.plan_type == 'free' %}
        <div class="mb-8">
            <div class="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-xl p-6">
                <div class="flex flex-col md:flex-row md:items-center md:justify-between">
                    <div class="flex items-center mb-4 md:mb-0">
                        <div class="bg-amber-500 rounded-lg p-3 mr-4">
                            <i class="fas fa-info-circle text-white text-xl"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-amber-800">Free Plan Usage</h3>
                            <p class="text-amber-700">{{ user.analyses_used }}/3 analyses used this month</p>
                            <div class="w-64 bg-amber-200 rounded-full h-2 mt-2">
                                <div class="bg-amber-500 h-2 rounded-full transition-all duration-500" 
                                     style="width: {{ (user.analyses_used / 3 * 100)|round(0) }}%"></div>
                            </div>
                        </div>
                    </div>
                    <a href="{{ url_for('pricing') }}" 
                       class="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 shadow-lg">
                        <i class="fas fa-crown mr-2"></i>
                        Upgrade to Pro
                    </a>
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Stats Overview -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <!-- Total Analyses Card -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-shadow duration-300">
                <div class="flex items-center">
                    <div class="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-3 mr-4">
                        <i class="fas fa-microscope text-white text-xl"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-bold text-gray-900">{{ total_analyses }}</div>
                        <div class="text-sm text-gray-600">Soil Analyses</div>
                    </div>
                </div>
                <div class="mt-4">
                    <div class="text-sm text-green-600 font-medium">
                        <i class="fas fa-chart-line mr-1"></i>
                        {% if user.plan_type == 'free' %}{{ 3 - user.analyses_used }} remaining{% else %}Unlimited{% endif %}
                    </div>
                </div>
            </div>

            <!-- Compost Recipes Card -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-shadow duration-300">
                <div class="flex items-center">
                    <div class="bg-gradient-to-r from-green-500 to-green-600 rounded-lg p-3 mr-4">
                        <i class="fas fa-recycle text-white text-xl"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-bold text-gray-900">{{ total_recipes }}</div>
                        <div class="text-sm text-gray-600">Compost Recipes</div>
                    </div>
                </div>
                <div class="mt-4">
                    <div class="text-sm text-blue-600 font-medium">
                        <i class="fas fa-leaf mr-1"></i>
                        Organic solutions
                    </div>
                </div>
            </div>

            <!-- Plan Type Card -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-shadow duration-300">
                <div class="flex items-center">
                    <div class="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-3 mr-4">
                        <i class="fas fa-{% if user.plan_type == 'pro' %}crown{% else %}seedling{% endif %} text-white text-xl"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-bold text-gray-900">{{ user.plan_type|title }}</div>
                        <div class="text-sm text-gray-600">Current Plan</div>
                    </div>
                </div>
                <div class="mt-4">
                    <div class="text-sm {% if user.plan_type == 'pro' %}text-purple-600{% else %}text-orange-600{% endif %} font-medium">
                        <i class="fas fa-{% if user.plan_type == 'pro' %}star{% else %}arrow-up{% endif %} mr-1"></i>
                        {% if user.plan_type == 'pro' %}
                            {% if days_remaining is not none %}
                                {% if days_remaining > 0 %}
                                    {{ days_remaining }} days remaining
                                {% else %}
                                    Expires today
                                {% endif %}
                            {% else %}
                                Premium features
                            {% endif %}
                        {% else %}
                            Upgrade available
                        {% endif %}
                    </div>
                </div>
            </div>

            <!-- Member Since Card -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-lg transition-shadow duration-300">
                <div class="flex items-center">
                    <div class="bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-lg p-3 mr-4">
                        <i class="fas fa-calendar text-white text-xl"></i>
                    </div>
                    <div>
                        <div class="text-2xl font-bold text-gray-900">{{ user.created_at[:7] if user.created_at else 'N/A' }}</div>
                        <div class="text-sm text-gray-600">Member Since</div>
                    </div>
                </div>
                <div class="mt-4">
                    <div class="text-sm text-indigo-600 font-medium">
                        <i class="fas fa-user-check mr-1"></i>
                        Trusted member
                    </div>
                </div>
            </div>
        </div>

        <!-- Quick Actions Section -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-blue-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-bolt text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Quick Actions</h3>
                            <p class="text-sm text-gray-600">Get started with your analysis tools</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <!-- Soil Analysis Action -->
                        <a href="{{ url_for('soil_analysis') }}" 
                           class="group bg-gradient-to-br from-blue-50 to-blue-100 hover:from-blue-100 hover:to-blue-200 border border-blue-200 rounded-xl p-6 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                            <div class="flex items-center mb-4">
                                <div class="bg-blue-500 group-hover:bg-blue-600 rounded-lg p-3 mr-4 transition-colors">
                                    <i class="fas fa-microscope text-white text-xl"></i>
                                </div>
                                <div>
                                    <h4 class="text-lg font-semibold text-gray-900">Soil Analysis</h4>
                                    <p class="text-sm text-gray-600">Professional analysis with scientific formulas</p>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Scientific lime calculations
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Evidence-based fertilizer recommendations
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Complete cost analysis
                                </div>
                            </div>
                            <div class="mt-4 flex items-center text-blue-600 font-medium">
                                Start Analysis
                                <i class="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                            </div>
                        </a>

                        <!-- Compost Calculator Action -->
                        <a href="{{ url_for('compost_calculator') }}" 
                           class="group bg-gradient-to-br from-green-50 to-green-100 hover:from-green-100 hover:to-green-200 border border-green-200 rounded-xl p-6 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                            <div class="flex items-center mb-4">
                                <div class="bg-green-500 group-hover:bg-green-600 rounded-lg p-3 mr-4 transition-colors">
                                    <i class="fas fa-recycle text-white text-xl"></i>
                                </div>
                                <div>
                                    <h4 class="text-lg font-semibold text-gray-900">Compost Calculator</h4>
                                    <p class="text-sm text-gray-600">Optimize organic recipes</p>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    C:N ratio optimization
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Material recommendations
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Quality scoring
                                </div>
                            </div>
                            <div class="mt-4 flex items-center text-green-600 font-medium">
                                Create Recipe
                                <i class="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                            </div>
                        </a>

                        <!-- Upgrade Action -->
                        <a href="{{ url_for('pricing') }}" 
                           class="group bg-gradient-to-br from-purple-50 to-purple-100 hover:from-purple-100 hover:to-purple-200 border border-purple-200 rounded-xl p-6 transition-all duration-300 transform hover:scale-105 hover:shadow-lg">
                            <div class="flex items-center mb-4">
                                <div class="bg-purple-500 group-hover:bg-purple-600 rounded-lg p-3 mr-4 transition-colors">
                                    <i class="fas fa-crown text-white text-xl"></i>
                                </div>
                                <div>
                                    <h4 class="text-lg font-semibold text-gray-900">Upgrade Plan</h4>
                                    <p class="text-sm text-gray-600">Unlock premium features</p>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Unlimited analyses
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Advanced features
                                </div>
                                <div class="flex items-center text-sm text-gray-700">
                                    <i class="fas fa-check text-green-500 mr-2"></i>
                                    Priority support
                                </div>
                            </div>
                            <div class="mt-4 flex items-center text-purple-600 font-medium">
                                {% if user.plan_type == 'pro' %}Manage Plan{% else %}Upgrade Now{% endif %}
                                <i class="fas fa-arrow-right ml-2 group-hover:translate-x-1 transition-transform"></i>
                            </div>
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <!-- Dynamic Testimonials Section -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-purple-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-comments text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Community Testimonials</h3>
                                <p class="text-sm text-gray-600">What our farmers say about SoilsFert</p>
                            </div>
                        </div>
                        <button onclick="openTestimonialModal()" 
                                class="inline-flex items-center px-4 py-2 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition-colors">
                            <i class="fas fa-plus mr-2"></i>
                            Share Your Experience
                        </button>
                    </div>
                </div>
                <div class="p-6">
                    <!-- Testimonials Container -->
                    <div class="relative">
                        <div id="testimonials-container" class="flex space-x-6 overflow-x-auto pb-4 scroll-smooth">
                            <!-- Loading placeholder -->
                            <div id="testimonials-loading" class="flex space-x-6">
                                <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                                    <div class="flex items-center mb-4">
                                        <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                        <div>
                                            <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                            <div class="h-3 bg-gray-300 rounded w-32"></div>
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="h-3 bg-gray-300 rounded"></div>
                                        <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                                    </div>
                                </div>
                                <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                                    <div class="flex items-center mb-4">
                                        <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                        <div>
                                            <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                            <div class="h-3 bg-gray-300 rounded w-32"></div>
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="h-3 bg-gray-300 rounded"></div>
                                        <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                                    </div>
                                </div>
                                <div class="flex-shrink-0 w-80 bg-gray-100 rounded-lg p-6 animate-pulse">
                                    <div class="flex items-center mb-4">
                                        <div class="w-12 h-12 bg-gray-300 rounded-full mr-4"></div>
                                        <div>
                                            <div class="h-4 bg-gray-300 rounded w-24 mb-2"></div>
                                            <div class="h-3 bg-gray-300 rounded w-32"></div>
                                        </div>
                                    </div>
                                    <div class="space-y-2">
                                        <div class="h-3 bg-gray-300 rounded"></div>
                                        <div class="h-3 bg-gray-300 rounded w-3/4"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Scroll buttons -->
                        <button id="scroll-left" onclick="scrollTestimonials('left')" 
                                class="absolute left-0 top-1/2 transform -translate-y-1/2 bg-white shadow-lg rounded-full p-3 hover:bg-gray-50 transition-colors opacity-0 invisible">
                            <i class="fas fa-chevron-left text-gray-600"></i>
                        </button>
                        <button id="scroll-right" onclick="scrollTestimonials('right')" 
                                class="absolute right-0 top-1/2 transform -translate-y-1/2 bg-white shadow-lg rounded-full p-3 hover:bg-gray-50 transition-colors opacity-0 invisible">
                            <i class="fas fa-chevron-right text-gray-600"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Activity Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Recent Analyses -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-blue-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-microscope text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Recent Analyses</h3>
                                <p class="text-sm text-gray-600">Latest soil testing results</p>
                            </div>
                        </div>
                        <a href="{{ url_for('soil_analysis') }}" class="text-sm text-blue-600 hover:text-blue-800 font-medium">
                            View All
                        </a>
                    </div>
                </div>
                <div class="p-6">
                    {% if analyses %}
                        <div class="space-y-4">
                            {% for analysis in analyses %}
                            <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                                <div class="flex items-center justify-between mb-2">
                                    <h4 class="font-medium text-gray-900">
                                        {{ analysis.crop_type|title if analysis.crop_type else 'General Analysis' }}
                                    </h4>
                                    <span class="text-xs text-gray-500">
                                        {{ analysis.created_at[:10] if analysis.created_at else 'N/A' }}
                                    </span>
                                </div>
                                <div class="grid grid-cols-2 gap-4 text-sm">
                                    <div class="flex items-center">
                                        <i class="fas fa-vial text-blue-500 mr-2"></i>
                                        <span class="text-gray-600">pH: </span>
                                        <span class="font-medium ml-1">{{ analysis.soil_ph if analysis.soil_ph else 'N/A' }}</span>
                                    </div>
                                    <div class="flex items-center">
                                        <i class="fas fa-chart-line text-green-500 mr-2"></i>
                                        <span class="text-gray-600">Rating: </span>
                                        <span class="font-medium ml-1">{{ analysis.overall_rating if analysis.overall_rating else 'N/A' }}%</span>
                                    </div>
                                </div>
                                {% if analysis.farm_location %}
                                <div class="mt-2 text-xs text-gray-500">
                                    <i class="fas fa-map-marker-alt mr-1"></i>
                                    {{ analysis.farm_location }}
                                </div>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="text-center py-8">
                            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i class="fas fa-microscope text-gray-400 text-xl"></i>
                            </div>
                            <h4 class="text-lg font-medium text-gray-900 mb-2">No analyses yet</h4>
                            <p class="text-gray-600 mb-4">Start your first soil analysis to see results here</p>
                            <a href="{{ url_for('soil_analysis') }}" 
                               class="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors">
                                <i class="fas fa-plus mr-2"></i>
                                Start Analysis
                            </a>
                        </div>
                    {% endif %}
                </div>
            </div>

            <!-- Recent Recipes -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-green-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-recycle text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Recent Recipes</h3>
                                <p class="text-sm text-gray-600">Latest compost formulations</p>
                            </div>
                        </div>
                        <a href="{{ url_for('compost_calculator') }}" class="text-sm text-green-600 hover:text-green-800 font-medium">
                            View All
                        </a>
                    </div>
                </div>
                <div class="p-6">
                    {% if recipes %}
                        <div class="space-y-4">
                            {% for recipe in recipes %}
                            <div class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                                <div class="flex items-center justify-between mb-2">
                                    <h4 class="font-medium text-gray-900">{{ recipe.recipe_name }}</h4>
                                    <span class="text-xs text-gray-500">
                                        {{ recipe.created_at[:10] if recipe.created_at else 'N/A' }}
                                    </span>
                                </div>
                                <div class="grid grid-cols-2 gap-4 text-sm">
                                    <div class="flex items-center">
                                        <i class="fas fa-weight text-green-500 mr-2"></i>
                                        <span class="text-gray-600">Yield: </span>
                                        <span class="font-medium ml-1">{{ recipe.estimated_yield if recipe.estimated_yield else 'N/A' }} kg</span>
                                    </div>
                                    <div class="flex items-center">
                                        <i class="fas fa-star text-yellow-500 mr-2"></i>
                                        <span class="text-gray-600">Quality: </span>
                                        <span class="font-medium ml-1">{{ recipe.quality_score if recipe.quality_score else 'N/A' }}%</span>
                                    </div>
                                </div>
                                {% if recipe.c_n_ratio %}
                                <div class="mt-2 text-xs text-gray-500">
                                    <i class="fas fa-balance-scale mr-1"></i>
                                    C:N Ratio: {{ recipe.c_n_ratio }}:1
                                </div>
                                {% endif %}
                            </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="text-center py-8">
                            <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i class="fas fa-recycle text-gray-400 text-xl"></i>
                            </div>
                            <h4 class="text-lg font-medium text-gray-900 mb-2">No recipes yet</h4>
                            <p class="text-gray-600 mb-4">Create your first compost recipe to see it here</p>
                            <a href="{{ url_for('compost_calculator') }}" 
                               class="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors">
                                <i class="fas fa-plus mr-2"></i>
                                Create Recipe
                            </a>
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- Analytics Chart (if there's data) -->
        {% if analyses or recipes %}
        <div class="mt-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-purple-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-chart-line text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Activity Overview</h3>
                            <p class="text-sm text-gray-600">Your productivity trends</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>
                            <canvas id="activityChart" width="400" height="200"></canvas>
                        </div>
                        <div class="space-y-4">
                            <div class="bg-blue-50 rounded-lg p-4">
                                <div class="flex items-center justify-between">
                                    <span class="text-sm font-medium text-blue-800">Soil Analyses</span>
                                    <span class="text-2xl font-bold text-blue-600">{{ total_analyses }}</span>
                                </div>
                                <p class="text-xs text-blue-600 mt-1">Scientific insights delivered</p>
                            </div>
                            <div class="bg-green-50 rounded-lg p-4">
                                <div class="flex items-center justify-between">
                                    <span class="text-sm font-medium text-green-800">Compost Recipes</span>
                                    <span class="text-2xl font-bold text-green-600">{{ total_recipes }}</span>
                                </div>
                                <p class="text-xs text-green-600 mt-1">Organic solutions created</p>
                            </div>
                            <div class="bg-purple-50 rounded-lg p-4">
                                <div class="flex items-center justify-between">
                                    <span class="text-sm font-medium text-purple-800">Success Rate</span>
                                    <span class="text-2xl font-bold text-purple-600">98%</span>
                                </div>
                                <p class="text-xs text-purple-600 mt-1">Accurate recommendations</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
    </div>

    <!-- Testimonial Modal -->
    <div id="testimonial-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden items-center justify-center z-50">
        <div class="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 p-6">
            <div class="flex items-center justify-between mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Share Your Experience</h3>
                <button onclick="closeTestimonialModal()" class="text-gray-400 hover:text-gray-600">
                    <i class="fas fa-times text-xl"></i>
                </button>
            </div>
            
            <form id="testimonial-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Your Title (Optional)</label>
                    <input type="text" id="user-title" placeholder="e.g., Commercial Farmer, Organic Grower" 
                           class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Rating</label>
                    <div class="flex space-x-1" id="rating-stars">
                        <button type="button" onclick="setRating(1)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(2)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(3)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(4)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                        <button type="button" onclick="setRating(5)" class="text-2xl text-gray-300 hover:text-yellow-400 transition-colors">⭐</button>
                    </div>
                    <input type="hidden" id="rating-value" value="5">
                </div>
                
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Your Experience</label>
                    <textarea id="comment" rows="4" required 
                              placeholder="Tell us how SoilsFert has helped your farming..."
                              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500"></textarea>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                        <span>Minimum 10 characters</span>
                        <span id="char-count">0/500</span>
                    </div>
                </div>
                
                <div class="flex space-x-3 pt-4">
                    <button type="button" onclick="closeTestimonialModal()" 
                            class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors">
                        Cancel
                    </button>
                    <button type="submit" 
                            class="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors">
                        Submit
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Testimonials functionality
        let currentRating = 5;

        // Load testimonials on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadTestimonials();
            initializeActivityChart();
            
            // Character counter for testimonial
            const commentField = document.getElementById('comment');
            if (commentField) {
                commentField.addEventListener('input', function() {
                    const count = this.value.length;
                    document.getElementById('char-count').textContent = `${count}/500`;
                });
            }
        });

        // Load testimonials from API
        async function loadTestimonials() {
            try {
                const response = await fetch('/api/testimonials');
                const testimonials = await response.json();
                displayTestimonials(testimonials);
            } catch (error) {
                console.error('Error loading testimonials:', error);
                showEmptyTestimonials();
            }
        }

        // Display testimonials
        function displayTestimonials(testimonials) {
            const container = document.getElementById('testimonials-container');
            const loading = document.getElementById('testimonials-loading');
            
            if (loading) loading.remove();

            if (testimonials.length === 0) {
                showEmptyTestimonials();
                return;
            }

            container.innerHTML = testimonials.map(testimonial => `
                <div class="flex-shrink-0 w-80 bg-white border border-gray-200 rounded-lg p-6 hover:shadow-lg transition-shadow">
                    <div class="flex items-center mb-4">
                        <div class="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mr-4">
                            <span class="text-white font-semibold text-sm">${testimonial.initials}</span>
                        </div>
                        <div>
                            <h4 class="font-semibold text-gray-900">${testimonial.user_name}</h4>
                            <p class="text-sm text-gray-600">${testimonial.user_title}</p>
                        </div>
                    </div>
                    <p class="text-gray-600 leading-relaxed mb-4">${testimonial.content}</p>
                    <div class="flex items-center justify-between">
                        <div class="flex text-yellow-400">
                            ${'⭐'.repeat(testimonial.rating)}
                        </div>
                        <span class="text-xs text-gray-500">${formatDate(testimonial.created_at)}</span>
                    </div>
                </div>
            `).join('');

            // Show scroll buttons if needed
            updateScrollButtons();
        }

        // Show empty state
        function showEmptyTestimonials() {
            const container = document.getElementById('testimonials-container');
            const loading = document.getElementById('testimonials-loading');
            
            if (loading) loading.remove();

            container.innerHTML = `
                <div class="w-full text-center py-12">
                    <div class="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fas fa-comments text-purple-500 text-xl"></i>
                    </div>
                    <h4 class="text-lg font-medium text-gray-900 mb-2">No testimonials yet</h4>
                    <p class="text-gray-600 mb-4">Be the first to share your experience with SoilsFert!</p>
                    <button onclick="openTestimonialModal()" 
                            class="inline-flex items-center px-6 py-3 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>
                        Share Your Story
                    </button>
                </div>
            `;
        }

        // Modal functions
        function openTestimonialModal() {
            // Check if user is logged in
            const isLoggedIn = {{ 'true' if session.user_id else 'false' }};
            
            if (!isLoggedIn) {
                // Redirect to login/register if not logged in
                if (confirm('You need to be logged in to share your experience. Would you like to create a free account?')) {
                    window.location.href = '/register';
                }
                return;
            }
            
            document.getElementById('testimonial-modal').classList.remove('hidden');
            document.getElementById('testimonial-modal').classList.add('flex');
            setRating(5); // Default to 5 stars
        }

        function closeTestimonialModal() {
            document.getElementById('testimonial-modal').classList.add('hidden');
            document.getElementById('testimonial-modal').classList.remove('flex');
            document.getElementById('testimonial-form').reset();
            document.getElementById('char-count').textContent = '0/500';
            setRating(5);
        }

        // Rating functionality
        function setRating(rating) {
            currentRating = rating;
            document.getElementById('rating-value').value = rating;
            
            const stars = document.querySelectorAll('#rating-stars button');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.style.color = '#F59E0B';
                } else {
                    star.style.color = '#D1D5DB';
                }
            });
        }

        // Submit testimonial
        document.getElementById('testimonial-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const userTitle = document.getElementById('user-title').value.trim();
            const comment = document.getElementById('comment').value.trim();
            const rating = parseInt(document.getElementById('rating-value').value);
            
            if (comment.length < 10) {
                if (typeof ModalUtils !== 'undefined') {
                    ModalUtils.error({
                        title: 'Validation Error',
                        message: 'Comment must be at least 10 characters long.',
                        confirmText: 'OK'
                    });
                } else {
                    alert('Comment must be at least 10 characters long');
                }
                return;
            }
            
            if (comment.length > 500) {
                if (typeof ModalUtils !== 'undefined') {
                    ModalUtils.error({
                        title: 'Validation Error',
                        message: 'Comment must be less than 500 characters.',
                        details: `Current length: ${comment.length}/500 characters`,
                        confirmText: 'OK'
                    });
                } else {
                    alert('Comment must be less than 500 characters');
                }
                return;
            }
            
            try {
                const response = await fetch('/api/submit-testimonial', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_title: userTitle,
                        content: comment,
                        rating: rating
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    if (typeof ModalUtils !== 'undefined') {
                        ModalUtils.success({
                            title: 'Thank You! 🌟',
                            message: 'Your testimonial has been submitted successfully!',
                            details: 'Thank you for sharing your experience with our community.',
                            autoHide: true,
                            autoHideDelay: 3000
                        });
                    } else {
                        alert('Thank you for your testimonial!');
                    }
                    closeTestimonialModal();
                    loadTestimonials(); // Reload testimonials
                } else {
                    if (typeof ModalUtils !== 'undefined') {
                        ModalUtils.error({
                            title: 'Submission Failed',
                            message: result.error || 'An error occurred while submitting your testimonial.',
                            details: 'Please check your connection and try again.',
                            confirmText: 'Try Again'
                        });
                    } else {
                        alert(result.error || 'An error occurred');
                    }
                }
            } catch (error) {
                console.error('Error submitting testimonial:', error);
                if (typeof ModalUtils !== 'undefined') {
                    ModalUtils.error({
                        title: 'Network Error',
                        message: 'Unable to submit your testimonial at this time.',
                        details: 'Please check your internet connection and try again.',
                        confirmText: 'Retry'
                    });
                } else {
                    alert('An error occurred while submitting your testimonial');
                }
            }
        });

        // Scroll functionality
        function scrollTestimonials(direction) {
            const container = document.getElementById('testimonials-container');
            const scrollAmount = 320; // Width of testimonial card + gap
            
            if (direction === 'left') {
                container.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            } else {
                container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            }
            
            setTimeout(updateScrollButtons, 300);
        }

        // Update scroll button visibility
        function updateScrollButtons() {
            const container = document.getElementById('testimonials-container');
            const leftButton = document.getElementById('scroll-left');
            const rightButton = document.getElementById('scroll-right');
            
            if (!container || !leftButton || !rightButton) return;
            
            const isScrollable = container.scrollWidth > container.clientWidth;
            
            if (isScrollable) {
                leftButton.classList.remove('opacity-0', 'invisible');
                rightButton.classList.remove('opacity-0', 'invisible');
                leftButton.classList.add('opacity-100', 'visible');
                rightButton.classList.add('opacity-100', 'visible');
            } else {
                leftButton.classList.add('opacity-0', 'invisible');
                rightButton.classList.add('opacity-0', 'invisible');
                leftButton.classList.remove('opacity-100', 'visible');
                rightButton.classList.remove('opacity-100', 'visible');
            }
        }

        // Utility functions
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric',
                year: 'numeric'
            });
        }

        // Initialize activity chart if data exists
        function initializeActivityChart() {
            {% if analyses or recipes %}
            const ctx = document.getElementById('activityChart');
            if (ctx) {
                new Chart(ctx.getContext('2d'), {
                    type: 'doughnut',
                    data: {
                        labels: ['Soil Analyses', 'Compost Recipes'],
                        datasets: [{
                            data: [{{ total_analyses }}, {{ total_recipes }}],
                            backgroundColor: [
                                'rgba(59, 130, 246, 0.8)',
                                'rgba(34, 197, 94, 0.8)'
                            ],
                            borderColor: [
                                'rgba(59, 130, 246, 1)',
                                'rgba(34, 197, 94, 1)'
                            ],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 20,
                                    font: {
                                        family: 'Inter, sans-serif'
                                    }
                                }
                            }
                        }
                    }
                });
            }
            {% endif %}
        }

        // Handle testimonials container scroll
        document.addEventListener('DOMContentLoaded', function() {
            const container = document.getElementById('testimonials-container');
            if (container) {
                container.addEventListener('scroll', updateScrollButtons);
                window.addEventListener('resize', updateScrollButtons);
            }
        });
    </script>

    <style>
        /* Custom scrollbar for testimonials */
        #testimonials-container::-webkit-scrollbar {
            height: 8px;
        }
        #testimonials-container::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 4px;
        }
        #testimonials-container::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        #testimonials-container::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Smooth transitions */
        * {
            transition: all 0.3s ease;
        }
        
        /* Gradient animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }

        /* Card hover effects */
        .hover\\:scale-105:hover {
            transform: scale(1.05);
        }

        /* Progress bar animation */
        @keyframes progress {
            from { width: 0; }
            to { width: var(--progress-width); }
        }

        /* Modal backdrop */
        .modal-backdrop {
            backdrop-filter: blur(4px);
        }
    </style>
</body>
</html>
'''               

ENHANCED_SOIL_ANALYSIS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Soil Analysis - SoilsFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <!-- Modern Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" 
                       class="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors">
                        <i class="fas fa-arrow-left mr-2"></i>
                        Dashboard
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="relative overflow-hidden">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="mb-6">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-4">
                        <i class="fas fa-microscope text-white text-2xl"></i>
                    </div>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent mb-4">
                    Professional Soil Analysis
                </h1>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto mb-6">
                    Advanced soil fertility analysis with evidence-based fertilizer recommendations and scientific lime calculations
                </p>
                <div class="flex flex-wrap justify-center gap-4 text-sm">
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800">
                        <i class="fas fa-check-circle mr-2"></i>
                        Scientific Method: t/ha = 5 × ΔAE × ρb × d
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800">
                        <i class="fas fa-calculator mr-2"></i>
                        Multi-Nutrient Mathematical Optimization
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-purple-100 text-purple-800">
                        <i class="fas fa-chart-line mr-2"></i>
                        Complete Cost Analysis
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Form Container -->
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-8">
                    {% for category, message in messages %}
                        <div class="rounded-lg p-4 {% if category == 'warning' %}bg-amber-50 border border-amber-200 text-amber-800{% else %}bg-blue-50 border border-blue-200 text-blue-800{% endif %}">
                            <div class="flex items-center">
                                <i class="fas fa-exclamation-triangle mr-3"></i>
                                {{ message }}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <!-- Progress Indicator -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-gray-900">Analysis Progress</h3>
                    <span class="text-sm text-gray-500">Complete all required sections</span>
                </div>
                <div class="flex space-x-4">
                    <div class="flex-1">
                        <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div id="progress-bar" class="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500" style="width: 0%"></div>
                        </div>
                    </div>
                    <span id="progress-text" class="text-sm font-medium text-gray-700">0%</span>
                </div>
            </div>
        </div>

        <!-- Main Form -->
        <form method="POST" id="soil-analysis-form" class="space-y-8">
            
            <!-- Section 1: Basic Information -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-blue-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-info-circle text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Basic Information</h3>
                            <p class="text-sm text-gray-600">Essential details for accurate analysis</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Extraction Method *
                                <i class="fas fa-info-circle text-blue-500 ml-1 cursor-help" 
                                   title="Affects nutrient target ranges and calculations"></i>
                            </label>
                            <select name="extraction_method" required
                                    class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <option value="olsen_modified">Olsen Modified / KCL 1N</option>
                                <option value="mehlich_iii">Mehlich III</option>
                            </select>
                            <p class="text-xs text-gray-500">Determines nutrient interpretation standards</p>
                        </div>


                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Field Area (hectares)
                                <i class="fas fa-ruler-combined text-purple-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0.01" name="surface_area" value="2.5"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                            <p class="text-xs text-gray-500">Total area to be treated</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 2: Soil Properties -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-green-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-globe text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Basic Soil Properties</h3>
                            <p class="text-sm text-gray-600">Fundamental soil characteristics</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Soil pH *
                                <i class="fas fa-vial text-red-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" max="14" name="ph" required value="6.2"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="6.5">
                            <div class="text-xs text-gray-500">
                                <span class="inline-flex items-center space-x-2">
                                    <span>Range: 0-14</span>
                                    <span class="text-red-600">• Acidic: &lt;7</span>
                                    <span class="text-blue-600">• Neutral: 7</span>
                                    <span class="text-green-600">• Alkaline: &gt;7</span>
                                </span>
                            </div>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Organic Matter (%)
                                <i class="fas fa-leaf text-green-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" max="100" name="organic_matter" required value="3.2"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="2.5">
                            <p class="text-xs text-gray-500">Affects nutrient availability and soil health</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 3: Physical Parameters -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-violet-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-purple-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-weight text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Physical Soil Parameters</h3>
                                <p class="text-sm text-gray-600">Critical for scientific lime calculations</p>
                            </div>
                        </div>
                        <div class="text-right">
                            <span class="text-xs text-purple-700 font-medium">Formula: t/ha = 5 × ΔAE × ρb × d</span>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Soil Depth (cm) *
                                <i class="fas fa-ruler-vertical text-orange-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="5" max="50" name="soil_depth_cm" value="25"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   onchange="calculatePhysicalProperties()">
                            <p class="text-xs text-gray-500">Incorporation depth (d)</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Bulk Density (g/cm³) *
                                <i class="fas fa-balance-scale text-red-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0.8" max="2.0" name="bulk_density" value="1.30" required
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   onchange="calculatePhysicalProperties()">
                            <p class="text-xs text-gray-500">ρb in formula</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Particle Density (g/cm³)
                                <i class="fas fa-atom text-gray-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="2.0" max="3.0" name="particle_density" value="2.65"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   onchange="calculatePhysicalProperties()">
                            <p class="text-xs text-gray-500">Mineral density</p>
                        </div>
                    </div>

                    <!-- Real-time Calculations Display -->
                    <div class="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
                        <h4 class="text-sm font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-calculator mr-2 text-blue-600"></i>
                            Live Calculations
                        </h4>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="text-center">
                                <div class="text-2xl font-bold text-blue-600" id="calculated-porosity">---%</div>
                                <div class="text-xs text-gray-600">Porosity</div>
                                <div class="text-xs text-gray-500">(1 - ρb/ρs) × 100</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-purple-600" id="calculated-volume">--- m³/ha</div>
                                <div class="text-xs text-gray-600">Soil Volume</div>
                                <div class="text-xs text-gray-500">Area × Depth</div>
                            </div>
                            <div class="text-center">
                                <div class="text-2xl font-bold text-green-600" id="calculated-mass">--- Mg/ha</div>
                                <div class="text-xs text-gray-600">Soil Mass</div>
                                <div class="text-xs text-gray-500">Volume × Density</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 4: Primary Nutrients -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-cyan-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-blue-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-flask text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Primary Nutrients (NPK)</h3>
                            <p class="text-sm text-gray-600">Essential macronutrients for plant growth</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Phosphorus (ppm) *
                                <i class="fas fa-fire text-orange-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" name="phosphorus_olsen" required value="2.5"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="1.0">
                            <p class="text-xs text-gray-500">Available P in soil (critical for root development)</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Potassium (cmol+/kg) *
                                <i class="fas fa-bolt text-yellow-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" name="potassium_exchangeable" required value="95.3"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="120">
                            <p class="text-xs text-gray-500">Exchangeable K (essential for plant metabolism)</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Exchangeable Acidity (cmol+/kg) *
                                <i class="fas fa-exclamation-triangle text-red-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" name="exchangeable_acidity" required value="2.1"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="1.5">
                            <p class="text-xs text-gray-500">For scientific lime calculation (ΔAE in formula)</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 5: Lime Calculation -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-yellow-50 to-orange-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-yellow-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-mountain text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Scientific Lime Calculation</h3>
                                <p class="text-sm text-gray-600">Precision lime recommendations based on soil physics</p>
                            </div>
                        </div>
                        <div class="bg-green-100 px-3 py-1 rounded-full">
                            <span class="text-xs font-medium text-green-800">🧮 Scientific Method</span>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Lime Type *
                                <i class="fas fa-mountain text-brown-500 ml-1"></i>
                            </label>
                            <select name="lime_type" required onchange="updateLimeInfo()"
                                    class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <option value="caco3">Calcium Carbonate (CaCO₃)</option>
                                <option value="dolomitic">Dolomitic Lime (CaCO₃+MgCO₃)</option>
                                <option value="hydrated">Calcium Hydroxide (Ca(OH)₂)</option>
                                <option value="oxide">Calcium Oxide (CaO)</option>
                                <option value="magnesium_oxide">Magnesium Oxide (MgO)</option>
                            </select>
                            <div id="lime-info" class="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                                Standard agricultural lime, CCE Factor: 1.0
                            </div>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Soil Type *
                                <i class="fas fa-layer-group text-amber-600 ml-1"></i>
                            </label>
                            <select name="soil_type" required onchange="updateSoilTypeInfo()"
                                    class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <option value="loamy">Loamy Soil (Balanced)</option>
                                <option value="sandy">Sandy Soil (Light)</option>
                                <option value="clay">Clay Soil (Heavy)</option>
                                <option value="organic">Organic/Peat Soil</option>
                                <option value="calcareous">Calcareous Soil</option>
                            </select>
                            <div id="soil-type-info" class="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                                Balanced texture, moderate CEC, standard lime response (Factor: 1.0x)
                            </div>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Target Exchangeable Acidity
                                <i class="fas fa-target text-green-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.1" min="0" max="2" name="target_ae" value="0.5"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                            <p class="text-xs text-gray-500">Recommended: 0.5 cmol+/kg for most crops</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Commercial Product ECCE (%)
                                <i class="fas fa-certificate text-blue-500 ml-1"></i>
                            </label>
                            <input type="number" step="1" min="50" max="120" name="product_ecce" value="100"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                            <p class="text-xs text-gray-500">Effective Calcium Carbonate Equivalent</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Collapsible Advanced Sections -->
            <div class="space-y-6">
                <!-- Secondary Nutrients -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <button type="button" onclick="toggleSection('secondary')" 
                            class="w-full bg-gradient-to-r from-orange-50 to-red-50 px-6 py-4 border-b border-gray-200 text-left focus:outline-none">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center">
                                <div class="bg-orange-500 rounded-lg p-2 mr-3">
                                    <i class="fas fa-atom text-white"></i>
                                </div>
                                <div>
                                    <h3 class="text-lg font-semibold text-gray-900">Secondary Nutrients (Ca, Mg, S)</h3>
                                    <p class="text-sm text-gray-600">Essential for CEC and cationic balance</p>
                                </div>
                            </div>
                            <i id="secondary-icon" class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                        </div>
                    </button>
                    <div id="secondary-content" class="hidden p-6">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Calcium (cmol+/kg) *
                                    <i class="fas fa-bone text-gray-500 ml-1"></i>
                                </label>
                                <input type="number" step="0.1" min="0" name="calcium" required value="650.8"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="800">
                                <p class="text-xs text-gray-500">Essential for CEC calculation</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Magnesium (cmol+/kg) *
                                    <i class="fas fa-leaf text-green-500 ml-1"></i>
                                </label>
                                <input type="number" step="0.1" min="0" name="magnesium" required value="125.4"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="150">
                                <p class="text-xs text-gray-500">Core of chlorophyll molecule</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Sulfur (ppm)
                                    <i class="fas fa-burn text-yellow-500 ml-1"></i>
                                </label>
                                <input type="number" step="0.1" min="0" name="sulfur_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Essential for protein synthesis</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Micronutrients -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <button type="button" onclick="toggleSection('micro')" 
                            class="w-full bg-gradient-to-r from-red-50 to-pink-50 px-6 py-4 border-b border-gray-200 text-left focus:outline-none">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center">
                                <div class="bg-red-500 rounded-lg p-2 mr-3">
                                    <i class="fas fa-microscope text-white"></i>
                                </div>
                                <div>
                                    <h3 class="text-lg font-semibold text-gray-900">Micronutrients (Fe, Cu, Mn, Zn, B, Mo)</h3>
                                    <p class="text-sm text-gray-600">Trace elements critical for plant health</p>
                                </div>
                            </div>
                            <i id="micro-icon" class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                        </div>
                    </button>
                    <div id="micro-content" class="hidden p-6">
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Iron (Fe) ppm</label>
                                <input type="number" step="0.1" min="0" name="iron_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Chlorophyll synthesis</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Copper (Cu) ppm</label>
                                <input type="number" step="0.1" min="0" name="copper_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Enzyme activation</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Manganese (Mn) ppm</label>
                                <input type="number" step="0.1" min="0" name="manganese_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Photosynthesis</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Zinc (Zn) ppm</label>
                                <input type="number" step="0.1" min="0" name="zinc_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Growth regulation</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Boron (B) ppm</label>
                                <input type="number" step="0.01" min="0" name="boron_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Cell wall formation</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Molybdenum (Mo) ppm</label>
                                <input type="number" step="0.01" min="0" name="molybdenum_ppm"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Nitrogen fixation</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Advanced Targets -->
                <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                    <button type="button" onclick="toggleSection('advanced')" 
                            class="w-full bg-gradient-to-r from-purple-50 to-indigo-50 px-6 py-4 border-b border-gray-200 text-left focus:outline-none">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center">
                                <div class="bg-purple-500 rounded-lg p-2 mr-3">
                                    <i class="fas fa-bullseye text-white"></i>
                                </div>
                                <div>
                                    <h3 class="text-lg font-semibold text-gray-900">Advanced Fertilization Targets</h3>
                                    <p class="text-sm text-gray-600">Scientific optimization parameters</p>
                                </div>
                            </div>
                            <i id="advanced-icon" class="fas fa-chevron-down text-gray-400 transition-transform"></i>
                        </div>
                    </button>
                    <div id="advanced-content" class="hidden p-6">
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Target Nitrogen (kg/ha)</label>
                                <input type="number" step="5" min="0" max="300" name="target_n_kg_ha" value="120"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Crop nitrogen requirement</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Expected Yield (tons/ha)</label>
                                <input type="number" step="0.5" min="0.5" max="50" name="expected_yield" value="5.0"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Target crop yield</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">Current Soil N (%)</label>
                                <input type="number" step="0.01" min="0" max="5" name="current_n_percent" value="0.1"
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Soil organic nitrogen</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Submit Button -->
            <div class="text-center pt-8">
                <button type="submit" id="submit-button" disabled
                        class="inline-flex items-center px-12 py-4 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-700 text-white font-semibold text-lg rounded-xl shadow-lg hover:from-blue-700 hover:via-purple-700 hover:to-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-300 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all duration-300 transform hover:scale-105 disabled:hover:scale-100">
                    <i class="fas fa-rocket mr-3"></i>
                    Analyze Soil with Scientific Precision
                    <i class="fas fa-arrow-right ml-3"></i>
                </button>
                <p class="mt-4 text-sm text-gray-600 max-w-2xl mx-auto">
                    🧬 Evidence-based multi-nutrient optimization • 🧮 Scientific lime calculations • 💰 Complete cost analysis
                </p>
            </div>
        </form>
    </div>

<script>
    // Enhanced form functionality
    let currentProgress = 0;
    const totalFields = document.querySelectorAll('input[required], select[required]').length;

    // Physical properties calculation - FIXED VERSION
    function calculatePhysicalProperties() {
        // Get input values with proper field names and fallbacks
        const bulkDensity = parseFloat(document.querySelector('input[name="bulk_density"]')?.value) || 1.3;
        const particleDensity = parseFloat(document.querySelector('input[name="particle_density"]')?.value) || 2.65;
        const landArea = parseFloat(document.querySelector('input[name="surface_area"]')?.value) || 1.0;
        const depthCm = parseFloat(document.querySelector('input[name="soil_depth_cm"]')?.value) || 20;
        
        console.log('Physical Parameters:', { bulkDensity, particleDensity, landArea, depthCm });
        
        // Calculate porosity: φ = (1 - ρb/ρs) × 100
        const porosity = (1 - (bulkDensity / particleDensity)) * 100;
        
        // Calculate volume per hectare - CORRECTED
        const depthM = depthCm / 100; // Convert cm to meters
        const volumePerHa = 10000 * depthM; // m³/ha (1 hectare = 10,000 m²)
        
        // Calculate mass per hectare
        const bulkDensityKgM3 = bulkDensity * 1000; // Convert g/cm³ to kg/m³
        const massKgPerHa = volumePerHa * bulkDensityKgM3; // kg/ha
        const massMgPerHa = massKgPerHa / 1000; // Convert to Mg/ha (tonnes/ha)
        
        console.log('Calculated Results:', { porosity, volumePerHa, massMgPerHa });
        
        // Update display elements
        const porosityEl = document.getElementById('calculated-porosity');
        const volumeEl = document.getElementById('calculated-volume');
        const massEl = document.getElementById('calculated-mass');
        
        if (porosityEl) {
            porosityEl.textContent = porosity.toFixed(1) + '%';
            console.log('Updated porosity:', porosity.toFixed(1) + '%');
        }
        
        if (volumeEl) {
            volumeEl.textContent = volumePerHa.toFixed(0) + ' m³/ha';
            console.log('Updated volume:', volumePerHa.toFixed(0) + ' m³/ha');
        }
        
        if (massEl) {
            massEl.textContent = massMgPerHa.toFixed(1) + ' Mg/ha';
            console.log('Updated mass:', massMgPerHa.toFixed(1) + ' Mg/ha');
        }
        
        // Add animation effect
        [porosityEl, volumeEl, massEl].forEach(el => {
            if (el) {
                el.style.transform = 'scale(1.1)';
                el.style.transition = 'transform 0.2s ease';
                el.style.color = '#059669'; // Green color for updated values
                setTimeout(() => {
                    el.style.transform = 'scale(1)';
                    el.style.color = ''; // Reset color
                }, 300);
            }
        });
    }

    // Lime type information
    const limeTypes = {
        'caco3': 'Standard agricultural lime • CCE: 1.0 • Speed: Slow • Cost: Low',
        'dolomitic': 'Contains Ca + Mg • CCE: 1.09 • Speed: Slow • Cost: Low',
        'hydrated': 'Quick lime • CCE: 1.35 • Speed: Fast • Cost: Medium',
        'oxide': 'Burnt lime • CCE: 1.78 • Speed: Very Fast • Cost: High',
        'magnesium_oxide': 'High Mg content • CCE: 2.47 • Speed: Very Fast • Cost: High'
    };

    // Soil type information
    const soilTypes = {
        'sandy': 'Low buffering capacity • Factor: 0.7x • Quick pH response • Split applications recommended',
        'loamy': 'Balanced texture • Factor: 1.0x • Standard lime response • Good drainage',
        'clay': 'High buffering capacity • Factor: 1.4x • Slow pH response • Allow 6-12 months',
        'organic': 'Very high buffering • Factor: 1.6x • Complex dynamics • Monitor pH closely',
        'calcareous': 'Contains natural lime • Factor: 0.3x • High pH buffering • Consider sulfur if pH high'
    };

    function updateLimeInfo() {
        const limeType = document.querySelector('select[name="lime_type"]')?.value || 'caco3';
        const infoEl = document.getElementById('lime-info');
        if (infoEl && limeTypes[limeType]) {
            infoEl.textContent = limeTypes[limeType];
        }
    }

    function updateSoilTypeInfo() {
        const soilType = document.querySelector('select[name="soil_type"]')?.value || 'loamy';
        const infoEl = document.getElementById('soil-type-info');
        if (infoEl && soilTypes[soilType]) {
            infoEl.textContent = soilTypes[soilType];
        }
    }

    // Section toggle functionality
    function toggleSection(sectionName) {
        const content = document.getElementById(`${sectionName}-content`);
        const icon = document.getElementById(`${sectionName}-icon`);
        
        if (content && icon) {
            if (content.classList.contains('hidden')) {
                content.classList.remove('hidden');
                icon.classList.add('rotate-180');
                // Trigger calculation when section is opened
                if (sectionName === 'advanced') {
                    calculatePhysicalProperties();
                }
            } else {
                content.classList.add('hidden');
                icon.classList.remove('rotate-180');
            }
        }
    }

    // Progress tracking
    function updateProgress() {
        const requiredFields = document.querySelectorAll('input[required], select[required]');
        let filledFields = 0;
        
        requiredFields.forEach(field => {
            if (field.value.trim() !== '') {
                filledFields++;
                field.classList.add('border-green-300', 'bg-green-50');
                field.classList.remove('border-red-300', 'bg-red-50');
            } else {
                field.classList.remove('border-green-300', 'bg-green-50');
            }
        });
        
        const progress = requiredFields.length > 0 ? (filledFields / requiredFields.length) * 100 : 0;
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        
        if (progressBar) progressBar.style.width = progress + '%';
        if (progressText) progressText.textContent = Math.round(progress) + '%';
        
        // Enable submit button when all required fields are filled
        const submitButton = document.getElementById('submit-button');
        if (submitButton) {
            if (progress === 100) {
                submitButton.disabled = false;
                submitButton.classList.remove('from-gray-400', 'to-gray-500');
                submitButton.classList.add('from-blue-600', 'via-purple-600', 'to-blue-700');
            } else {
                submitButton.disabled = true;
                submitButton.classList.add('from-gray-400', 'to-gray-500');
                submitButton.classList.remove('from-blue-600', 'via-purple-600', 'to-blue-700');
            }
        }
    }

    // Form validation
    function validateForm() {
        const requiredFields = document.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('border-red-300', 'bg-red-50');
                isValid = false;
            } else {
                field.classList.remove('border-red-300', 'bg-red-50');
                field.classList.add('border-green-300', 'bg-green-50');
            }
        });
        
        return isValid;
    }

    // Initialize everything when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded, initializing soil analysis form...');
        
        // Set up event listeners for physical parameter inputs
        const physicalParameterInputs = [
            'input[name="surface_area"]',
            'input[name="soil_depth_cm"]', 
            'input[name="bulk_density"]',
            'input[name="particle_density"]'
        ];
        
        physicalParameterInputs.forEach(selector => {
            const input = document.querySelector(selector);
            if (input) {
                console.log('Setting up listener for:', selector);
                input.addEventListener('input', function() {
                    console.log('Input changed:', selector, 'value:', this.value);
                    calculatePhysicalProperties();
                });
                input.addEventListener('change', calculatePhysicalProperties);
                input.addEventListener('keyup', calculatePhysicalProperties);
            } else {
                console.warn('Input not found:', selector);
            }
        });
        
        // Set up event listeners for all form inputs
        document.querySelectorAll('input, select').forEach(field => {
            field.addEventListener('input', updateProgress);
            field.addEventListener('change', function() {
                updateProgress();
                // Trigger physical calculations if it's a physical parameter
                if (this.name && physicalParameterInputs.some(selector => selector.includes(this.name))) {
                    calculatePhysicalProperties();
                }
            });
            
            // Add focus effects
            field.addEventListener('focus', function() {
                this.parentElement.classList.add('scale-105');
            });
            
            field.addEventListener('blur', function() {
                this.parentElement.classList.remove('scale-105');
            });
        });
        
        // Set up lime type selector
        const limeTypeSelect = document.querySelector('select[name="lime_type"]');
        if (limeTypeSelect) {
            limeTypeSelect.addEventListener('change', updateLimeInfo);
        }
        
        // Initialize calculations and display
        updateLimeInfo();
        calculatePhysicalProperties();
        updateProgress();
        
        console.log('Initialization complete');
        
        // Form submission handler
        const form = document.getElementById('soil-analysis-form');
        if (form) {
            form.addEventListener('submit', function(e) {
                console.log('Form submission attempted');
                
                if (!validateForm()) {
                    e.preventDefault();
                    alert('Please complete all required fields marked with *');
                    
                    // Scroll to first invalid field
                    const firstInvalid = document.querySelector('.border-red-300');
                    if (firstInvalid) {
                        firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        firstInvalid.focus();
                    }
                } else {
                    // Show loading state
                    const submitButton = document.getElementById('submit-button');
                    if (submitButton) {
                        submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-3"></i>Analyzing Soil...';
                        submitButton.disabled = true;
                    }
                }
            });
        }
        
        // Debug: Log current input values
        setTimeout(() => {
            const bulkDensity = document.querySelector('input[name="bulk_density"]')?.value;
            const depthCm = document.querySelector('input[name="soil_depth_cm"]')?.value;
            const landArea = document.querySelector('input[name="surface_area"]')?.value;
            console.log('Current input values after init:', { bulkDensity, depthCm, landArea });
        }, 500);
    });

    // Global functions for onclick handlers
    window.calculatePhysicalProperties = calculatePhysicalProperties;
    window.updateLimeInfo = updateLimeInfo;
    window.updateSoilTypeInfo = updateSoilTypeInfo;
    window.toggleSection = toggleSection;
</script>

    <style>
        .form-input {
            transition: all 0.3s ease;
        }
        .form-input:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }
        
        .transition-transform {
            transition: transform 0.3s ease;
        }
        
        .rotate-180 {
            transform: rotate(180deg);
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Smooth animations */
        * {
            scroll-behavior: smooth;
        }
        
        /* Gradient text animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }
    </style>
</body>
</html>
'''

ENHANCED_SOIL_ANALYSIS_RESULT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analysis Results - SoilFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <!-- Modern Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" 
                       class="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors">
                        <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
                    </a>
                    <a href="{{ url_for('soil_analysis') }}" 
                       class="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>New Analysis
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 text-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4">
                    <i class="fas fa-chart-line text-white text-2xl"></i>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold mb-4">
                    Scientific Analysis Results
                </h1>
                <p class="text-xl text-blue-100 mb-6">
                    {{ result.extraction_method|title|replace('_', ' ') }} Method • {{ result.crop_type|title }} Crop
                </p>
                <div class="flex flex-wrap justify-center gap-4">
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-calculator mr-2"></i>
                        {{ result.calculation_method }}
                    </span>
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-robot mr-2"></i>
                        AI-Optimized Recommendations
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 -mt-8">
        
        <!-- Overall Scores Section -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-gray-50 to-blue-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-trophy mr-3 text-yellow-500"></i>
                        Overall Performance Scores
                    </h3>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <!-- Overall Rating -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4">
                                <canvas id="overallRatingChart" width="96" height="96"></canvas>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-xl font-bold {% if result.overall_rating >= 80 %}text-green-600{% elif result.overall_rating >= 60 %}text-yellow-600{% else %}text-red-600{% endif %}">
                                        {{ result.overall_rating }}
                                    </span>
                                </div>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Overall Rating</h4>
                            <p class="text-sm text-gray-600">
                                {% if result.overall_rating >= 80 %}🌟 Excellent
                                {% elif result.overall_rating >= 60 %}👍 Good
                                {% else %}⚠️ Needs Work{% endif %}
                            </p>
                        </div>

                        <!-- Fertility Index -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4">
                                <canvas id="fertilityChart" width="96" height="96"></canvas>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-xl font-bold text-blue-600">{{ result.fertility_index }}</span>
                                </div>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Fertility Index</h4>
                            <p class="text-sm text-gray-600">0.0 - 1.0 Scale</p>
                        </div>

                        <!-- Soil Health -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4">
                                <canvas id="healthChart" width="96" height="96"></canvas>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-xl font-bold text-purple-600">{{ result.soil_health_score }}</span>
                                </div>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Soil Health</h4>
                            <p class="text-sm text-gray-600">Combined Score</p>
                        </div>

                        <!-- Yield Potential -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4">
                                <canvas id="yieldChart" width="96" height="96"></canvas>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-xl font-bold text-orange-600">{{ result.estimated_yield_potential }}%</span>
                                </div>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Yield Potential</h4>
                            <p class="text-sm text-gray-600">Expected Performance</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Smart Multi-Nutrient Analysis -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-blue-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-purple-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-robot text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-gray-900">Smart Multi-Nutrient Analysis</h3>
                                <p class="text-sm text-gray-600">AI-optimized fertilizer recommendations</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                            {{ result.summary.overall_efficiency }}% Efficiency
                        </span>
                    </div>
                </div>
                <div class="p-6">
                    <!-- Efficiency Overview -->
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                        <div class="text-center p-4 bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg border border-green-200">
                            <div class="text-3xl font-bold text-green-700 mb-2">{{ result.summary.overall_efficiency }}%</div>
                            <div class="text-sm text-gray-600 font-medium">Compensation Efficiency</div>
                            <div class="text-xs text-gray-500">AI-Optimized</div>
                        </div>
                        <div class="text-center p-4 bg-blue-50 rounded-lg">
                            <div class="text-2xl font-bold text-blue-600 mb-2">{{ result.summary.total_nutrients_needed }}</div>
                            <div class="text-sm text-gray-600 font-medium">Nutrients Needed</div>
                            <div class="text-xs text-gray-500">From soil analysis</div>
                        </div>
                        <div class="text-center p-4 bg-purple-50 rounded-lg">
                            <div class="text-2xl font-bold text-purple-600 mb-2">{{ result.summary.total_products_recommended }}</div>
                            <div class="text-sm text-gray-600 font-medium">Products Selected</div>
                            <div class="text-xs text-gray-500">Optimized count</div>
                        </div>
                        <div class="text-center p-4 bg-yellow-50 rounded-lg">
                            <div class="text-2xl font-bold text-yellow-600 mb-2">${{ result.summary.total_cost_per_ha }}</div>
                            <div class="text-sm text-gray-600 font-medium">Total Cost/ha</div>
                            <div class="text-xs text-gray-500">Complete solution</div>
                        </div>
                    </div>

                    <!-- Nutrient Requirements Chart -->
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900 mb-4">Nutrient Requirements (kg/ha)</h4>
                            <div class="relative h-64">
                                <canvas id="nutrientRequirementsChart"></canvas>
                            </div>
                        </div>
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900 mb-4">Coverage Efficiency (%)</h4>
                            <div class="relative h-64">
                                <canvas id="coverageChart"></canvas>
                            </div>
                        </div>
                    </div>

                    <!-- Product Recommendations Table -->
                    {% if result.smart_fertilizer_recommendations.smart_recommendations %}
                    <div class="mt-8">
                        <h4 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                            <i class="fas fa-shopping-cart mr-2 text-blue-500"></i>
                            Smart Product Recommendations
                        </h4>
                        <div class="overflow-x-auto">
                            <table class="w-full">
                                <thead>
                                    <tr class="bg-gray-50 border-b border-gray-200">
                                        <th class="px-4 py-3 text-left text-sm font-semibold text-gray-900">Product</th>
                                        <th class="px-4 py-3 text-center text-sm font-semibold text-gray-900">Rate (kg/ha)</th>
                                        <th class="px-4 py-3 text-center text-sm font-semibold text-gray-900">Key Nutrients</th>
                                        <th class="px-4 py-3 text-center text-sm font-semibold text-gray-900">Cost/ha</th>
                                        <th class="px-4 py-3 text-center text-sm font-semibold text-gray-900">Efficiency</th>
                                    </tr>
                                </thead>
                                <tbody class="divide-y divide-gray-200">
                                    {% for product in result.smart_fertilizer_recommendations.smart_recommendations %}
                                    <tr class="hover:bg-gray-50 transition-colors">
                                        <td class="px-4 py-4">
                                            <div class="font-semibold text-gray-900">{{ product.product_name }}</div>
                                            <span class="inline-block px-2 py-1 text-xs font-medium rounded-full mt-1
                                                 {% if product.category == 'NPK' %}bg-blue-100 text-blue-800
                                                 {% elif product.category == 'Secondary' %}bg-orange-100 text-orange-800
                                                 {% elif product.category == 'Micronutrient' %}bg-red-100 text-red-800
                                                 {% elif product.category == 'Complete' %}bg-green-100 text-green-800
                                                 {% else %}bg-gray-100 text-gray-800{% endif %}">
                                                {{ product.category }}
                                            </span>
                                        </td>
                                        <td class="px-4 py-4 text-center">
                                            <div class="text-lg font-bold text-blue-600">{{ product.application_rate_kg_ha }}</div>
                                            <div class="text-xs text-gray-500">kg/ha</div>
                                        </td>
                                        <td class="px-4 py-4">
                                            <div class="space-y-1">
                                                {% for nutrient, amount in product.nutrients_supplied.items() %}
                                                    {% if amount > 0.1 %}
                                                        <div class="flex justify-between text-xs bg-gray-100 px-2 py-1 rounded">
                                                            <span>{{ nutrient }}:</span>
                                                            <span class="font-semibold text-green-600">{{ amount|round(1) }}kg</span>
                                                        </div>
                                                    {% endif %}
                                                {% endfor %}
                                            </div>
                                        </td>
                                        <td class="px-4 py-4 text-center">
                                            <div class="text-lg font-bold text-green-600">${{ product.cost_per_ha }}</div>
                                        </td>
                                        <td class="px-4 py-4 text-center">
                                            <div class="flex items-center justify-center">
                                                <div class="w-16 bg-gray-200 rounded-full h-2">
                                                    <div class="bg-gradient-to-r from-green-400 to-green-600 h-2 rounded-full" 
                                                         style="width: {{ (product.get('efficiency_score', 0.5) * 100)|round(0) }}%"></div>
                                                </div>
                                                <span class="ml-2 text-xs font-medium">{{ (product.get('efficiency_score', 0.5) * 100)|round(0) }}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>

        <!-- SIMPLE RESULTS SUMMARY DASHBOARD -->
        <div class="mb-8">
            <div class="bg-gradient-to-r from-green-50 to-blue-50 rounded-xl p-6 border border-green-200">
                <h2 class="text-2xl font-bold text-gray-800 mb-4 text-center">Your Soil Analysis Results</h2>
                
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <!-- Soil Health Score -->
                    <div class="bg-white rounded-lg p-4 text-center shadow-sm">
                        <div class="text-3xl font-bold text-blue-600 mb-1">
                            {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}85%{% elif data.ph|float >= 5.5 %}70%{% else %}45%{% endif %}
                        </div>
                        <div class="text-sm text-gray-600 font-medium">Soil Health</div>
                        <div class="text-xs text-gray-500">Overall condition</div>
                    </div>
                    
                    <!-- pH Status -->
                    <div class="bg-white rounded-lg p-4 text-center shadow-sm">
                        <div class="text-3xl font-bold {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}text-green-600{% elif data.ph|float >= 5.5 %}text-yellow-600{% else %}text-red-600{% endif %} mb-1">
                            {{ data.ph }}
                        </div>
                        <div class="text-sm text-gray-600 font-medium">Current pH</div>
                        <div class="text-xs {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}text-green-600{% elif data.ph|float >= 5.5 %}text-yellow-600{% else %}text-red-600{% endif %}">
                            {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}Optimal{% elif data.ph|float >= 5.5 %}Slightly Acidic{% else %}Too Acidic{% endif %}
                        </div>
                    </div>
                    
                    <!-- Lime Needed -->
                    <div class="bg-white rounded-lg p-4 text-center shadow-sm">
                        <div class="text-3xl font-bold text-yellow-600 mb-1">
                            {{ result.enhanced_lime_calculation.lime_needed_t_ha }}
                        </div>
                        <div class="text-sm text-gray-600 font-medium">Lime (t/ha)</div>
                        <div class="text-xs text-yellow-600">To fix pH</div>
                    </div>
                    
                    <!-- Action Priority -->
                    <div class="bg-white rounded-lg p-4 text-center shadow-sm">
                        <div class="text-3xl font-bold {% if result.enhanced_lime_calculation.lime_needed_t_ha > 2 %}text-red-600{% elif result.enhanced_lime_calculation.lime_needed_t_ha > 0.5 %}text-yellow-600{% else %}text-green-600{% endif %} mb-1">
                            {% if result.enhanced_lime_calculation.lime_needed_t_ha > 2 %}HIGH{% elif result.enhanced_lime_calculation.lime_needed_t_ha > 0.5 %}MED{% else %}LOW{% endif %}
                        </div>
                        <div class="text-sm text-gray-600 font-medium">Priority</div>
                        <div class="text-xs text-gray-500">Action needed</div>
                    </div>
                </div>
                
                <!-- Quick Action Summary -->
                <div class="bg-white rounded-lg p-4 text-center">
                    <div class="text-lg font-semibold text-gray-800 mb-2">
                        {% if result.enhanced_lime_calculation.lime_needed_t_ha > 2 %}
                            🚨 Immediate Action Required: Apply {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha lime
                        {% elif result.enhanced_lime_calculation.lime_needed_t_ha > 0.5 %}
                            ⚠️ Moderate Action: Apply {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha lime this season
                        {% else %}
                            ✅ Good Condition: Minimal lime needed ({{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha)
                        {% endif %}
                    </div>
                    <div class="text-sm text-gray-600">
                        Your {{ result.enhanced_lime_calculation.soil_type_name.lower() }} soil needs attention to optimize crop yields
                    </div>
                </div>
            </div>
        </div>

        <!-- Scientific Lime Calculation -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <!-- SIMPLIFIED LIME RESULTS -->
                <div class="bg-white border-l-4 border-green-500 p-6">
                    <!-- Main Result - Big and Clear -->
                    <div class="text-center mb-6">
                        <div class="text-4xl font-bold text-green-600 mb-2">
                            {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha
                        </div>
                        <div class="text-lg text-gray-700 mb-1">
                            {{ result.enhanced_lime_calculation.lime_name.split("(")[0].strip() }} Needed
                        </div>
                        <div class="text-sm text-gray-500">
                            For {{ result.land_area_ha }} hectare(s) = {{ result.enhanced_lime_calculation.lime_needed_t_total }} tonnes total
                        </div>
                    </div>

                    <!-- Simple Summary Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-lg font-semibold text-gray-700">Your Soil</div>
                            <div class="text-sm text-gray-600">{{ result.enhanced_lime_calculation.soil_type_name }}</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-lg font-semibold text-gray-700">Current pH</div>
                            <div class="text-sm text-gray-600">{{ result.ph }} (Acidic)</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 text-center">
                            <div class="text-lg font-semibold text-gray-700">Target pH</div>
                            <div class="text-sm text-gray-600">6.0-6.5 (Optimal)</div>
                        </div>
                    </div>

                    <!-- Simple Action Steps -->
                    <div class="bg-blue-50 rounded-lg p-4">
                        <h4 class="font-semibold text-blue-800 mb-3 flex items-center">
                            <i class="fas fa-list-check mr-2"></i>
                            What to Do
                        </h4>
                        <div class="space-y-2 text-sm text-blue-700">
                            <div class="flex items-start">
                                <span class="bg-blue-200 text-blue-800 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">1</span>
                                <span>Apply <strong>{{ result.enhanced_lime_calculation.lime_needed_t_ha }} tonnes per hectare</strong> of {{ result.enhanced_lime_calculation.lime_name.split("(")[0].strip() }}</span>
                            </div>
                            <div class="flex items-start">
                                <span class="bg-blue-200 text-blue-800 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">2</span>
                                <span>Mix thoroughly into top 20cm of soil</span>
                            </div>
                            <div class="flex items-start">
                                <span class="bg-blue-200 text-blue-800 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">3</span>
                                <span>Wait 3-6 months before planting for full effect</span>
                            </div>
                        </div>
                    </div>

                    <!-- Advanced Details (Collapsible) -->
                    <div class="mt-6">
                        <button onclick="toggleAdvancedDetails()" class="w-full text-left bg-gray-100 hover:bg-gray-200 rounded-lg p-3 transition-colors">
                            <div class="flex items-center justify-between">
                                <span class="text-sm font-medium text-gray-700">Show Advanced Details</span>
                                <i id="advanced-icon" class="fas fa-chevron-down text-gray-500"></i>
                            </div>
                        </button>
                        <div id="advanced-details" class="hidden mt-4 space-y-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div class="bg-gray-50 rounded-lg p-3">
                                    <div class="text-xs text-gray-500 mb-1">Scientific Formula</div>
                                    <div class="text-sm font-mono">t/ha = 5 × ΔAE × ρb × d</div>
                                </div>
                                <div class="bg-gray-50 rounded-lg p-3">
                                    <div class="text-xs text-gray-500 mb-1">Soil Buffering Factor</div>
                                    <div class="text-sm">{{ result.enhanced_lime_calculation.soil_type_name }}: {{ result.enhanced_lime_calculation.soil_factor }}x</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <script>
                function toggleAdvancedDetails() {
                    const details = document.getElementById('advanced-details');
                    const icon = document.getElementById('advanced-icon');
                    const button = event.currentTarget;
                    
                    if (details.classList.contains('hidden')) {
                        details.classList.remove('hidden');
                        icon.classList.remove('fa-chevron-down');
                        icon.classList.add('fa-chevron-up');
                        button.querySelector('span').textContent = 'Hide Advanced Details';
                    } else {
                        details.classList.add('hidden');
                        icon.classList.remove('fa-chevron-up');
                        icon.classList.add('fa-chevron-down');
                        button.querySelector('span').textContent = 'Show Advanced Details';
                    }
                }
                </script>

        <!-- SIMPLIFIED NUTRIENT RESULTS -->
        {% if result.comprehensive_nutrient_requirements %}
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-white border-l-4 border-blue-500 p-6">
                    <!-- Main Nutrient Needs -->
                    <div class="text-center mb-6">
                        <h3 class="text-2xl font-bold text-blue-600 mb-2">Fertilizer Recommendations</h3>
                        <p class="text-gray-600">Based on your soil test results</p>
                    </div>

                    <!-- Simple Nutrient Cards -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        {% if result.comprehensive_nutrient_requirements.primary_nutrients.N.needed > 0 %}
                        <div class="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-green-600">{{ result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|round(0) }}</div>
                            <div class="text-sm text-green-700 font-medium">kg/ha Nitrogen (N)</div>
                            <div class="text-xs text-green-600 mt-1">For healthy growth</div>
                        </div>
                        {% endif %}
                        
                        {% if result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed > 0 %}
                        <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-orange-600">{{ result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|round(0) }}</div>
                            <div class="text-sm text-orange-700 font-medium">kg/ha Phosphorus (P₂O₅)</div>
                            <div class="text-xs text-orange-600 mt-1">For root development</div>
                        </div>
                        {% endif %}
                        
                        {% if result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed > 0 %}
                        <div class="bg-purple-50 border border-purple-200 rounded-lg p-4 text-center">
                            <div class="text-2xl font-bold text-purple-600">{{ result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|round(0) }}</div>
                            <div class="text-sm text-purple-700 font-medium">kg/ha Potassium (K₂O)</div>
                            <div class="text-xs text-purple-600 mt-1">For disease resistance</div>
                        </div>
                        {% endif %}
                    </div>

                    <!-- Simple Product Recommendations -->
                    {% if result.smart_fertilizer_recommendations.product_recommendations %}
                    <div class="bg-yellow-50 rounded-lg p-4">
                        <h4 class="font-semibold text-yellow-800 mb-3 flex items-center">
                            <i class="fas fa-shopping-cart mr-2"></i>
                            Recommended Products
                        </h4>
                        <div class="space-y-2">
                            {% for product in result.smart_fertilizer_recommendations.product_recommendations[:2] %}
                            <div class="flex justify-between items-center bg-white rounded p-3">
                                <div>
                                    <div class="font-medium text-gray-800">{{ product.product_name }}</div>
                                    <div class="text-sm text-gray-600">{{ product.application_rate|round(0) }} kg/ha</div>
                                </div>
                                <div class="text-right">
                                    <div class="text-sm font-medium text-gray-800">${{ product.cost_per_ha|round(2) }}/ha</div>
                                    <div class="text-xs text-gray-500">{{ product.efficiency_score|round(1) }}% efficient</div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endif %}

        <!-- PROFESSIONAL SOIL ANALYSIS TABLE -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-xl font-bold text-gray-800 flex items-center">
                        <i class="fas fa-table mr-3 text-blue-600"></i>
                        Professional Soil Analysis Report
                    </h3>
                    <p class="text-sm text-gray-600 mt-1">Detailed comparison of your soil values against optimal ranges</p>
                </div>
                
                <div class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Parameter</th>
                                <th class="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Your Value</th>
                                <th class="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Optimal Range</th>
                                <th class="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th class="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Recommendation</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            <!-- pH Row -->
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                                            <i class="fas fa-flask text-blue-600 text-sm"></i>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Soil pH</div>
                                            <div class="text-xs text-gray-500">Acidity/Alkalinity</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ data.ph }}</div>
                                    <div class="text-xs text-gray-500">pH units</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">6.0 - 7.0</div>
                                    <div class="text-xs text-gray-500">Optimal for most crops</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Optimal
                                    </span>
                                    {% elif data.ph|float >= 5.5 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Slightly Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Too Low
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if data.ph|float >= 6.0 and data.ph|float <= 7.0 %}
                                    <div class="text-sm text-green-700">✓ No action needed</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha lime</div>
                                    <div class="text-xs text-gray-500">{{ result.enhanced_lime_calculation.lime_name.split("(")[0].strip() }}</div>
                                    {% endif %}
                                </td>
                            </tr>

                            <!-- Phosphorus Row -->
                            {% if data.phosphorus_ppm %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-orange-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-orange-600">P</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Phosphorus (P)</div>
                                            <div class="text-xs text-gray-500">Root development</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ data.phosphorus_ppm }}</div>
                                    <div class="text-xs text-gray-500">ppm</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">15 - 25</div>
                                    <div class="text-xs text-gray-500">ppm (Olsen method)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if data.phosphorus_ppm|float >= 15 and data.phosphorus_ppm|float <= 25 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Optimal
                                    </span>
                                    {% elif data.phosphorus_ppm|float >= 10 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% elif data.phosphorus_ppm|float > 25 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                        <i class="fas fa-arrow-up mr-1"></i>High
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if data.phosphorus_ppm|float >= 15 and data.phosphorus_ppm|float <= 25 %}
                                    <div class="text-sm text-green-700">✓ Maintain current levels</div>
                                    {% elif data.phosphorus_ppm|float > 25 %}
                                    <div class="text-sm text-blue-700">Reduce P fertilizer application</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.phosphorus_needed|round(0) }} kg/ha P₂O₅</div>
                                    <div class="text-xs text-gray-500">Triple superphosphate or DAP</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Potassium Row -->
                            {% if data.potassium_cmol %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-purple-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-purple-600">K</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Potassium (K)</div>
                                            <div class="text-xs text-gray-500">Disease resistance</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ data.potassium_cmol }}</div>
                                    <div class="text-xs text-gray-500">cmol+/kg</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">0.3 - 0.8</div>
                                    <div class="text-xs text-gray-500">cmol+/kg</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if data.potassium_cmol|float >= 0.3 and data.potassium_cmol|float <= 0.8 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Optimal
                                    </span>
                                    {% elif data.potassium_cmol|float >= 0.2 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% elif data.potassium_cmol|float > 0.8 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                        <i class="fas fa-arrow-up mr-1"></i>High
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if data.potassium_cmol|float >= 0.3 and data.potassium_cmol|float <= 0.8 %}
                                    <div class="text-sm text-green-700">✓ Maintain current levels</div>
                                    {% elif data.potassium_cmol|float > 0.8 %}
                                    <div class="text-sm text-blue-700">Reduce K fertilizer application</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.potassium_needed|round(0) }} kg/ha K₂O</div>
                                    <div class="text-xs text-gray-500">Muriate of potash or sulfate of potash</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Organic Matter Row -->
                            {% if data.organic_matter %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
                                            <i class="fas fa-leaf text-green-600 text-sm"></i>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Organic Matter</div>
                                            <div class="text-xs text-gray-500">Soil health indicator</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ data.organic_matter }}%</div>
                                    <div class="text-xs text-gray-500">by weight</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">3.0 - 5.0%</div>
                                    <div class="text-xs text-gray-500">Good soil health</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if data.organic_matter|float >= 3.0 and data.organic_matter|float <= 5.0 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Good
                                    </span>
                                    {% elif data.organic_matter|float >= 2.0 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Fair
                                    </span>
                                    {% elif data.organic_matter|float > 5.0 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                        <i class="fas fa-arrow-up mr-1"></i>Very High
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Low
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if data.organic_matter|float >= 3.0 and data.organic_matter|float <= 5.0 %}
                                    <div class="text-sm text-green-700">✓ Excellent soil health</div>
                                    {% elif data.organic_matter|float > 5.0 %}
                                    <div class="text-sm text-blue-700">Consider drainage improvement</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Add compost or manure</div>
                                    <div class="text-xs text-gray-500">2-4 tons/ha annually</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Exchangeable Acidity Row -->
                            {% if data.exchangeable_acidity %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-red-100 rounded-full flex items-center justify-center">
                                            <i class="fas fa-exclamation text-red-600 text-sm"></i>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Exchangeable Acidity</div>
                                            <div class="text-xs text-gray-500">Soil acidity level</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ data.exchangeable_acidity }}</div>
                                    <div class="text-xs text-gray-500">cmol+/kg</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">< 0.5</div>
                                    <div class="text-xs text-gray-500">cmol+/kg (target)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if data.exchangeable_acidity|float <= 0.5 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Good
                                    </span>
                                    {% elif data.exchangeable_acidity|float <= 1.0 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Moderate
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>High
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if data.exchangeable_acidity|float <= 0.5 %}
                                    <div class="text-sm text-green-700">✓ No liming needed</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Reduce by {{ result.enhanced_lime_calculation.ae_to_neutralize }} cmol+/kg</div>
                                    <div class="text-xs text-gray-500">Apply {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha lime</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- CEC Row -->
                            {% if result.calculated_cec %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-indigo-100 rounded-full flex items-center justify-center">
                                            <i class="fas fa-exchange-alt text-indigo-600 text-sm"></i>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">CEC</div>
                                            <div class="text-xs text-gray-500">Cation Exchange Capacity</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.calculated_cec }}</div>
                                    <div class="text-xs text-gray-500">cmol+/kg</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">15 - 25</div>
                                    <div class="text-xs text-gray-500">cmol+/kg (good)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.calculated_cec >= 15 and result.calculated_cec <= 25 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Good
                                    </span>
                                    {% elif result.calculated_cec >= 10 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Fair
                                    </span>
                                    {% elif result.calculated_cec > 25 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                        <i class="fas fa-arrow-up mr-1"></i>High
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Low
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.calculated_cec >= 15 and result.calculated_cec <= 25 %}
                                    <div class="text-sm text-green-700">✓ Good nutrient holding capacity</div>
                                    {% elif result.calculated_cec > 25 %}
                                    <div class="text-sm text-blue-700">High clay content - good retention</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Increase organic matter</div>
                                    <div class="text-xs text-gray-500">Add compost to improve CEC</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- FERTILIZER SECTION HEADER -->
                            <tr class="bg-blue-50">
                                <td colspan="5" class="px-6 py-3">
                                    <div class="flex items-center">
                                        <i class="fas fa-seedling text-blue-600 mr-2"></i>
                                        <span class="text-sm font-bold text-blue-800 uppercase tracking-wider">Fertilizer Requirements</span>
                                    </div>
                                </td>
                            </tr>

                            <!-- Nitrogen Row -->
                            {% if result.comprehensive_nutrient_requirements %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-green-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-green-600">N</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Nitrogen (N)</div>
                                            <div class="text-xs text-gray-500">Plant growth & protein</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">100 - 150</div>
                                    <div class="text-xs text-gray-500">kg/ha for most crops</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|default(0) <= 20 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|default(0) <= 50 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|default(0) <= 20 %}
                                    <div class="text-sm text-green-700">✓ Minimal N needed</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.primary_nutrients.N.needed|default(0)|round(0) }} kg/ha N</div>
                                    <div class="text-xs text-gray-500">Urea, ammonium sulfate, or CAN</div>
                                    {% endif %}
                                </td>
                            </tr>

                            <!-- Phosphorus Fertilizer Row -->
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-orange-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-orange-600">P₂O₅</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Phosphorus (P₂O₅)</div>
                                            <div class="text-xs text-gray-500">Root development</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">40 - 80</div>
                                    <div class="text-xs text-gray-500">kg/ha for most crops</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|default(0) <= 10 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|default(0) <= 30 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|default(0) <= 10 %}
                                    <div class="text-sm text-green-700">✓ Minimal P₂O₅ needed</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed|default(0)|round(0) }} kg/ha P₂O₅</div>
                                    <div class="text-xs text-gray-500">TSP, DAP, or MAP</div>
                                    {% endif %}
                                </td>
                            </tr>

                            <!-- Potassium Fertilizer Row -->
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-purple-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-purple-600">K₂O</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Potassium (K₂O)</div>
                                            <div class="text-xs text-gray-500">Disease resistance</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">60 - 120</div>
                                    <div class="text-xs text-gray-500">kg/ha for most crops</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|default(0) <= 15 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|default(0) <= 40 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|default(0) <= 15 %}
                                    <div class="text-sm text-green-700">✓ Minimal K₂O needed</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed|default(0)|round(0) }} kg/ha K₂O</div>
                                    <div class="text-xs text-gray-500">MOP, SOP, or potassium sulfate</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- SECONDARY NUTRIENTS SECTION HEADER -->
                            {% if result.comprehensive_nutrient_requirements.secondary_nutrients %}
                            <tr class="bg-indigo-50">
                                <td colspan="5" class="px-6 py-3">
                                    <div class="flex items-center">
                                        <i class="fas fa-atom text-indigo-600 mr-2"></i>
                                        <span class="text-sm font-bold text-indigo-800 uppercase tracking-wider">Secondary Nutrients</span>
                                    </div>
                                </td>
                            </tr>

                            <!-- Calcium Row -->
                            {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Ca %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-gray-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-gray-600">Ca</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Calcium (Ca)</div>
                                            <div class="text-xs text-gray-500">Cell wall strength</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">800 - 2000</div>
                                    <div class="text-xs text-gray-500">kg/ha (adequate)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed|default(0) <= 50 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed|default(0) <= 150 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed|default(0) <= 50 %}
                                    <div class="text-sm text-green-700">✓ Adequate calcium</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed|default(0)|round(0) }} kg/ha Ca</div>
                                    <div class="text-xs text-gray-500">Gypsum or lime application</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Magnesium Row -->
                            {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Mg %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-teal-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-teal-600">Mg</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Magnesium (Mg)</div>
                                            <div class="text-xs text-gray-500">Chlorophyll center</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">120 - 300</div>
                                    <div class="text-xs text-gray-500">kg/ha (adequate)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed|default(0) <= 25 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed|default(0) <= 75 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed|default(0) <= 25 %}
                                    <div class="text-sm text-green-700">✓ Adequate magnesium</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed|default(0)|round(0) }} kg/ha Mg</div>
                                    <div class="text-xs text-gray-500">Dolomitic lime or Epsom salt</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Sulfur Row -->
                            {% if result.comprehensive_nutrient_requirements.secondary_nutrients.S %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-yellow-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-yellow-600">S</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Sulfur (S)</div>
                                            <div class="text-xs text-gray-500">Protein synthesis</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed|default(0)|round(0) }}</div>
                                    <div class="text-xs text-gray-500">kg/ha needed</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">20 - 40</div>
                                    <div class="text-xs text-gray-500">kg/ha (adequate)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed|default(0) <= 5 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        <i class="fas fa-check-circle mr-1"></i>Adequate
                                    </span>
                                    {% elif result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed|default(0) <= 15 %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                        <i class="fas fa-exclamation-triangle mr-1"></i>Low
                                    </span>
                                    {% else %}
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                    {% endif %}
                                </td>
                                <td class="px-6 py-4">
                                    {% if result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed|default(0) <= 5 %}
                                    <div class="text-sm text-green-700">✓ Adequate sulfur</div>
                                    {% else %}
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed|default(0)|round(0) }} kg/ha S</div>
                                    <div class="text-xs text-gray-500">Ammonium sulfate or gypsum</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}
                            {% endif %}

                            <!-- MICRONUTRIENTS SECTION HEADER -->
                            {% if result.comprehensive_nutrient_requirements.micronutrients_needed %}
                            <tr class="bg-emerald-50">
                                <td colspan="5" class="px-6 py-3">
                                    <div class="flex items-center">
                                        <i class="fas fa-microscope text-emerald-600 mr-2"></i>
                                        <span class="text-sm font-bold text-emerald-800 uppercase tracking-wider">Micronutrients</span>
                                    </div>
                                </td>
                            </tr>

                            <!-- Iron Row -->
                            {% if result.comprehensive_nutrient_requirements.micronutrients.Fe %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-red-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-red-600">Fe</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Iron (Fe)</div>
                                            <div class="text-xs text-gray-500">Chlorophyll synthesis</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ result.comprehensive_nutrient_requirements.micronutrients.Fe.current_ppm|default(0)|round(1) }}</div>
                                    <div class="text-xs text-gray-500">ppm available</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">10 - 100</div>
                                    <div class="text-xs text-gray-500">ppm (adequate)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                </td>
                                <td class="px-6 py-4">
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.micronutrients.Fe.needed|default(0)|round(1) }} kg/ha Fe</div>
                                    <div class="text-xs text-gray-500">Iron sulfate or chelated iron</div>
                                </td>
                            </tr>
                            {% endif %}

                            <!-- Zinc Row -->
                            {% if result.comprehensive_nutrient_requirements.micronutrients_needed.zinc %}
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="flex items-center">
                                        <div class="flex-shrink-0 h-8 w-8 bg-blue-100 rounded-full flex items-center justify-center">
                                            <div class="text-xs font-bold text-blue-600">Zn</div>
                                        </div>
                                        <div class="ml-3">
                                            <div class="text-sm font-medium text-gray-900">Zinc (Zn)</div>
                                            <div class="text-xs text-gray-500">Enzyme activation</div>
                                        </div>
                                    </div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm font-bold text-gray-900">{{ (3 - result.comprehensive_nutrient_requirements.micronutrients_needed.zinc.deficit_ppm|default(0))|round(1) }}</div>
                                    <div class="text-xs text-gray-500">ppm available</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <div class="text-sm text-gray-900">2 - 10</div>
                                    <div class="text-xs text-gray-500">ppm (adequate)</div>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        <i class="fas fa-times-circle mr-1"></i>Deficient
                                    </span>
                                </td>
                                <td class="px-6 py-4">
                                    <div class="text-sm text-gray-900">Apply {{ result.comprehensive_nutrient_requirements.micronutrients_needed.zinc.kg_ha_needed|default(0)|round(1) }} kg/ha Zn</div>
                                    <div class="text-xs text-gray-500">Zinc sulfate or zinc oxide</div>
                                </td>
                            </tr>
                            {% endif %}
                            {% endif %}
                        </tbody>
                    </table>
                </div>
                
                <!-- Table Footer with Summary -->
                <div class="bg-gray-50 px-6 py-4 border-t border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="text-sm text-gray-600">
                            <i class="fas fa-info-circle mr-2"></i>
                            Analysis based on standard soil test interpretation guidelines
                        </div>
                        <div class="text-sm font-medium text-gray-900">
                            Total estimated cost: ${{ result.estimated_cost }}/ha
                        </div>
                    </div>
                </div>
            </div>
        </div>

                        <!-- Lime Types Comparison Chart -->
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900 mb-4">Lime Types Comparison</h4>
                            <div class="relative h-64">
                                <canvas id="limeTypesChart"></canvas>
                            </div>
                            <div class="mt-4 text-xs text-gray-600">
                                <strong>Selected:</strong> {{ result.enhanced_lime_calculation.lime_name }}
                                {% if result.enhanced_lime_calculation.safety_cap_applied %}
                                <span class="text-red-600">⚠️ Capped at 8 t/ha for safety</span>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Soil Chemistry & Physical Properties -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Soil Chemistry -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-flask mr-2 text-green-500"></i>
                        Soil Chemistry
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-4">
                        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span class="font-medium text-gray-700">CEC (cmol+/kg)</span>
                            <span class="text-xl font-bold text-green-600">{{ result.calculated_cec }}</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span class="font-medium text-gray-700">Base Saturation</span>
                            <span class="text-xl font-bold text-blue-600">{{ result.calculated_base_saturation }}%</span>
                        </div>
                        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span class="font-medium text-gray-700">Acid Saturation</span>
                            <span class="text-xl font-bold text-red-600">{{ result.calculated_acid_saturation }}%</span>
                        </div>
                    </div>
                    
                    <!-- Cationic Ratios Chart -->
                    <div class="mt-6">
                        <h4 class="text-md font-semibold text-gray-900 mb-3">Cationic Ratios</h4>
                        <div class="relative h-48">
                            <canvas id="cationicRatiosChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Physical Properties -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-50 to-violet-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-weight mr-2 text-purple-500"></i>
                        Physical Properties
                    </h3>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="text-center p-4 bg-green-50 rounded-lg">
                            <div class="text-2xl font-bold text-green-600">{{ result.calculated_porosity }}%</div>
                            <div class="text-sm text-gray-600">Porosity</div>
                            <div class="text-xs text-gray-500">(1 - ρb/ρs) × 100</div>
                        </div>
                        <div class="text-center p-4 bg-blue-50 rounded-lg">
                            <div class="text-2xl font-bold text-blue-600">{{ result.enhanced_lime_calculation.soil_calculations.soil_volume_m3_per_ha }}</div>
                            <div class="text-sm text-gray-600">Volume (m³/ha)</div>
                            <div class="text-xs text-gray-500">Area × Depth</div>
                        </div>
                    </div>
                    
                    <!-- Physical Properties Visualization -->
                    <div class="relative h-48">
                        <canvas id="physicalPropertiesChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Nutrient Status -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Primary & Secondary Nutrients -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-cyan-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-flask mr-2 text-blue-500"></i>
                        Primary & Secondary Nutrients
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-3">
                        {% for nutrient, status in result.nutrient_status.items() %}
                        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span class="capitalize font-medium text-gray-700">{{ nutrient.replace('_', ' ') }}</span>
                            <span class="px-3 py-1 rounded-full text-sm font-medium
                                       {% if status == 'Optimal' %}bg-green-100 text-green-800
                                       {% elif status == 'High' %}bg-yellow-100 text-yellow-800
                                       {% else %}bg-red-100 text-red-800{% endif %}">
                                {{ status }}
                            </span>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <!-- Micronutrients -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-red-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-microscope mr-2 text-red-500"></i>
                        Micronutrients Status
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-3">
                        {% for nutrient, status in result.micronutrient_status.items() %}
                        <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                            <span class="capitalize font-medium text-gray-700">{{ nutrient.replace('_', ' ') }}</span>
                            <span class="px-3 py-1 rounded-full text-sm font-medium
                                       {% if status == 'Optimal' %}bg-green-100 text-green-800
                                       {% elif status == 'High' %}bg-yellow-100 text-yellow-800
                                       {% elif status == 'Not Tested' %}bg-gray-100 text-gray-800
                                       {% else %}bg-red-100 text-red-800{% endif %}">
                                {{ status }}
                            </span>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Cost Analysis -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-dollar-sign mr-3 text-green-500"></i>
                        Complete Cost Analysis
                    </h3>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Cost Breakdown -->
                        <div>
                            <div class="grid grid-cols-2 gap-4 mb-6">
                                <div class="text-center p-4 bg-yellow-50 rounded-lg">
                                    <div class="text-2xl font-bold text-yellow-600">${{ result.detailed_cost_breakdown.lime_cost_per_ha }}</div>
                                    <div class="text-sm text-gray-600">Lime Cost/ha</div>
                                </div>
                                <div class="text-center p-4 bg-blue-50 rounded-lg">
                                    <div class="text-2xl font-bold text-blue-600">${{ result.detailed_cost_breakdown.comprehensive_fertilizer_cost_per_ha }}</div>
                                    <div class="text-sm text-gray-600">Fertilizer Cost/ha</div>
                                </div>
                            </div>
                            
                            <div class="text-center p-6 bg-gradient-to-r from-green-100 to-emerald-100 rounded-lg border-2 border-green-200">
                                <div class="text-3xl font-bold text-green-700 mb-2">${{ result.detailed_cost_breakdown.total_cost_per_ha }}</div>
                                <div class="text-lg font-semibold text-green-800">Total Cost per Hectare</div>
                                <div class="text-sm text-green-600 mt-2">
                                    Field total ({{ result.land_area_ha }} ha): ${{ (result.detailed_cost_breakdown.total_cost_per_ha * result.land_area_ha)|round(2) }}
                                </div>
                            </div>
                        </div>

                        <!-- Cost Distribution Chart -->
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900 mb-4">Cost Distribution</h4>
                            <div class="relative h-64">
                                <canvas id="costDistributionChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 🤖 AI-POWERED INSIGHTS SECTION -->
        {% if result.ai_insights %}
        <div class="mb-8">
            <div class="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl shadow-lg border border-purple-200 overflow-hidden">
                <div class="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-4">
                    <h3 class="text-xl font-bold text-white flex items-center">
                        <i class="fas fa-brain mr-3"></i>
                        AI-Powered Soil Analysis
                        <span class="ml-2 px-2 py-1 bg-white bg-opacity-20 rounded-full text-xs font-medium">SMART</span>
                    </h3>
                    <p class="text-purple-100 text-sm mt-1">Advanced insights powered by artificial intelligence</p>
                </div>
                
                <div class="p-6 space-y-6">
                    <!-- AI Summary -->
                    <div class="bg-white rounded-lg p-5 border border-purple-100">
                        <div class="flex items-start">
                            <div class="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-lightbulb text-purple-600"></i>
                            </div>
                            <div class="ml-4 flex-1">
                                <h4 class="text-lg font-semibold text-gray-900 mb-2">Executive Summary</h4>
                                <p class="text-gray-700 leading-relaxed">{{ result.ai_insights.ai_summary }}</p>
                            </div>
                        </div>
                    </div>

                    <!-- Smart Recommendations -->
                    {% if result.ai_insights.smart_recommendations %}
                    <div class="bg-white rounded-lg p-5 border border-purple-100">
                        <div class="flex items-start">
                            <div class="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-tasks text-green-600"></i>
                            </div>
                            <div class="ml-4 flex-1">
                                <h4 class="text-lg font-semibold text-gray-900 mb-3">Smart Recommendations</h4>
                                <div class="space-y-3">
                                    {% for recommendation in result.ai_insights.smart_recommendations %}
                                    <div class="flex items-start p-3 bg-green-50 border border-green-200 rounded-lg">
                                        <div class="flex-shrink-0 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center mr-3 mt-0.5">
                                            <span class="text-white text-xs font-bold">{{ loop.index }}</span>
                                        </div>
                                        <p class="text-green-800 text-sm">{{ recommendation }}</p>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endif %}

                    <!-- Contextual Insights -->
                    {% if result.ai_insights.contextual_insights %}
                    <div class="bg-white rounded-lg p-5 border border-purple-100">
                        <div class="flex items-start">
                            <div class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-eye text-blue-600"></i>
                            </div>
                            <div class="ml-4 flex-1">
                                <h4 class="text-lg font-semibold text-gray-900 mb-3">Key Insights</h4>
                                <div class="space-y-2">
                                    {% for insight in result.ai_insights.contextual_insights %}
                                    <div class="flex items-start">
                                        <i class="fas fa-arrow-right text-blue-500 mr-2 mt-1 text-sm"></i>
                                        <p class="text-gray-700 text-sm">{{ insight }}</p>
                                    </div>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                    {% endif %}

                    <!-- Risk Assessment -->
                    <div class="bg-white rounded-lg p-5 border border-purple-100">
                        <div class="flex items-start">
                            <div class="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                                <i class="fas fa-shield-alt text-orange-600"></i>
                            </div>
                            <div class="ml-4 flex-1">
                                <h4 class="text-lg font-semibold text-gray-900 mb-2">Risk Assessment</h4>
                                <p class="text-gray-700 text-sm">{{ result.ai_insights.risk_assessment }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- AI Disclaimer -->
                <div class="bg-gray-50 px-6 py-3 border-t border-gray-200">
                    <p class="text-xs text-gray-500 flex items-center">
                        <i class="fas fa-info-circle mr-2"></i>
                        AI analysis is based on soil data patterns and should be used alongside professional agronomic advice.
                    </p>
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Action Buttons -->
        <div class="text-center space-x-4 mb-8">
            <a href="{{ url_for('soil_analysis') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-plus mr-2"></i>New Analysis
            </a>
            <a href="{{ url_for('dashboard') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
            </a>
            <button onclick="window.print()" 
                    class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-print mr-2"></i>Print Report
            </button>
        </div>
    </div>

    <script>
        // Chart.js configuration
        Chart.defaults.font.family = 'Inter, sans-serif';
        Chart.defaults.color = '#6B7280';

        document.addEventListener('DOMContentLoaded', function() {
            // Overall Rating Doughnut Chart
            new Chart(document.getElementById('overallRatingChart'), {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [{{ result.overall_rating }}, {{ 100 - result.overall_rating }}],
                        backgroundColor: [
                            {% if result.overall_rating >= 80 %}'#22C55E'{% elif result.overall_rating >= 60 %}'#EAB308'{% else %}'#EF4444'{% endif %},
                            '#E5E7EB'
                        ],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });

            // Fertility Index Chart
            new Chart(document.getElementById('fertilityChart'), {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [{{ (result.fertility_index * 100)|round(0) }}, {{ 100 - (result.fertility_index * 100)|round(0) }}],
                        backgroundColor: ['#3B82F6', '#E5E7EB'],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });

            // Soil Health Chart
            new Chart(document.getElementById('healthChart'), {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [{{ result.soil_health_score|round(0) }}, {{ 100 - result.soil_health_score|round(0) }}],
                        backgroundColor: ['#8B5CF6', '#E5E7EB'],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });

            // Yield Potential Chart
            new Chart(document.getElementById('yieldChart'), {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [{{ result.estimated_yield_potential|round(0) }}, {{ 100 - result.estimated_yield_potential|round(0) }}],
                        backgroundColor: ['#F59E0B', '#E5E7EB'],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });

            // Nutrient Requirements Bar Chart
            new Chart(document.getElementById('nutrientRequirementsChart'), {
                type: 'bar',
                data: {
                    labels: ['N', 'P₂O₅', 'K₂O', 'Ca', 'Mg', 'S'],
                    datasets: [{
                        label: 'Required (kg/ha)',
                        data: [
                            {{ result.comprehensive_nutrient_requirements.primary_nutrients.N.needed }},
                            {{ result.comprehensive_nutrient_requirements.primary_nutrients.P2O5.needed }},
                            {{ result.comprehensive_nutrient_requirements.primary_nutrients.K2O.needed }},
                            {{ result.comprehensive_nutrient_requirements.secondary_nutrients.Ca.needed }},
                            {{ result.comprehensive_nutrient_requirements.secondary_nutrients.Mg.needed }},
                            {{ result.comprehensive_nutrient_requirements.secondary_nutrients.S.needed }}
                        ],
                        backgroundColor: [
                            '#3B82F6', '#8B5CF6', '#10B981',
                            '#F59E0B', '#EF4444', '#6B7280'
                        ],
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return Math.round(context.parsed.y * 10) / 10 + ' kg/ha needed';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'kg/ha'
                            }
                        }
                    },
                    animation: {
                        onComplete: function() {
                            const ctx = this.chart.ctx;
                            ctx.font = '11px Inter, sans-serif';
                            ctx.fillStyle = '#374151';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            
                            this.data.datasets.forEach((dataset, i) => {
                                const meta = this.getDatasetMeta(i);
                                meta.data.forEach((bar, index) => {
                                    const data = Math.round(dataset.data[index] * 10) / 10;
                                    if (data > 0) {
                                        ctx.fillText(data + ' kg', bar.x, bar.y - 5);
                                    }
                                });
                            });
                        }
                    }
                }
            });

            // Coverage Efficiency Chart
            new Chart(document.getElementById('coverageChart'), {
                type: 'radar',
                data: {
                    labels: Object.keys({{ result.comprehensive_nutrient_balance.coverage_percentages|tojson }}),
                    datasets: [{
                        label: 'Coverage %',
                        data: Object.values({{ result.comprehensive_nutrient_balance.coverage_percentages|tojson }}),
                        backgroundColor: 'rgba(34, 197, 94, 0.2)',
                        borderColor: '#22C55E',
                        borderWidth: 2,
                        pointBackgroundColor: '#22C55E'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                stepSize: 20
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });

            // Lime Types Comparison Chart
            new Chart(document.getElementById('limeTypesChart'), {
                type: 'bar',
                data: {
                    labels: [
                        {% for lime_id, lime_data in result.lime_comparison.lime_types.items() %}
                        '{{ lime_data.name.split("(")[0].strip() }}'{% if not loop.last %},{% endif %}
                        {% endfor %}
                    ],
                    datasets: [{
                        label: 't/ha needed',
                        data: [
                            {% for lime_id, lime_data in result.lime_comparison.lime_types.items() %}
                            {{ lime_data.t_ha }}{% if not loop.last %},{% endif %}
                            {% endfor %}
                        ],
                        backgroundColor: [
                            {% for lime_id, lime_data in result.lime_comparison.lime_types.items() %}
                            {% if lime_id == result.enhanced_lime_calculation.lime_type %}'#EAB308'{% else %}'#94A3B8'{% endif %}{% if not loop.last %},{% endif %}
                            {% endfor %}
                        ],
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.parsed.y + ' t/ha needed';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 't/ha'
                            }
                        }
                    },
                    animation: {
                        onComplete: function() {
                            const ctx = this.chart.ctx;
                            ctx.font = '12px Inter, sans-serif';
                            ctx.fillStyle = '#374151';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            
                            this.data.datasets.forEach((dataset, i) => {
                                const meta = this.getDatasetMeta(i);
                                meta.data.forEach((bar, index) => {
                                    const data = dataset.data[index];
                                    ctx.fillText(data + ' t/ha', bar.x, bar.y - 5);
                                });
                            });
                        }
                    }
                }
            });

            // Cationic Ratios Chart
            new Chart(document.getElementById('cationicRatiosChart'), {
                type: 'bar',
                data: {
                    labels: ['Ca/Mg', 'Ca/K', 'Mg/K'],
                    datasets: [{
                        label: 'Current Ratio',
                        data: [{{ result.ca_mg_ratio }}, {{ result.ca_k_ratio }}, {{ result.mg_k_ratio }}],
                        backgroundColor: ['#3B82F6', '#10B981', '#8B5CF6'],
                        borderRadius: 4
                    }, {
                        label: 'Optimal Range (min)',
                        data: [2, 5, 2.5],
                        backgroundColor: 'rgba(34, 197, 94, 0.3)',
                        borderColor: '#22C55E',
                        borderWidth: 2,
                        type: 'line'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + Math.round(context.parsed.y * 100) / 100;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Ratio'
                            }
                        }
                    },
                    animation: {
                        onComplete: function() {
                            const ctx = this.chart.ctx;
                            ctx.font = '12px Inter, sans-serif';
                            ctx.fillStyle = '#374151';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            
                            // Only show data labels for the bar dataset (index 0)
                            const dataset = this.data.datasets[0];
                            const meta = this.getDatasetMeta(0);
                            meta.data.forEach((bar, index) => {
                                const data = Math.round(dataset.data[index] * 100) / 100;
                                ctx.fillText(data, bar.x, bar.y - 5);
                            });
                        }
                    }
                }
            });

            // Physical Properties Chart
            new Chart(document.getElementById('physicalPropertiesChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Solids', 'Pore Space'],
                    datasets: [{
                        data: [{{ 100 - result.calculated_porosity }}, {{ result.calculated_porosity }}],
                        backgroundColor: ['#8B5CF6', '#22C55E'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });

            // Cost Distribution Chart
            new Chart(document.getElementById('costDistributionChart'), {
                type: 'pie',
                data: {
                    labels: ['Lime', 'Fertilizers'],
                    datasets: [{
                        data: [
                            {{ result.detailed_cost_breakdown.lime_cost_per_ha }},
                            {{ result.detailed_cost_breakdown.comprehensive_fertilizer_cost_per_ha }}
                        ],
                        backgroundColor: ['#EAB308', '#3B82F6'],
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        });

        // Print styles
        const printStyles = `
            @media print {
                .no-print { display: none !important; }
                body { background: white !important; }
                .shadow-lg, .shadow-xl { box-shadow: none !important; }
                .bg-gradient-to-r, .bg-gradient-to-br { background: white !important; }
            }
        `;
        const styleSheet = document.createElement("style");
        styleSheet.innerText = printStyles;
        document.head.appendChild(styleSheet);
    </script>

    <style>
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Smooth transitions */
        * {
            transition: all 0.3s ease;
        }

        /* Gradient animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }

        /* Chart containers */
        canvas {
            max-height: 400px;
        }

        /* Card hover effects */
        .hover\:scale-105:hover {
            transform: scale(1.05);
        }

        /* Table hover effects */
        tbody tr:hover {
            background-color: #f9fafb;
        }
    </style>
    
    
</body>
</html>
'''
# ♻️ COMPOST CALCULATOR TEMPLATE  
COMPOST_CALCULATOR_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Compost Calculator - SoilsFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-green-50 min-h-screen">
    <!-- Enhanced Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
     <div class="flex items-center space-x-3">
         <a href="{{ url_for('index') }}">
             <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
         </a>
     </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" 
                       class="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors">
                        <i class="fas fa-arrow-left mr-2"></i>
                        Dashboard
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="relative overflow-hidden">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="mb-6">
                    <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full mb-4">
                        <i class="fas fa-recycle text-white text-2xl"></i>
                    </div>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-green-600 via-emerald-600 to-green-800 bg-clip-text text-transparent mb-4">
                    Scientific Compost Calculator
                </h1>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto mb-6">
                    Optimize organic matter decomposition with precision C:N ratio calculations
                </p>
                <div class="flex flex-wrap justify-center gap-4 text-sm">
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800">
                        <i class="fas fa-atom mr-2"></i>
                        Carbon-Nitrogen Balance
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800">
                        <i class="fas fa-microscope mr-2"></i>
                        Quality Prediction
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-12 -mt-8">
        
        <!-- Main Calculator Form -->
        <form method="POST" id="compost-form" class="space-y-8">
            
            <!-- Basic Parameters -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-green-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-info-circle text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Recipe Parameters</h3>
                            <p class="text-sm text-gray-600">Define your compost composition</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Recipe Name *
                                <i class="fas fa-tag text-green-500 ml-1"></i>
                            </label>
                            <input type="text" name="recipe_name" required
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors"
                                   placeholder="My Compost Recipe">
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Target Volume (kg) *
                                <i class="fas fa-weight text-blue-500 ml-1"></i>
                            </label>
                            <input type="number" name="target_volume" min="1" value="100" required
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 transition-colors">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Material Selection -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-orange-50 to-yellow-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center">
                        <div class="bg-orange-500 rounded-lg p-2 mr-3">
                            <i class="fas fa-leaf text-white"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-900">Organic Material Selection</h3>
                            <p class="text-sm text-gray-600">Balance carbon-rich and nitrogen-rich materials</p>
                        </div>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {% for material, data in materials.items() %}
                        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
                            <div class="flex justify-between items-start mb-3">
                                <div class="flex-1">
                                    <label class="block text-sm font-medium text-gray-700">
                                        {{ material.replace('_', ' ').title() }}
                                    </label>
                                    <div class="text-xs text-gray-600 mb-2">{{ data.description }}</div>
                                    <div class="flex space-x-2 text-xs">
                                        <span class="inline-flex items-center px-2 py-1 bg-amber-100 text-amber-800 rounded">
                                            C: {{ data.carbon }}%
                                        </span>
                                        <span class="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 rounded">
                                            N: {{ data.nitrogen }}%
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div class="flex items-center space-x-2">
                                <input type="number" name="material_{{ material }}" 
                                       min="0" max="100" step="1" 
                                       class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500"
                                       placeholder="0">
                                <span class="text-sm text-gray-600">%</span>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>

            <!-- Submit Button -->
            <div class="text-center">
                <button type="submit"
                        class="inline-flex items-center px-12 py-4 bg-gradient-to-r from-green-600 via-emerald-600 to-green-700 text-white font-semibold text-lg rounded-xl shadow-lg hover:from-green-700 hover:via-emerald-700 hover:to-green-800 focus:outline-none focus:ring-4 focus:ring-green-300 transition-all duration-300 transform hover:scale-105">
                    <i class="fas fa-flask mr-3"></i>
                    Calculate Recipe
                    <i class="fas fa-arrow-right ml-3"></i>
                </button>
            </div>
        </form>
    </div>

    <style>
        input:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(34, 197, 94, 0.15);
        }
        
        .transition-all {
            transition: all 0.3s ease;
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }
        
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
    </style>
</body>
</html>
'''

COMPOST_RESULT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compost Analysis Results - SoilsFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body class="bg-gradient-to-br from-slate-50 to-green-50 min-h-screen">
    <!-- Enhanced Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
     <div class="flex items-center space-x-3">
         <a href="{{ url_for('index') }}">
             <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
         </a>
     </div>
     <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" 
                       class="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors">
                        <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
                    </a>
                    <a href="{{ url_for('compost_calculator') }}" 
{{ ... }}
                       class="inline-flex items-center px-4 py-2 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>New Recipe
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="bg-gradient-to-r from-green-600 via-emerald-600 to-green-800 text-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4">
                    <i class="fas fa-chart-line text-white text-2xl"></i>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold mb-4">
                    Compost Recipe Analysis
                </h1>
                <p class="text-xl text-green-100 mb-6">
                    Scientific optimization results for your organic matter formulation
                </p>
                <div class="flex flex-wrap justify-center gap-4">
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-flask mr-2"></i>
                        C:N Ratio: {{ result.c_n_ratio }}:1
                    </span>
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-star mr-2"></i>
                        Quality Score: {{ result.quality_score }}%
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 -mt-8">
        
        <!-- Overall Performance Score -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-gray-50 to-green-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-trophy mr-3 text-yellow-500"></i>
                        Recipe Performance Analysis
                    </h3>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <!-- Quality Score -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-green-100 to-green-200 rounded-full">
                                <span class="text-xl font-bold text-green-600">{{ result.quality_score }}</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Quality Score</h4>
                            <p class="text-sm text-gray-600">
                                {% if result.quality_score >= 90 %}🌟 Excellent
                                {% elif result.quality_score >= 70 %}👍 Good
                                {% else %}⚠️ Needs Improvement{% endif %}
                            </p>
                        </div>

                        <!-- C:N Ratio -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-200 rounded-full">
                                <span class="text-xl font-bold text-blue-600">{{ result.c_n_ratio }}:1</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">C:N Ratio</h4>
                            <p class="text-sm text-gray-600">
                                {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}✅ Optimal
                                {% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}⚡ Good
                                {% else %}⚠️ Adjust{% endif %}
                            </p>
                        </div>

                        <!-- Maturation Time -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-purple-100 to-purple-200 rounded-full">
                                <span class="text-xl font-bold text-purple-600">{{ result.maturation_time }}</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Maturation Time</h4>
                            <p class="text-sm text-gray-600">Weeks to completion</p>
                        </div>

                        <!-- Expected Yield -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-orange-100 to-orange-200 rounded-full">
                                <span class="text-xl font-bold text-orange-600">{{ "%.0f"|format(result.estimated_yield) }}</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Expected Yield</h4>
                            <p class="text-sm text-gray-600">kg finished compost</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Recipe Composition -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mb-8">
            <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                    <i class="fas fa-list mr-2 text-green-500"></i>
                    Recipe Composition
                </h3>
            </div>
            <div class="p-6">
                <div class="space-y-4">
                    {% for material, weight in result.recipe.items() %}
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-lg">
                        <span class="capitalize font-medium text-gray-700">{{ material.replace('_', ' ') }}</span>
                        <div class="text-right">
                            <div class="text-lg font-bold text-gray-900">{{ "%.1f"|format(weight) }} kg</div>
                            <div class="text-sm text-gray-500">{{ "%.1f"|format((weight/result.total_weight)*100) }}%</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Recommendations -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mb-8">
            <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                    <i class="fas fa-lightbulb mr-2 text-blue-500"></i>
                    Recommendations
                </h3>
            </div>
            <div class="p-6">
                <div class="space-y-4">
                    {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}
                    <div class="flex items-start p-4 bg-green-50 border border-green-200 rounded-lg">
                        <i class="fas fa-check-circle text-green-500 mr-3 mt-1"></i>
                        <div>
                            <p class="font-medium text-green-800">Excellent C:N Balance</p>
                            <p class="text-sm text-green-700">Your recipe provides optimal microbial nutrition for rapid decomposition.</p>
                        </div>
                    </div>
                    {% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}
                    <div class="flex items-start p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                        <i class="fas fa-exclamation-triangle text-yellow-500 mr-3 mt-1"></i>
                        <div>
                            <p class="font-medium text-yellow-800">Good C:N Balance</p>
                            <p class="text-sm text-yellow-700">Recipe will compost well, minor adjustment could improve efficiency.</p>
                        </div>
                    </div>
                    {% else %}
                    <div class="flex items-start p-4 bg-red-50 border border-red-200 rounded-lg">
                        <i class="fas fa-times-circle text-red-500 mr-3 mt-1"></i>
                        <div>
                            <p class="font-medium text-red-800">C:N Ratio Needs Adjustment</p>
                            <p class="text-sm text-red-700">
                                {% if result.c_n_ratio > 40 %}Add more nitrogen-rich materials (greens).
                                {% else %}Add more carbon-rich materials (browns).{% endif %}
                            </p>
                        </div>
                    </div>
                    {% endif %}
                    
                    <div class="flex items-start p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <i class="fas fa-thermometer-half text-blue-500 mr-3 mt-1"></i>
                        <div>
                            <p class="font-medium text-blue-800">Monitor Temperature</p>
                            <p class="text-sm text-blue-700">Maintain 55-70°C during active composting phase.</p>
                        </div>
                    </div>
                    
                    <div class="flex items-start p-4 bg-purple-50 border border-purple-200 rounded-lg">
                        <i class="fas fa-sync-alt text-purple-500 mr-3 mt-1"></i>
                        <div>
                            <p class="font-medium text-purple-800">Turn Regularly</p>
                            <p class="text-sm text-purple-700">Turn pile weekly for proper aeration and decomposition.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="text-center space-x-4">
            <a href="{{ url_for('compost_calculator') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-plus mr-2"></i>Create New Recipe
            </a>
            <a href="{{ url_for('dashboard') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
            </a>
        </div>
    </div>
</body>
</html>
'''



# ENHANCED COMPOST RESULT TEMPLATE


'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compost Analysis Results - SoilsFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-green-50 min-h-screen">
    <!-- Enhanced Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-3">
                    <div class="bg-gradient-to-r from-green-500 to-emerald-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
                    </span>
                </div>
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('dashboard') }}" 
                       class="inline-flex items-center px-4 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors">
                        <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
                    </a>
                    <a href="{{ url_for('compost_calculator') }}" 
                       class="inline-flex items-center px-4 py-2 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 transition-colors">
                        <i class="fas fa-plus mr-2"></i>New Recipe
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="bg-gradient-to-r from-green-600 via-emerald-600 to-green-800 text-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div class="text-center">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4">
                    <i class="fas fa-chart-line text-white text-2xl"></i>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold mb-4">
                    Compost Recipe Analysis
                </h1>
                <p class="text-xl text-green-100 mb-6">
                    Scientific optimization results for your organic matter formulation
                </p>
                <div class="flex flex-wrap justify-center gap-4">
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-flask mr-2"></i>
                        C:N Ratio: {{ result.c_n_ratio }}:1
                    </span>
                    <span class="inline-flex items-center px-4 py-2 bg-white/20 rounded-full text-sm">
                        <i class="fas fa-star mr-2"></i>
                        Quality Score: {{ result.quality_score }}%
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 -mt-8">
        
        <!-- Overall Performance Score -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-gray-50 to-green-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-trophy mr-3 text-yellow-500"></i>
                        Recipe Performance Analysis
                    </h3>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <!-- Quality Score -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4">
                                <canvas id="qualityChart" width="96" height="96"></canvas>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-xl font-bold {% if result.quality_score >= 90 %}text-green-600{% elif result.quality_score >= 70 %}text-yellow-600{% else %}text-red-600{% endif %}">
                                        {{ result.quality_score }}
                                    </span>
                                </div>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Quality Score</h4>
                            <p class="text-sm text-gray-600">
                                {% if result.quality_score >= 90 %}🌟 Excellent
                                {% elif result.quality_score >= 70 %}👍 Good
                                {% else %}⚠️ Needs Improvement{% endif %}
                            </p>
                        </div>

                        <!-- C:N Ratio -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-blue-100 to-blue-200 rounded-full">
                                <span class="text-xl font-bold text-blue-600">{{ result.c_n_ratio }}:1</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">C:N Ratio</h4>
                            <p class="text-sm text-gray-600">
                                {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}✅ Optimal
                                {% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}⚡ Good
                                {% else %}⚠️ Adjust{% endif %}
                            </p>
                        </div>

                        <!-- Maturation Time -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-purple-100 to-purple-200 rounded-full">
                                <span class="text-xl font-bold text-purple-600">{{ result.maturation_time }}</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Maturation Time</h4>
                            <p class="text-sm text-gray-600">Weeks to completion</p>
                        </div>

                        <!-- Expected Yield -->
                        <div class="text-center">
                            <div class="relative w-24 h-24 mx-auto mb-4 flex items-center justify-center bg-gradient-to-br from-orange-100 to-orange-200 rounded-full">
                                <span class="text-xl font-bold text-orange-600">{{ "%.0f"|format(result.estimated_yield) }}</span>
                            </div>
                            <h4 class="text-lg font-semibold text-gray-900">Expected Yield</h4>
                            <p class="text-sm text-gray-600">kg finished compost</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Detailed Analysis -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Recipe Composition -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-list mr-2 text-green-500"></i>
                        Recipe Composition
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-4 mb-6">
                        {% for material, weight in result.recipe.items() %}
                        <div class="flex justify-between items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                            <div class="flex items-center">
                                <div class="w-4 h-4 rounded-full mr-3" style="background-color: {{ ['#22C55E', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#6B7280'][loop.index0 % 6] }}"></div>
                                <span class="capitalize font-medium text-gray-700">{{ material.replace('_', ' ') }}</span>
                            </div>
                            <div class="text-right">
                                <div class="text-lg font-bold text-gray-900">{{ "%.1f"|format(weight) }} kg</div>
                                <div class="text-sm text-gray-500">{{ "%.1f"|format((weight/result.total_weight)*100) }}%</div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                    
                    <!-- Material Distribution Chart -->
                    <div class="relative h-64">
                        <canvas id="materialChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Scientific Analysis -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-microscope mr-2 text-blue-500"></i>
                        Scientific Analysis
                    </h3>
                </div>
                <div class="p-6">
                    <!-- Key Metrics -->
                    <div class="grid grid-cols-2 gap-4 mb-6">
                        <div class="text-center p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200">
                            <div class="text-2xl font-bold text-green-600 mb-1">{{ "%.1f"|format(result.total_weight) }}</div>
                            <div class="text-sm text-gray-600 font-medium">Total Input</div>
                            <div class="text-xs text-gray-500">kg wet weight</div>
                        </div>
                        <div class="text-center p-4 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-lg border border-blue-200">
                            <div class="text-2xl font-bold text-blue-600 mb-1">30%</div>
                            <div class="text-sm text-gray-600 font-medium">Volume Reduction</div>
                            <div class="text-xs text-gray-500">typical shrinkage</div>
                        </div>
                    </div>
                    
                    <!-- C:N Balance Visualization -->
                    <div class="mb-6">
                        <h4 class="text-md font-semibold text-gray-900 mb-3">Carbon-Nitrogen Balance</h4>
                        <div class="relative h-48">
                            <canvas id="cnBalanceChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Process Timeline -->
                    <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <h5 class="font-semibold text-yellow-800 mb-3 flex items-center">
                            <i class="fas fa-clock mr-2"></i>
                            Decomposition Timeline
                        </h5>
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between">
                                <span class="text-yellow-700">🌡️ Thermophilic Phase:</span>
                                <span class="font-medium text-yellow-800">Weeks 1-4 (55-70°C)</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-yellow-700">🔄 Mesophilic Phase:</span>
                                <span class="font-medium text-yellow-800">Weeks 4-8 (40-55°C)</span>
                            </div>
                            <div class="flex justify-between">
                                <span class="text-yellow-700">✅ Maturation Phase:</span>
                                <span class="font-medium text-yellow-800">Weeks 8-{{ result.maturation_time }} (25-40°C)</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Process Summary -->
        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden mb-8">
            <div class="bg-gradient-to-r from-purple-50 to-violet-50 px-6 py-4 border-b border-gray-200">
                <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                    <i class="fas fa-cogs mr-3 text-purple-500"></i>
                    Process Summary & Recommendations
                </h3>
            </div>
            <div class="p-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <!-- Process Parameters -->
                    <div>
                        <h4 class="text-lg font-semibold text-gray-900 mb-4">Optimal Process Parameters</h4>
                        <div class="space-y-4">
                            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span class="font-medium text-gray-700">Temperature Range</span>
                                <span class="text-lg font-bold text-red-600">55-70°C</span>
                            </div>
                            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span class="font-medium text-gray-700">Moisture Content</span>
                                <span class="text-lg font-bold text-blue-600">40-60%</span>
                            </div>
                            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span class="font-medium text-gray-700">Turning Frequency</span>
                                <span class="text-lg font-bold text-green-600">Weekly</span>
                            </div>
                            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                                <span class="font-medium text-gray-700">Pile Size</span>
                                <span class="text-lg font-bold text-purple-600">1m³ minimum</span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Scientific Recommendations -->
                    <div>
                        <h4 class="text-lg font-semibold text-gray-900 mb-4">Scientific Recommendations</h4>
                        <div class="space-y-3">
                            {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}
                            <div class="flex items-start p-3 bg-green-50 border border-green-200 rounded-lg">
                                <i class="fas fa-check-circle text-green-500 mr-3 mt-1"></i>
                                <div>
                                    <p class="font-medium text-green-800">Excellent C:N Balance</p>
                                    <p class="text-sm text-green-700">Your recipe provides optimal microbial nutrition for rapid decomposition.</p>
                                </div>
                            </div>
                            {% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}
                            <div class="flex items-start p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                                <i class="fas fa-exclamation-triangle text-yellow-500 mr-3 mt-1"></i>
                                <div>
                                    <p class="font-medium text-yellow-800">Good C:N Balance</p>
                                    <p class="text-sm text-yellow-700">Recipe will compost well, minor adjustment could improve efficiency.</p>
                                </div>
                            </div>
                            {% else %}
                            <div class="flex items-start p-3 bg-red-50 border border-red-200 rounded-lg">
                                <i class="fas fa-times-circle text-red-500 mr-3 mt-1"></i>
                                <div>
                                    <p class="font-medium text-red-800">C:N Ratio Needs Adjustment</p>
                                    <p class="text-sm text-red-700">
                                        {% if result.c_n_ratio > 40 %}Add more nitrogen-rich materials (greens).
                                        {% else %}Add more carbon-rich materials (browns).{% endif %}
                                    </p>
                                </div>
                            </div>
                            {% endif %}
                            
                            <div class="flex items-start p-3 bg-blue-50 border border-blue-200 rounded-lg">
                                <i class="fas fa-thermometer-half text-blue-500 mr-3 mt-1"></i>
                                <div>
                                    <p class="font-medium text-blue-800">Monitor Temperature</p>
                                    <p class="text-sm text-blue-700">Use a compost thermometer to track decomposition progress.</p>
                                </div>
                            </div>
                            
                            <div class="flex items-start p-3 bg-purple-50 border border-purple-200 rounded-lg">
                                <i class="fas fa-sync-alt text-purple-500 mr-3 mt-1"></i>
                                <div>
                                    <p class="font-medium text-purple-800">Aeration Strategy</p>
                                    <p class="text-sm text-purple-700">Turn pile weekly during active phase for oxygen supply.</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="text-center space-x-4 mb-8">
            <a href="{{ url_for('compost_calculator') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-plus mr-2"></i>Create New Recipe
            </a>
            <a href="{{ url_for('dashboard') }}" 
               class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-tachometer-alt mr-2"></i>Dashboard
            </a>
            <button onclick="window.print()" 
                    class="inline-flex items-center px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105 shadow-lg">
                <i class="fas fa-print mr-2"></i>Print Recipe
            </button>
        </div>
    </div>

    <script>
        // Chart.js configuration
        Chart.defaults.font.family = 'Inter, sans-serif';
        Chart.defaults.color = '#6B7280';

        document.addEventListener('DOMContentLoaded', function() {
            // Quality Score Chart
            new Chart(document.getElementById('qualityChart'), {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [{{ result.quality_score }}, {{ 100 - result.quality_score }}],
                        backgroundColor: [
                            {% if result.quality_score >= 90 %}'#22C55E'{% elif result.quality_score >= 70 %}'#EAB308'{% else %}'#EF4444'{% endif %},
                            '#E5E7EB'
                        ],
                        borderWidth: 0,
                        cutout: '70%'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });

            // Material Distribution Chart
            new Chart(document.getElementById('materialChart'), {
                type: 'doughnut',
                data: {
                    labels: [{% for material in result.recipe.keys() %}'{{ material.replace("_", " ").title() }}'{% if not loop.last %},{% endif %}{% endfor %}],
                    datasets: [{
                        data: [{% for weight in result.recipe.values() %}{{ weight }}{% if not loop.last %},{% endif %}{% endfor %}],
                        backgroundColor: ['#22C55E', '#3B82F6', '#8B5CF6', '#F59E0B', '#EF4444', '#6B7280', '#EC4899', '#10B981'],
                        borderWidth: 2,
                        borderColor: '#FFFFFF'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value.toFixed(1)} kg (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });

            // C:N Balance Chart
            new Chart(document.getElementById('cnBalanceChart'), {
                type: 'bar',
                data: {
                    labels: ['Current Recipe', 'Optimal Range (Min)', 'Optimal Range (Max)'],
                    datasets: [{
                        label: 'C:N Ratio',
                        data: [{{ result.c_n_ratio }}, 25, 35],
                        backgroundColor: [
                            {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}'#22C55E'{% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}'#EAB308'{% else %}'#EF4444'{% endif %},
                            'rgba(34, 197, 94, 0.3)',
                            'rgba(34, 197, 94, 0.3)'
                        ],
                        borderColor: [
                            {% if result.c_n_ratio >= 25 and result.c_n_ratio <= 35 %}'#16A34A'{% elif result.c_n_ratio >= 20 and result.c_n_ratio <= 40 %}'#CA8A04'{% else %}'#DC2626'{% endif %},
                            '#22C55E',
                            '#22C55E'
                        ],
                        borderWidth: 2,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return 'C:N Ratio: ' + context.parsed.y.toFixed(1) + ':1';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'C:N Ratio'
                            }
                        }
                    },
                    animation: {
                        onComplete: function() {
                            const ctx = this.chart.ctx;
                            ctx.font = '12px Inter, sans-serif';
                            ctx.fillStyle = '#374151';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'bottom';
                            
                            this.data.datasets.forEach((dataset, i) => {
                                const meta = this.getDatasetMeta(i);
                                meta.data.forEach((bar, index) => {
                                    const data = dataset.data[index];
                                    if (index === 0) { // Only show label for current recipe
                                        ctx.fillText(data.toFixed(1) + ':1', bar.x, bar.y - 5);
                                    }
                                });
                            });
                        }
                    }
                }
            });
        });

        // Print styles
        const printStyles = `
            @media print {
                .no-print { display: none !important; }
                body { background: white !important; }
                .shadow-lg, .shadow-xl { box-shadow: none !important; }
                .bg-gradient-to-r, .bg-gradient-to-br { background: white !important; }
            }
        `;
        const styleSheet = document.createElement("style");
        styleSheet.innerText = printStyles;
        document.head.appendChild(styleSheet);
    </script>

    <style>
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* Smooth transitions */
        * {
            transition: all 0.3s ease;
        }

        /* Gradient animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }

        /* Chart containers */
        canvas {
            max-height: 400px;
        }

        /* Card hover effects */
        .hover\:scale-105:hover {
            transform: scale(1.05);
        }
    </style>
</body>
</html>
'''
# 💰 PRICING TEMPLATE
PRICING_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pricing - SoilFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'soil-green': {
                            50: '#f0fdf4',
                            100: '#dcfce7',
                            500: '#22c55e',
                            600: '#16a34a',
                            700: '#15803d',
                            800: '#166534'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <!-- Navigation -->
    <nav class="bg-white/80 backdrop-blur-lg shadow-lg border-b border-slate-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center py-4">
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    {% if session.user_id %}
                        <a href="{{ url_for('dashboard') }}" 
                           class="text-slate-600 hover:text-soil-green-600 font-medium transition-colors duration-200">
                            Dashboard
                        </a>
                    {% else %}
                        <a href="{{ url_for('login') }}" 
                           class="text-slate-600 hover:text-soil-green-600 font-medium transition-colors duration-200">
                            Login
                        </a>
                        <a href="{{ url_for('register') }}" 
                           class="bg-gradient-to-r from-soil-green-600 to-soil-green-700 text-white px-6 py-2 rounded-xl hover:from-soil-green-700 hover:to-soil-green-800 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-medium">
                            Sign Up
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <!-- Header Section -->
        <div class="text-center mb-16">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-amber-400 to-orange-500 rounded-2xl mb-6 shadow-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"></path>
                </svg>
            </div>
            <h1 class="text-4xl md:text-5xl font-bold text-slate-900 mb-4">Choose Your Plan</h1>
            <p class="text-xl text-slate-600 max-w-2xl mx-auto">Select the perfect plan for your farming needs and start optimizing your soil health today</p>
        </div>

        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-8 space-y-3">
                    {% for category, message in messages %}
                        <div class="p-4 rounded-xl border-l-4 {% if category == 'error' %}bg-red-50 border-red-400 text-red-800{% else %}bg-green-50 border-green-400 text-green-800{% endif %} shadow-sm">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    {% if category == 'error' %}
                                        <svg class="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                                        </svg>
                                    {% else %}
                                        <svg class="h-5 w-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                        </svg>
                                    {% endif %}
                                </div>
                                <div class="ml-3">
                                    <p class="text-sm font-medium">{{ message }}</p>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <!-- Pricing Cards -->
        <div class="grid md:grid-cols-2 gap-8 mb-16">
            {% for plan_id, plan in plans.items() %}
            <div class="relative bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden {% if plan_id == 'pro' %}ring-2 ring-soil-green-500 transform scale-105{% endif %} transition-all duration-300 hover:shadow-2xl">
                {% if plan_id == 'pro' %}
                    <div class="absolute top-0 left-0 right-0 bg-gradient-to-r from-soil-green-500 to-soil-green-600 text-white text-center py-2 text-sm font-semibold">
                        ⭐ RECOMMENDED
                    </div>
                {% endif %}
                
                <div class="p-8 {% if plan_id == 'pro' %}pt-12{% endif %}">
                    <div class="text-center mb-8">
                        <div class="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br {% if plan_id == 'pro' %}from-soil-green-500 to-soil-green-600{% else %}from-blue-500 to-blue-600{% endif %} rounded-xl mb-4">
                            {% if plan_id == 'pro' %}
                                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                </svg>
                            {% else %}
                                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path>
                                </svg>
                            {% endif %}
                        </div>
                        <h3 class="text-2xl font-bold text-slate-900 mb-2">{{ plan.name }}</h3>
                        <div class="mb-4">
                            {% if plan.price == 0 %}
                                <span class="text-5xl font-bold text-soil-green-600">FREE</span>
                            {% else %}
                                <span class="text-5xl font-bold text-slate-900">${{ "%.0f"|format(plan.price) }}</span>
                                <span class="text-slate-600 text-lg">/month</span>
                            {% endif %}
                        </div>
                        <div class="inline-flex items-center px-4 py-2 bg-slate-100 rounded-full">
                            <svg class="w-4 h-4 text-slate-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"></path>
                            </svg>
                            <span class="text-sm text-slate-600 font-medium">
                                {% if plan.analyses_limit == -1 %}
                                    Unlimited analyses
                                {% else %}
                                    {{ plan.analyses_limit }} analyses per month
                                {% endif %}
                            </span>
                        </div>
                    </div>
                    
                    <ul class="space-y-4 mb-8">
                        {% for feature in plan.features %}
                        <li class="flex items-center">
                            <div class="flex-shrink-0 w-5 h-5 bg-soil-green-100 rounded-full flex items-center justify-center mr-3">
                                <svg class="w-3 h-3 text-soil-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
                                </svg>
                            </div>
                            <span class="text-slate-700">{{ feature }}</span>
                        </li>
                        {% endfor %}
                    </ul>
                    
                    <div class="text-center">
                        {% if session.user_id %}
                            {% if session.plan_type == plan_id %}
                                <div class="w-full bg-slate-100 text-slate-600 py-3 px-4 rounded-xl border-2 border-slate-200 font-semibold flex items-center justify-center">
                                    <svg class="w-5 h-5 text-soil-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                    Current Plan
                                </div>
                            {% else %}
                                {% if plan_id == 'pro' %}
                                    <!-- Payment Options -->
                                    <div class="space-y-3">
                                        <!-- Stripe Credit/Debit Card Button -->
                                        <a href="{{ url_for('stripe_checkout') }}" 
                                           class="block w-full bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold flex items-center justify-center space-x-3">
                                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                                            </svg>
                                            <span>Pay $5.00 with Card</span>
                                        </a>
                                        
                                        <!-- PayPal Payment Button -->
                                        <a href="{{ url_for('create_paypal_payment') }}" 
                                           class="block w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white py-4 px-6 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold flex items-center justify-center space-x-3">
                                            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
                                                <path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a9.124 9.124 0 0 1-.414 2.06c-.93 4.68-4.098 6.37-7.75 6.37h-1.48c-.524 0-.968.382-1.05.9l-.72 4.56-.2 1.28c-.05.32.18.61.51.61h3.04c.46 0 .85-.34.92-.79l.04-.2.76-4.83.05-.27c.07-.45.46-.79.92-.79h.58c3.76 0 6.7-1.53 7.56-5.95.36-1.85.17-3.4-.73-4.56-.27-.35-.6-.65-.98-.9z"/>
                                            </svg>
                                            <span>Pay $5.00 with PayPal</span>
                                        </a>
                                        
                                        <div class="text-center">
                                            <p class="text-xs text-slate-500">Secure payment • SSL Encrypted</p>
                                        </div>
                                    </div>
                                {% endif %}
                            {% endif %}
                        {% else %}
                            <a href="{{ url_for('register') }}" 
                               class="block w-full bg-gradient-to-r {% if plan_id == 'pro' %}from-soil-green-600 to-soil-green-700 hover:from-soil-green-700 hover:to-soil-green-800{% else %}from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800{% endif %} text-white py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold">
                                Get Started {% if plan.price == 0 %}Free{% endif %}
                            </a>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- FAQ Section -->
        <div class="bg-white rounded-2xl shadow-xl border border-slate-200 p-8 lg:p-12">
            <div class="text-center mb-10">
                <div class="inline-flex items-center justify-center w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl mb-4">
                    <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <h2 class="text-3xl font-bold text-slate-900 mb-2">Frequently Asked Questions</h2>
                <p class="text-slate-600">Everything you need to know about our pricing plans</p>
            </div>
            
            <div class="grid md:grid-cols-2 gap-8">
                <div class="space-y-6">
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-2 flex items-center">
                            <div class="w-6 h-6 bg-soil-green-100 rounded-full flex items-center justify-center mr-3">
                                <span class="text-soil-green-600 text-sm font-bold">?</span>
                            </div>
                            Is the free plan really free?
                        </h3>
                        <p class="text-slate-600 ml-9">Yes! No credit card required. Includes professional lime calculations and basic soil analysis tools.</p>
                    </div>
                    
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-2 flex items-center">
                            <div class="w-6 h-6 bg-soil-green-100 rounded-full flex items-center justify-center mr-3">
                                <span class="text-soil-green-600 text-sm font-bold">?</span>
                            </div>
                            Can I upgrade anytime?
                        </h3>
                        <p class="text-slate-600 ml-9">Yes, upgrade instantly with one click. Your new features will be available immediately.</p>
                    </div>
                </div>
                
                <div class="space-y-6">
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-2 flex items-center">
                            <div class="w-6 h-6 bg-soil-green-100 rounded-full flex items-center justify-center mr-3">
                                <span class="text-soil-green-600 text-sm font-bold">?</span>
                            </div>
                            How accurate are the lime calculations?
                        </h3>
                        <p class="text-slate-600 ml-9">Based on scientific Exchangeable Acidity method with 95% field accuracy, trusted by agricultural professionals.</p>
                    </div>
                    
                    <div>
                        <h3 class="font-semibold text-slate-900 mb-2 flex items-center">
                            <div class="w-6 h-6 bg-soil-green-100 rounded-full flex items-center justify-center mr-3">
                                <span class="text-soil-green-600 text-sm font-bold">?</span>
                            </div>
                            What lime types are supported?
                        </h3>
                        <p class="text-slate-600 ml-9">5 types: CaCO₃, Dolomitic, Ca(OH)₂, CaO, and MgO with precise CCE calculations for optimal results.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Trust Section -->
        <div class="text-center mt-16">
            <div class="bg-gradient-to-r from-slate-50 to-slate-100 rounded-2xl p-8 border border-slate-200">
                <h3 class="text-lg font-semibold text-slate-900 mb-2">Trusted by Agricultural Professionals</h3>
                <p class="text-slate-600">Join thousands of farmers optimizing their soil health with SoilFert's scientific approach</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

# =====================================
# 📧 EMAIL CONFIGURATION FOR HOSTINGER (env-driven)
# =====================================
import os, re, smtplib, ssl
from datetime import datetime, timezone
from email.message import EmailMessage

# Read secrets from environment (optional for email functionality)
MAIL_SERVER   = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL", MAIL_USERNAME)

# (Optional) keep a copy in app.config if other parts of the app expect it
app.config.update(
    MAIL_SERVER=MAIL_SERVER,
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    ADMIN_EMAIL=ADMIN_EMAIL,
)

# =====================================
# 📧 EMAIL SENDER (UTF-8 + 465/587 fallback)
# =====================================
def _build_msg(name: str, email: str, subject: str, message: str) -> EmailMessage:
    """Create a UTF-8 email message safely (prevents header injection)."""
    subject = re.sub(r'[\r\n]+', ' ', subject).strip()[:150]
    now = datetime.now(timezone.utc)
    body = (
        "🌱 NEW CONTACT FORM SUBMISSION - SoilsFert\n"
        + "=" * 50 + "\n\n"
        "📝 CONTACT DETAILS:\n"
        f"   Name: {name}\n"
        f"   Email: {email}\n"
        f"   Subject: {subject}\n\n"
        "💬 MESSAGE:\n"
        f"{message}\n\n"
        "📅 SUBMISSION INFO:\n"
        f"   Date: {now.strftime('%Y-%m-%d')}\n"
        f"   Time: {now.strftime('%H:%M:%S %Z')}\n"
        "   Platform: SoilsFert Website Contact Form\n\n"
        + "=" * 50 + "\n"
        "🔄 TO REPLY: Simply reply to this email\n"
        "🌐 Website: https://soilsfert.com\n"
    )

    msg = EmailMessage()
    msg["From"] = MAIL_USERNAME
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = f"SoilsFert Contact Form: {subject}"
    msg["Reply-To"] = email
    msg.set_content(body, charset="utf-8")  # ✅ emojis/accents safe
    return msg

def send_contact_email(name: str, email: str, subject: str, message: str) -> bool:
    """Send contact form email using SMTP with SSL→STARTTLS fallback."""
    # Check if email credentials are configured
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        print("Email not configured - skipping email send")
        return False
        
    msg = _build_msg(name, email, subject, message)
    ctx = ssl.create_default_context()
    # Try SSL 465 first
    try:
        with smtplib.SMTP_SSL(MAIL_SERVER, 465, timeout=20, context=ctx) as s:
            s.login(MAIL_USERNAME, MAIL_PASSWORD)
            s.send_message(msg)
        print("Email sent via SSL:465")
        return True
    except Exception as e1:
        print("SSL:465 failed, trying STARTTLS:587 ->", repr(e1))
        # Fallback to STARTTLS 587
        try:
            with smtplib.SMTP(MAIL_SERVER, 587, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(MAIL_USERNAME, MAIL_PASSWORD)
                s.send_message(msg)
            print("Email sent via STARTTLS:587")
            return True
        except Exception as e2:
            print("Email send failed:", repr(e2))
            return False

# =====================================
# 🧪 EMAIL TEST FUNCTION (runs the same sender)
# =====================================
def test_email_configuration() -> bool:
    print("Testing email configuration...")
    print(f"SMTP Server: {MAIL_SERVER}")
    print(f"Username: {MAIL_USERNAME}")
    print(f"Admin Email: {ADMIN_EMAIL}")

    ok = send_contact_email(
        name="Test User",
        email="test@example.com",
        subject="Email Configuration Test",
        message="This is a test sent from the SoilsFert VPS using env vars and UTF-8."
    )
    if ok:
        print("Email configuration test PASSED!")
    else:
        print("Email configuration test FAILED. Check logs above.")
    return ok


# =====================================
# 📧 EMAIL TEST FUNCTION
# =====================================

def test_email_configuration():
    """Test email configuration"""
    print("Testing email configuration...")
    print(f"SMTP Server: {app.config['MAIL_SERVER']}")
    print(f"Port: {app.config['MAIL_PORT']}")
    print(f"Username: {app.config['MAIL_USERNAME']}")
    print(f"Admin Email: {app.config['ADMIN_EMAIL']}")
    
    # Send test email
    success = send_contact_email(
        name="Test User",
        email="test@example.com",
        subject="Email Configuration Test",
        message="This is a test message to verify that the email configuration is working correctly with Hostinger SMTP."
    )
    
    if success:
        print("Email configuration test PASSED!")
        print("Contact form emails will work correctly")
    else:
        print("Email configuration test FAILED!")
        print("Please check your credentials and try again")
    
    return success
# =====================================
# 📄 TERMS OF SERVICE ROUTE
# =====================================

@app.route('/terms')
def terms_of_service():
    """Terms of Service page"""
    return render_template_string(TERMS_OF_SERVICE_TEMPLATE)

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template_string(PRIVACY_POLICY_TEMPLATE)

# =====================================
# 📧 CONTACT ROUTES
# =====================================

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact form page"""
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validation
        errors = []
        if not name:
            errors.append('Name is required')
        if not email:
            errors.append('Email is required')
        elif '@' not in email:
            errors.append('Valid email is required')
        if not subject:
            errors.append('Subject is required')
        if not message:
            errors.append('Message is required')
        elif len(message) < 10:
            errors.append('Message must be at least 10 characters')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template_string(CONTACT_TEMPLATE, 
                                        name=name, email=email, subject=subject, message=message)
        
        # Save to database (optional - you can add a contacts table)
        try:
            execute_db('''
                INSERT INTO contacts (name, email, subject, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', [name, email, subject, message, datetime.now().isoformat()])
        except:
            pass  # Table might not exist, that's OK
        
        # Send email
        if send_contact_email(name, email, subject, message):
            flash('Thank you for your message! We\'ll get back to you soon.', 'success')
        else:
            flash('Message saved, but email delivery failed. We\'ll still respond to your inquiry.', 'warning')
        
        return redirect(url_for('contact'))
    
    return render_template_string(CONTACT_TEMPLATE)

# =====================================
# 🗄️ CONTACTS TABLE MIGRATION (Optional)
# =====================================

def create_contacts_table():
    """Create contacts table for storing contact form submissions"""
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Contacts table created successfully!")

# =====================================
# 📄 TERMS OF SERVICE TEMPLATE
# =====================================

TERMS_OF_SERVICE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - Solganic</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .glass-effect { backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.9); }
        .section-card { transition: all 0.3s ease; }
        .section-card:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
        .download-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .download-btn:hover { background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%); }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 via-white to-purple-50 min-h-screen">
    <!-- Floating Header -->
    <header class="fixed top-0 w-full z-50 glass-effect border-b border-white/20">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    <button onclick="downloadPDF()" class="download-btn text-white px-6 py-2.5 rounded-lg font-medium shadow-lg hover:shadow-xl transition-all duration-300 flex items-center space-x-2">
                        <i class="fas fa-download"></i>
                        <span>Download PDF</span>
                    </button>
                    <a href="{{ url_for('index') }}" class="text-gray-600 hover:text-gray-900 font-medium px-4 py-2 rounded-lg hover:bg-white/50 transition-all duration-300">
                        <i class="fas fa-arrow-left mr-2"></i>Back to Home
                    </a>
                </div>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="gradient-bg pt-32 pb-16">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div class="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
                <h1 class="text-4xl md:text-5xl font-bold text-white mb-4">Terms of Service</h1>
                <p class="text-xl text-white/90 mb-6">Your rights and responsibilities when using Solganic</p>
                <div class="flex items-center justify-center space-x-6 text-white/80">
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-calendar-alt"></i>
                        <span>Effective: August 22, 2025</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-globe"></i>
                        <span>Governed by Zambian Law</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 -mt-8">
        <!-- Introduction Card -->
        <div class="bg-white rounded-2xl shadow-xl p-8 mb-8 border border-gray-100">
            <div class="flex items-start space-x-4">
                <div class="bg-blue-100 p-3 rounded-xl">
                    <i class="fas fa-info-circle text-blue-600 text-xl"></i>
                </div>
                <div>
                    <h2 class="text-2xl font-bold text-gray-900 mb-4">Welcome to Solganic</h2>
                    <p class="text-gray-700 leading-relaxed">By accessing or using our website, mobile application, WhatsApp chatbot, and related services (collectively, the "Platform"), you agree to comply with and be bound by these Terms of Service ("Terms"). Please read them carefully.</p>
                </div>
            </div>
        </div>

        <div class="space-y-6">
            <!-- Section 1 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-green-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-handshake text-green-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">1. Acceptance of Terms</h3>
                        <p class="text-gray-700 leading-relaxed">By using our Platform or purchasing our products, you acknowledge that you have read, understood, and agreed to these Terms. If you do not agree, please do not use our services.</p>
                    </div>
                </div>
            </div>

            <!-- Section 2 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-purple-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-seedling text-purple-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">2. Services Provided</h3>
                        <p class="text-gray-700 mb-4">Solganic provides:</p>
                        <div class="space-y-3">
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Organic fertilizers and soil health solutions</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">A digital platform (SoilFert) for interpreting soil test results, compost analysis, and fertilizer recommendations</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Access to resources and training on sustainable farming</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 3 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-orange-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-user-check text-orange-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">3. Eligibility</h3>
                        <p class="text-gray-700 leading-relaxed">You must be at least 18 years old or have legal guardian consent to use our services.</p>
                    </div>
                </div>
            </div>

            <!-- Section 4 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-red-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-tasks text-red-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">4. User Responsibilities</h3>
                        <p class="text-gray-700 mb-4">You agree to:</p>
                        <div class="space-y-3">
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-red-500 rounded-full"></div>
                                <span class="text-gray-700">Provide accurate and truthful information</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-red-500 rounded-full"></div>
                                <span class="text-gray-700">Use the Platform for lawful agricultural and educational purposes only</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-red-500 rounded-full"></div>
                                <span class="text-gray-700">Not misuse, hack, or interfere with the operation of our services</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 5 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-yellow-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-credit-card text-yellow-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">5. Payments and Subscriptions</h3>
                        <div class="space-y-3">
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
                                <span class="text-gray-700">Some services may require payment or a subscription</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
                                <span class="text-gray-700">All fees are displayed clearly before payment</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-yellow-500 rounded-full"></div>
                                <span class="text-gray-700">Subscriptions may renew automatically unless canceled</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 6 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-indigo-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-copyright text-indigo-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">6. Intellectual Property</h3>
                        <p class="text-gray-700 leading-relaxed">All content, logos, software, and materials provided by Solganic remain our intellectual property. Users may not reproduce, distribute, or modify any content without permission.</p>
                    </div>
                </div>
            </div>

            <!-- Section 7 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-teal-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-shield-alt text-teal-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">7. Data and Privacy</h3>
                        <p class="text-gray-700 leading-relaxed">Your use of the Platform is also governed by our Privacy Policy, which explains how we collect and use your information.</p>
                    </div>
                </div>
            </div>

            <!-- Section 8 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-gray-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-exclamation-triangle text-gray-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">8. Limitation of Liability</h3>
                        <div class="space-y-3">
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-gray-500 rounded-full"></div>
                                <span class="text-gray-700">Our fertilizer recommendations and digital outputs are for guidance only</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-gray-500 rounded-full"></div>
                                <span class="text-gray-700">Farming outcomes may vary due to external factors (e.g., weather, pests, management practices)</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-gray-500 rounded-full"></div>
                                <span class="text-gray-700">Solganic is not liable for direct or indirect losses resulting from use of our services</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sections 9-12 in a grid -->
            <div class="grid md:grid-cols-2 gap-6">
                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-pink-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-ban text-pink-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">9. Termination</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">We reserve the right to suspend or terminate access to our services if you violate these Terms.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-blue-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-edit text-blue-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">10. Changes to Terms</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">We may update these Terms from time to time. Updates will be posted on our website with a new effective date.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-green-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-gavel text-green-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">11. Governing Law</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">These Terms shall be governed by the laws of Zambia, without regard to conflict of law principles.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-purple-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-envelope text-purple-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">12. Contact Us</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">For questions about these Terms, contact us via the contact details on our website.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-8 mt-16">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p class="text-gray-400">&copy; 2025 Solganic. All rights reserved.</p>
        </div>
    </footer>
    <!-- JavaScript for PDF Download -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script>
        function downloadPDF() {
            const btn = document.querySelector('.download-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Generating PDF...</span>';
            btn.disabled = true;
            
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Set font
            doc.setFont("helvetica");
            
            // Title
            doc.setFontSize(20);
            doc.setTextColor(40, 40, 40);
            doc.text('Solganic Terms of Service', 20, 30);
            
            // Effective date
            doc.setFontSize(12);
            doc.setTextColor(100, 100, 100);
            doc.text('Effective Date: 22nd August 2025', 20, 45);
            
            let yPosition = 65;
            const lineHeight = 7;
            const pageHeight = doc.internal.pageSize.height;
            const margin = 20;
            
            // Introduction
            doc.setFontSize(14);
            doc.setTextColor(40, 40, 40);
            doc.text('Welcome to Solganic', 20, yPosition);
            yPosition += lineHeight + 3;
            
            doc.setFontSize(11);
            const introText = 'By accessing or using our website, mobile application, WhatsApp chatbot, and related services (collectively, the "Platform"), you agree to comply with and be bound by these Terms of Service ("Terms"). Please read them carefully.';
            const splitIntro = doc.splitTextToSize(introText, 170);
            doc.text(splitIntro, 20, yPosition);
            yPosition += splitIntro.length * lineHeight + 10;
            
            // Terms sections
            const sections = [
                {
                    title: '1. Acceptance of Terms',
                    content: 'By using our Platform or purchasing our products, you acknowledge that you have read, understood, and agreed to these Terms. If you do not agree, please do not use our services.'
                },
                {
                    title: '2. Services Provided',
                    content: 'Solganic provides: • Organic fertilizers and soil health solutions • A digital platform (SoilFert) for interpreting soil test results, compost analysis, and fertilizer recommendations • Access to resources and training on sustainable farming'
                },
                {
                    title: '3. Eligibility',
                    content: 'You must be at least 18 years old or have legal guardian consent to use our services.'
                },
                {
                    title: '4. User Responsibilities',
                    content: 'You agree to: • Provide accurate and truthful information • Use the Platform for lawful agricultural and educational purposes only • Not misuse, hack, or interfere with the operation of our services'
                },
                {
                    title: '5. Payments and Subscriptions',
                    content: '• Some services may require payment or a subscription • All fees are displayed clearly before payment • Subscriptions may renew automatically unless canceled'
                },
                {
                    title: '6. Intellectual Property',
                    content: 'All content, logos, software, and materials provided by Solganic remain our intellectual property. Users may not reproduce, distribute, or modify any content without permission.'
                },
                {
                    title: '7. Data and Privacy',
                    content: 'Your use of the Platform is also governed by our Privacy Policy, which explains how we collect and use your information.'
                },
                {
                    title: '8. Limitation of Liability',
                    content: '• Our fertilizer recommendations and digital outputs are for guidance only • Farming outcomes may vary due to external factors (e.g., weather, pests, management practices) • Solganic is not liable for direct or indirect losses resulting from use of our services'
                },
                {
                    title: '9. Termination',
                    content: 'We reserve the right to suspend or terminate access to our services if you violate these Terms.'
                },
                {
                    title: '10. Changes to Terms',
                    content: 'We may update these Terms from time to time. Updates will be posted on our website with a new effective date. Continued use of the Platform means acceptance of the changes.'
                },
                {
                    title: '11. Governing Law',
                    content: 'These Terms shall be governed by the laws of Zambia, without regard to conflict of law principles.'
                },
                {
                    title: '12. Contact Us',
                    content: 'For questions about these Terms, contact us via the contact details on our website.'
                }
            ];
            
            sections.forEach(section => {
                // Check if we need a new page
                if (yPosition > pageHeight - 50) {
                    doc.addPage();
                    yPosition = 30;
                }
                
                // Section title
                doc.setFontSize(12);
                doc.setTextColor(40, 40, 40);
                doc.text(section.title, 20, yPosition);
                yPosition += lineHeight + 2;
                
                // Section content
                doc.setFontSize(10);
                doc.setTextColor(60, 60, 60);
                const splitContent = doc.splitTextToSize(section.content, 170);
                doc.text(splitContent, 20, yPosition);
                yPosition += splitContent.length * lineHeight + 8;
            });
            
            // Save the PDF
            doc.save('Solganic_Terms_of_Service.pdf');
            
            // Reset button
            btn.innerHTML = originalText;
            btn.disabled = false;
        }

        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.section-card');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, { threshold: 0.1 });

            cards.forEach(card => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(card);
            });
        });
    </script>
</body>
</html>
'''

# =====================================
# 🔒 PRIVACY POLICY TEMPLATE
# =====================================

PRIVACY_POLICY_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - Solganic</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .glass-effect { backdrop-filter: blur(10px); background: rgba(255, 255, 255, 0.9); }
        .section-card { transition: all 0.3s ease; }
        .section-card:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
        .download-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .download-btn:hover { background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%); }
    </style>
</head>
<body class="bg-gradient-to-br from-blue-50 via-white to-purple-50 min-h-screen">
    <!-- Floating Header -->
    <header class="fixed top-0 w-full z-50 glass-effect border-b border-white/20">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>
                <div class="flex items-center space-x-4">
                    <button onclick="downloadPDF()" class="download-btn text-white px-6 py-2.5 rounded-lg font-medium shadow-lg hover:shadow-xl transition-all duration-300 flex items-center space-x-2">
                        <i class="fas fa-download"></i>
                        <span>Download PDF</span>
                    </button>
                    <a href="{{ url_for('index') }}" class="text-gray-600 hover:text-gray-900 font-medium px-4 py-2 rounded-lg hover:bg-white/50 transition-all duration-300">
                        <i class="fas fa-arrow-left mr-2"></i>Back to Home
                    </a>
                </div>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="gradient-bg pt-32 pb-16">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div class="bg-white/10 backdrop-blur-lg rounded-2xl p-8 border border-white/20">
                <h1 class="text-4xl md:text-5xl font-bold text-white mb-4">Privacy Policy</h1>
                <p class="text-xl text-white/90 mb-6">How we protect and handle your information</p>
                <div class="flex items-center justify-center space-x-6 text-white/80">
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-calendar-alt"></i>
                        <span>Effective: August 22, 2025</span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <i class="fas fa-shield-alt"></i>
                        <span>Your Privacy Matters</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Main Content -->
    <main class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 -mt-8">
        <!-- Introduction Card -->
        <div class="bg-white rounded-2xl shadow-xl p-8 mb-8 border border-gray-100">
            <div class="flex items-start space-x-4">
                <div class="bg-blue-100 p-3 rounded-xl">
                    <i class="fas fa-shield-alt text-blue-600 text-xl"></i>
                </div>
                <div>
                    <h2 class="text-2xl font-bold text-gray-900 mb-4">Your Privacy is Our Priority</h2>
                    <p class="text-gray-700 leading-relaxed">Solganic ("we," "our," "us") is committed to protecting the privacy of our farmers, customers, partners, and digital platform users. This Privacy Policy explains how we collect, use, store, and protect personal information when you use our services, including our website, digital soil health platform, WhatsApp chatbot, and fertilizer distribution programs.</p>
                </div>
            </div>
        </div>

        <div class="space-y-6">
            <!-- Section 1 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-green-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-database text-green-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">1. Information We Collect</h3>
                        <p class="text-gray-700 mb-4">We may collect the following information:</p>
                        <div class="grid md:grid-cols-2 gap-4">
                            <div class="bg-green-50 p-4 rounded-lg">
                                <h4 class="font-semibold text-green-800 mb-2">Personal Information</h4>
                                <p class="text-sm text-gray-700">Name, phone number, email address, location (village, district, province), and payment details</p>
                            </div>
                            <div class="bg-blue-50 p-4 rounded-lg">
                                <h4 class="font-semibold text-blue-800 mb-2">Agricultural Data</h4>
                                <p class="text-sm text-gray-700">Soil analysis results, farm size, crop type, fertilizer use, composting materials, and farming practices</p>
                            </div>
                            <div class="bg-purple-50 p-4 rounded-lg">
                                <h4 class="font-semibold text-purple-800 mb-2">Platform Usage Data</h4>
                                <p class="text-sm text-gray-700">Login details, preferences, and interactions with our online, offline, and WhatsApp tools</p>
                            </div>
                            <div class="bg-yellow-50 p-4 rounded-lg">
                                <h4 class="font-semibold text-yellow-800 mb-2">Transaction Data</h4>
                                <p class="text-sm text-gray-700">Purchases of fertilizer, subscriptions, and service payments</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 2 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-purple-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-cogs text-purple-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">2. How We Use Your Information</h3>
                        <div class="space-y-3">
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Provide fertilizer recommendations and soil health analysis</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Help you generate compost nutrient profiles and carbon-nitrogen ratios</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Process orders, subscriptions, and payments</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Improve our digital platform and customer experience</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Send important updates, training resources, and service alerts</span>
                            </div>
                            <div class="flex items-center space-x-3">
                                <div class="w-2 h-2 bg-purple-500 rounded-full"></div>
                                <span class="text-gray-700">Comply with legal obligations</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 3 -->
            <div class="section-card bg-white rounded-2xl shadow-lg p-8 border border-gray-100">
                <div class="flex items-start space-x-4">
                    <div class="bg-orange-100 p-3 rounded-xl flex-shrink-0">
                        <i class="fas fa-share-alt text-orange-600 text-xl"></i>
                    </div>
                    <div class="flex-1">
                        <h3 class="text-xl font-bold text-gray-900 mb-4">3. Data Sharing</h3>
                        <div class="bg-orange-50 p-4 rounded-lg mb-4">
                            <p class="text-orange-800 font-semibold">We do not sell your personal data.</p>
                        </div>
                        <p class="text-gray-700 mb-4">We may share information only with:</p>
                        <div class="space-y-3">
                            <div class="flex items-start space-x-3">
                                <div class="w-2 h-2 bg-orange-500 rounded-full mt-2"></div>
                                <div>
                                    <span class="font-semibold text-gray-900">Trusted Partners:</span>
                                    <span class="text-gray-700"> Agronomists, cooperatives, or NGOs supporting farmer training</span>
                                </div>
                            </div>
                            <div class="flex items-start space-x-3">
                                <div class="w-2 h-2 bg-orange-500 rounded-full mt-2"></div>
                                <div>
                                    <span class="font-semibold text-gray-900">Service Providers:</span>
                                    <span class="text-gray-700"> Payment processors, IT service providers, or cloud storage providers</span>
                                </div>
                            </div>
                            <div class="flex items-start space-x-3">
                                <div class="w-2 h-2 bg-orange-500 rounded-full mt-2"></div>
                                <div>
                                    <span class="font-semibold text-gray-900">Legal Authorities:</span>
                                    <span class="text-gray-700"> If required by law or to protect our rights</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sections 4-9 in a grid -->
            <div class="grid md:grid-cols-2 gap-6">
                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-red-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-lock text-red-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">4. Data Security</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">We use encryption, secure servers, and access controls to protect your information. However, no system is 100% secure.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-blue-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-user-shield text-blue-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">5. Your Rights</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">Access, correct, delete your data, and withdraw consent for communications.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-green-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-clock text-green-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">6. Data Retention</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">We retain your data only as long as necessary to provide services or comply with legal requirements.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-yellow-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-child text-yellow-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">7. Children's Privacy</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">Our services are intended for adults involved in farming. We do not knowingly collect data from individuals under 18.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-indigo-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-edit text-indigo-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">8. Changes to This Policy</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">We may update this Privacy Policy from time to time. Changes will be posted with a revised effective date.</p>
                        </div>
                    </div>
                </div>

                <div class="section-card bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                    <div class="flex items-start space-x-3">
                        <div class="bg-purple-100 p-2 rounded-lg flex-shrink-0">
                            <i class="fas fa-envelope text-purple-600"></i>
                        </div>
                        <div>
                            <h3 class="text-lg font-bold text-gray-900 mb-3">9. Contact Us</h3>
                            <p class="text-gray-700 text-sm leading-relaxed">For questions about this Privacy Policy, please contact us via the contact details on our website.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="bg-gray-900 text-white py-8 mt-16">
        <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <p class="text-gray-400">&copy; 2025 Solganic. All rights reserved.</p>
        </div>
    </footer>

    <!-- JavaScript for PDF Download -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script>
        function downloadPDF() {
            const btn = document.querySelector('.download-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Generating PDF...</span>';
            btn.disabled = true;
            
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();
            
            // Set font
            doc.setFont("helvetica");
            
            // Title
            doc.setFontSize(20);
            doc.setTextColor(40, 40, 40);
            doc.text('Solganic Privacy Policy', 20, 30);
            
            // Effective date
            doc.setFontSize(12);
            doc.setTextColor(100, 100, 100);
            doc.text('Effective Date: 22nd August 2025', 20, 45);
            
            let yPosition = 65;
            const lineHeight = 7;
            const pageHeight = doc.internal.pageSize.height;
            const margin = 20;
            
            // Introduction
            doc.setFontSize(14);
            doc.setTextColor(40, 40, 40);
            doc.text('Your Privacy is Our Priority', 20, yPosition);
            yPosition += lineHeight + 3;
            
            doc.setFontSize(11);
            const introText = 'Solganic ("we," "our," "us") is committed to protecting the privacy of our farmers, customers, partners, and digital platform users. This Privacy Policy explains how we collect, use, store, and protect personal information when you use our services, including our website, digital soil health platform, WhatsApp chatbot, and fertilizer distribution programs.';
            const splitIntro = doc.splitTextToSize(introText, 170);
            doc.text(splitIntro, 20, yPosition);
            yPosition += splitIntro.length * lineHeight + 10;
            
            // Privacy sections
            const sections = [
                {
                    title: '1. Information We Collect',
                    content: 'We may collect the following information: • Personal Information: Name, phone number, email address, location (village, district, province), and payment details • Agricultural Data: Soil analysis results, farm size, crop type, fertilizer use, composting materials, and farming practices • Platform Usage Data: Login details, preferences, and interactions with our online, offline, and WhatsApp tools • Transaction Data: Purchases of fertilizer, subscriptions, and service payments'
                },
                {
                    title: '2. How We Use Your Information',
                    content: 'We use your information to: • Provide fertilizer recommendations and soil health analysis • Help you generate compost nutrient profiles and carbon-nitrogen ratios • Process orders, subscriptions, and payments • Improve our digital platform and customer experience • Send important updates, training resources, and service alerts • Comply with legal obligations'
                },
                {
                    title: '3. Data Sharing',
                    content: 'We do not sell your personal data. We may share information only with: • Trusted Partners: Agronomists, cooperatives, or NGOs supporting farmer training • Service Providers: Payment processors, IT service providers, or cloud storage providers • Legal Authorities: If required by law or to protect our rights'
                },
                {
                    title: '4. Data Security',
                    content: 'We use encryption, secure servers, and access controls to protect your information. However, no system is 100% secure, and we cannot guarantee absolute security.'
                },
                {
                    title: '5. Your Rights',
                    content: 'As a user, you have the right to: • Access and request a copy of your data • Correct inaccurate information • Request deletion of your data (subject to legal and contractual obligations) • Withdraw consent for communications'
                },
                {
                    title: '6. Data Retention',
                    content: 'We retain your personal and agricultural data only as long as necessary to provide our services or comply with legal requirements.'
                },
                {
                    title: '7. Children\'s Privacy',
                    content: 'Our services are intended for adults involved in farming. We do not knowingly collect data from individuals under 18.'
                },
                {
                    title: '8. Changes to This Policy',
                    content: 'We may update this Privacy Policy from time to time. Any changes will be posted on our website and digital platforms with a revised effective date.'
                },
                {
                    title: '9. Contact Us',
                    content: 'If you have any questions or requests about this Privacy Policy, please contact us via the contact details on our website.'
                }
            ];
            
            sections.forEach(section => {
                // Check if we need a new page
                if (yPosition > pageHeight - 50) {
                    doc.addPage();
                    yPosition = 30;
                }
                
                // Section title
                doc.setFontSize(12);
                doc.setTextColor(40, 40, 40);
                doc.text(section.title, 20, yPosition);
                yPosition += lineHeight + 2;
                
                // Section content
                doc.setFontSize(10);
                doc.setTextColor(60, 60, 60);
                const splitContent = doc.splitTextToSize(section.content, 170);
                doc.text(splitContent, 20, yPosition);
                yPosition += splitContent.length * lineHeight + 8;
            });
            
            // Save the PDF
            doc.save('Solganic_Privacy_Policy.pdf');
            
            // Reset button
            btn.innerHTML = originalText;
            btn.disabled = false;
        }

        document.addEventListener('DOMContentLoaded', function() {
            const cards = document.querySelectorAll('.section-card');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }
                });
            }, { threshold: 0.1 });

            cards.forEach(card => {
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
                observer.observe(card);
            });
        });
    </script>
</body>
</html>
'''

# =====================================
# 📧 MODERN CONTACT FORM TEMPLATE
# =====================================

CONTACT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Contact Us - SoilsFert Professional</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#f0f9ff',
                            500: '#3b82f6',
                            600: '#2563eb',
                            700: '#1d4ed8'
                        },
                        success: {
                            50: '#f0fdf4',
                            500: '#22c55e',
                            600: '#16a34a'
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-blue-50 min-h-screen">
    <!-- Modern Navigation -->
    <nav class="bg-white/80 backdrop-blur-md shadow-lg border-b border-gray-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <!-- Logo Section -->
                <div class="flex items-center space-x-3">
                    <a href="{{ url_for('index') }}">
                        <img src="{{ url_for('serve_logo') }}" alt="SoilsFert Logo" class="h-10 w-auto rounded-lg">
                    </a>
                </div>

                <!-- Navigation Links -->
                <div class="flex items-center space-x-4">
                    <a href="{{ url_for('index') }}" class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                        Home
                    </a>
                    {% if session.user_id %}
                        <a href="{{ url_for('dashboard') }}" class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                            Dashboard
                        </a>
                    {% else %}
                        <a href="{{ url_for('login') }}" class="text-gray-700 hover:text-gray-900 font-medium transition-colors">
                            Login
                        </a>
                        <a href="{{ url_for('register') }}" 
                           class="inline-flex items-center px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105 shadow-lg">
                            Sign Up
                        </a>
                    {% endif %}
                </div>
            </div>
        </div>
    </nav>

    <!-- Hero Header -->
    <div class="relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50"></div>
        <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
            <div class="text-center">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mb-6">
                    <i class="fas fa-envelope text-white text-2xl"></i>
                </div>
                <h1 class="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent mb-4">
                    Contact Our Team
                </h1>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto mb-6">
                    Get in touch with our agricultural experts and technical support team
                </p>
                <div class="flex flex-wrap justify-center gap-4 text-sm">
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-green-100 text-green-800">
                        <i class="fas fa-clock mr-2"></i>
                        24-48 hour response
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800">
                        <i class="fas fa-users mr-2"></i>
                        Expert support team
                    </span>
                    <span class="inline-flex items-center px-3 py-1 rounded-full bg-purple-100 text-purple-800">
                        <i class="fas fa-shield-alt mr-2"></i>
                        Professional service
                    </span>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 -mt-8">
        
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="mb-8">
                    {% for category, message in messages %}
                        <div class="rounded-lg p-4 mb-4 {% if category == 'error' %}bg-red-50 border border-red-200 text-red-800{% elif category == 'success' %}bg-green-50 border border-green-200 text-green-800{% elif category == 'warning' %}bg-amber-50 border border-amber-200 text-amber-800{% else %}bg-blue-50 border border-blue-200 text-blue-800{% endif %}">
                            <div class="flex items-center">
                                <i class="fas fa-{% if category == 'error' %}exclamation-circle{% elif category == 'success' %}check-circle{% elif category == 'warning' %}exclamation-triangle{% else %}info-circle{% endif %} mr-3"></i>
                                {{ message }}
                            </div>
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12">
            
            <!-- Contact Form -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-paper-plane mr-3 text-blue-500"></i>
                        Send us a Message
                    </h3>
                </div>
                <div class="p-6">
                    <form method="POST" class="space-y-6" id="contact-form">
                        <!-- Name Field -->
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Full Name *
                                <i class="fas fa-user text-blue-500 ml-1"></i>
                            </label>
                            <input type="text" name="name" required value="{{ name if name else '' }}"
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="Your full name">
                        </div>

                        <!-- Email Field -->
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Email Address *
                                <i class="fas fa-envelope text-green-500 ml-1"></i>
                            </label>
                            <input type="email" name="email" required value="{{ email if email else '' }}"
                                   class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="your.email@example.com">
                        </div>

                        <!-- Subject Field -->
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Subject *
                                <i class="fas fa-tag text-purple-500 ml-1"></i>
                            </label>
                            <select name="subject" required
                                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <option value="">Select a subject</option>
                                <option value="Technical Support" {{ 'selected' if subject == 'Technical Support' else '' }}>🔧 Technical Support</option>
                                <option value="Billing Question" {{ 'selected' if subject == 'Billing Question' else '' }}>💳 Billing Question</option>
                                <option value="Feature Request" {{ 'selected' if subject == 'Feature Request' else '' }}>🚀 Feature Request</option>
                                <option value="Partnership Inquiry" {{ 'selected' if subject == 'Partnership Inquiry' else '' }}>🤝 Partnership Inquiry</option>
                                <option value="General Question" {{ 'selected' if subject == 'General Question' else '' }}>❓ General Question</option>
                                <option value="Bug Report" {{ 'selected' if subject == 'Bug Report' else '' }}>🐛 Bug Report</option>
                                <option value="Other" {{ 'selected' if subject == 'Other' else '' }}>📝 Other</option>
                            </select>
                        </div>

                        <!-- Message Field -->
                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Message *
                                <i class="fas fa-comment text-orange-500 ml-1"></i>
                            </label>
                            <textarea name="message" rows="6" required
                                      class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors resize-none"
                                      placeholder="Please describe your inquiry in detail...">{{ message if message else '' }}</textarea>
                            <div class="flex justify-between text-xs text-gray-500">
                                <span>Minimum 10 characters</span>
                                <span id="char-count">0/1000</span>
                            </div>
                        </div>

                        <!-- Submit Button -->
                        <div class="pt-4">
                            <button type="submit" id="submit-button"
                                    class="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-blue-700 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-700 hover:via-purple-700 hover:to-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-300 transition-all duration-300 transform hover:scale-105 shadow-lg">
                                <i class="fas fa-paper-plane mr-2"></i>
                                Send Message
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Contact Information -->
            <div class="space-y-8">
                
                <!-- Contact Details -->
                <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                    <div class="bg-gradient-to-r from-green-50 to-emerald-50 px-6 py-4 border-b border-gray-200">
                        <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                            <i class="fas fa-info-circle mr-3 text-green-500"></i>
                            Contact Information
                        </h3>
                    </div>
                    <div class="p-6 space-y-4">
                        <div class="flex items-center p-4 bg-gray-50 rounded-lg">
                            <div class="bg-blue-100 rounded-lg p-3 mr-4">
                                <i class="fas fa-envelope text-blue-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Email Support</h4>
                                <p class="text-gray-600">contact@soilsfert.com</p>
                                <p class="text-xs text-gray-500">24-48 hour response time</p>
                            </div>
                        </div>

                        <div class="flex items-center p-4 bg-gray-50 rounded-lg">
                            <div class="bg-green-100 rounded-lg p-3 mr-4">
                                <i class="fas fa-clock text-green-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Business Hours</h4>
                                <p class="text-gray-600">Monday - Friday: 9:00 AM - 6:00 PM</p>
                                <p class="text-xs text-gray-500">Pacific Standard Time (PST)</p>
                            </div>
                        </div>

                        <div class="flex items-center p-4 bg-gray-50 rounded-lg">
                            <div class="bg-purple-100 rounded-lg p-3 mr-4">
                                <i class="fas fa-headset text-purple-600"></i>
                            </div>
                            <div>
                                <h4 class="font-semibold text-gray-900">Technical Support</h4>
                                <p class="text-gray-600">Expert agricultural consultants</p>
                                <p class="text-xs text-gray-500">Soil analysis and fertilizer guidance</p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Social Media -->
                <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                    <div class="bg-gradient-to-r from-purple-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                        <h3 class="text-xl font-semibold text-gray-900 flex items-center">
                            <i class="fas fa-share-alt mr-3 text-purple-500"></i>
                            Follow Us
                        </h3>
                    </div>
                    <div class="p-6">
                        <div class="grid grid-cols-2 gap-4">
                            <a href="https://www.facebook.com/share/1SVcgqUTbP/?mibextid=wwXIfr" target="_blank" 
                               class="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors group">
                                <i class="fab fa-facebook-f text-blue-600 text-xl mr-3 group-hover:scale-110 transition-transform"></i>
                                <span class="font-medium text-gray-700">Facebook</span>
                            </a>
                            
                            <a href="https://www.instagram.com/solganic_5?igsh=aDhyZnAwdmdsaHV4&utm_source=qr" target="_blank" 
                               class="flex items-center p-4 bg-pink-50 rounded-lg hover:bg-pink-100 transition-colors group">
                                <i class="fab fa-instagram text-pink-600 text-xl mr-3 group-hover:scale-110 transition-transform"></i>
                                <span class="font-medium text-gray-700">Instagram</span>
                            </a>
                            
                            <a href="https://youtube.com/@solganic?si=wozdWZDNi9NWfiHn" target="_blank" 
                               class="flex items-center p-4 bg-red-50 rounded-lg hover:bg-red-100 transition-colors group">
                                <i class="fab fa-youtube text-red-600 text-xl mr-3 group-hover:scale-110 transition-transform"></i>
                                <span class="font-medium text-gray-700">YouTube</span>
                            </a>
                            
                            <a href="https://www.linkedin.com/company/solganic/" target="_blank" 
                               class="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors group">
                                <i class="fab fa-linkedin-in text-blue-700 text-xl mr-3 group-hover:scale-110 transition-transform"></i>
                                <span class="font-medium text-gray-700">LinkedIn</span>
                            </a>
                        </div>
                    </div>
                </div>

                <!-- FAQ Link -->
                <div class="bg-gradient-to-r from-blue-100 to-purple-100 rounded-xl p-6 border border-blue-200">
                    <div class="text-center">
                        <div class="w-12 h-12 bg-white rounded-full flex items-center justify-center mx-auto mb-4">
                            <i class="fas fa-question-circle text-blue-600 text-xl"></i>
                        </div>
                        <h4 class="font-semibold text-gray-900 mb-2">Quick Questions?</h4>
                        <p class="text-gray-600 text-sm mb-4">Check our frequently asked questions for instant answers</p>
                        <a href="{{ url_for('pricing') }}" 
                           class="inline-flex items-center px-4 py-2 bg-white text-blue-600 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                            <i class="fas fa-external-link-alt mr-2"></i>
                            View FAQ
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Character counter for message field
        document.addEventListener('DOMContentLoaded', function() {
            const messageField = document.querySelector('textarea[name="message"]');
            const charCount = document.getElementById('char-count');
            const submitButton = document.getElementById('submit-button');
            const form = document.getElementById('contact-form');

            if (messageField && charCount) {
                messageField.addEventListener('input', function() {
                    const count = this.value.length;
                    charCount.textContent = `${count}/1000`;
                    
                    // Prevent exceeding 1000 characters
                    if (count > 1000) {
                        this.value = this.value.substring(0, 1000);
                        charCount.textContent = '1000/1000';
                    }
                    
                    // Update color based on length
                    if (count < 10) {
                        charCount.classList.add('text-red-500');
                        charCount.classList.remove('text-green-500', 'text-gray-500');
                    } else if (count >= 10 && count <= 1000) {
                        charCount.classList.add('text-green-500');
                        charCount.classList.remove('text-red-500', 'text-gray-500');
                    } else {
                        charCount.classList.add('text-gray-500');
                        charCount.classList.remove('text-red-500', 'text-green-500');
                    }
                });
                
                // Initial count
                messageField.dispatchEvent(new Event('input'));
            }

            // Form enhancement
            if (form && submitButton) {
                form.addEventListener('submit', function(e) {
                    const name = document.querySelector('input[name="name"]').value.trim();
                    const email = document.querySelector('input[name="email"]').value.trim();
                    const subject = document.querySelector('select[name="subject"]').value;
                    const message = document.querySelector('textarea[name="message"]').value.trim();
                    
                    // Basic validation
                    if (!name || !email || !subject || !message) {
                        e.preventDefault();
                        alert('Please fill in all required fields');
                        return;
                    }
                    
                    if (message.length < 10) {
                        e.preventDefault();
                        alert('Message must be at least 10 characters long');
                        return;
                    }
                    
                    // Show loading state
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Sending...';
                    submitButton.disabled = true;
                });
            }

            // Add focus effects to form inputs
            document.querySelectorAll('input, select, textarea').forEach(field => {
                field.addEventListener('focus', function() {
                    this.parentElement.classList.add('scale-105');
                });
                
                field.addEventListener('blur', function() {
                    this.parentElement.classList.remove('scale-105');
                });
            });
        });
    </script>

    <style>
        /* Custom input focus effects */
        input:focus, select:focus, textarea:focus {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        }
        
        /* Smooth transitions */
        * {
            transition: all 0.3s ease;
        }
        
        /* Gradient animation */
        @keyframes gradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .bg-clip-text {
            background-size: 200% 200%;
            animation: gradient 4s ease infinite;
        }

        /* Card hover effects */
        .group:hover {
            transform: translateY(-2px);
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }
        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
    </style>
</body>
</html>
'''

# =====================================
# 🚀 CORRECTED APPLICATION STARTUP SECTION
# =====================================

if __name__ == '__main__':
    create_contacts_table()
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Complete migration including physical parameters
    print("Migrating database with enhanced physical parameters...")
    complete_database_migration()
    
    # Add testimonials table
    print("Creating testimonials table...")
    migrate_testimonials_table()
    
    # Create demo user if not exists (CORRECTED INDENTATION)
    sample_user = query_db('SELECT id FROM users WHERE email = ?', ['demo@soilfert.com'], one=True)
    if not sample_user:
        password_hash = generate_password_hash('demo123')
        execute_db('''
            INSERT INTO users (email, password_hash, first_name, last_name, 
                             country, region, farm_size, plan_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            'demo@soilfert.com', password_hash, 'Demo', 'User',
            'United States', 'California', 100.0, 'pro'
        ])
        print("Demo user created: demo@soilfert.com / demo123")
    else:
        print("Demo user already exists")
    
    print("\nSoilFert Enhanced Professional Application Starting...")
    print("=" * 80)
    print("NEW FEATURE: Dynamic Testimonials System")
    print("   Users can submit their own testimonials")
    print("   Horizontally scrollable testimonials display")
    print("   5-star rating system")
    print("   Real-time updates and modern UI")
    print("=" * 80)
    print("ENHANCED FEATURES AVAILABLE:")
    print("   PHYSICAL PARAMETERS: Bulk density, particle density, porosity calculation")
    print("   VOLUME & MASS: Precise soil volume and mass calculations")
    print("   ENHANCED LIME CALCULATOR: Density and depth adjusted lime requirements")
    print("   TOTAL COST ESTIMATION: Per hectare and total field costs")
    print("   COMPLETE SOIL ANALYSIS: All nutrients + physical properties")
    print("   AUTOMATIC CALCULATIONS: CEC, cationic ratios, porosity")
    print("=" * 80)
    print("Visit: http://localhost:5000")
    print("Demo: demo@soilfert.com / demo123")
    print("Try the Enhanced Lime Calculator with Physical Parameters!")
    print("NEW: Try the Dynamic Testimonials System!")
    print("=" * 80)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)

# =====================================
# 💳 STRIPE CHECKOUT TEMPLATE
# =====================================

STRIPE_CHECKOUT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Secure Payment - SoilsFert</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://js.stripe.com/v3/"></script>
</head>
<body class="bg-gradient-to-br from-slate-50 to-slate-100 min-h-screen">
    <div class="max-w-md mx-auto pt-16 px-4">
        <!-- Header -->
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl mb-4 shadow-lg">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-slate-900 mb-2">Secure Payment</h1>
            <p class="text-slate-600">SoilsFert Pro Plan - $5.00 USD</p>
        </div>

        <!-- Payment Form -->
        <div class="bg-white rounded-2xl shadow-xl border border-slate-200 p-6">
            <form id="payment-form">
                <div class="mb-6">
                    <label class="block text-sm font-medium text-slate-700 mb-2">
                        Card Information
                    </label>
                    <div id="card-element" class="p-3 border border-slate-300 rounded-lg">
                        <!-- Stripe Elements will create form elements here -->
                    </div>
                    <div id="card-errors" role="alert" class="text-red-600 text-sm mt-2"></div>
                </div>

                <button id="submit-button" 
                        class="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold flex items-center justify-center space-x-2">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                    </svg>
                    <span id="button-text">Pay $5.00 Securely</span>
                </button>

                <div class="mt-4 text-center">
                    <p class="text-xs text-slate-500">
                        <svg class="w-4 h-4 inline mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
                        </svg>
                        Secured by Stripe • SSL Encrypted
                    </p>
                </div>
            </form>

            <div class="mt-6 pt-4 border-t border-slate-200">
                <a href="{{ url_for('pricing') }}" 
                   class="text-slate-600 hover:text-slate-800 text-sm font-medium flex items-center justify-center">
                    <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
                    </svg>
                    Back to Pricing
                </a>
            </div>
        </div>
    </div>

    <script>
        const stripe = Stripe('{{ publishable_key }}');
        const elements = stripe.elements();

        // Create card element
        const cardElement = elements.create('card', {
            style: {
                base: {
                    fontSize: '16px',
                    color: '#424770',
                    '::placeholder': {
                        color: '#aab7c4',
                    },
                },
            },
        });

        cardElement.mount('#card-element');

        // Handle form submission
        const form = document.getElementById('payment-form');
        const submitButton = document.getElementById('submit-button');
        const buttonText = document.getElementById('button-text');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            submitButton.disabled = true;
            buttonText.textContent = 'Processing...';

            try {
                // Create payment intent
                const response = await fetch('/stripe/create-payment-intent', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                });

                const {client_secret, error} = await response.json();

                if (error) {
                    throw new Error(error);
                }

                // Confirm payment
                const {error: stripeError, paymentIntent} = await stripe.confirmCardPayment(client_secret, {
                    payment_method: {
                        card: cardElement,
                    }
                });

                if (stripeError) {
                    // Show error to customer
                    document.getElementById('card-errors').textContent = stripeError.message;
                    submitButton.disabled = false;
                    buttonText.textContent = 'Pay $5.00 Securely';
                } else {
                    // Payment succeeded
                    window.location.href = '/stripe/payment-success?payment_intent=' + paymentIntent.id;
                }
            } catch (error) {
                document.getElementById('card-errors').textContent = error.message;
                submitButton.disabled = false;
                buttonText.textContent = 'Pay $5.00 Securely';
            }
        });

        // Handle real-time validation errors from the card Element
        cardElement.on('change', ({error}) => {
            const displayError = document.getElementById('card-errors');
            if (error) {
                displayError.textContent = error.message;
            } else {
                displayError.textContent = '';
            }
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
