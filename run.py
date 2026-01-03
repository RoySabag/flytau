from flask import Flask
from app.classes.db_manager import DBManager
# הפנייה למיקום האמיתי בתוך models/daos
from app.models.daos.employee_dao import EmployeeDAO
from app.routes.admin_routes import admin_bp

app = Flask(__name__)
app.secret_key = 'your_secret_key' # חובה עבור Session

# אתחול ה-DB
db = DBManager()
app.employee_dao = EmployeeDAO(db)

# הצמדת ה-DAO לאפליקציה כדי שיהיה זמין ב-Blueprints
app.employee_dao = EmployeeDAO(db)

# רישום ה-Blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    # שינוי הפורט ל-5001 כדי למנוע התנגשות ב-Mac
    app.run(debug=True, port=5001)