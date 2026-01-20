import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import SpeechButton from '../components/SpeechButton';
import './LandingPage.css';

const LandingPage = () => {
    const [stories, setStories] = useState([]);
    const [theme, setTheme] = useState('');
    const [currentStoryId, setCurrentStoryId] = useState(null);
    const [popupStory, setPopupStory] = useState(null);
    const [isLoading, setIsLoading] = useState(false); // Loading state
    const [isGeneratingStory, setIsGeneratingStory] = useState(false); // Streaming state
    const [streamingStory, setStreamingStory] = useState(''); // Streaming story text
    const [generatedStoryId, setGeneratedStoryId] = useState(null); // Generated story ID
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1);
    const [storyVersion, setStoryVersion] = useState('v1'); // v1 or v2
    const audioRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        // Clear stories immediately when version changes
        setStories([]);

        const fetchStories = async () => {
            try {
                // Fetch from appropriate endpoint based on version
                const endpoint = storyVersion === 'v2'
                    ? 'http://localhost:8000/stories-v2/'
                    : 'http://localhost:8000/get-all-stories/';

                // Add cache-busting to prevent stale data
                const response = await fetch(endpoint, {
                    cache: 'no-store',
                    headers: { 'Cache-Control': 'no-cache' }
                });
                const data = await response.json();

                // Normalize data format for both versions
                if (storyVersion === 'v2') {
                    // V2 uses thread_id instead of story_id
                    setStories(data.map(story => ({
                        story_id: story.thread_id,
                        theme: story.theme,
                        content: story.content_preview,
                        turn: story.turn,
                        phase: story.phase
                    })));
                } else {
                    setStories(data);
                }
            } catch (error) {
                console.error('Error fetching stories:', error);
            }
        };

        fetchStories();

        // Cleanup on unmount
        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
        };
    }, [storyVersion]); // Re-fetch when version changes

    const handleGenerateStory = async () => {
        if (!theme) {
            alert("Please enter a theme.");
            return;
        }

        // Generate a unique ID upfront (simple UUID v4)
        const newStoryId = crypto.randomUUID();

        // Navigate to story page with the ID, theme, and version
        navigate(`/story/${newStoryId}`, {
            state: { theme, isNew: true, version: storyVersion }
        });
    };

    const handleViewStory = async (storyId) => {
        // Reset audio state when opening a new story
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlayingAudio(false);

        setIsLoading(true); // Start loading

        try {
            // Fetch from appropriate endpoint based on version
            const endpoint = storyVersion === 'v2'
                ? `http://localhost:8000/story-v2/${storyId}`
                : `http://localhost:8000/get-story/?story_id=${storyId}`;

            const response = await fetch(endpoint);
            const data = await response.json();

            // Normalize data for popup display
            if (storyVersion === 'v2') {
                setPopupStory({
                    story_id: data.thread_id,
                    theme: data.theme,
                    content: data.content,
                    turn: data.turn,
                    phase: data.phase
                });
            } else {
                setPopupStory(data);
            }
        } catch (error) {
            console.error('Error fetching story:', error);
        } finally {
            setIsLoading(false); // Stop loading
        }
    };

    const handleClosePopup = () => {
        // Stop audio if playing
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setPopupStory(null);
        setIsPlayingAudio(false);
        setCurrentWordIndex(-1);
    };

    const handleVoiceInput = (transcript) => {
        setTheme(transcript);
    };

    const handleDeleteStory = async (e, storyId) => {
        e.stopPropagation(); // Prevent card click
        e.preventDefault();

        // Remove from UI immediately
        setStories(prev => prev.filter(s => s.story_id !== storyId));

        // Then delete from backend
        try {
            const endpoint = storyVersion === 'v2'
                ? `http://localhost:8000/story-v2/${storyId}`
                : `http://localhost:8000/delete-story/${storyId}`;

            await fetch(endpoint, { method: 'DELETE' });
        } catch (error) {
            console.error('Error deleting story:', error);
        }
    };

    const handlePlayStory = async () => {
        if (!popupStory?.content) return;

        // If already playing, pause it
        if (isPlayingAudio && audioRef.current) {
            audioRef.current.pause();
            setIsPlayingAudio(false);
            return;
        }

        // If paused, resume
        if (audioRef.current && !isPlayingAudio) {
            audioRef.current.play();
            setIsPlayingAudio(true);
            return;
        }

        // Start new playback
        setIsPlayingAudio(true);
        setCurrentWordIndex(-1);

        try {
            const response = await fetch('http://localhost:8000/text-to-speech/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: popupStory.content }),
            });

            if (!response.ok) {
                console.error('TTS failed');
                setIsPlayingAudio(false);
                return;
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audioRef.current = audio;

            // Wait for audio metadata to get duration
            await new Promise(resolve => setTimeout(resolve, 100));

            const duration = audio.duration;
            const words = popupStory.content.split(/\s+/);

            if (duration && isFinite(duration)) {
                // Use timeupdate event to sync highlighting
                audio.ontimeupdate = () => {
                    const currentTime = audio.currentTime;
                    const progress = currentTime / duration;
                    const wordIndex = Math.floor(progress * words.length);

                    if (wordIndex < words.length) {
                        setCurrentWordIndex(wordIndex);
                    }
                };
            }

            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                setIsPlayingAudio(false);
                setCurrentWordIndex(-1);
                audioRef.current = null;
            };

            audio.onerror = () => {
                URL.revokeObjectURL(audioUrl);
                console.error('Audio playback error');
                setIsPlayingAudio(false);
                setCurrentWordIndex(-1);
                audioRef.current = null;
            };

            await audio.play();
        } catch (error) {
            console.error('TTS error:', error);
            setIsPlayingAudio(false);
            setCurrentWordIndex(-1);
            audioRef.current = null;
        }
    };

    return (
        <div className="landing-page">
            <div className="generate-story-section">
                <h2>Generate New Story</h2>

                {/* Agentic Mode Toggle */}
                <div className="agentic-toggle">
                    <span className={`toggle-label ${storyVersion === 'v1' ? 'active' : ''}`}>Simple</span>
                    <label className="toggle-switch">
                        <input
                            type="checkbox"
                            checked={storyVersion === 'v2'}
                            onChange={(e) => setStoryVersion(e.target.checked ? 'v2' : 'v1')}
                        />
                        <span className="toggle-slider"></span>
                    </label>
                    <span className={`toggle-label ${storyVersion === 'v2' ? 'active' : ''}`}>Agentic</span>
                </div>

                <div className="theme-input-container">
                    <input
                        type="text"
                        placeholder="Enter story theme"
                        value={theme}
                        onChange={(e) => setTheme(e.target.value)}
                    />
                    <SpeechButton
                        onTranscript={handleVoiceInput}
                        placeholder="Use Chrome for voice input"
                    />
                </div>
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
                            <button
                                className="delete-story-btn"
                                onClick={(e) => handleDeleteStory(e, story.story_id)}
                                title="Delete story"
                            >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg>
                            </button>
                            <h2>{story.theme}</h2>
                            <p>{story.content?.slice(0, 100) || 'No content yet'}...</p>
                        </div>
                    ))}
                </div>
            </div>

            {popupStory && (
                <div className="popup-overlay" onClick={handleClosePopup}>
                    <div className="popup-content" onClick={(e) => e.stopPropagation()}>
                        <div className="popup-header">
                            <h2>{popupStory.theme}</h2>
                            <button className="popup-close" onClick={handleClosePopup}>×</button>
                        </div>
                        <div className="popup-body">
                            <p>
                                {(() => {
                                    const words = (popupStory.content || '').split(/(\s+)/); // Preserve whitespace
                                    let wordIndex = 0;

                                    return words.map((word, i) => {
                                        const isWhitespace = /^\s+$/.test(word);
                                        const currentWordIdx = wordIndex;
                                        if (!isWhitespace) wordIndex++;

                                        // Highlight if this is the current word and audio is playing
                                        const shouldHighlight = !isWhitespace &&
                                                              currentWordIdx === currentWordIndex &&
                                                              isPlayingAudio;

                                        return (
                                            <span
                                                key={i}
                                                className={shouldHighlight ? 'highlighted-word' : ''}
                                            >
                                                {word}
                                            </span>
                                        );
                                    });
                                })()}
                            </p>
                        </div>
                        <div className="popup-footer">
                            <button onClick={handlePlayStory}>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    {isPlayingAudio ? (
                                        <>
                                            <rect x="6" y="4" width="4" height="16"/>
                                            <rect x="14" y="4" width="4" height="16"/>
                                        </>
                                    ) : (
                                        <polygon points="5 3 19 12 5 21 5 3"/>
                                    )}
                                </svg>
                                {isPlayingAudio ? 'Pause' : (audioRef.current ? 'Resume Story' : 'Play Story')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default LandingPage;
