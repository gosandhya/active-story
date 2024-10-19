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
    const [loadingImprov, setLoadingImprov] = useState(false); // Loading state for improvisation
    const [loadingSave, setLoadingSave] = useState(false); // Loading state for saving

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

        setLoadingImprov(true); // Set loading to true when API call starts

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
        } finally {
            setLoadingImprov(false); // Set loading to false when API call ends
        }
    };

    const handleSaveStory = async () => {
        setLoadingSave(true); // Set loading to true when API call starts
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
        } finally {
            setLoadingSave(false); // Set loading to false when API call ends
        }
    };

    // Function to render story with line breaks
    const renderStory = (storyContent) => {
        return storyContent.split('\n').map((item, index) => (
            <span key={index}>
                {item}
                <br /> {/* Add a line break for each new line */}
            </span>
        ));
    };

    return (
        <div className="story-page">
            <h2>Story Page</h2>
            <div className="story-content">
                {renderStory(story)}
            </div>
            {improvisationsCount < maxImprovisations && (
                <div className="improvisation-section">
                    <input
                        type="text"
                        placeholder="Add improvisation"
                        value={improvisation}
                        onChange={(e) => setImprovisation(e.target.value)}
                    />
                    <button onClick={handleAddImprovisation} disabled={loadingImprov}>
                        {loadingImprov ? <span className="spinner"></span> : "Add Improvisation"}
                    </button>
                </div>
            )}
            <button onClick={handleSaveStory} disabled={loadingSave}>
                {loadingSave ? <span className="spinner"></span> : "Save Story"}
            </button>
        </div>
    );
};

export default StoryPage;
