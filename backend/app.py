from flask import Flask, redirect, request, session
import os
import requests
import xmltodict
from urllib.parse import urlencode
from flask_cors import CORS
from dotenv import load_dotenv
from mcp_c import create_mcp
from fastmcp import Client
import anthropic
import json
import asyncio
import mcp.types

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET")  # for signing cookies
CORS(
    app
    # supports_credentials=True,
    # origins=["http://localhost:5000"], # TODO: change to prod
    # methods=["GET", "POST"]
)

os.environ["ANTHROPIC_BASE_URL"] = "https://api.minimax.io/anthropic"

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def mil_time_to_minutes_since_midnight(t):
    hours, minutes = t.split(":")
    return int(hours) * 60 + int(minutes)


def get_courses_from_coursetable():
    with open("courses.json", "r", encoding="utf-8") as f:
        tmp = json.load(f)

    data = []

    for i in tmp["data"]["courses"]:
        for j in i["course_meetings"]:
            j["start_time"] = mil_time_to_minutes_since_midnight(j["start_time"])
            j["end_time"] = mil_time_to_minutes_since_midnight(j["end_time"])
        data.append(i)

    return data


def get_prompts():
    with open("prompts.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_major_reqs():
    with open("major_reqs.json", "r", encoding="utf-8") as f:
        return json.load(f)


mcp = create_mcp(get_courses_from_coursetable(), get_major_reqs())
tools = asyncio.run(mcp.list_tools())
mcp_client = Client(mcp)


async def call_mcp_tool(name: str, args: dict, id):

    async with mcp_client:  # <-- REQUIRED
        args["client_id"] = id
        return await mcp_client.call_tool(name, args)


def mcp_tool_to_anthropic_toolparam(t) -> dict:  # mcp_types.Tool
    d = t.model_dump()  # pydantic model -> dict
    # MCP uses inputSchema; Anthropic expects input_schema
    d["input_schema"] = d.pop("inputSchema")
    # Anthropic ToolParam allows extra fields, but you can also trim to just what you need:
    return {
        "name": d["name"],
        "description": d.get("description", ""),
        "input_schema": d["input_schema"],
    }


anthropic_tools = [mcp_tool_to_anthropic_toolparam(t) for t in tools]

contexts = {}

prompts = get_prompts()

MAIN_PROMPT = prompts["main_prompt"]
persona_prompts = prompts["persona_prompts"]


@app.route("/", methods=["GET", "POST"])
def index():
    # current courses, major, id, year, prompt
    if request.method == "POST":
        data = request.get_json()
        courses = data["courses"]
        major = data["major"]
        id = data["netId"]
        name = data["name"]
        year = data["year"]
        prompt = data["prompt"]
        persona = data["persona"]

        system_prompt = MAIN_PROMPT + persona_prompts[persona]

        courses_crn = [str(c["crn"]) for c in courses]
        tool_result = asyncio.run(
            call_mcp_tool("set_selected", {"ids": courses_crn}, id)
        )

        if id not in contexts:
            contexts[id] = []
            contexts[id].append(
                {
                    "role": f"user",
                    "content": f"I am {name}, a {year} at Yale with id {id} {"studying " + major if major != "Undeclared" else ""}. My worksheet currently contains: {courses}, and I am looking for my courses next semester. Around 5 courses per semester is typical with 6 being a overload.",
                }
            )

        if prompt:
            contexts[id].append({"role": f"user", "content": f"User {id}: " + prompt})

        message = client.messages.create(
            model="MiniMax-M2.5",
            max_tokens=3000,
            system=system_prompt,
            messages=contexts[id],
            tools=anthropic_tools,
            # tool_choice="auto",  # set to "required" to force at least one tool call
        )

        # append
        contexts[id].append({"role": "assistant", "content": message.content})

        max_tool_rounds = 6
        # chosen = None
        rounds = 0
        actions = []

        # content = message.content if hasattr(message, "content") else message.content]
        content = message.content
        tool_calls = [
            b
            for b in content
            if (getattr(b, "type", None) or b.get("type")) == "tool_use"
        ]

        while len(tool_calls) > 0 and rounds < max_tool_rounds:
            rounds += 1

            tool_result_blocks = []

            for call in tool_calls:
                # extract name and args
                fn_name = call.name
                args = call.input or {}
                tool_use_id = call.id

                # run tool
                print(fn_name)
                print(args)
                tool_result = asyncio.run(call_mcp_tool(fn_name, args, id))

                if fn_name in {
                    "add_to_selected",
                    "remove_from_selected",
                    "clear_selected",
                    "set_selected",
                }:
                    selected_result = asyncio.run(
                        call_mcp_tool("get_selected", {"client_id": id}, id)
                    )
                    chosen = json.loads(selected_result.content[0].text)["items"]
                    # just get crn field
                    crns = [c["crn"] for c in chosen]
                    actions.append(
                        {"type": "update_worksheet", "args": {"selected": crns}}
                    )

                if fn_name == "create_worksheet":
                    actions.append({"type": "create_worksheet", "args": args})

                if not isinstance(tool_result, str):
                    result_str = "\n".join([c.text for c in tool_result.content])
                else:
                    result_str = tool_result

                # return tool result to model
                tool_result_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_str,
                    }
                )

            contexts[id].append(
                {
                    "role": "user",
                    "content": tool_result_blocks,
                }
            )

            message = client.messages.create(
                model="MiniMax-M2.5",
                max_tokens=3000,
                system=system_prompt,
                messages=contexts[id],
                tools=anthropic_tools,
                # tool_choice="auto",
            )

            # content = message.content if hasattr(message, "content") else message["content"]
            content = message.content
            tool_calls = [
                b
                for b in content
                if (getattr(b, "type", None) or b.get("type")) == "tool_use"
            ]

            # append assistant message again
            contexts[id].append({"role": "assistant", "content": message.content})

        # now message should be final assistant text
        final_text = "".join(
            block.text for block in message.content if block.type == "text"
        )

        print("sending response")
        # print(len(chosen) if chosen else "no chosen")

        print(actions)

        return {"message": final_text, "actions": actions}
    else:
        return {"we fucked up": "we fucked up"}


if __name__ == "__main__":
    app.run(debug=False, port=5001)
