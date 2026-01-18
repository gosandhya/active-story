import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from active_story_service.db_crud import (
    add_story, get_single_story, get_all_stories, update_story, delete_story,
    get_latest_checkpoint, get_all_story_threads, delete_thread_checkpoints,
    reconstruct_content, extract_theme
)
from active_story_service.models import StoryInput, ContinueStoryInput
from active_story_service.models_v2 import StoryTurnRequest, StoryTurnResponse, StoryListItem
from active_story_service.app.graph import build_graph
from active_story_service.app.state import initial_state
import os

import anthropic
from anthropic import HUMAN_PROMPT, AI_PROMPT

from anthropic import AsyncAnthropic

import re

from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent.parent.parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

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

# ============================================================================
# V2 Agentic Story Endpoints (LangGraph-based)
# ============================================================================

# Initialize the LangGraph agent
graph = build_graph()


@app.post("/story/turn", response_model=StoryTurnResponse)
async def story_turn(req: StoryTurnRequest):
    """
    V2 Story Turn Endpoint - handles both initial story and continuations.

    For initial story: provide thread_id, user_text, and theme
    For continuation: provide thread_id and user_text only
    """
    try:
        # Build seed state if this is a new story (theme provided)
        seed = initial_state(theme=req.theme) if req.theme else {}

        # Invoke the LangGraph agent
        result = await graph.ainvoke(
            {**seed, "messages": [{"role": "user", "content": req.user_text}]},
            config={"configurable": {"thread_id": req.thread_id}}
        )

        # Extract the latest assistant message (the new story segment)
        last_ai = None
        for msg in reversed(result.get("messages", [])):
            if msg.get("role") == "assistant" or msg.get("type") == "ai":
                last_ai = msg
                break

        story_text = last_ai.get("content", "") if last_ai else ""

        # Reconstruct full content from all messages
        content = reconstruct_content(result.get("messages", []))

        return StoryTurnResponse(
            thread_id=req.thread_id,
            story_text=story_text,
            content=content,
            turn=result.get("story_progress", {}).get("turn", 0),
            phase=result.get("story_progress", {}).get("phase", "Introduction"),
            world_state=result.get("world_state", {})
        )
    except Exception as e:
        print(f"V2 story turn error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")


@app.get("/stories-v2/", response_model=List[StoryListItem])
async def get_all_v2_stories():
    """
    List all V2 stories from the checkpoint collection.
    """
    try:
        checkpoints = await get_all_story_threads()
        stories = []

        for checkpoint in checkpoints:
            # Extract data from checkpoint
            thread_id = checkpoint.get("thread_id", "")
            channel_values = checkpoint.get("channel_values", {})
            world_state = channel_values.get("world_state", {})
            story_progress = channel_values.get("story_progress", {})
            messages = channel_values.get("messages", [])

            # Get theme and content
            theme = extract_theme(world_state.get("world_facts", []))
            content = reconstruct_content(messages)
            content_preview = content[:100] + "..." if len(content) > 100 else content

            stories.append(StoryListItem(
                thread_id=thread_id,
                theme=theme,
                content_preview=content_preview,
                turn=story_progress.get("turn", 0),
                phase=story_progress.get("phase", "Introduction"),
                created_at=None  # LangGraph doesn't store timestamps by default
            ))

        return stories
    except Exception as e:
        print(f"Error fetching V2 stories: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch stories: {str(e)}")


