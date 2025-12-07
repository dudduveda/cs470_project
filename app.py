"""
Full Stack App: Users & Restaurants with SQLite
Run: python app.py
Then open: http://localhost:5000
"""
from enum import Enum
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from restaurants import initial_restaurants
import math
app = Flask(__name__)



CORS(app)
r_list = initial_restaurants()
# Database configuration
DB_PATH = 'app.db'

class Util(Enum):
    min_utility_maxing = 0
    total_utility_maxing = 1
    nash_welfare = 2


# toggle between these
ns_value = 1.2
utility_scheme = Util.total_utility_maxing

# ==================== Pydantic Models ====================

class RestaurantPreference(BaseModel):
    restaurant_id: int
    rating: float = Field(..., ge=1.0, le=10.0, description="Rating from 1.0 to 10.0")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return round(v, 1)  # Round to 1 decimal place

class CuisinePreference(BaseModel):
    cuisine: str = Field(..., min_length=1, max_length=50)
    rating: float = Field(..., ge=1.0, le=10.0, description="Rating from 1.0 to 10.0")
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return round(v, 1)  # Round to 1 decimal place

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    preferences: Optional[List[RestaurantPreference]] = Field(default_factory=list)
    cuisine_preferences: Optional[List[CuisinePreference]] = Field(default_factory=list)

class RestaurantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    cuisine: str = Field(..., min_length=1, max_length=50)
    price: int = Field(..., ge=1, le=3, description="Price level from 1 ($) to 3 ($$)")

class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    cuisine: Optional[str] = Field(None, min_length=1, max_length=50)
    price: Optional[int] = Field(None, ge=1, le=3)


class DayOfRating(BaseModel):
    rating: float = Field(..., ge=1.0, le=10.0)
    restaurant_id: Optional[int] = None
    cuisine: Optional[str] = None
    
    @field_validator("rating")
    @classmethod
    def round_rating(cls, v):
        return round(v, 1)
    
    @model_validator(mode="after")
    def validate_choice(self):
        r = self.restaurant_id
        c = self.cuisine
        
        if not r and not c:
            raise ValueError("Must include restaurant_id OR cuisine")
        if r and c:
            raise ValueError("Cannot include both restaurant_id AND cuisine")
        return self


class DayOfRatingsBulk(BaseModel):
    user_id: int
    ratings: List[DayOfRating]

    @field_validator("ratings")
    @classmethod
    def validate_max_three(cls, v):
        if len(v) > 3:
            raise ValueError("Maximum of 3 ratings allowed")
        return v

class Matching(BaseModel):
    user_ratings: List[DayOfRatingsBulk]

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
                price INTEGER NOT NULL CHECK(price >= 1 AND price <= 3),
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
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_cuisine_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                cuisine TEXT NOT NULL,
                rating REAL NOT NULL CHECK(rating >= 1.0 AND rating <= 10.0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, cuisine)
            )
        ''')

        # conn.execute('''
        #     CREATE TABLE IF NOT EXISTS day_of_ratings (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         user_id INTEGER NOT NULL,
        #         restaurant_id INTEGER,
        #         cuisine TEXT,
        #         rating REAL NOT NULL CHECK(rating >= 1.0 AND rating <= 10.0),
        #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        #         FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        #     )
        # ''')
        
        # Check if restaurants table is empty and seed with initial data
        count = conn.execute('SELECT COUNT(*) FROM restaurants').fetchone()[0]
        if count == 0:
            seed_restaurants(conn)

