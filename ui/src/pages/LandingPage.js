import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './LandingPage.css';

const LandingPage = () => {
    const [stories, setStories] = useState([]);
    const [theme, setTheme] = useState('');
    const [currentStoryId, setCurrentStoryId] = useState(null);
    const [popupStory, setPopupStory] = useState(null);
    const [isLoading, setIsLoading] = useState(false); // Loading state
    const navigate = useNavigate();

    useEffect(() => {
        const fetchStories = async () => {
            try {
                const response = await fetch('http://localhost:8000/get-all-stories/');
                const data = await response.json();
                setStories(data);
            } catch (error) {
                console.error('Error fetching stories:', error);
            }
        };

        fetchStories();
    }, []);

    const handleGenerateStory = async () => {
        if (!theme) {
            alert("Please enter a theme.");
            return;
        }

        setIsLoading(true); // Start loading

        try {
            const response = await fetch('http://localhost:8000/generate-story/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    theme,
                    improvisations: [], // No improvisations for now
                }),
            });
            const data = await response.json();
            setCurrentStoryId(data.story_id);
            navigate(`/story/${data.story_id}`);
        } catch (error) {
            console.error('Error generating story:', error);
        } finally {
            setIsLoading(false); // Stop loading
        }
    };

    const handleViewStory = async (storyId) => {
        setIsLoading(true); // Start loading

        try {
            const response = await fetch(`http://localhost:8000/get-story/?story_id=${storyId}`);
            const data = await response.json();
            setPopupStory(data);
        } catch (error) {
            console.error('Error fetching story:', error);
        } finally {
            setIsLoading(false); // Stop loading
        }
    };

    const handleClosePopup = () => {
        setPopupStory(null);
    };

    return (
        <div className="landing-page">
            <div className="generate-story-section">
                <h2>Generate New Story</h2>
                <input
                    type="text"
                    placeholder="Enter story theme"
                    value={theme}
                    onChange={(e) => setTheme(e.target.value)}
                />
                <button onClick={handleGenerateStory} disabled={isLoading}>
                    {isLoading ? (
                        <span className="spinner"></span> // Spinner during loading
                    ) : (
                        "Generate Story"
                    )}
                </button>
            </div>

            <div className="saved-stories-section">
                <h2>Your Stories</h2>
                <div className="stories-container">
                    {stories.map((story) => (
                        <div
                            key={story.story_id}
                            className="story-card"
                            onClick={() => handleViewStory(story.story_id)}
                        >
                            <h2>{story.theme}</h2>
                            <p>{story.content.slice(0, 100)}...</p>
                        </div>
                    ))}
                </div>
            </div>

            {popupStory && (
                <div className="popup-overlay">
                    <div className="popup-content">
                        <h2>{popupStory.theme}</h2>
                        <p>{popupStory.content}</p>
                        <div className="popup-footer">
                            <button onClick={handleClosePopup}>Close</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LandingPage;
