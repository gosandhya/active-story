import uuid
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from active_story_service.db_crud import add_story, get_single_story, get_all_stories, update_story, delete_story
from active_story_service.models import StoryInput, ContinueStoryInput  # Import models



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
    story_content = f"Once upon a time, in a land where {input_data.theme}, there lived a..."
    story_data = {
        "theme": input_data.theme,
        "content": story_content,
        "improvisations": input_data.improvisations
    }
    story_id = await add_story(story_data)
    return {"story_id": story_id, "story": story_content}


@app.post("/continue-story/")
async def continue_story(input_data: ContinueStoryInput):
    story_id = input_data.story_id
    improv = input_data.improv

    story = await get_story(story_id)
    print("type[story]", story)
    print("story", story)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    continued_story = f"{story['content']} And then, {improv} happened."
    update_data = {"content": continued_story, "improvisations": [improv]}
    await update_story(story_id, update_data)
    
    return {"story_id": story_id, "story": continued_story}



@app.get("/get-story/")
async def get_story(story_id: str):
    # Retrieve the story from MongoDB
    story = await get_single_story(story_id)
    
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    return {
        "story_id": story_id,
        "content": story.get("content", ""),
        "improvisations": story.get("improvisations", [])
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

