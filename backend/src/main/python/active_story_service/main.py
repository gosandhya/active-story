import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from active_story_service.db_crud import add_story, get_single_story, get_all_stories, update_story, delete_story
from active_story_service.models import StoryInput, ContinueStoryInput  # Import models
import os

import anthropic
from anthropic import HUMAN_PROMPT, AI_PROMPT

from anthropic import AsyncAnthropic

import re

client = AsyncAnthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
)



app = FastAPI()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow only the React frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.post("/generate-story/")
async def generate_story(input_data: StoryInput):
    #story_content = f"Once upon a time, in a land where {input_data.theme}, there lived a..."

    theme = input_data.theme
    #characters = input_data.characters if hasattr(input_data, 'characters') else "some interesting characters"
    #location = input_data.location if hasattr(input_data, 'location') else "a magical place"

    
    prompt = f"""You are a creative storyteller for young children. Your task is to begin a short, engaging story based on a given theme. This story should be suitable for children aged 3-6 and will encourage co-creation between parents and children.

    Here is the theme for the story:
    <theme>
    {theme}
    </theme>

    Before writing the story, plan your approach inside <story_planning> tags, considering the following:

    1. **Character Development**:
    - Create non-traditional characters that challenge stereotypes.
    - Describe their unique traits and abilities in a fun way.

    2. **Setting Creation**:
    - Imagine an interesting and imaginative setting that sparks curiosity.
    - Think about how the setting can enhance the story's magic.

    3. **Plot Outline**:
    - Develop a simple yet engaging plot idea.
    - Introduce a gentle conflict or challenge for the characters to overcome.

    4. **Opportunities for Child Participation**:
    - Plan moments for children to contribute their ideas and imagination.
    - Include open-ended questions to encourage creativity during the story.

    5. **Educational Elements**:
    - Consider moral lessons or educational themes to subtly weave into the narrative.
    - Ensure these lessons are presented in a fun and engaging manner.

    After your planning, write the beginning of the story (about 20 words) inside <story> tags. Remember to stop mid-story, leaving space for the child to continue co-creating.

    Your story should:
    1. Be engaging and kid-friendly.
    2. Use simple language suitable for 3-6 year olds.
    3. Introduce characters with non-traditional roles that promote diversity.
    4. Avoid gender stereotypes.
    5. Encourage imagination and creativity.
    6. Be open-ended to allow for co-creation.

    Start your response with your story planning, followed by the story fragment."""


    message = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        temperature=0.8,
        system="You are a creative storyteller whose goal is to make story generation a delightful bonding experience for parents and children. Always finish your thoughts, and avoid starting with 'Once upon a time.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "<story_planning>"
                    }
                ]
            }
        ]
    )

    response = message.content[0].text
    story_match = re.search(r'<story>(.*?)</story>', response, re.DOTALL)
    if story_match:
        initial_content = story_match.group(1).strip()  # Get the matched content and strip leading/trailing whitespace


    waiting_for_input = "..." in initial_content
    story_data = {
        "theme": theme,
        "content": initial_content,
        "story_cursor": len(initial_content),
        "improvisations": input_data.improvisations,
        "remaining_improvs": 3,  # You may want to track this dynamically based on usage
        "waiting_for_input": waiting_for_input  # New flag to indicate waiting for input

    }
    
    story_id = await add_story(story_data)
    return {
        "story_id": story_id,
        "story": initial_content,  # Send the extracted story content back
        "waiting_for_input": waiting_for_input  # Include the flag in the response

    }


