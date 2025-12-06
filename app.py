"""
Full Stack App: Users & Restaurants with SQLite
Run: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

app = Flask(__name__)
CORS(app)

# Database configuration
DB_PATH = 'app.db'

# ==================== Pydantic Models ====================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    preferences: Optional[List[int]] = Field(default_factory=list)

class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cuisine: str = Field(..., min_length=1, max_length=50)
    price: int = Field(..., ge=1, le=4, description="Price level from 1 ($) to 4 ($$$$)")
    rating: float = Field(..., ge=0, le=5, description="Rating from 0 to 5")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return round(v, 1)  # Round to 1 decimal place

class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cuisine: Optional[str] = Field(None, min_length=1, max_length=50)
    price: Optional[int] = Field(None, ge=1, le=4)
    rating: Optional[float] = Field(None, ge=0, le=5)
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        if v is not None:
            return round(v, 1)
        return v

# ==================== Database Layer ====================

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database schema"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                price INTEGER NOT NULL CHECK(price >= 1 AND price <= 4),
                rating REAL NOT NULL CHECK(rating >= 0 AND rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

# ==================== Frontend Route ====================

@app.route('/')
def index():
    """Serve the frontend HTML"""
    return render_template("index.html")

# ==================== API Routes ====================

@app.route('/api/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
            users_list = []
            for row in rows:
                user_dict = dict(row)
                # Parse preferences JSON string to list
                if user_dict.get('preferences'):
                    try:
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                    except:
                        user_dict['preferences'] = []
                else:
                    user_dict['preferences'] = []
                users_list.append(user_dict)
            return jsonify(users_list)
    
    elif request.method == 'POST':
        try:
            user_data = UserCreate(**request.json)
            with get_db() as conn:
                # Convert preferences list to JSON string
                preferences_json = json.dumps(user_data.preferences)
                cursor = conn.execute(
                    'INSERT INTO users (username, preferences) VALUES (?, ?)',
                    (user_data.username, preferences_json)
                )
                return jsonify({
                    'id': cursor.lastrowid, 
                    'message': 'User created',
                    'preferences': user_data.preferences
                }), 201
        except sqlite3.IntegrityError as e:
            return jsonify({'error': f'Username already exists: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Validation error: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/users/<int:user_id>', methods=['GET', 'DELETE'])
def user_detail(user_id):
    if request.method == 'GET':
        with get_db() as conn:
            row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
            if row:
                user_dict = dict(row)
                # Parse preferences JSON string to list
                if user_dict.get('preferences'):
                    try:
                        user_dict['preferences'] = json.loads(user_dict['preferences'])
                    except:
                        user_dict['preferences'] = []
                else:
                    user_dict['preferences'] = []
                return jsonify(user_dict)
            return jsonify({'error': 'User not found'}), 404
    
    elif request.method == 'DELETE':
        with get_db() as conn:
            # Check if user exists
            row = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
            if not row:
                return jsonify({'error': 'User not found'}), 404
            
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/api/restaurants', methods=['GET', 'POST'])
def restaurants():
    if request.method == 'GET':
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM restaurants ORDER BY rating DESC, created_at DESC').fetchall()
            return jsonify([dict(row) for row in rows])
    
    elif request.method == 'POST':
        try:
            restaurant_data = RestaurantCreate(**request.json)
            with get_db() as conn:
                cursor = conn.execute(
                    '''INSERT INTO restaurants (name, cuisine, price, rating)
                       VALUES (?, ?, ?, ?)''',
                    (restaurant_data.name, restaurant_data.cuisine, 
                     restaurant_data.price, restaurant_data.rating)
                )
                return jsonify({
                    'id': cursor.lastrowid, 
                    'message': 'Restaurant created',
                    'data': restaurant_data.model_dump()
                }), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@app.route('/api/restaurants/<int:restaurant_id>', methods=['GET', 'PUT', 'DELETE'])
def restaurant_detail(restaurant_id):
    if request.method == 'GET':
        with get_db() as conn:
            row = conn.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,)).fetchone()
            if row:
                return jsonify(dict(row))
            return jsonify({'error': 'Restaurant not found'}), 404
    
    elif request.method == 'PUT':
        try:
            restaurant_data = RestaurantUpdate(**request.json)
            with get_db() as conn:
                # Build dynamic update query based on provided fields
                updates = []
                params = []
                data_dict = restaurant_data.model_dump(exclude_none=True)
                
                for field, value in data_dict.items():
                    updates.append(f"{field} = ?")
                    params.append(value)
                
                if not updates:
                    return jsonify({'error': 'No fields to update'}), 400
                
                params.append(restaurant_id)
                query = f"UPDATE restaurants SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
                
                conn.execute(query, params)
                return jsonify({'message': 'Restaurant updated', 'data': data_dict})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    elif request.method == 'DELETE':
        with get_db() as conn:
            conn.execute('DELETE FROM restaurants WHERE id = ?', (restaurant_id,))
            return jsonify({'message': 'Restaurant deleted'})

@app.route('/api/restaurants/search', methods=['GET'])
def search_restaurants():
    """Search restaurants by cuisine, price, or rating"""
    cuisine = request.args.get('cuisine')
    max_price = request.args.get('max_price', type=int)
    min_rating = request.args.get('min_rating', type=float)
    
    with get_db() as conn:
        query = 'SELECT * FROM restaurants WHERE 1=1'
        params = []
        
        if cuisine:
            query += ' AND cuisine LIKE ?'
            params.append(f'%{cuisine}%')
        if max_price:
            query += ' AND price <= ?'
            params.append(max_price)
        if min_rating:
            query += ' AND rating >= ?'
            params.append(min_rating)
        
        query += ' ORDER BY rating DESC'
        rows = conn.execute(query, params).fetchall()
        return jsonify([dict(row) for row in rows])

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ==================== Main ====================

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("🚀 Users & Restaurants App Started!")
    print("="*50)
    print("\n📱 Open in browser: http://localhost:5000")
    print("\n📡 API Endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/users")
    print("  POST /api/users")
    print("  GET  /api/users/<id>")
    print("  DELETE /api/users/<id>")
    print("  GET  /api/restaurants")
    print("  POST /api/restaurants")
    print("  GET  /api/restaurants/<id>")
    print("  PUT  /api/restaurants/<id>")
    print("  DELETE /api/restaurants/<id>")
    print("  GET  /api/restaurants/search?cuisine=&max_price=&min_rating=")
    print("\n" + "="*50 + "\n")
    app.run(debug=True, port=5000)