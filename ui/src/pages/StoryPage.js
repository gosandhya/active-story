import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './StoryPage.css';

const StoryPage = () => {
    const { storyId } = useParams();
    const navigate = useNavigate();
    const [story, setStory] = useState('');
    const [improvisation, setImprovisation] = useState('');
    const [improvisationsCount, setImprovisationsCount] = useState(0);
    const [maxImprovisations] = useState(3);

    useEffect(() => {
        const fetchStory = async () => {
            try {
                const response = await fetch(`http://localhost:8000/get-story/?story_id=${storyId}`);
                const data = await response.json();
                setStory(data.content);
            } catch (error) {
                console.error('Error fetching story:', error);
            }
        };

        fetchStory();
    }, [storyId]);

    const handleAddImprovisation = async () => {
        if (improvisationsCount >= maxImprovisations) {
            alert("You can only add improvisations 3 times.");
            return;
        }

        if (!improvisation) {
            alert("Please enter an improvisation.");
            return;
        }

        try {
            const response = await fetch('http://localhost:8000/continue-story/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyId,
                    improv: improvisation,
                }),
            });
            const data = await response.json();
            setStory(data.story);
            setImprovisation('');
            setImprovisationsCount(improvisationsCount + 1);
        } catch (error) {
            console.error('Error adding improvisation:', error);
        }
    };

    const handleSaveStory = async () => {
        try {
            await fetch(`http://localhost:8000/update-story/${storyId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: story,
                }),
            });
            navigate('/');
        } catch (error) {
            console.error('Error saving story:', error);
        }
    };

    return (
        <div className="story-page">
            <h2>Story Page</h2>
            <div className="story-content">
                <p>{story}</p>
            </div>
            {improvisationsCount < maxImprovisations && (
                <div className="improvisation-section">
                    <input
                        type="text"
                        placeholder="Add improvisation"
                        value={improvisation}
                        onChange={(e) => setImprovisation(e.target.value)}
                    />
                    <button onClick={handleAddImprovisation}>Add Improvisation</button>
                </div>
            )}
            <button onClick={handleSaveStory}>Save Story</button>
        </div>
    );
};

export default StoryPage;
