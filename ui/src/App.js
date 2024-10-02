import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import StoryPage from './pages/StoryPage';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/story/:storyId" element={<StoryPage />} />
            </Routes>
        </Router>
    );
}

export default App;
