from flask import Flask, render_template

# 1. Create the application instance
# This initializes the app and tells Flask to look for 'templates' and 'static' folders here
app = Flask(__name__)

# 2. Define the main route (Home Page)
@app.route('/')
def home():
    # When a user visits the root URL ('/'), this function runs.
    # It renders the 'base.html' template we created.
    return render_template('base.html')

# 3. Run the server
if __name__ == '__main__':
    # 'debug=True' enables error messages in the browser and auto-reloads
    # the server when you save changes to the code.
    app.run(debug=True, port=5001)