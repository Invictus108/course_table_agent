from flask import Flask, redirect, request, session
import os
import requests
import xmltodict
from urllib.parse import urlencode
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET") # for signing cookies
CORS(app,
    supports_credentials=True,
    origins=["http://localhost:5000"], # TODO: change to prod
    methods=["GET", "POST"]
)


@app.route("/")
def index():
    # TODO: this should be a form that gets user data
    return

@app.route("/chat")
def chat():
    # TODO: this should be a chat with the minimax agent that has recived the search courses
    # TODO: option for major tweaks (run embeddings search again (noise makes it different)) or minor which just changes a few thing from the list tha chat has
    #   - maintain chat history for this
    # TODO: when user is satisfied with their choice, uplaod courses to coursetable
    return




# Login stuff: not needed if we can just get off the cookies

# SITE_URL = "http://localhost:5000"

# # validation urls
# CAS_LOGIN_URL = "https://secure-tst.its.yale.edu/cas/login" # remove -tst fot production
# CAS_VALIDATE_URL = "https://secure-tst.its.yale.edu/cas/p3/serviceValidate"

# # callback URL 
# SERVICE_URL = os.getenv("ORIGIN", "http://localhost:5000") + "/login_callback"


# def parse_cas_response(xml_text: str):
#     return xmltodict.parse(xml_text, dict_constructor=dict)

# # make sure they are actaully logged in
# def validate_ticket(ticket: str) -> str:
#     # make sure user actaully logged in
#     params = {
#         "ticket": ticket,
#         "service": SERVICE_URL,
#     }

#     resp = requests.get(CAS_VALIDATE_URL, params=params)
#     data = parse_cas_response(resp.text)

#     sr = data.get("cas:serviceResponse", {})

#     # authentication failed
#     if "authenticationFailure" in sr:
#         reason = sr["authenticationFailure"].get("@code", "UNKNOWN")
#         raise Exception(f"CAS Authentication failed: {reason}")

#     # authentication success
#     success = sr.get("cas:authenticationSuccess")
#     if not success:
#         raise Exception("CAS returned no authenticationSuccess node")

#     # return netID
#     netid = success["cas:user"]

#     return netid

# # redirect to login
# @app.route("/login")
# def login():
#     params = {
#         "service": SERVICE_URL
#     }
#     cas_url = f"{CAS_LOGIN_URL}?{urlencode(params)}"
#     return redirect(cas_url)

# # callback
# @app.route("/login_callback")
# def login_callback():
#     # get ticket
#     ticket = request.args.get("ticket")
#     if not ticket:
#         return "Missing CAS ticket", 400

#     # Validate with CAS server → get NetID
#     netid = validate_ticket(ticket)

#     # Store NetID in session
#     session["netid"] = netid

#     return redirect(SITE_URL) # frontend url

# @app.route("/logout")
# def logout():
#     session.clear()
#     return redirect("http://localhost:5173/")
