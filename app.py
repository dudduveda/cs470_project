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

class RestaurantPreference(BaseModel):
    restaurant_id: int
    rating: float = Field(..., ge=1.0, le=10.0, description="Rating from 1.0 to 10.0")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return round(v, 1)  # Round to 1 decimal place

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    preferences: Optional[List[RestaurantPreference]] = Field(default_factory=list)

class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cuisine: str = Field(..., min_length=1, max_length=50)
    price: int = Field(..., ge=1, le=4, description="Price level from 1 ($) to 4 ($$)")

class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cuisine: Optional[str] = Field(None, min_length=1, max_length=50)
    price: Optional[int] = Field(None, ge=1, le=4)

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                price INTEGER NOT NULL CHECK(price >= 1 AND price <= 4),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                restaurant_id INTEGER NOT NULL,
                rating REAL NOT NULL CHECK(rating >= 1.0 AND rating <= 10.0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE,
                UNIQUE(user_id, restaurant_id)
            )
        ''')
        
        # Check if restaurants table is empty and seed with initial data
        count = conn.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
        if count == 0:
            seed_restaurants(conn)

def seed_restaurants(conn):
    """Seed the database with initial restaurants"""
    initial_restaurants = [
        # Italian
        ("Mama Mia Trattoria", "Italian", 3),
        ("Pizza Napoli", "Italian", 2),
        ("Bella Vista", "Italian", 4),
        
        # Mexican
        ("Taco Fiesta", "Mexican", 1),
        ("El Mariachi", "Mexican", 2),
        ("Casa Grande", "Mexican", 3),
        
        # Chinese
        ("Golden Dragon", "Chinese", 2),
        ("Szechuan Palace", "Chinese", 3),
        ("Dim Sum House", "Chinese", 2),
        
        # Japanese
        ("Sakura Sushi", "Japanese", 3),
        ("Ramen Bowl", "Japanese", 2),
        ("Tokyo Grill", "Japanese", 4),
        
        # American
        ("The Burger Joint", "American", 2),
        ("Steakhouse Prime", "American", 4),
        ("Diner Deluxe", "American", 1),
        
        # Indian
        ("Curry House", "Indian", 2),
        ("Taj Mahal", "Indian", 3),
        ("Bombay Spice", "Indian", 2),
        
        # Thai
        ("Thai Basil", "Thai", 2),
        ("Bangkok Street Food", "Thai", 1),
        ("Royal Thai", "Thai", 3),
        
        # French
        ("Le Petit Bistro", "French", 4),
        ("Café Paris", "French", 3),
        
        # Mediterranean
        ("Olive Garden Bistro", "Mediterranean", 3),
        ("Greek Taverna", "Mediterranean", 2),
    ]
    
    conn.executemany(
        'INSERT INTO restaurants (name, cuisine, price) VALUES (?, ?, ?)',
        initial_restaurants
    )
    print(f"\n✅ Seeded database with {len(initial_restaurants)} restaurants")

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
                # Get preferences for this user
                prefs = conn.execute(
                    '''SELECT restaurant_id, rating 
                       FROM user_preferences 
                       WHERE user_id = ?''',
                    (user_dict['id'],)
                ).fetchall()
                user_dict['preferences'] = [
                    {'restaurant_id': p['restaurant_id'], 'rating': p['rating']} 
                    for p in prefs
                ]
                users_list.append(user_dict)
            return jsonify(users_list)
    
    elif request.method == 'POST':
        try:
            user_data = UserCreate(**request.json)
            with get_db() as conn:
                # Insert user
                cursor = conn.execute(
                    'INSERT INTO users (username) VALUES (?)',
                    (user_data.username,)
                )
                user_id = cursor.lastrowid
                
                # Insert preferences
                if user_data.preferences:
                    for pref in user_data.preferences:
                        conn.execute(
                            '''INSERT INTO user_preferences (user_id, restaurant_id, rating)
                               VALUES (?, ?, ?)''',
                            (user_id, pref.restaurant_id, pref.rating)
                        )
                
                return jsonify({
                    'id': user_id, 
                    'message': 'User created',
                    'preferences': [p.model_dump() for p in user_data.preferences]
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
                # Get preferences for this user
                prefs = conn.execute(
                    '''SELECT restaurant_id, rating 
                       FROM user_preferences 
                       WHERE user_id = ?''',
                    (user_id,)
                ).fetchall()
                user_dict['preferences'] = [
                    {'restaurant_id': p['restaurant_id'], 'rating': p['rating']} 
                    for p in prefs
                ]
                return jsonify(user_dict)
            return jsonify({'error': 'User not found'}), 404
    
    elif request.method == 'DELETE':
        with get_db() as conn:
            # Check if user exists
            row = conn.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
            if not row:
                return jsonify({'error': 'User not found'}), 404
            
            # Delete user (preferences will be deleted automatically due to CASCADE)
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
            return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/api/restaurants', methods=['GET', 'POST'])
def restaurants():
    if request.method == 'GET':
        with get_db() as conn:
            rows = conn.execute('SELECT * FROM restaurants ORDER BY name ASC').fetchall()
            return jsonify([dict(row) for row in rows])
    
    elif request.method == 'POST':
        try:
            restaurant_data = RestaurantCreate(**request.json)
            with get_db() as conn:
                cursor = conn.execute(
                    '''INSERT INTO restaurants (name, cuisine, price)
                       VALUES (?, ?, ?)''',
                    (restaurant_data.name, restaurant_data.cuisine, 
                     restaurant_data.price)
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
    """Search restaurants by cuisine or price"""
    cuisine = request.args.get('cuisine')
    max_price = request.args.get('max_price', type=int)
    
    with get_db() as conn:
        query = 'SELECT * FROM restaurants WHERE 1=1'
        params = []
        
        if cuisine:
            query += ' AND cuisine LIKE ?'
            params.append(f'%{cuisine}%')
        if max_price:
            query += ' AND price <= ?'
            params.append(max_price)
        
        query += ' ORDER BY name ASC'
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
    print("  GET  /api/restaurants/search?cuisine=&max_price=")
    print("\n" + "="*50 + "\n")
    app.run(debug=True, port=5000)