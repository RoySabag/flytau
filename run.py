from flask import Flask, render_template
# 1. Import DB Connector (Savage's logic)
from app.classes.db_connector import DB

app = Flask(__name__)

@app.route('/')
def home():
    # Check DB connection in Console only (keeping HTML clean for now)
    try:
        roles = DB.execute_query("SELECT count(*) as count FROM roles")
        print(f"✅ DB Check: Connection Successful! Found {roles[0]['count']} roles.")
    except Exception as e:
        print(f"❌ DB Check: Connection Failed. Error: {e}")

    # 2. Render the base template (Sela's design)
    return render_template('base.html')

if __name__ == '__main__':
    # 3. Run config (Port 5001 for Mac compatibility)
    app.run(debug=True, port=5001)