@app.post("/continue-story/")
async def continue_story(input_data: ContinueStoryInput):
    story_id = input_data.story_id
    improv = input_data.improv

    story = await get_story(story_id)

    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    # If no improvisations remain, stop
    if story['remaining_improvs'] <= 0:
        return {"message": "The story is finished, no more improvisations allowed."}
    
    current_theme = story["theme"]
    current_story = story["content"]
    story_cursor = story.get("story_cursor", len(current_story))  # Default to end if no cursor

    print("context", current_story[story_cursor:])
    # Refined continuation prompt

    prompt = f"""You are an AI storyteller specializing in continuing stories for young children (ages 3-6). Your task is to generate engaging story continuations (about 20 words) that incorporate user input while maintaining the story's theme and flow. You will be working with the following elements:

    1. The current story:
    <current_story>
    {current_story}
    </current_story>

    2. The current theme of the story:
    <current_theme>
    {current_theme}
    </current_theme>

    3. User input to incorporate:
    <user_input>
    {improv}
    </user_input>

    4. Remaining improvisations:
    <remaining_improvs>
    {story['remaining_improvs']}
    </remaining_improvs>

    Your goal is to continue the story from where it stopped, smoothly incorporating the user input while adhering to the current theme. Follow these steps:

    1. Analyze the current story and theme.
    2. Plan how to incorporate the user input naturally.
    3. Generate a continuation that flows seamlessly from the existing story.
    4. Ensure the continuation doesn't repeat any part of the existing content.
    5. Check if more user input is needed based on the remaining_improvs value.

    Before writing the continuation, plan your approach inside <story_planning> tags. Include the following:
    - A 1-2 sentence summary of the current story and theme.
    - 2-3 key elements from the user input to incorporate.
    - 2-3 ways to naturally include the user input in the story.
    - 1-2 potential plot developments or character arcs.
    - 2-3 age-appropriate language choices or concepts to include.
    - The current value of remaining_improvs and how it affects your plan.
    - 2-3 potential challenges in incorporating the user input and how to overcome them.
    - A brief list of 5-7 age-appropriate vocabulary words related to the story theme and user input.
    - 1-2 ideas for simple moral lessons or positive messages that could be subtly included.

    After your planning process, write the story continuation inside <story_continuation> tags. The continuation should:
    - Be engaging and suitable for children aged 3-6.
    - Use simple, age-appropriate language.
    - Flow naturally from the existing story.
    - Incorporate the user input seamlessly.
    - Maintain the current theme.
    - Avoid repeating any part of the existing content.
    - Include at least 3 of the age-appropriate vocabulary words you listed.
    - Subtly incorporate one of the moral lessons or positive messages you identified.

    If remaining_improvs is greater than 0, end your continuation at a point that naturally invites further user input. If remaining_improvs is 0 or less, bring the story to a satisfying conclusion.

    Remember, your role is to continue an existing story, not to start a new one. Focus on creating a smooth, engaging continuation that feels like a natural progression of the narrative.

    Example output structure:

    <story_planning>
    [Your detailed analysis and planning for the story continuation]
    </story_planning>

    <story_continuation>
    [Your age-appropriate story continuation, incorporating user input and adhering to the theme]
    </story_continuation>

    Please proceed with your story planning and continuation based on the provided information."""

            

    message = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        system="Your goal is to continue the story from where it stopped, smoothly incorporating the user input while adhering to the current theme. Keep the continuation short and simple about 20-20 words",  
        messages=[
            {
                "role": "user", 
                "content": [ 
                {
                    "type": "text",
                    "text": prompt
                } 
            ]
            },
            {
                "role": "assistant",
                "content": [
                {
                    "type": "text",
                    "text": "<story_planning>"
                }
            ]
            }
        ]
    )
    response = message.content[0].text
    print('response', response)

    new_content = None

    story_match = re.search(r'<story_continuation>(.*?)</story_continuation>', response, re.DOTALL)
    print("story_match", story_match)
    if story_match:
        new_content = story_match.group(1).strip()  # Get the matched content and strip leading/trailing whitespace
    
    print("new_content", new_content)
    continued_story = f"{story['content']} {new_content}"  # Append the new part only
    new_cursor = len(continued_story)

    story['improvisations'].append(improv)
    update_data = {
        "content": continued_story, 
        "story_cursor": new_cursor,
        "improvisations": story['improvisations'],
        "remaining_improvs": story['remaining_improvs'] - 1
    }
    await update_story(story_id, update_data)

    story = await get_story(story_id)

    return {"story_id": story["story_id"], "story": story["content"]}


@app.get("/get-story/")
async def get_story(story_id: str):
    # Retrieve the story from MongoDB
    story = await get_single_story(story_id)
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return {
        "story_id": story_id,
        "content": story.get("content", ""),
        "theme": story.get("theme", ""),
        "improvisations": story.get("improvisations", []),
        "remaining_improvs": story.get("remaining_improvs", 0)

    }



@app.get("/get-all-stories/")
async def get_all_stories_endpoint() -> List[Dict[str, Any]]:
    stories = await get_all_stories()
    return stories


@app.delete("/delete-story/{story_id}")
async def delete_story_endpoint(story_id: str):
    success = await delete_story(story_id)
    if not success:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"message": "Story deleted successfully"}



@app.get("/")
async def root():
    return {"message": "Welcome to the Bedtime Reading App"}

