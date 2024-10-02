
# Active Story 

Active Story is a story generation app that allows parents and their children to interactively create stories. 
It demonstrates how AI can make bedtime stories more interactive and fun. 
It gives parents and kids a chance to bond as they co-create stories, making the experience both playful and hands-on. 
The app features a FastAPI backend for story generation, a React frontend for the user interface, and MongoDB for data persistence.


### Backend (`backend`)

The FastAPI backend provides the endpoints for generating stories. It's responsible for handling the story input and returning a story that can be dynamically updated based on user interactions.

#### How to Run the Backend

To run the FastAPI backend locally, use the following command:

```bash
uvicorn active_story_service.main:app --reload --host 0.0.0.0 --port 8000
```

This will start the backend server on `http://localhost:8000/`.

### MongoDB (`mongo-docker`)

The app uses MongoDB for storing story data, and it runs inside a Docker container.

#### How to Run MongoDB

To start MongoDB using Docker, navigate to the `mongo-docker` directory and run:

```bash
docker-compose up
```

This will spin up a MongoDB instance locally. Ensure that you have Docker installed and running on your system.

### Frontend (`ui`)

The React-based frontend provides the user interface where parents can input themes and interact with the story generation process.

- **Landing Page**: Allows users to input a theme for the story.
- **Story Page**: Displays the story, including interactive improvisation input.

#### How to Run the Frontend

Navigate to the `ui` folder and start the frontend by running:

```bash
npm start
```

This will start the frontend on `http://localhost:3000/`.

### Requirements

- **Backend**: Python 3.x, FastAPI, Uvicorn
- **Frontend**: Node.js, React
- **Database**: MongoDB (via Docker)

### Installation Steps

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/gosandhya/active-story.git
   cd active-story
   ```

2. **Backend Setup**:

   - Navigate to the `backend` folder:
     ```bash
     cd backend
     ```
   - Install dependencies:
     ```bash
     pip install -r requirements.txt
     ```
   - Run the FastAPI server:
     ```bash
     uvicorn active_story_service.main:app --reload --host 0.0.0.0 --port 8000
     ```

3. **Frontend Setup**:

   - Navigate to the `ui` folder:
     ```bash
     cd ui
     ```
   - Install dependencies:
     ```bash
     npm install
     ```
   - Start the React frontend:
     ```bash
     npm start
     ```

4. **MongoDB Setup**:

   - Navigate to the `mongo-docker` folder:
     ```bash
     cd mongo-docker
     ```
   - Start MongoDB using Docker:
     ```bash
     docker-compose up
     ```

### API Endpoints

access swagger docs: http://localhost:8000/docs