def seed_restaurants(conn):
    """Seed the database with initial restaurants"""

    conn.executemany(
        'INSERT INTO restaurants (name, cuisine, price) VALUES (?, ?, ?)',
        r_list
    )
    print(f"\n✅ Seeded database with {len(r_list)} restaurants")

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
                
                # Get restaurant preferences for this user
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
                
                # Get cuisine preferences for this user
                cuisine_prefs = conn.execute(
                    '''SELECT cuisine, rating 
                       FROM user_cuisine_preferences 
                       WHERE user_id = ?''',
                    (user_dict['id'],)
                ).fetchall()
                user_dict['cuisine_preferences'] = [
                    {'cuisine': p['cuisine'], 'rating': p['rating']} 
                    for p in cuisine_prefs
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
                
                # Insert restaurant preferences
                if user_data.preferences:
                    for pref in user_data.preferences:
                        conn.execute(
                            '''INSERT INTO user_preferences (user_id, restaurant_id, rating)
                               VALUES (?, ?, ?)''',
                            (user_id, pref.restaurant_id, pref.rating)
                        )
                
                # Insert cuisine preferences
                if user_data.cuisine_preferences:
                    for pref in user_data.cuisine_preferences:
                        conn.execute(
                            '''INSERT INTO user_cuisine_preferences (user_id, cuisine, rating)
                               VALUES (?, ?, ?)''',
                            (user_id, pref.cuisine, pref.rating)
                        )
                
                return jsonify({
                    'id': user_id, 
                    'message': 'User created',
                    'preferences': [p.model_dump() for p in user_data.preferences],
                    'cuisine_preferences': [p.model_dump() for p in user_data.cuisine_preferences]
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
                
                # Get restaurant preferences for this user
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
                
                # Get cuisine preferences for this user
                cuisine_prefs = conn.execute(
                    '''SELECT cuisine, rating 
                       FROM user_cuisine_preferences 
                       WHERE user_id = ?''',
                    (user_id,)
                ).fetchall()
                user_dict['cuisine_preferences'] = [
                    {'cuisine': p['cuisine'], 'rating': p['rating']} 
                    for p in cuisine_prefs
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

@app.route('/api/day-of-ratings/bulk', methods=['POST'])
def save_dayof_ratings_bulk():
    try:
        data = DayOfRatingsBulk(**request.json)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400

    with get_db() as conn:
        # Check if user exists
        row = conn.execute(
            'SELECT id FROM users WHERE id = ?', 
            (data.user_id,)
        ).fetchone()

        if not row:
            return jsonify({"error": "User does not exist"}), 404

        # ❗ Remove old day-of ratings for this user
        conn.execute(
            "DELETE FROM day_of_ratings WHERE user_id = ?", 
            (data.user_id,)
        )

        # Insert new ones
        for rating in data.ratings:
            conn.execute('''
                INSERT INTO day_of_ratings (user_id, restaurant_id, cuisine, rating)
                VALUES (?, ?, ?, ?)
            ''', (
                data.user_id,
                rating.restaurant_id,
                rating.cuisine,
                rating.rating
            ))

    return jsonify({"message": "Day-of ratings saved"}), 200
max_utility = 100

# sigmoid like shape to explain the phenomena of extrema being more comparable
def dayofrestupdate(rating):
    return 2 / (1 + math.exp(-2 * (rating - 5.5)))
def dayofcuisineupdate(rating):
    return 2 / (1 + math.exp(-1 * (rating - 5.5)))
def user_utility(dayof):
    userId = dayof.user_id
    dayofratings = dayof.ratings
    dayofrests = {x.restaurant_id: x.rating for x in dayofratings if x.restaurant_id is not None}
    dayofcuisines = {x.cuisine: x.rating for x in dayofratings if x.cuisine is not None}

    if userId is None:
        return [max_utility for i in range(len(r_list))]
    
    with get_db() as conn:
        rests = conn.execute('''
            SELECT restaurant_id, rating 
            FROM user_preferences
            WHERE user_id = ?
            ORDER BY restaurant_id ASC
        ''',
        (userId,)
        ).fetchall()
        
        cuisines = conn.execute('''
            SELECT cuisine, rating 
            FROM user_cuisine_preferences
            WHERE user_id = ?
            ORDER BY cuisine ASC
        ''', 
        (userId,) 
        ).fetchall()
        
        # Convert to dict for easier lookup
        rests_dict = {r['restaurant_id']: r['rating'] for r in rests}
        cuisines_dict = {c['cuisine']: c['rating'] for c in cuisines}
        
        output = []
        for i, rest in enumerate(r_list):
            # Get base rating (either from restaurant pref or cuisine pref)
            if i in rests_dict:
                value = rests_dict[i]
            else:
                # Use max cuisine rating if restaurant not rated
                cuisine_ratings = [cuisines_dict.get(c.strip(), 5.0) for c in rest[1].split(",")]
                value = max(cuisine_ratings) if cuisine_ratings else 5.0
            
            # Apply day-of restaurant modifier if exists
            if i in dayofrests:
                value *= dayofrestupdate(dayofrests[i])
            
            # Apply day-of cuisine modifier if exists
            for cuisine in rest[1].split(","):
                cuisine = cuisine.strip()
                if cuisine in dayofcuisines:
                    value *= dayofcuisineupdate(dayofcuisines[cuisine])
            
            output.append(value * ns_value)
    
    return output


@app.route('/api/matching', methods=["POST"])
def matching():
    try:
        data = Matching(**request.json)
    except Exception as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    utilities = []
    for dayof in data.user_ratings:
        utilities.append(user_utility(dayof))
    # min utility maximizing
    if utility_scheme == Util.min_utility_maxing:
        ans = []
        for i in range(len(r_list)):
            worst = max_utility
            for utility in utilities:
                worst = min(worst, utility[i])
            ans.append((i, worst))
        ans.sort(key=lambda x: x[1],reverse=True)
    # total utility maximizing
    elif utility_scheme == Util.total_utility_maxing:
        ans = []
        for i in range(len(r_list)):
            total = 0
            for utility in utilities:
                total += utility[i]
            ans.append((i, total))
        ans.sort(key=lambda x: x[1],reverse=True)
        # return [i for (i, v) in ans]   
    elif utility_scheme == Util.nash_welfare:
        ans = []
        for i in range(len(r_list)):
            total = 1
            for utility in utilities:
                total *= utility[i]
            ans.append((i, total))
        ans.sort(key=lambda x: x[1],reverse=True)
        # return [i for (i, v) in ans]   
    else:

        print("something bad happened, utility scheme inval")
        return []
    return [(r_list[i][0], r_list[i][1], v) for (i, v) in ans]


# ==================== Main ====================



if __name__ == '__main__':
    init_db()
    # print("\n" + "="*50)
    # print("🚀 Users & Restaurants App Started!")
    # print("="*50)
    # print("\n📱 Open in browser: http://localhost:5000")
    # print("\n📡 API Endpoints:")
    # print("  GET  /api/health")
    # print("  GET  /api/users")
    # print("  POST /api/users")
    # print("  GET  /api/users/<id>")
    # print("  DELETE /api/users/<id>")
    # print("  GET  /api/restaurants")
    # print("  POST /api/restaurants")
    # print("  GET  /api/restaurants/<id>")
    # print("  PUT  /api/restaurants/<id>")
    # print("  DELETE /api/restaurants/<id>")
    # print("  GET  /api/restaurants/search?cuisine=&max_price=")
    # print("\n" + "="*50 + "\n")
    app.run(debug=True, port=5000)