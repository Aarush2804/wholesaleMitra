# app.py
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
from flask import session
import secrets

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # Allows smooth frontend-backend connection

db_config = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', 'SECRET_PLACEHOLDER'), # Safe placeholder
    'database': os.environ.get('DB_NAME', 'wholesaledb')
}

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="wholesale_pool",
        pool_size=5,
        **db_config
    )
    print("✅ MySQL Connection Pool established dynamically.")
except Exception as e:
    print(f"❌ Error creating connection pool: {e}")

# Keep your function below it as a fallback tool
def get_db_connection():
    try:
        return db_pool.get_connection()
    except Exception:
        # Fallback if pool is exhausted or fails
        return mysql.connector.connect(**db_config, autocommit=True)

# Route to serve our frontend homepage
@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')



# Set a secret key so Flask can safely handle user sessions/logins
app.secret_key = 'your_super_secret_session_key'

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Look up the user directly by credentials
        query = "SELECT userID, roleID FROM Users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid username or password"}), 401

        session['user_id'] = user['userID']
        
        # Explicit mapping by numerical roleID
        if user['roleID'] == 1:
            session['role'] = 'Admin'
            session['segment'] = 'large' # Lowercase matches new column names
            return jsonify({"message": "Welcome Admin!", "role": "Admin"}), 200
            
        elif user['roleID'] == 2:
            session['role'] = 'Customer'
            session['segment'] = 'small'
            return jsonify({"message": "Login successful!", "role": "Customer", "companyName": username, "segment": "Small"})
            
        elif user['roleID'] == 3:
            session['role'] = 'Customer'
            session['segment'] = 'medium'
            return jsonify({"message": "Login successful!", "role": "Customer", "companyName": username, "segment": "Medium"})
            
        elif user['roleID'] == 4:
            session['role'] = 'Customer'
            session['segment'] = 'large'
            return jsonify({"message": "Login successful!", "role": "Customer", "companyName": username, "segment": "Large"})

        return jsonify({"error": "Role profile not recognized"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route('/api/products/search', methods=['GET'])
def search_products():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized. Please log in first."}), 401

    # Default to 'small' if segment isn't set, fallback to 'large' if Admin logs in
    segment = session.get('segment', 'small')
    if session.get('role') == 'Admin':
        segment = 'large'

    # The column name matches your segment variable perfectly now ('small', 'medium', 'large')
    price_column = segment 

    search_type = request.args.get('type')
    query_val = request.args.get('query', '').strip()

    sql_query = f"SELECT productID, sku, productName, category, {price_column} AS wholesalePrice FROM Products"
    conditions = []
    params = []

    if search_type == 'id' and query_val:
        conditions.append("productID = %s")
        params.append(query_val)
    elif search_type == 'name' and query_val:
        conditions.append("(productName LIKE %s OR SOUNDEX(productName) = SOUNDEX(%s))")
        params.extend([f"%{query_val}%", query_val])
    elif search_type == 'category' and query_val:
        conditions.append("category = %s")
        params.append(query_val)

    if conditions:
        sql_query += " WHERE " + " AND ".join(conditions)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql_query, tuple(params))
        results = cursor.fetchall()
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/api/admin/all-products', methods=['GET'])
def admin_get_all_products():
    # Protection Check: Ensure user is logged in AND is an Admin
    if 'user_id' not in session or session.get('role') != 'Admin':
        return jsonify({"error": "Unauthorized. Admin access only."}), 403

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Select everything so the Admin can see all 3 pricing tiers at once
        cursor.execute("SELECT productID, sku, productName, category, priceSmall, priceMedium, priceLarge FROM Products")
        products = cursor.fetchall()
        
        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
if __name__ == '__main__':
    print("🚀 Flask application starting on http://localhost:5000")
    app.run(debug=True, port=5000)
