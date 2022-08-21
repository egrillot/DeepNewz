from Newsapp import app, init_db
from waitress import serve

if __name__ == "__main__":
    init_db(app)
    serve(app, port=8080)