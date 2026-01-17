import React, { useEffect } from 'react';
import useSpeechRecognition from '../hooks/useSpeechRecognition';
import './SpeechButton.css';

/**
 * Reusable microphone button for speech-to-text
 * @param {Function} onTranscript - Callback when speech is finalized (user stops listening)
 * @param {string} placeholder - Placeholder text when not supported
 */
const SpeechButton = ({ onTranscript, placeholder = '' }) => {
  const {
    transcript,
    isListening,
    error,
    supported,
    startListening,
    stopListening,
    resetTranscript
  } = useSpeechRecognition();

  // Only update when user stops listening (not live)
  useEffect(() => {
    if (!isListening && transcript && onTranscript) {
      console.log('SpeechButton: Sending transcript to parent:', transcript);
      onTranscript(transcript);
      resetTranscript(); // Clear after sending
    }
  }, [isListening, transcript, onTranscript, resetTranscript]);

  const handleClick = () => {
    if (isListening) {
      console.log('SpeechButton: Stopping listening, current transcript:', transcript);
      stopListening();
    } else {
      console.log('SpeechButton: Starting listening');
      startListening();
    }
  };

  if (!supported) {
    return (
      <div className="speech-button-unsupported">
        <span title="Speech recognition not supported in this browser">🎤❌</span>
        {placeholder && <small>{placeholder}</small>}
      </div>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={`speech-button-inline ${isListening ? 'listening' : ''}`}
      title={isListening ? 'Stop listening' : 'Voice input'}
      type="button"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
      </svg>
    </button>
  );
};

export default SpeechButton;
