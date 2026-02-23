from flask import Flask, redirect, request, session
import os
import requests
import xmltodict
from urllib.parse import urlencode
from flask_cors import CORS
from dotenv import load_dotenv
from mcp import create_mcp
import anthropic
import json

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET") # for signing cookies
CORS(app,
    supports_credentials=True,
    origins=["http://localhost:5000"], # TODO: change to prod
    methods=["GET", "POST"]
)

client = anthropic.Anthropic(
  api_key=os.getenv("ANTHROPIC_API_KEY")
)

def get_courses_from_coursetable():
    # TODO: get courses from coursetable
    return {}

mcp = create_mcp(get_courses_from_coursetable())
tools = mcp.get_tools()

contexts = {}

@app.route("/", methods=["GET", "POST"])
def index():
    # current courses, major, id, year, prompt
    if request.method == "POST":
        courses = request.form["courses"]
        major = request.form["major"]
        id = request.form["id"]
        year = request.form["year"]
        prompt = request.form["prompt"]

        if id not in contexts:
            contexts[id] = []
            contexts[id].append({"role": f"user {id}", "content": f"I am a {year} at Yale with id {id} studying {major}. I have taken the following courses: {courses}, and I am looking for my courses next semester."})

        if prompt:
            contexts[id].append({"role": f"user {id}", "content": prompt})

        message = client.messages.create(
            model="MiniMax-M2.5",
            max_tokens=3000,
            system="You are a helpful assistant.",
            messages=contexts[id],
            tools=tools,
            tool_choice="auto",  # set to "required" to force at least one tool call
        )

        # append
        contexts[id].append({"role": "assistant", "content": message["content"]})

        max_tool_rounds = 6
        rounds = 0

        while message.get("tool_calls") and rounds < max_tool_rounds:
            rounds += 1

            for call in message["tool_calls"]:
                # extract name and args
                fn_name = call["function"]["name"]
                args = call["function"].get("arguments", "{}")
                if isinstance(args, str):
                    args = json.loads(args)

                # run tool
                tool_result = mcp.run({"name": fn_name, "arguments": args})

                # return tool result to model 
                contexts[id].append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": tool_result if isinstance(tool_result, str) else json.dumps(tool_result),
                })

            message = client.messages.create(
                model="MiniMax-M2.5",
                max_tokens=3000,
                system="You are a helpful assistant.",
                messages=contexts[id],
                tools=tools,
                tool_choice="auto",
            )

            # append assistant message again
            contexts[id].append(message)

        # now message should be final assistant text
        final_text = message.get("content")
        return {"message": final_text}
    else:
        return {"we fucked up": "we fucked up"}
