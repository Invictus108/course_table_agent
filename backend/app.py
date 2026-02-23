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

def mil_time_to_minutes_since_midnight(t):
    hours, minutes = t.split(":")
    return int(hours) * 60 + int(minutes)

def get_courses_from_coursetable():
    with open('202601.json', 'r', encoding="utf-8") as f:
        data = json.load(f)
    
    for i in data["data"]["courses"]:
        for j in i["course_meetings"]:
            j["start_time"] = mil_time_to_minutes_since_midnight(j["start_time"])
            j["end_time"] = mil_time_to_minutes_since_midnight(j["end_time"])

    return data


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
            contexts[id].append({"role": f"user", "content": f"I am a {year} at Yale with id {id} studying {major}. I have taken the following courses: {courses}, and I am looking for my courses next semester."})

        if prompt:
            contexts[id].append({"role": f"user", "content": f"User {id}: " + prompt})

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
        chosen = None
        rounds = 0

        content = message.content if hasattr(message, "content") else message["content"]
        tool_calls = [b for b in content if (getattr(b, "type", None) or b.get("type")) == "tool_use"]
        
        while len(tool_calls) > 0 and rounds < max_tool_rounds:
            rounds += 1


            for call in tool_calls:
                # extract name and args
                fn_name = getattr(call, "name", None) or call["name"]
                args = getattr(call, "input", None) or call.get("input", {})
                call_id = getattr(call, "id", None) or call["id"]


                if isinstance(args, str):
                    args = json.loads(args)

                # run tool
                tool_result = mcp.run({"name": fn_name, "arguments": args})

                if fn_name in {"add_to_selected", "remove_from_selected","clear_selected"}:
                    chosen = mcp.run({"name": "get_selected", "arguments": {"client_id": id}})


                # return tool result to model 
                contexts[id].append({
                    "role": "tool",
                    "tool_call_id": call_id,
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

            content = message.content if hasattr(message, "content") else message["content"]
            tool_calls = [b for b in content if (getattr(b, "type", None) or b.get("type")) == "tool_use"]
            
            # append assistant message again
            contexts[id].append({"role": "assistant", "content": message["content"]})



        # now message should be final assistant text
        final_text = message.get("content")
        return {"message": final_text , "courses": chosen}
    else:
        return {"we fucked up": "we fucked up"}
