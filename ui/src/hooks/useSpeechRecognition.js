import { useState, useEffect, useRef } from 'react';

/**
 * Custom hook for speech-to-text using Web Speech API
 * Works best in Chrome/Edge, limited support in Safari, minimal in Firefox
 */
const useSpeechRecognition = () => {
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const [supported, setSupported] = useState(false);

  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check browser compatibility
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSupported(false);
      setError('Speech recognition not supported in this browser. Try Chrome or Edge.');
      return;
    }

    setSupported(true);

    // Initialize speech recognition
    const recognition = new SpeechRecognition();
    recognition.continuous = true; // Keep listening
    recognition.interimResults = true; // Show interim results
    recognition.lang = 'en-US';

    // Handle results
    recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      // Build up final and interim transcripts
      for (let i = 0; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      // Combine final + interim for live display
      const fullTranscript = (finalTranscript + interimTranscript).trim();
      console.log('Speech recognition result:', fullTranscript);
      setTranscript(fullTranscript);
    };

    // Handle errors
    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);

      switch (event.error) {
        case 'no-speech':
          setError('No speech detected. Please try again.');
          break;
        case 'audio-capture':
          setError('Microphone not found. Please check your device.');
          break;
        case 'not-allowed':
          setError('Microphone permission denied. Please allow microphone access.');
          break;
        case 'network':
          setError('Network error. Please check your connection.');
          break;
        default:
          setError(`Error: ${event.error}`);
      }
    };

    // Handle end of recognition
    recognition.onend = () => {
      console.log('Speech recognition ended');
      setIsListening(false);
    };

    // Handle start
    recognition.onstart = () => {
      console.log('Speech recognition started');
      setIsListening(true);
      setError(null);
    };

    recognitionRef.current = recognition;

    // Cleanup
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const startListening = () => {
    if (!supported) {
      console.log('Speech recognition not supported');
      return;
    }

    setError(null);
    setTranscript(''); // Clear previous transcript
    console.log('Starting speech recognition...');

    try {
      recognitionRef.current?.start();
    } catch (err) {
      console.error('Error starting recognition:', err);
      setError('Failed to start listening. Please try again.');
    }
  };

  const stopListening = () => {
    if (!supported) {
      return;
    }

    try {
      recognitionRef.current?.stop();
    } catch (err) {
      console.error('Error stopping recognition:', err);
    }
  };

  const resetTranscript = () => {
    setTranscript('');
    setError(null);
  };

  return {
    transcript,
    isListening,
    error,
    supported,
    startListening,
    stopListening,
    resetTranscript
  };
};

export default useSpeechRecognition;
