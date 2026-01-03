from flask import Flask
from app.routes import routes  # מייבא את הנתיבים החדשים (login, register)

app = Flask(__name__)
app.secret_key = 'flytau_secret_key'  # מפתח הצפנה (חובה להתחברות)

# השורה הכי חשובה: מחברת את דף ה-Login לאפליקציה!
app.register_blueprint(routes)

if __name__ == '__main__':
    # שים לב: שיניתי לפורט 5000 (ברירת המחדל)
    app.run(debug=True, port=5000)