@app.get("/story-v2/{thread_id}")
async def get_v2_story(thread_id: str):
    """
    Get a single V2 story by thread_id.
    """
    try:
        checkpoint = await get_latest_checkpoint(thread_id)

        if not checkpoint:
            raise HTTPException(status_code=404, detail="Story not found")

        channel_values = checkpoint.get("channel_values", {})
        world_state = channel_values.get("world_state", {})
        story_progress = channel_values.get("story_progress", {})
        messages = channel_values.get("messages", [])

        theme = extract_theme(world_state.get("world_facts", []))
        content = reconstruct_content(messages)

        return {
            "thread_id": thread_id,
            "theme": theme,
            "content": content,
            "turn": story_progress.get("turn", 0),
            "phase": story_progress.get("phase", "Introduction"),
            "world_state": world_state,
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching V2 story: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch story: {str(e)}")


@app.delete("/story-v2/{thread_id}")
async def delete_v2_story(thread_id: str):
    """
    Delete a V2 story (all checkpoints for the thread).
    """
    try:
        success = await delete_thread_checkpoints(thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Story not found")
        return {"message": "Story deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting V2 story: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete story: {str(e)}")


# ============================================================================
# V1 Story Endpoints (Original)
# ============================================================================

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
        "story_id": input_data.story_id,  # Use frontend-provided ID
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


@app.post("/generate-story-stream/")
async def generate_story_stream(input_data: StoryInput):
    """
    Streaming version of generate-story using Server-Sent Events.
    Streams the story text as it's generated by Claude.
    """
    from fastapi.responses import StreamingResponse
    import json

    theme = input_data.theme
    story_id = input_data.story_id if hasattr(input_data, 'story_id') else None

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

    async def event_generator():
        full_response = ""

        async with client.messages.stream(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0.8,
            system="You are a creative storyteller whose goal is to make story generation a delightful bonding experience for parents and children. Always finish your thoughts, and avoid starting with 'Once upon a time.",
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                },
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "<story_planning>"}]
                }
            ]
        ) as stream:
            async for text in stream.text_stream:
                full_response += text
                # Don't stream to frontend - let frontend show only after audio is ready

        # Extract story from response
        story_match = re.search(r'<story>(.*?)</story>', full_response, re.DOTALL)
        initial_content = ""
        if story_match:
            initial_content = story_match.group(1).strip()

        waiting_for_input = "..." in initial_content

        # Save to database
        story_data = {
            "story_id": input_data.story_id,  # Use frontend-provided ID
            "theme": theme,
            "content": initial_content,
            "story_cursor": len(initial_content),
            "improvisations": input_data.improvisations,
            "remaining_improvs": 3,
            "waiting_for_input": waiting_for_input
        }

        saved_story_id = await add_story(story_data)

        # Send final message with story_id
        yield f"data: {json.dumps({'done': True, 'story': initial_content, 'story_id': saved_story_id, 'waiting_for_input': waiting_for_input})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/continue-story/")
async def continue_story(input_data: ContinueStoryInput):
    story_id = input_data.story_id
    improv = input_data.improv

    story = await get_single_story(story_id)

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

    new_content = None

    story_match = re.search(r'<story_continuation>(.*?)</story_continuation>', response, re.DOTALL)

    if story_match:
        new_content = story_match.group(1).strip()  # Get the matched content and strip leading/trailing whitespace
    

    continued_story = f"{story['content']} \n\n\n {new_content}"  # Append the new part only
    new_cursor = len(continued_story)

    story['improvisations'].append(improv)
    update_data = {
        "content": continued_story, 
        "story_cursor": new_cursor,
        "improvisations": story['improvisations'],
        "remaining_improvs": story['remaining_improvs'] - 1
    }
    await update_story(story_id, update_data)

    story = await get_single_story(story_id)

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


@app.post("/text-to-speech/")
async def text_to_speech(request: Dict[str, Any]):
    """
    Convert text to speech using Deepgram API with aura-2-thalia-en model.
    Simple and fast - just returns audio without extra metadata.
    """
    from fastapi.responses import Response
    import httpx

    text = request.get("text", "")

    print(f"=== TTS REQUEST ===")
    print(f"Text length: {len(text)}")
    print(f"Text (first 100 chars): {text[:100]}")
    print(f"Text (last 100 chars): {text[-100:]}")
    print(f"Text ends with: '{text[-20:]}'")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    try:
        # Use Deepgram Aura 2 - Thalia voice (expressive storytelling)
        url = "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en"

        headers = {
            "Authorization": f"Token {os.environ.get('DEEPGRAM_API_KEY')}",
            "Content-Type": "text/plain"  # Send as plain text, not JSON
        }

        # Make async HTTP request to Deepgram
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, content=text, timeout=30.0)
            response.raise_for_status()
            audio_data = response.content

        # Return audio as response
        return Response(
            content=audio_data,
            media_type="audio/mp3",
            headers={
                "Content-Disposition": "inline",
                "Cache-Control": "no-cache"
            }
        )

    except Exception as e:
        print(f"Deepgram TTS error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


@app.get("/")
async def root():
    return {"message": "Welcome to the Bedtime Reading App"}

