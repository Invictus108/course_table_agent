# Course Table Agent

An AI agent that uses an MCP server and retrieval-augmented generation (RAG) to help Yale students explore and optimize course options. The agent can add/remove courses, create and manage worksheets, and provide context-aware recommendations based on a student’s goals and constraints.

## Features

- Add, remove, and inspect planned courses.
- Create and manage multiple worksheets (semester plans / degree maps).
- RAG-enabled recommendations using contextual information, course catalog, and degree requirements.
- Context-aware constraint handling (professors, time conflicts, credits).
- Connects to an MCP server for tool execution.

## Quickstart

1. Clone the repo:
   git clone <repo-url>
2. Install dependencies (example using Python):
   
   python -m venv .venv
   
   source .venv/bin/activate
   
   pip install -r requirements.txt
4. Configure environment variable:
   - ANTHROPIC_API_KEY — required API key for the Anthropic model
5. Start the server:
   python3 app.py
6. Load frontend:
   - To use the frontend, load the `frontend` folder as an extension in Chrome (Developer mode → Load unpacked).

## Configuration

Required:

- ANTHROPIC_API_KEY — API key for Anthropic model access

## Architecture

- MCP server: exposes tool APIs and coordinates multi-turn flows.
- Agent layer: uses MiniMax M2.5 to orchestrate state and tool calls.
- Tools: worksheet manager, catalog search, RAG pipeline.

## Usage

- Interact via the frontend loaded as a Chrome extension.
- Example flows:
  - "Help me plan a spring semester with 4-5 classes, include one CS elective and avoid morning classes."
  - "Add CPSC 2010 to my worksheet and check prereqs and schedule conflicts."
  - "Recommend courses for a student aiming for research in CS"
