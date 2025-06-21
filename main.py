from flask import Flask
from authlib.integrations.flask_client import OAuth

import users, courses


app = Flask(__name__)
app.secret_key = "SECRET_KEY"


app.register_blueprint(users.bp, url_prefix="/users")
app.register_blueprint(courses.bp, url_prefix="/courses")

CLIENT_ID = "****"
CLIENT_SECRET = "****"
DOMAIN = "****"
ALGORITHMS = ["****"]

oauth = OAuth(app)

auth0 = oauth.register(
    "auth0",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        "scope": "openid profile email",
    },
)


@app.route("/")
def index():
    return "Josquin Larsen, Tarpaulin"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
