import anthropic

import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(
  api_key=os.getenv("ANTHROPIC_API_KEY")
)

prompt = input("User > ")
messages = []

while (prompt != "" and prompt.lower() != "exit"):
  messages.append(
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": prompt
        }
      ]
    }
  )

  message = client.messages.create(
    model="MiniMax-M2.5",
    max_tokens=3000,
    system="You are a helpful assistant. You are responding in a terminal output, so you should not use markdown formatting",
    messages=messages
  )

  # Look at the message to see total tokens, cached tokens, etc
  print(message)

  for block in message.content:
    if block.type == "thinking":
      pass
      # print(f"Thinking:\n{block.thinking}\n")
    elif block.type == "text":
      print(f"MiniMax > {block.text}\n")

      messages.append(
      {
        "role": "assistant",
        "content": [
          {
            "type": "text",
            "text": block.text
          }
        ]
      }
    )


  prompt = input("User > ")