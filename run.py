from flask import Flask
from app.classes.db_connector import DB

app = Flask(__name__)

# ראוט זמני לבדיקה שהשרת והדאטה-בייס מחוברים
@app.route('/')
def home():
    # בדיקת חיבור ל-DB
    roles = DB.execute_query("SELECT count(*) as count FROM roles")
    if roles is not None:
        return "<h1>FlyTau Server is RUNNING! ✈️</h1><p>Database Connection: <span style='color:green'>SUCCESS</span></p>"
    else:
        return "<h1>FlyTau Server is RUNNING! ✈️</h1><p>Database Connection: <span style='color:red'>FAILED</span></p>"

if __name__ == '__main__':
    app.run(debug=True)