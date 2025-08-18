#!/usr/bin/env python3
"""
SoilFert - Complete Soil Fertility Analysis Application with Enhanced Lime Calculation
Single file with organized sections for easy individual editing
"""

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
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify

# =====================================
# ⚙️ FLASK APP CONFIGURATION
# =====================================

app = Flask(__name__)
app.secret_key = 'soilfert-secret-key-change-in-production'
app.config['DATABASE'] = 'soilfert.db'




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
            last_login TIMESTAMP
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
    
    print("🔄 Starting enhanced database migration...")
    
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
            print(f"✅ Added enhanced column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                print(f"❌ Error adding column {column_name}: {e}")
    
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
    
    print("✅ Created enhanced tracking tables")
    
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
    
    print("✅ Updated existing analyses with default values")
    
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
            print(f"✅ Created index: {index_sql.split(' ')[-1]}")
        except sqlite3.OperationalError:
            pass
    
    conn.commit()
    conn.close()
    print("🎉 Enhanced database migration completed successfully!")


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
            print(f"✅ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"❌ Error adding column {column_name}: {e}")
    
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
            print(f"✅ Added physical parameter column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"❌ Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()    

# =====================================
# 🔐 AUTHENTICATION HELPERS
# =====================================

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =====================================
# 🧮 ENHANCED LIME CALCULATION ENGINE WITH SCIENTIFIC METHOD
# =====================================

class EnhancedLimeCalculator:
    """Enhanced lime calculation using scientifically proven method: t/ha = 5 × ΔAE × ρb × d"""
    
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
                                          particle_density_g_cm3=2.65, product_ecce=100.0):
        """
        Enhanced lime requirement calculation using scientific method:
        t/ha = 5 × ΔAE × ρb × d (for CaCO₃-equivalent)
        
        Args:
            exchangeable_acidity (float): Current EA in cmol+/kg
            lime_type (str): Type of lime to use
            target_ae (float): Target EA level (default 0.5 cmol+/kg)
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
        
        # If AE is already at or below target, no lime needed
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
                'message': f'✅ Exchangeable Acidity ({exchangeable_acidity:.2f}) is already at target level ({target_ae:.2f})',
                'calculation_method': 'Scientific Formula: t/ha = 5 × ΔAE × ρb × d',
                'physical_properties': physical_props,
                'soil_calculations': soil_calcs
            }
        
        # Calculate AE that needs to be neutralized
        ae_to_neutralize = exchangeable_acidity - target_ae
        
        # Get lime type data
        lime_data = EnhancedLimeCalculator.LIME_TYPES[lime_type]
        
        # SCIENTIFIC METHOD: t/ha = 5 × ΔAE × ρb × d
        # Convert depth from cm to meters for the formula
        depth_m = depth_cm / 100
        
        # Calculate CaCO₃-equivalent requirement first
        caco3_eq_t_ha = 5 * ae_to_neutralize * bulk_density_g_cm3 * depth_m
        
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
        
        # Prepare detailed explanation
        formula_explanation = f"""
        🧮 Scientific Calculation Method:
        1. CaCO₃-eq needed: t/ha = 5 × {ae_to_neutralize:.2f} × {bulk_density_g_cm3} × {depth_m:.2f} = {caco3_eq_t_ha:.3f} t/ha
        2. {lime_data['name']}: {caco3_eq_t_ha:.3f} ÷ {lime_data['cce_factor']} = {lime_t_ha:.3f} t/ha
        3. Commercial ECCE adjustment: {lime_t_ha:.3f} ÷ {product_ecce_fraction:.2f} = {lime_t_ha_real:.3f} t/ha
        4. Final recommendation: {lime_kg_ha:.0f} kg/ha ({lime_t_ha_real:.2f} t/ha)
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
            
            # Messages and explanations
            'message': f'Apply {lime_kg_ha:.0f} kg/ha ({lime_t_ha_real:.2f} t/ha) of {lime_data["name"]} to reduce AE from {exchangeable_acidity:.2f} to {target_ae:.2f}',
            'calculation_method': 'Scientific Formula: t/ha = 5 × ΔAE × ρb × d',
            'formula_explanation': formula_explanation,
            'safety_message': '⚠️ Application capped at 8 t/ha for safety' if safety_cap_applied else '',
            
            # Additional data
            'physical_properties': physical_props,
            'soil_calculations': soil_calcs
        }
    
    @staticmethod
    def compare_all_lime_types(exchangeable_acidity, target_ae=0.5, land_area_ha=1.0, 
                              depth_cm=20.0, bulk_density_g_cm3=1.3, product_ecce=100.0):
        """
        Compare lime requirements for all lime types using scientific method
        
        Returns:
            dict: Comparison of all lime types
        """
        comparison = {}
        
        # Calculate CaCO₃-equivalent requirement first
        ae_to_neutralize = max(0, exchangeable_acidity - target_ae)
        depth_m = depth_cm / 100
        caco3_eq_t_ha = 5 * ae_to_neutralize * bulk_density_g_cm3 * depth_m
        
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


# Example usage and testing
if __name__ == "__main__":
    # Test the calculator
    calc = EnhancedLimeCalculator()
    
    # Example calculation
    result = calc.calculate_enhanced_lime_requirement(
        exchangeable_acidity=2.5,
        lime_type='caco3',
        target_ae=0.5,
        land_area_ha=5.0,
        depth_cm=20.0,
        bulk_density_g_cm3=1.3,
        product_ecce=95.0
    )
    
    print("🧮 Enhanced Lime Calculator Results:")
    print(f"Lime needed: {result['lime_needed_kg_ha']} kg/ha ({result['lime_needed_t_ha']} t/ha)")
    print(f"Total for {result['land_area_ha']} ha: {result['lime_needed_kg_total']} kg ({result['lime_needed_t_total']} t)")
    print(f"Lime type: {result['lime_name']}")
    print(f"Message: {result['message']}")
    
    # Compare all lime types
    comparison = calc.compare_all_lime_types(
        exchangeable_acidity=2.5,
        target_ae=0.5,
        land_area_ha=5.0
    )
    
    print("\n🔍 Comparison of All Lime Types:")
    for lime_type, data in comparison['lime_types'].items():
        print(f"{data['name']}: {data['kg_ha']} kg/ha ({data['t_ha']} t/ha) - {data['speed']} acting")
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
    
    # COMPREHENSIVE COMMERCIAL FERTILIZER DATABASE
    FERTILIZER_PRODUCTS = {
        # === PRIMARY NUTRIENTS (NPK) ===
        'DAP': {'N': 18, 'P2O5': 46, 'K2O': 0, 'price_per_kg': 0.55, 'category': 'primary'},
        'TSP': {'N': 0, 'P2O5': 46, 'K2O': 0, 'price_per_kg': 0.52, 'category': 'primary'},
        'MAP': {'N': 11, 'P2O5': 52, 'K2O': 0, 'price_per_kg': 0.58, 'category': 'primary'},
        'Superphosphate': {'N': 0, 'P2O5': 20, 'K2O': 0, 'Ca': 18, 'S': 12, 'price_per_kg': 0.45, 'category': 'primary'},
        
        # Potassium fertilizers
        'Muriate_KCl': {'N': 0, 'P2O5': 0, 'K2O': 60, 'price_per_kg': 0.40, 'category': 'primary'},
        'Sulfate_K2SO4': {'N': 0, 'P2O5': 0, 'K2O': 50, 'S': 18, 'price_per_kg': 0.48, 'category': 'primary'},
        
        # NPK compound fertilizers
        'NPK_12_12_17': {'N': 12, 'P2O5': 12, 'K2O': 17, 'S': 2, 'price_per_kg': 0.50, 'category': 'compound'},
        'NPK_15_15_15': {'N': 15, 'P2O5': 15, 'K2O': 15, 'price_per_kg': 0.52, 'category': 'compound'},
        'NPK_20_10_10': {'N': 20, 'P2O5': 10, 'K2O': 10, 'price_per_kg': 0.54, 'category': 'compound'},
        'NPK_10_20_20': {'N': 10, 'P2O5': 20, 'K2O': 20, 'S': 3, 'price_per_kg': 0.53, 'category': 'compound'},
        'NPK_16_16_16': {'N': 16, 'P2O5': 16, 'K2O': 16, 'S': 5, 'Mg': 2, 'price_per_kg': 0.55, 'category': 'compound'},
        
        # Nitrogen fertilizers
        'Urea': {'N': 46, 'P2O5': 0, 'K2O': 0, 'price_per_kg': 0.35, 'category': 'primary'},
        'Ammonium_sulfate': {'N': 21, 'P2O5': 0, 'K2O': 0, 'S': 24, 'price_per_kg': 0.32, 'category': 'primary'},
        'Calcium_nitrate': {'N': 15.5, 'P2O5': 0, 'K2O': 0, 'Ca': 19, 'price_per_kg': 0.42, 'category': 'primary'},
        
        # === SECONDARY NUTRIENTS ===
        'Gypsum': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 23, 'S': 18, 'price_per_kg': 0.25, 'category': 'secondary'},
        'Magnesium_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mg': 10, 'S': 13, 'price_per_kg': 0.35, 'category': 'secondary'},
        'Calcium_chloride': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 36, 'price_per_kg': 0.30, 'category': 'secondary'},
        'Dolomitic_lime': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 22, 'Mg': 12, 'price_per_kg': 0.15, 'category': 'secondary'},
        'Elemental_sulfur': {'N': 0, 'P2O5': 0, 'K2O': 0, 'S': 90, 'price_per_kg': 0.40, 'category': 'secondary'},
        
        # === MICRONUTRIENT PRODUCTS ===
        'Zinc_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Zn': 35, 'S': 17, 'price_per_kg': 2.50, 'category': 'micronutrient'},
        'Copper_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Cu': 25, 'S': 12, 'price_per_kg': 3.00, 'category': 'micronutrient'},
        'Manganese_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mn': 32, 'S': 15, 'price_per_kg': 2.80, 'category': 'micronutrient'},
        'Iron_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 20, 'S': 11, 'price_per_kg': 2.20, 'category': 'micronutrient'},
        'Iron_EDDHA': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 6, 'price_per_kg': 8.50, 'category': 'micronutrient'},
        'Boron_borate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'B': 17, 'price_per_kg': 4.00, 'category': 'micronutrient'},
        'Molybdenum_oxide': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Mo': 66, 'price_per_kg': 25.00, 'category': 'micronutrient'},
        
        # === MULTI-NUTRIENT PRODUCTS ===
        'Complete_micro_blend': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Fe': 8, 'Cu': 2, 'Mn': 5, 'Zn': 3, 'B': 1, 'Mo': 0.1, 'price_per_kg': 6.50, 'category': 'micronutrient'},
        'Secondary_blend': {'N': 0, 'P2O5': 0, 'K2O': 0, 'Ca': 15, 'Mg': 8, 'S': 20, 'price_per_kg': 0.45, 'category': 'secondary'},
        'NPK_Ca_Mg_S': {'N': 12, 'P2O5': 8, 'K2O': 16, 'Ca': 8, 'Mg': 4, 'S': 10, 'price_per_kg': 0.65, 'category': 'complete'},
        'Organic_complete': {'N': 5, 'P2O5': 3, 'K2O': 4, 'Ca': 12, 'Mg': 3, 'S': 8, 'Fe': 2, 'Mn': 1, 'Zn': 0.5, 'price_per_kg': 1.20, 'category': 'organic'}
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
        
        # Physics-based conversions
        p_build_up_coeff = 0.75 if extraction_method == 'olsen_modified' else 0.65
        k_build_up_efficiency = 0.8
        
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
        # Calcium
        current_ca_cmol = float(current_levels.get('calcium_cmol', 0))
        target_ca_cmol = float(target_levels.get('calcium_cmol', 6.0))
        ca_deficit_cmol = max(0, target_ca_cmol - current_ca_cmol)
        ca_needed_kg_ha = ca_deficit_cmol * 400.8 * (soil_mass_kg_ha / 2600000) * 0.8  # Ca conversion
        
        # Magnesium
        current_mg_cmol = float(current_levels.get('magnesium_cmol', 0))
        target_mg_cmol = float(target_levels.get('magnesium_cmol', 2.0))
        mg_deficit_cmol = max(0, target_mg_cmol - current_mg_cmol)
        mg_needed_kg_ha = mg_deficit_cmol * 121.5 * (soil_mass_kg_ha / 2600000) * 0.8  # Mg conversion
        
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
        }.get(crop.lower(), 15)
        
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
            'n_index_used': n_index
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
    
    # EXPANDED COMMERCIAL FERTILIZER PRODUCTS DATABASE
    FERTILIZER_PRODUCTS = {
        # =====================================
        # PRIMARY NPK FERTILIZERS
        # =====================================
        'DAP': {'N': 18, 'P2O5': 46, 'K2O': 0, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.55, 'category': 'NPK'},
        'MAP': {'N': 11, 'P2O5': 52, 'K2O': 0, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.58, 'category': 'NPK'},
        'TSP': {'N': 0, 'P2O5': 46, 'K2O': 0, 'S': 0, 'Ca': 20, 'Mg': 0, 'price_per_kg': 0.52, 'category': 'NPK'},
        'Superphosphate': {'N': 0, 'P2O5': 20, 'K2O': 0, 'S': 12, 'Ca': 18, 'Mg': 0, 'price_per_kg': 0.45, 'category': 'NPK'},
        
        # Potassium fertilizers
        'Muriate_KCl': {'N': 0, 'P2O5': 0, 'K2O': 60, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.40, 'category': 'NPK'},
        'Sulfate_K2SO4': {'N': 0, 'P2O5': 0, 'K2O': 50, 'S': 18, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.48, 'category': 'NPK'},
        
        # NPK compound fertilizers with enhanced formulations
        'NPK_12_12_17_2S': {'N': 12, 'P2O5': 12, 'K2O': 17, 'S': 2, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.50, 'category': 'NPK'},
        'NPK_15_15_15': {'N': 15, 'P2O5': 15, 'K2O': 15, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.52, 'category': 'NPK'},
        'NPK_20_10_10': {'N': 20, 'P2O5': 10, 'K2O': 10, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.54, 'category': 'NPK'},
        'NPK_10_20_20': {'N': 10, 'P2O5': 20, 'K2O': 20, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.53, 'category': 'NPK'},
        'NPK_16_8_24_3S': {'N': 16, 'P2O5': 8, 'K2O': 24, 'S': 3, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.56, 'category': 'NPK'},
        
        # Nitrogen fertilizers
        'Urea': {'N': 46, 'P2O5': 0, 'K2O': 0, 'S': 0, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.35, 'category': 'NPK'},
        'Ammonium_sulfate': {'N': 21, 'P2O5': 0, 'K2O': 0, 'S': 24, 'Ca': 0, 'Mg': 0, 'price_per_kg': 0.32, 'category': 'NPK'},
        'Calcium_nitrate': {'N': 15.5, 'P2O5': 0, 'K2O': 0, 'S': 0, 'Ca': 19, 'Mg': 0, 'price_per_kg': 0.42, 'category': 'NPK'},
        
        # =====================================
        # SECONDARY NUTRIENT FERTILIZERS
        # =====================================
        'Gypsum': {'N': 0, 'P2O5': 0, 'K2O': 0, 'S': 18, 'Ca': 23, 'Mg': 0, 'price_per_kg': 0.25, 'category': 'Secondary'},
        'Lime_dolomitic': {'N': 0, 'P2O5': 0, 'K2O': 0, 'S': 0, 'Ca': 30, 'Mg': 18, 'price_per_kg': 0.15, 'category': 'Secondary'},
        'Magnesium_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'S': 13, 'Ca': 0, 'Mg': 16, 'price_per_kg': 0.45, 'category': 'Secondary'},
        'Calcium_sulfate': {'N': 0, 'P2O5': 0, 'K2O': 0, 'S': 18, 'Ca': 29, 'Mg': 0, 'price_per_kg': 0.28, 'category': 'Secondary'},
        'Sul_Po_Mag': {'N': 0, 'P2O5': 0, 'K2O': 22, 'S': 22, 'Ca': 0, 'Mg': 18, 'price_per_kg': 0.52, 'category': 'Secondary'},
        
        # =====================================
        # MICRONUTRIENT FERTILIZERS
        # =====================================
        'Iron_sulfate': {'Fe': 20, 'S': 11, 'price_per_kg': 1.2, 'category': 'Micronutrient'},
        'Iron_chelate_EDDHA': {'Fe': 6, 'price_per_kg': 8.5, 'category': 'Micronutrient'},
        'Zinc_sulfate': {'Zn': 35, 'S': 17, 'price_per_kg': 2.2, 'category': 'Micronutrient'},
        'Copper_sulfate': {'Cu': 25, 'S': 12, 'price_per_kg': 3.5, 'category': 'Micronutrient'},
        'Manganese_sulfate': {'Mn': 32, 'S': 15, 'price_per_kg': 2.8, 'category': 'Micronutrient'},
        'Boron_boric_acid': {'B': 17, 'price_per_kg': 4.2, 'category': 'Micronutrient'},
        'Molybdenum_sodium': {'Mo': 39, 'price_per_kg': 25.0, 'category': 'Micronutrient'},
        
        # =====================================
        # MULTI-NUTRIENT COMPLEX FERTILIZERS
        # =====================================
        'Complete_15_9_12_2Mg_1S': {'N': 15, 'P2O5': 9, 'K2O': 12, 'S': 1, 'Ca': 0, 'Mg': 2, 'price_per_kg': 0.58, 'category': 'Complete'},
        'Garden_mix_12_8_16_4S_2Mg': {'N': 12, 'P2O5': 8, 'K2O': 16, 'S': 4, 'Ca': 2, 'Mg': 2, 'price_per_kg': 0.62, 'category': 'Complete'},
        'Vegetable_special_18_6_12_3S_1Mg': {'N': 18, 'P2O5': 6, 'K2O': 12, 'S': 3, 'Ca': 1, 'Mg': 1, 'price_per_kg': 0.65, 'category': 'Complete'},
        
        # =====================================
        # MICRONUTRIENT MIXES
        # =====================================
        'Micro_mix_standard': {'Fe': 2.5, 'Mn': 1.5, 'Zn': 1.0, 'Cu': 0.5, 'B': 0.2, 'Mo': 0.05, 'price_per_kg': 5.5, 'category': 'Micronutrient'},
        'Micro_chelated_premium': {'Fe': 4.0, 'Mn': 2.0, 'Zn': 1.5, 'Cu': 0.8, 'B': 0.3, 'Mo': 0.1, 'price_per_kg': 12.0, 'category': 'Micronutrient'},
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
        crop_type = CropType(data.get('crop_type', 'general')) if data.get('crop_type') else CropType.GENERAL
        
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
        land_area_ha = float(data.get('land_area_ha', 1.0))
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
            product_ecce=product_ecce
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
    
    print("🔄 Creating testimonials table...")
    
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
    print("✅ Testimonials table created successfully!")

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
# 🏠 LANDING PAGE ROUTE
# =====================================

@app.route('/')
def index():
    """Landing page"""
    return render_template_string(LANDING_PAGE_TEMPLATE)

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
    """Enhanced dashboard with dynamic testimonials"""
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
    
    return render_template_string(ENHANCED_DASHBOARD_TEMPLATE,
                                user=user,
                                analyses=recent_analyses,
                                recipes=recent_recipes,
                                total_analyses=total_analyses,
                                total_recipes=total_recipes,
                                user_testimonial=user_testimonial)
    
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
        
        # Calculate enhanced lime requirement using SCIENTIFIC METHOD
        enhanced_lime_calculation = EnhancedLimeCalculator.calculate_enhanced_lime_requirement(
            exchangeable_acidity=float(data.get('exchangeable_acidity', 0)),
            lime_type=data.get('lime_type', 'caco3'),
            target_ae=float(data.get('target_ae', 0.5)),
            land_area_ha=land_area_ha,
            depth_cm=soil_depth_cm,
            bulk_density_g_cm3=bulk_density,
            particle_density_g_cm3=particle_density,
            product_ecce=product_ecce
        )
        
        # Generate comparison of all lime types
        lime_comparison = EnhancedLimeCalculator.compare_all_lime_types(
            exchangeable_acidity=float(data.get('exchangeable_acidity', 0)),
            target_ae=float(data.get('target_ae', 0.5)),
            land_area_ha=land_area_ha,
            depth_cm=soil_depth_cm,
            bulk_density_g_cm3=bulk_density,
            product_ecce=product_ecce
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
            print(f"✅ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass  # Column already exists
            else:
                print(f"❌ Error adding column {column_name}: {e}")
    
    conn.commit()
    conn.close()
    print("🗄️ Database migration completed!")



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
            'price': 19.99,
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

# =====================================
# 💬 TESTIMONIALS API ENDPOINTS
# =====================================

@app.route('/api/testimonials', methods=['GET'])
def api_get_testimonials():
    """Get all approved testimonials - public endpoint"""
    testimonials = query_db('''
        SELECT t.*, u.first_name, u.last_name
        FROM testimonials t
        JOIN users u ON t.user_id = u.id
        WHERE t.is_approved = TRUE
        ORDER BY t.created_at DESC
        LIMIT 10
    ''')
    
    result = []
    for testimonial in testimonials:
        result.append({
            'id': testimonial['id'],
            'user_name': f"{testimonial['first_name']} {testimonial['last_name']}",
            'user_title': testimonial['user_title'] or 'SoilsFert User',
            'comment': testimonial['comment'],
            'rating': testimonial['rating'],
            'created_at': testimonial['created_at'],
            'initials': f"{testimonial['first_name'][0]}{testimonial['last_name'][0]}"
        })
    
    return jsonify(result)

@app.route('/api/testimonials', methods=['POST'])
@login_required
def api_submit_testimonial():
    """Submit a new testimonial"""
    try:
        data = request.get_json()
        user_id = session['user_id']
        
        # Get user info
        user = query_db('SELECT first_name, last_name FROM users WHERE id = ?', [user_id], one=True)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Validate input
        comment = data.get('comment', '').strip()
        user_title = data.get('user_title', '').strip()
        rating = int(data.get('rating', 5))
        
        if len(comment) < 10:
            return jsonify({'error': 'Comment must be at least 10 characters long'}), 400
        
        if len(comment) > 500:
            return jsonify({'error': 'Comment must be less than 500 characters'}), 400
        
        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        
        # Check if user already submitted a testimonial recently (within 30 days)
        recent_testimonial = query_db('''
            SELECT id FROM testimonials 
            WHERE user_id = ? AND created_at > date('now', '-30 days')
        ''', [user_id], one=True)
        
        if recent_testimonial:
            return jsonify({'error': 'You can only submit one testimonial per month'}), 429
        
        # Insert testimonial
        execute_db('''
            INSERT INTO testimonials (user_id, user_name, user_title, comment, rating, is_approved)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            user_id,
            f"{user['first_name']} {user['last_name']}",
            user_title or 'SoilsFert User',
            comment,
            rating,
            True  # Auto-approve for now
        ])
        
        return jsonify({'success': True, 'message': 'Testimonial submitted successfully!'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
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
<body class="bg-white">
    <!-- Modern Navigation -->
    <nav class="bg-white/95 backdrop-blur-md shadow-sm border-b border-gray-100 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <!-- Logo Section -->
                <div class="flex items-center space-x-3">
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-2xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
                        SoilsFert
                    </span>
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
    <section class="relative overflow-hidden">
        <!-- Background Gradient -->
        <div class="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50"></div>
        
        <!-- Animated Background Elements -->
        <div class="absolute inset-0 overflow-hidden">
            <div class="absolute -top-40 -right-40 w-80 h-80 bg-gradient-to-r from-blue-400 to-purple-400 rounded-full opacity-10 animate-pulse"></div>
            <div class="absolute -bottom-40 -left-40 w-80 h-80 bg-gradient-to-r from-green-400 to-blue-400 rounded-full opacity-10 animate-pulse"></div>
        </div>

        <div class="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
            <div class="text-center">
                <!-- Main Headline -->
                <div class="mb-8">
                    <div class="inline-flex items-center px-4 py-2 bg-green-100 text-green-800 rounded-full text-sm font-medium mb-6">
                        <i class="fas fa-leaf mr-2"></i>
                        Professional Soil Analysis Platform
                    </div>
                    <h1 class="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 mb-6">
                        <span class="block">🌱 Smart Soil</span>
                        <span class="block bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 bg-clip-text text-transparent">
                            Analysis
                        </span>
                    </h1>
                    <p class="text-xl sm:text-2xl text-gray-600 max-w-4xl mx-auto leading-relaxed">
                        Get precise soil analysis with professional lime calculations and optimize your compost recipes with our advanced scientific platform.
                    </p>
                </div>

                <!-- CTA Buttons -->
                <div class="mb-12">
                    <div class="flex flex-col sm:flex-row justify-center items-center space-y-4 sm:space-y-0 sm:space-x-6">
                        <a href="{{ url_for('register') }}" 
                           class="inline-flex items-center px-8 py-4 bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 text-white text-lg font-semibold rounded-xl hover:from-green-700 hover:via-blue-700 hover:to-purple-700 transition-all transform hover:scale-105 shadow-xl">
                            <i class="fas fa-rocket mr-3"></i>
                            Start Free Analysis
                            <i class="fas fa-arrow-right ml-3"></i>
                        </a>
                        <a href="#demo" 
                           class="inline-flex items-center px-8 py-4 bg-white border-2 border-gray-300 text-gray-700 text-lg font-semibold rounded-xl hover:border-blue-500 hover:text-blue-600 transition-all transform hover:scale-105 shadow-lg">
                            <i class="fas fa-play mr-3"></i>
                            Watch Demo
                        </a>
                    </div>
                </div>

                <!-- Social Proof -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto">
                    <div class="flex items-center justify-center space-x-2 text-green-600">
                        <i class="fas fa-check-circle text-xl"></i>
                        <span class="font-semibold">3 Free Analyses</span>
                    </div>
                    <div class="flex items-center justify-center space-x-2 text-blue-600">
                        <i class="fas fa-check-circle text-xl"></i>
                        <span class="font-semibold">Scientific Method</span>
                    </div>
                    <div class="flex items-center justify-center space-x-2 text-purple-600">
                        <i class="fas fa-check-circle text-xl"></i>
                        <span class="font-semibold">No Credit Card</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section id="features" class="py-20 bg-white">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="text-center mb-16">
                <h2 class="text-4xl lg:text-5xl font-bold text-gray-900 mb-6">
                    Advanced Scientific Features
                </h2>
                <p class="text-xl text-gray-600 max-w-3xl mx-auto">
                    Soil analisis driven by rigorous scientific methodology
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                <!-- Feature 1: Professional Analysis -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-blue-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-blue-500 to-blue-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-microscope text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">🔬 Professional Analysis</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Complete soil testing with automatic CEC, cationic ratios, and precise lime calculations based on Exchangeable Acidity.
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Automatic CEC calculation
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Cationic ratios analysis
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Scientific lime recommendations
                        </li>
                    </ul>
                </div>

                <!-- Feature 2: Smart Lime Calculator -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-green-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-green-500 to-green-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-mountain text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">🪨 Smart Lime Calculator</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Choose from 5 lime types with precise kg/ha recommendations using the scientific formula: t/ha = 5 × ΔAE × ρb × d
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            5 lime types supported
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Physics-based calculations
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Cost optimization
                        </li>
                    </ul>
                </div>

                <!-- Feature 3: Smart Multi-Nutrient System -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-purple-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-purple-500 to-purple-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-cogs text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">⚙️ Smart Multi-Nutrient System</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Advanced fertilizer recommendations covering all nutrients with maximum compensation efficiency and cost optimization.
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Primary + Secondary + Micros
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Smart product selection
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Cost optimization algorithm
                        </li>
                    </ul>
                </div>

                <!-- Feature 4: Compost Calculator -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-orange-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-orange-500 to-orange-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-recycle text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">♻️ Compost Calculator</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Optimize compost recipes with carbon-nitrogen ratio calculations for maximum efficiency and quality scoring.
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            C:N ratio optimization
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Material recommendations
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Quality scoring system
                        </li>
                    </ul>
                </div>

                <!-- Feature 5: Complete Analysis -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-indigo-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-indigo-500 to-indigo-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-chart-line text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">📊 Complete Analysis</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Comprehensive reports with interactive charts, cost breakdowns, and actionable recommendations.
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Interactive charts & graphs
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Detailed cost analysis
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Printable reports
                        </li>
                    </ul>
                </div>

                <!-- Feature 6: Scientific Method -->
                <div class="group bg-white border border-gray-200 rounded-2xl p-8 hover:shadow-2xl hover:border-red-300 transition-all duration-300 transform hover:-translate-y-2">
                    <div class="bg-gradient-to-br from-red-500 to-red-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                        <i class="fas fa-graduation-cap text-white text-2xl"></i>
                    </div>
                    <h3 class="text-2xl font-bold text-gray-900 mb-4">🎓 Scientific Method</h3>
                    <p class="text-gray-600 leading-relaxed mb-6">
                        Based on peer-reviewed research and scientific formulas, not arbitrary conversion factors.
                    </p>
                    <ul class="space-y-2 text-sm text-gray-600">
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Peer-reviewed methods
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            Physics-based calculations
                        </li>
                        <li class="flex items-center">
                            <i class="fas fa-check text-green-500 mr-2"></i>
                            95% field accuracy
                        </li>
                    </ul>
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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
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
                    <li><a href="#" class="text-gray-400 hover:text-white transition-colors">Help Center</a></li>
                    <li><a href="#" class="text-gray-400 hover:text-white transition-colors">Documentation</a></li>
                    <li><a href="{{ url_for('contact') }}" class="text-gray-400 hover:text-white transition-colors">Contact Us</a></li>
                    <li><a href="#" class="text-gray-400 hover:text-white transition-colors">Privacy Policy</a></li>
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
                    <p class="text-gray-600 leading-relaxed mb-4">${testimonial.comment}</p>
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
                        const response = await fetch('/api/testimonials', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                user_title: userTitle,
                                comment: comment,
                                rating: rating
                            })
                        });
                        
                        const result = await response.json();
                        
                        if (response.ok) {
                            alert('Thank you for your testimonial! 🌟');
                            closeTestimonialModal();
                            loadTestimonials(); // Reload testimonials
                        } else {
                            alert(result.error || 'An error occurred');
                        }
                    } catch (error) {
                        console.error('Error submitting testimonial:', error);
                        alert('An error occurred while submitting your testimonial');
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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <a href="{{ url_for('index') }}" class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <a href="{{ url_for('index') }}" class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
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
                        {% if user.plan_type == 'pro' %}Premium features{% else %}Upgrade available{% endif %}
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
                    <p class="text-gray-600 leading-relaxed mb-4">${testimonial.comment}</p>
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
                alert('Comment must be at least 10 characters long');
                return;
            }
            
            if (comment.length > 500) {
                alert('Comment must be less than 500 characters');
                return;
            }
            
            try {
                const response = await fetch('/api/testimonials', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        user_title: userTitle,
                        comment: comment,
                        rating: rating
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Thank you for your testimonial!');
                    closeTestimonialModal();
                    loadTestimonials(); // Reload testimonials
                } else {
                    alert(result.error || 'An error occurred');
                }
            } catch (error) {
                console.error('Error submitting testimonial:', error);
                alert('An error occurred while submitting your testimonial');
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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
                    </span>
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
                                Crop Type *
                                <i class="fas fa-seedling text-green-500 ml-1"></i>
                            </label>
                            <select name="crop_type" required
                                    class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <option value="general">🌱 General Agriculture</option>
                                <option value="corn">🌽 Corn</option>
                                <option value="wheat">🌾 Wheat</option>
                                <option value="tomatoes">🍅 Tomatoes</option>
                                <option value="potatoes">🥔 Potatoes</option>
                                <option value="soybeans">🫘 Soybeans</option>
                                <option value="lettuce">🥬 Lettuce</option>
                                <option value="carrots">🥕 Carrots</option>
                                <option value="rice">🌾 Rice</option>
                                <option value="coffee">☕ Coffee</option>
                            </select>
                            <p class="text-xs text-gray-500">Optimizes nutrient recommendations</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Field Area (hectares)
                                <i class="fas fa-ruler-combined text-purple-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0.01" name="surface_area" value="1.0"
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
                            <input type="number" step="0.1" min="0" max="14" name="ph" required
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
                            <input type="number" step="0.1" min="0" name="organic_matter"
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="3.0">
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
                                Land Area (ha) *
                                <i class="fas fa-map text-blue-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0.01" name="land_area_ha" value="1.0" required
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   onchange="calculatePhysicalProperties()">
                            <p class="text-xs text-gray-500">Total field size</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Soil Depth (cm) *
                                <i class="fas fa-ruler-vertical text-orange-500 ml-1"></i>
                            </label>
                            <input type="number" step="1" min="5" max="100" name="soil_depth_cm" value="20" required
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
                            <input type="number" step="0.01" min="0" name="phosphorus_ppm" required
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="15.0">
                            <p class="text-xs text-gray-500">Available P in soil (critical for root development)</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Potassium (cmol+/kg) *
                                <i class="fas fa-bolt text-yellow-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0" name="potassium_cmol" required
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="0.4">
                            <p class="text-xs text-gray-500">Exchangeable K (essential for plant metabolism)</p>
                        </div>

                        <div class="space-y-2">
                            <label class="block text-sm font-medium text-gray-700">
                                Exchangeable Acidity (cmol+/kg) *
                                <i class="fas fa-exclamation-triangle text-red-500 ml-1"></i>
                            </label>
                            <input type="number" step="0.01" min="0" name="exchangeable_acidity" required
                                   class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                                   placeholder="1.2">
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
                                <input type="number" step="0.01" min="0" name="calcium_cmol" required
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
                                <p class="text-xs text-gray-500">Essential for CEC calculation</p>
                            </div>

                            <div class="space-y-2">
                                <label class="block text-sm font-medium text-gray-700">
                                    Magnesium (cmol+/kg) *
                                    <i class="fas fa-leaf text-green-500 ml-1"></i>
                                </label>
                                <input type="number" step="0.01" min="0" name="magnesium_cmol" required
                                       class="form-input w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors">
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
        const landArea = parseFloat(document.querySelector('input[name="land_area_ha"]')?.value) || 1.0;
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

    function updateLimeInfo() {
        const limeType = document.querySelector('select[name="lime_type"]')?.value || 'caco3';
        const infoEl = document.getElementById('lime-info');
        if (infoEl && limeTypes[limeType]) {
            infoEl.textContent = limeTypes[limeType];
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
            'input[name="land_area_ha"]',
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
            const landArea = document.querySelector('input[name="land_area_ha"]')?.value;
            console.log('Current input values after init:', { bulkDensity, depthCm, landArea });
        }, 500);
    });

    // Global functions for onclick handlers
    window.calculatePhysicalProperties = calculatePhysicalProperties;
    window.updateLimeInfo = updateLimeInfo;
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

# 📊 COMPLETE ENHANCED SOIL ANALYSIS RESULTS TEMPLATE WITH SMART MULTI-NUTRIENT SYSTEM
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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilFert Professional
                    </span>
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
                                <h3 class="text-xl font-semibold text-gray-900">Smart Multi-Nutrient Analysis</h3>
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
                        <div class="text-center p-4 bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg border border-green-200">
                            <div class="text-3xl font-bold text-green-600 mb-2">{{ result.summary.overall_efficiency }}%</div>
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

        <!-- Scientific Lime Calculation -->
        <div class="mb-8">
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-yellow-50 to-orange-50 px-6 py-4 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <div class="bg-yellow-500 rounded-lg p-2 mr-3">
                                <i class="fas fa-mountain text-white"></i>
                            </div>
                            <div>
                                <h3 class="text-xl font-semibold text-gray-900">Scientific Lime Calculation</h3>
                                <p class="text-sm text-gray-600">Physics-based lime recommendations</p>
                            </div>
                        </div>
                        <span class="px-3 py-1 bg-green-100 text-green-800 text-sm font-medium rounded-full">
                            {{ result.enhanced_lime_calculation.lime_needed_t_ha }} t/ha needed
                        </span>
                    </div>
                </div>
                <div class="p-6">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <!-- Lime Requirements -->
                        <div>
                            <div class="grid grid-cols-2 gap-4 mb-6">
                                <div class="text-center p-4 bg-gradient-to-br from-yellow-50 to-orange-50 rounded-lg border border-yellow-200">
                                    <div class="text-2xl font-bold text-yellow-600">{{ result.enhanced_lime_calculation.lime_needed_t_ha }}</div>
                                    <div class="text-sm text-gray-600 font-medium">{{ result.enhanced_lime_calculation.lime_name.split('(')[0].strip() }}</div>
                                    <div class="text-xs text-gray-500">{{ result.enhanced_lime_calculation.lime_formula }}</div>
                                </div>
                                <div class="text-center p-4 bg-green-50 rounded-lg">
                                    <div class="text-2xl font-bold text-green-600">{{ result.enhanced_lime_calculation.caco3_eq_t_ha }}</div>
                                    <div class="text-sm text-gray-600 font-medium">CaCO₃-Equivalent</div>
                                    <div class="text-xs text-gray-500">Base calculation</div>
                                </div>
                            </div>
                            
                            <!-- Scientific Formula -->
                            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                                <h5 class="font-semibold text-blue-800 mb-2 flex items-center">
                                    <i class="fas fa-calculator mr-2"></i>
                                    Scientific Formula
                                </h5>
                                <div class="text-sm text-blue-700 space-y-2">
                                    <p><strong>t/ha = 5 × ΔAE × ρb × d</strong></p>
                                    <div class="grid grid-cols-2 gap-2 text-xs">
                                        <div>ΔAE: {{ result.enhanced_lime_calculation.ae_to_neutralize }} cmol+/kg</div>
                                        <div>ρb: {{ result.bulk_density }} g/cm³</div>
                                        <div>d: {{ result.enhanced_lime_calculation.depth_m }} m</div>
                                        <div>CCE: {{ result.enhanced_lime_calculation.cce_factor }}</div>
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
                    <h3 class="text-xl font-semibold text-gray-900 flex items-center">
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

        <!-- Recommendations & Limiting Factors -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- Limiting Factors -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-red-50 to-pink-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-exclamation-triangle mr-2 text-red-500"></i>
                        Limiting Factors
                    </h3>
                </div>
                <div class="p-6">
                    {% if result.limiting_factors %}
                        <div class="space-y-3">
                            {% for factor in result.limiting_factors %}
                            <div class="flex items-center p-3 bg-red-50 border border-red-200 rounded-lg">
                                <i class="fas fa-exclamation-circle text-red-500 mr-3"></i>
                                <span class="font-medium text-red-800">{{ factor }}</span>
                            </div>
                            {% endfor %}
                        </div>
                    {% else %}
                        <div class="text-center py-8">
                            <div class="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <i class="fas fa-check text-green-500 text-xl"></i>
                            </div>
                            <h4 class="text-lg font-medium text-gray-900 mb-2">No Major Issues</h4>
                            <p class="text-green-800 font-medium">🎉 No significant limiting factors identified!</p>
                        </div>
                    {% endif %}
                </div>
            </div>

            <!-- Priority Actions -->
            <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i class="fas fa-lightbulb mr-2 text-blue-500"></i>
                        Priority Actions
                    </h3>
                </div>
                <div class="p-6">
                    <div class="space-y-3">
                        {% for recommendation in result.recommendations[:5] %}
                        <div class="flex items-start p-3 bg-blue-50 border border-blue-200 rounded-lg">
                            <i class="fas fa-arrow-right text-blue-500 mr-3 mt-1 flex-shrink-0"></i>
                            <p class="text-sm text-blue-800">{{ recommendation }}</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>

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
                    <div class="bg-gradient-to-r from-green-500 to-emerald-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
                    </span>
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

# ♻️ COMPOST RESULT TEMPLATE
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
                    <div class="bg-gradient-to-r from-green-500 to-emerald-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <span class="text-xl font-bold">SoilsFert Professional</span>
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
                    <div class="w-10 h-10 bg-gradient-to-br from-soil-green-500 to-soil-green-600 rounded-xl flex items-center justify-center">
                        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
                        </svg>
                    </div>
                    <span class="text-xl font-bold text-slate-900">SoilFert</span>
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
                                <a href="{{ url_for('upgrade_plan', plan=plan_id) }}" 
                                   class="block w-full bg-gradient-to-r {% if plan_id == 'pro' %}from-soil-green-600 to-soil-green-700 hover:from-soil-green-700 hover:to-soil-green-800{% else %}from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800{% endif %} text-white py-3 px-4 rounded-xl transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 font-semibold">
                                    {% if plan.price == 0 %}Switch to Free{% else %}Upgrade to Pro{% endif %}
                                </a>
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

# Read secrets from environment (set these in systemd)
MAIL_SERVER   = "smtp.hostinger.com"                     # works on your VPS
MAIL_USERNAME = os.environ["MAIL_USERNAME"]              # e.g. contact@soilsfert.com
MAIL_PASSWORD = os.environ["MAIL_PASSWORD"]              # set in systemd drop-in
ADMIN_EMAIL   = os.environ.get("ADMIN_EMAIL", MAIL_USERNAME)

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
    """Send contact form email using Hostinger SMTP with SSL→STARTTLS fallback."""
    msg = _build_msg(name, email, subject, message)
    ctx = ssl.create_default_context()
    # Try SSL 465 first
    try:
        with smtplib.SMTP_SSL(MAIL_SERVER, 465, timeout=20, context=ctx) as s:
            s.login(MAIL_USERNAME, MAIL_PASSWORD)
            s.send_message(msg)
        print("✅ Email sent via SSL:465")
        return True
    except Exception as e1:
        print("⚠️ SSL:465 failed, trying STARTTLS:587 ->", repr(e1))
        # Fallback to STARTTLS 587
        try:
            with smtplib.SMTP(MAIL_SERVER, 587, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(MAIL_USERNAME, MAIL_PASSWORD)
                s.send_message(msg)
            print("✅ Email sent via STARTTLS:587")
            return True
        except Exception as e2:
            print("❌ Email send failed:", repr(e2))
            return False

# =====================================
# 🧪 EMAIL TEST FUNCTION (runs the same sender)
# =====================================
def test_email_configuration() -> bool:
    print("🧪 Testing email configuration...")
    print(f"📧 SMTP Server: {MAIL_SERVER}")
    print(f"👤 Username: {MAIL_USERNAME}")
    print(f"📮 Admin Email: {ADMIN_EMAIL}")

    ok = send_contact_email(
        name="Test User",
        email="test@example.com",
        subject="Email Configuration Test",
        message="This is a test sent from the SoilsFert VPS using env vars and UTF-8."
    )
    if ok:
        print("✅ Email configuration test PASSED!")
    else:
        print("❌ Email configuration test FAILED. Check logs above.")
    return ok


# =====================================
# 📧 EMAIL TEST FUNCTION
# =====================================

def test_email_configuration():
    """Test email configuration"""
    print("🧪 Testing email configuration...")
    print(f"📧 SMTP Server: {app.config['MAIL_SERVER']}")
    print(f"🔌 Port: {app.config['MAIL_PORT']}")
    print(f"👤 Username: {app.config['MAIL_USERNAME']}")
    print(f"📮 Admin Email: {app.config['ADMIN_EMAIL']}")
    
    # Send test email
    success = send_contact_email(
        name="Test User",
        email="test@example.com",
        subject="Email Configuration Test",
        message="This is a test message to verify that the email configuration is working correctly with Hostinger SMTP."
    )
    
    if success:
        print("✅ Email configuration test PASSED!")
        print("🎉 Contact form emails will work correctly")
    else:
        print("❌ Email configuration test FAILED!")
        print("🔧 Please check your credentials and try again")
    
    return success
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
    print("✅ Contacts table created successfully!")

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
                    <div class="bg-gradient-to-r from-green-500 to-blue-500 p-2 rounded-lg">
                        <i class="fas fa-seedling text-white text-xl"></i>
                    </div>
                    <a href="{{ url_for('index') }}" class="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                        SoilsFert Professional
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
    print("🔧 Initializing database...")
    init_db()
    
    # Complete migration including physical parameters
    print("🔄 Migrating database with enhanced physical parameters...")
    complete_database_migration()
    
    # Add testimonials table
    print("🔄 Creating testimonials table...")
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
        print("✅ Demo user created: demo@soilfert.com / demo123")
    else:
        print("✅ Demo user already exists")
    
    print("\n🌱 SoilFert Enhanced Professional Application Starting...")
    print("=" * 80)
    print("🧪 NEW FEATURE: Dynamic Testimonials System")
    print("   💬 Users can submit their own testimonials")
    print("   📱 Horizontally scrollable testimonials display")
    print("   ⭐ 5-star rating system")
    print("   🚀 Real-time updates and modern UI")
    print("=" * 80)
    print("🧪 ENHANCED FEATURES AVAILABLE:")
    print("   🌍 PHYSICAL PARAMETERS: Bulk density, particle density, porosity calculation")
    print("   📏 VOLUME & MASS: Precise soil volume and mass calculations")
    print("   🪨 ENHANCED LIME CALCULATOR: Density and depth adjusted lime requirements")
    print("   💰 TOTAL COST ESTIMATION: Per hectare and total field costs")
    print("   🔬 COMPLETE SOIL ANALYSIS: All nutrients + physical properties")
    print("   ⚖️ AUTOMATIC CALCULATIONS: CEC, cationic ratios, porosity")
    print("=" * 80)
    print("🌐 Visit: http://localhost:5000")
    print("🧪 Demo: demo@soilfert.com / demo123")
    print("🪨 Try the Enhanced Lime Calculator with Physical Parameters!")
    print("💬 NEW: Try the Dynamic Testimonials System!")
    print("=" * 80)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)