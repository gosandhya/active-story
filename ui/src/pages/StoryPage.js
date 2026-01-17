import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import SpeechButton from '../components/SpeechButton';
import './StoryPage.css';

const StoryPage = () => {
    const { storyId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();

    const [storyTurns, setStoryTurns] = useState([]); // Array of story turns (chat-like)
    const [currentStreamingText, setCurrentStreamingText] = useState(''); // Currently streaming text
    const [isStreaming, setIsStreaming] = useState(false);
    const [improvisation, setImprovisation] = useState('');
    const [improvisationsCount, setImprovisationsCount] = useState(0);
    const [maxImprovisations] = useState(3);
    const [loadingImprov, setLoadingImprov] = useState(false);
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);
    const [hasAudio, setHasAudio] = useState(false);
    const [preparingAudio, setPreparingAudio] = useState(false);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1); // For word highlighting
    const [activeTurnIndex, setActiveTurnIndex] = useState(-1); // Which turn is currently playing
    const audioRef = useRef(null);
    const hasInitializedRef = useRef(false);
    const preparedAudioRef = useRef(null); // Store prepared audio

    // Single effect - initialize story (generate new OR fetch existing)
    useEffect(() => {
        if (hasInitializedRef.current) return; // Run only once

        hasInitializedRef.current = true;

        // Stop any audio that might be playing from other pages
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlayingAudio(false);
        setHasAudio(false);
        setCurrentWordIndex(-1);
        setActiveTurnIndex(-1);

        if (location.state?.isNew && location.state?.theme) {
            // NEW story - generate with this storyId
            console.log('Generating NEW story with ID:', storyId);
            handleStreamingGeneration(location.state.theme, storyId);
        } else {
            // EXISTING story - fetch from backend
            console.log('Fetching EXISTING story:', storyId);
            fetchExistingStory();
        }

        // Cleanup
        return () => {
            hasInitializedRef.current = false;
        };
    }, [storyId]);

    const handleStreamingGeneration = async (theme, providedStoryId) => {
        console.log('handleStreamingGeneration: Starting with ID', providedStoryId);
        setIsStreaming(true);
        setCurrentStreamingText('');

        try {
            // Use simple streaming endpoint (text only, no audio)
            const response = await fetch('http://localhost:8000/generate-story-stream/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    theme,
                    improvisations: [],
                    story_id: providedStoryId, // Pass the ID to backend
                }),
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let completeStory = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.text) {
                                completeStory += data.text;
                                setCurrentStreamingText(completeStory);
                            }

                            if (data.done) {
                                console.log('=== DONE MESSAGE ===');
                                console.log('Accumulated story length:', completeStory.length);
                                console.log('Accumulated story:', completeStory);
                                if (data.story) {
                                    console.log('Backend story length:', data.story.length);
                                    console.log('Backend story:', data.story);
                                    console.log('Stories match?', completeStory === data.story);
                                    completeStory = data.story; // Use backend's cleaned version
                                }
                                console.log('Final story to display/play:', completeStory);
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }

            console.log('=== AFTER STREAMING LOOP ===');
            console.log('Complete story length:', completeStory.length);
            console.log('Complete story (first 200 chars):', completeStory.substring(0, 200));

            // Hide streaming text and show preparing state
            setCurrentStreamingText('');
            setIsStreaming(false);
            setPreparingAudio(true);

            // NO NAVIGATION - we're already on the right URL!

            // Prepare audio first (this takes time with Deepgram)
            console.log('Preparing TTS audio...');
            const audioReady = await prepareStoryAudio(completeStory);

            if (audioReady) {
                // Now show the text AND start playing audio simultaneously
                console.log('Audio ready! Showing text and playing...');
                setStoryTurns([{ text: completeStory, type: 'story' }]);
                setPreparingAudio(false);
                await playPreparedAudio();
            } else {
                // Fallback: show text even if audio failed
                setStoryTurns([{ text: completeStory, type: 'story' }]);
                setPreparingAudio(false);
            }

        } catch (error) {
            console.error('Streaming error:', error);
            setIsStreaming(false);
            setPreparingAudio(false);
        }
    };

    const prepareStoryAudio = async (text) => {
        console.log('=== prepareStoryAudio: Fetching audio from Deepgram ===');
        if (!text) return false;

        try {
            const ttsStartTime = Date.now();
            const response = await fetch('http://localhost:8000/text-to-speech/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });
            console.log(`TTS API took: ${Date.now() - ttsStartTime}ms`);

            if (!response.ok) {
                console.error('TTS failed');
                return false;
            }

            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);

            preparedAudioRef.current = { audio, audioUrl, text };
            console.log('Audio prepared and ready to play');
            return true;
        } catch (error) {
            console.error('TTS preparation error:', error);
            return false;
        }
    };

    const playPreparedAudio = async (turnIndex = 0) => {
        if (!preparedAudioRef.current) {
            console.log('No prepared audio');
            return;
        }

        const { audio, audioUrl, text } = preparedAudioRef.current;
        audioRef.current = audio;
        setHasAudio(true);
        setActiveTurnIndex(turnIndex);
        setIsPlayingAudio(true);

        console.log('playPreparedAudio: Starting playback');

        // Calculate words for highlighting
        const words = text.split(/\s+/);

        // Use a small delay to ensure audio duration is available
        await new Promise(resolve => setTimeout(resolve, 100));

        const duration = audio.duration;
        console.log('Audio duration:', duration, 'seconds');

        if (!duration || duration === 0 || !isFinite(duration)) {
            console.error('Invalid audio duration, highlighting disabled');
            // Just play without highlighting
            audio.play();

            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                setIsPlayingAudio(false);
                setHasAudio(false);
                setActiveTurnIndex(-1);
                audioRef.current = null;
                preparedAudioRef.current = null;
            };

            return;
        }

        // Use timeupdate event to sync highlighting with actual playback position
        console.log(`Using linear interpolation for ${words.length} words`);

        audio.ontimeupdate = () => {
            const currentTime = audio.currentTime; // in seconds
            const progress = currentTime / duration; // 0 to 1
            const currentWordIndex = Math.floor(progress * words.length);

            if (currentWordIndex < words.length) {
                setCurrentWordIndex(currentWordIndex);
            }
        };

        // Set up cleanup handlers
        audio.onended = () => {
            console.log('Audio ended');
            URL.revokeObjectURL(audioUrl);
            setIsPlayingAudio(false);
            setHasAudio(false);
            setCurrentWordIndex(-1);
            setActiveTurnIndex(-1);
            audioRef.current = null;
            preparedAudioRef.current = null;
        };

        audio.onerror = (e) => {
            console.error('Audio playback error:', e);
            URL.revokeObjectURL(audioUrl);
            setIsPlayingAudio(false);
            setHasAudio(false);
            setCurrentWordIndex(-1);
            setActiveTurnIndex(-1);
            audioRef.current = null;
            preparedAudioRef.current = null;
        };

        // Start playing
        try {
            await audio.play();
            console.log('Audio playing successfully');
        } catch (err) {
            console.error('Error starting playback:', err);
        }
    };

    const playStoryAudio = async (text) => {
        console.log('=== playStoryAudio CALLED (legacy) ===');
        console.log('Text length:', text?.length);
        console.log('Text (first 200 chars):', text?.substring(0, 200));

        if (!text) {
            console.log('playStoryAudio: No text provided');
            return;
        }

        // Prevent double playback
        if (isPlayingAudio || audioRef.current) {
            console.log('playStoryAudio: Audio already playing or loaded, skipping');
            return;
        }

        console.log('Sending to TTS API...');
        setIsPlayingAudio(true);

        try {
            const ttsStartTime = Date.now();
            // Call TTS endpoint with complete story
            const response = await fetch('http://localhost:8000/text-to-speech/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text }),
            });
            console.log(`TTS API call took: ${Date.now() - ttsStartTime}ms`);

            if (!response.ok) {
                console.error('TTS failed');
                setIsPlayingAudio(false);
                return;
            }

            // Get audio blob and play
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audioRef.current = audio;
            setHasAudio(true); // Show pause button

            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
                setIsPlayingAudio(false);
                setHasAudio(false);
                audioRef.current = null;
            };

            audio.onerror = () => {
                URL.revokeObjectURL(audioUrl);
                console.error('Audio playback error');
                setIsPlayingAudio(false);
                setHasAudio(false);
                audioRef.current = null;
            };

            console.log('Starting audio playback...');
            await audio.play();
        } catch (error) {
            console.error('TTS error:', error);
            setIsPlayingAudio(false);
            setHasAudio(false);
            audioRef.current = null;
        }
    };

    const toggleAudioPlayback = () => {
        if (!audioRef.current) {
            console.log('toggleAudioPlayback: No audio ref');
            return;
        }

        console.log('toggleAudioPlayback: Current state:', isPlayingAudio);

        if (isPlayingAudio) {
            console.log('Pausing audio...');
            audioRef.current.pause();
            setIsPlayingAudio(false);
            setCurrentWordIndex(-1); // Clear highlighting when paused
            // Pause the highlight interval (don't clear it, so we can resume)
            // Note: We don't clear the interval here because we want to resume from the same position
        } else {
            console.log('Resuming audio...');
            audioRef.current.play().catch(err => {
                console.error('Error resuming audio:', err);
            });
            setIsPlayingAudio(true);
            // Note: The interval continues running, so highlighting will resume
        }
    };

    const fetchExistingStory = async () => {
        console.log('fetchExistingStory: Loading story', storyId);
        try {
            const response = await fetch(`http://localhost:8000/get-story/?story_id=${storyId}`);
            const data = await response.json();

            // Convert existing story to turns format
            setStoryTurns([{ text: data.content, type: 'story' }]);
            setImprovisationsCount(data.improvisations?.length || 0);

            // DON'T auto-play audio for existing stories
            console.log('Existing story loaded. NOT auto-playing audio.');
        } catch (error) {
            console.error('Error fetching story:', error);
        }
    };

    const handleAddImprovisation = async () => {
        if (improvisationsCount >= maxImprovisations) {
            alert("You can only add improvisations 3 times.");
            return;
        }

        if (!improvisation) {
            alert("Please enter an improvisation.");
            return;
        }

        // Clear previous audio before adding new turn
        if (audioRef.current) {
            console.log('Clearing previous audio before new improvisation');
            audioRef.current.pause();
            audioRef.current = null;
            setIsPlayingAudio(false);
            setHasAudio(false);
            setCurrentWordIndex(-1);
            setActiveTurnIndex(-1);
        }

        // Add user's improvisation as a turn
        setStoryTurns(prev => [...prev, { text: improvisation, type: 'user' }]);

        const userImprov = improvisation;
        setImprovisation('');
        setLoadingImprov(true);

        try {
            const response = await fetch('http://localhost:8000/continue-story/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    story_id: storyId,
                    improv: userImprov,
                }),
            });
            const data = await response.json();

            // Extract just the new continuation (last part after \n\n\n)
            const newContinuation = data.story.split('\n\n\n').pop();

            // Show preparing state
            setLoadingImprov(false);
            setPreparingAudio(true);

            // Prepare audio first before showing text
            const audioReady = await prepareStoryAudio(newContinuation);

            // Now add the turn and play audio
            // We already added the user turn earlier, so AI turn will be at storyTurns.length + 1
            const turnIndex = storyTurns.length + 1;
            setStoryTurns(prev => [...prev, { text: newContinuation, type: 'story' }]);
            setImprovisationsCount(improvisationsCount + 1);
            setPreparingAudio(false);

            if (audioReady) {
                await playPreparedAudio(turnIndex);
            }

        } catch (error) {
            console.error('Error adding improvisation:', error);
        } finally {
            setLoadingImprov(false);
            setPreparingAudio(false);
        }
    };

    const handleGoHome = () => {
        // Clean up audio before navigating
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        setIsPlayingAudio(false);
        setHasAudio(false);
        setCurrentWordIndex(-1);
        setActiveTurnIndex(-1);
        navigate('/');
    };

    const handleVoiceImprovisation = (transcript) => {
        setImprovisation(transcript);
    };

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
            setCurrentWordIndex(-1);
            setActiveTurnIndex(-1);
        };
    }, []);

    return (
        <div className="story-page">
            <div className="story-header">
                <h2>📖 Story Time</h2>
                <div className="header-actions">
                    {hasAudio && (
                        <button
                            className="audio-control-button"
                            onClick={toggleAudioPlayback}
                            title={isPlayingAudio ? 'Pause audio' : 'Resume audio'}
                        >
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
                        </button>
                    )}
                    <button className="home-button" onClick={handleGoHome}>
                        ← Home
                    </button>
                </div>
            </div>

            {/* Story turns - chat-like bubbles */}
            <div className="story-turns-container">
                {storyTurns.map((turn, index) => {
                    // Split text into words for highlighting
                    const words = turn.text.split(/(\s+)/); // Preserve whitespace
                    let wordIndex = 0;

                    return (
                        <div
                            key={index}
                            className={`story-turn ${turn.type === 'user' ? 'user-turn' : 'story-turn'}`}
                        >
                            <div className="turn-label">
                                {turn.type === 'user' ? '👤 You' : '✨ Story'}
                            </div>
                            <div className="turn-text">
                                {words.map((word, i) => {
                                    // Skip whitespace words when counting
                                    const isWhitespace = /^\s+$/.test(word);
                                    const currentWordIdx = wordIndex;
                                    if (!isWhitespace) wordIndex++;

                                    // Highlight if: this is the active turn AND this word is the current one AND audio is playing
                                    const shouldHighlight = index === activeTurnIndex &&
                                                          turn.type === 'story' &&
                                                          !isWhitespace &&
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
                                })}
                            </div>
                        </div>
                    );
                })}

                {/* Currently streaming text */}
                {isStreaming && currentStreamingText && (
                    <div className="story-turn story-turn streaming">
                        <div className="turn-label">
                            ✨ Story <span className="streaming-indicator">●</span>
                        </div>
                        <div className="turn-text">
                            {currentStreamingText}
                        </div>
                    </div>
                )}

                {/* Loading indicator for improvisation */}
                {loadingImprov && !currentStreamingText && (
                    <div className="story-turn story-turn">
                        <div className="turn-label">
                            ✨ Story
                        </div>
                        <div className="turn-text">
                            <span className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </span>
                        </div>
                    </div>
                )}

                {/* Preparing audio indicator */}
                {preparingAudio && (
                    <div className="story-turn story-turn">
                        <div className="turn-label">
                            🎵 Preparing Story
                        </div>
                        <div className="turn-text">
                            <span className="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </span>
                        </div>
                    </div>
                )}
            </div>

            {/* Improvisation input - only show after story generation is complete */}
            {improvisationsCount < maxImprovisations && !isStreaming && storyTurns.length > 0 && !loadingImprov && (
                <div className="improvisation-section">
                    <div className="improv-input-container">
                        <input
                            type="text"
                            placeholder="What happens next?"
                            value={improvisation}
                            onChange={(e) => setImprovisation(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleAddImprovisation()}
                        />
                        <SpeechButton
                            onTranscript={handleVoiceImprovisation}
                            placeholder="Use Chrome for voice"
                        />
                    </div>
                    <button onClick={handleAddImprovisation} disabled={loadingImprov || !improvisation}>
                        Continue Story →
                    </button>
                </div>
            )}

            {improvisationsCount >= maxImprovisations && (
                <div className="story-complete">
                    <p>🎉 Story Complete!</p>
                    <button onClick={handleGoHome}>
                        Create Another Story
                    </button>
                </div>
            )}
        </div>
    );
};

export default StoryPage;
