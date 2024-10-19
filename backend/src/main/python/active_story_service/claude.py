import requests
import os
import anthropic
from anthropic import HUMAN_PROMPT, AI_PROMPT

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
)

theme = "kindness"
Prompt = f"Generate a 20 word kid friendly story following the theme of ${theme}.. stop at some point so that kid can improvise the story and you will co-create the story"
message = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1024,
    system="Respond only in English.",
    messages=[
        {"role": "user", "content": Prompt} 
    ]
)

# prompt=f"Generate a story for a kid friendly story following the theme: {input_data.theme}",
# message = client.messages.create(
#     model="claude-3-haiku-20240307",
#     max_tokens=1024,
#     system="add elements of humor, fun, kid friendly and creativity",
#     messages=[
#     {"role": "user", "content": prompt} 
#     ]
# )




print(message.content[0].text)

