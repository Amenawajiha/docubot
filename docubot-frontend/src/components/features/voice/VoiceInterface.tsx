"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { Mic, MicOff, Volume2, Loader2, AlertCircle, Sparkles, Send, Keyboard, X } from "lucide-react";
import { AudioQueue } from "@/lib/voice/audioQueue";

interface VoiceInterfaceProps {
  workspaceId: string;
  chatbotId: string;
  chatbotName?: string;
  botColor?: string;
  sessionToken?: string | null;
  onClose?: () => void;
  onNewMessage?: (msg: { role: "user" | "bot"; text: string; sources?: any[] }) => void;
}

type Mode = "ptt" | "handsfree";
type Status = "idle" | "listening" | "processing" | "speaking";

export function VoiceInterface({
  workspaceId,
  chatbotId,
  chatbotName = "DocuBot",
  botColor = "#6366f1",
  sessionToken,
  onClose,
  onNewMessage,
}: VoiceInterfaceProps) {
  const [mode] = useState<Mode>("handsfree");
  const [status, setStatus] = useState<Status>("idle");
  const [connected, setConnected] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [textInput, setTextInput] = useState("");
  const [isMuted, setIsMuted] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioQueueRef = useRef<AudioQueue | null>(null);

  // Web Audio refs for VAD and Visualizer
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const orbRef = useRef<HTMLButtonElement>(null);
  const orbGlowRef = useRef<HTMLDivElement>(null);

  // Hands-free VAD state tracking
  const isRecordingRef = useRef(false);
  const isPlayingRef = useRef(false);
  const silenceStartRef = useRef<number | null>(null);
  const lastVolumeRef = useRef<number>(0);
  const hasSpokenRef = useRef(false);
  const speechFramesCountRef = useRef(0);

  // Derive WebSocket URL
  const getWsUrl = useCallback(() => {
    if (!sessionToken) return "";
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";
    const wsBase = apiBase.replace(/^http/, "ws");
    return `${wsBase}/workspaces/${workspaceId}/chatbots/${chatbotId}/playground/voice?token=${sessionToken}`;
  }, [workspaceId, chatbotId, sessionToken]);

  // Setup AudioQueue
  useEffect(() => {
    const queue = new AudioQueue();
    queue.setOnEnded(() => {
      isPlayingRef.current = false;
      setStatus("idle");
      // Re-enable microphone strictly after speech playback completes
      if (mode === "handsfree" && !isMuted && !isRecordingRef.current) {
        setTimeout(() => {
          if (!isPlayingRef.current && !isRecordingRef.current) {
            startRecording();
          }
        }, 400);
      }
    });
    audioQueueRef.current = queue;

    return () => {
      audioQueueRef.current?.interrupt();
    };
  }, [mode, isMuted]);

  // Manage WebSocket connection
  useEffect(() => {
    if (!workspaceId || !chatbotId || !sessionToken) return;

    connectWebSocket();

    return () => {
      disconnectWebSocket();
    };
  }, [workspaceId, chatbotId, sessionToken]);

  // Visualizer Animation Loop
  useEffect(() => {
    let active = true;

    const updateOrb = () => {
      if (!active) return;
      animationFrameRef.current = requestAnimationFrame(updateOrb);

      let currentVolume = 0;

      // 1. User mic volume
      if (isRecordingRef.current && analyserRef.current && !isMuted) {
        const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
        analyserRef.current.getByteTimeDomainData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          const val = (dataArray[i] - 128) / 128;
          sum += val * val;
        }
        currentVolume = Math.sqrt(sum / dataArray.length);
        lastVolumeRef.current = currentVolume;
      }
      // 2. Assistant speech volume
      else if (status === "speaking" && audioQueueRef.current) {
        currentVolume = audioQueueRef.current.getVolumeLevel();
      }

      // 3. Smooth dynamic scaling
      if (orbRef.current && orbGlowRef.current) {
        const basePulse = 1 + 0.04 * Math.sin(Date.now() / 250);
        const volumeScale = currentVolume * 2.8;
        const totalScale = basePulse + volumeScale;

        orbRef.current.style.transform = `scale(${totalScale})`;

        const glowScale = totalScale * 1.2;
        const glowOpacity = Math.min(0.7, 0.15 + currentVolume * 1.8);
        orbGlowRef.current.style.transform = `scale(${glowScale})`;
        orbGlowRef.current.style.opacity = `${glowOpacity}`;
      }
    };

    updateOrb();

    return () => {
      active = false;
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [status, isMuted]);

  const connectWebSocket = () => {
    if (!sessionToken) return;
    disconnectWebSocket();
    setErrorMsg(null);

    const wsUrl = getWsUrl();
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setErrorMsg(null);
      ws.send(JSON.stringify({ type: "start", token: sessionToken }));
      startRecording();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        switch (message.type) {
          case "status":
            if (message.status === "ready") {
              // Only re-enter listening state if assistant is NOT currently speaking
              if (!isPlayingRef.current && !isRecordingRef.current) {
                setStatus("idle");
                if (mode === "handsfree" && !isMuted) {
                  startRecording();
                }
              }
            } else if (message.status === "processing") {
              setStatus("processing");
            } else if (message.status === "playing") {
              isPlayingRef.current = true;
              setStatus("speaking");
              stopRecording();
            }
            break;

          case "transcript":
            if (message.sender === "user") {
              if (message.isFinal && message.text) {
                onNewMessage?.({ role: "user", text: message.text });
              }
            } else {
              if (message.isFinal && message.text) {
                onNewMessage?.({ role: "bot", text: message.text, sources: message.sources });
              }
            }
            break;

          case "audio":
            if (!isMuted && message.data) {
              isPlayingRef.current = true;
              setStatus("speaking");
              stopRecording();
              audioQueueRef.current?.enqueueBase64(message.data);
            }
            break;

          case "error":
            setErrorMsg(message.message || "Voice processing error.");
            break;
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    ws.onerror = () => {
      setErrorMsg("WebSocket connection error.");
      setConnected(false);
      setStatus("idle");
    };

    ws.onclose = () => {
      setConnected(false);
      setStatus("idle");
    };
  };

  const disconnectWebSocket = () => {
    stopRecording();
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    setConnected(false);
    setStatus("idle");
  };

  const startRecording = async () => {
    if (isRecordingRef.current || isPlayingRef.current) return;

    try {
      if (audioStreamRef.current) {
        audioStreamRef.current.getTracks().forEach((track) => track.stop());
        audioStreamRef.current = null;
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      audioStreamRef.current = stream;

      // Set up Web Audio Analyser
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioContextClass();
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      audioCtxRef.current = ctx;
      analyserRef.current = analyser;

      if (ctx.state === "suspended") {
        await ctx.resume();
      }

      if (audioQueueRef.current) {
        audioQueueRef.current.resume();
      }

      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: "start_turn" }));
      }

      // VAD configuration: relaxed for natural human pauses
      const SPEECH_THRESHOLD = 0.035;
      const SILENCE_THRESHOLD = 0.018;
      const SILENCE_DURATION_MS = 2200; // 2.2 seconds pause before commit
      const MIN_SPEECH_FRAMES = 2;

      silenceStartRef.current = null;
      hasSpokenRef.current = false;
      speechFramesCountRef.current = 0;

      let options: MediaRecorderOptions = { mimeType: "audio/webm;codecs=opus", audioBitsPerSecond: 128000 };
      if (!MediaRecorder.isTypeSupported(options.mimeType!)) {
        options = { mimeType: "audio/ogg;codecs=opus" };
      }
      if (!MediaRecorder.isTypeSupported(options.mimeType!)) {
        options = {};
      }

      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0 && socketRef.current?.readyState === WebSocket.OPEN && !isMuted) {
          socketRef.current.send(event.data);
        }

        // Hands-free VAD analysis
        if (mode === "handsfree" && !isMuted && isRecordingRef.current) {
          const rms = lastVolumeRef.current;

          if (rms > SPEECH_THRESHOLD) {
            speechFramesCountRef.current += 1;
            if (speechFramesCountRef.current >= MIN_SPEECH_FRAMES) {
              hasSpokenRef.current = true;
              silenceStartRef.current = null;
              setStatus("listening");
            }
          } else if (hasSpokenRef.current && rms < SILENCE_THRESHOLD) {
            if (!silenceStartRef.current) {
              silenceStartRef.current = Date.now();
            } else if (Date.now() - silenceStartRef.current > SILENCE_DURATION_MS) {
              // Silence detected after user finished speaking -> commit turn
              stopRecording();
            }
          } else if (rms >= SILENCE_THRESHOLD) {
            silenceStartRef.current = null;
          }
        }
      };

      mediaRecorder.start(200);
      isRecordingRef.current = true;
      setStatus("listening");
    } catch (err) {
      console.error("Error accessing microphone:", err);
      setErrorMsg("Microphone access denied or unavailable.");
      setStatus("idle");
    }
  };

  const stopRecording = () => {
    if (!isRecordingRef.current) return;
    isRecordingRef.current = false;

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }

    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }

    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    analyserRef.current = null;

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "stop" }));
    }

    if (!isPlayingRef.current) {
      setStatus("processing");
    }
  };

  const handleInterrupt = () => {
    stopRecording();
    isPlayingRef.current = false;
    audioQueueRef.current?.interrupt();
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "interrupt" }));
    }
    setStatus("idle");
  };

  const handleMicButton = () => {
    if (audioQueueRef.current) {
      audioQueueRef.current.initContext();
    }

    if (status === "speaking") {
      // Tap while bot is speaking -> interrupt bot and start listening
      handleInterrupt();
      setTimeout(() => startRecording(), 100);
    } else if (isMuted) {
      setIsMuted(false);
      setErrorMsg(null);
      setTimeout(() => startRecording(), 50);
    } else if (isRecordingRef.current) {
      // Tap while listening -> commit speech immediately to AI
      stopRecording();
    } else {
      setIsMuted(false);
      startRecording();
    }
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || !socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;

    audioQueueRef.current?.interrupt();
    socketRef.current.send(JSON.stringify({ type: "interrupt" }));

    onNewMessage?.({ role: "user", text: textInput.trim() });
    socketRef.current.send(JSON.stringify({ type: "text", text: textInput.trim() }));
    setTextInput("");
    setStatus("processing");
  };

  const getStatusLabel = () => {
    if (!sessionToken) return "Connecting to Voice Gateway...";
    if (!connected) return "Connecting to Voice Gateway...";
    if (isMuted) return "Microphone Muted";
    switch (status) {
      case "listening":
        return "Listening (Speak now or tap mic when done)...";
      case "processing":
        return "Thinking...";
      case "speaking":
        return `${chatbotName} is speaking`;
      default:
        return "Listening (Hands-free active)";
    }
  };

  return (
    <div className="w-full bg-white dark:bg-[#0d111b] border-t border-slate-200 dark:border-white/5 p-4 flex flex-col items-center gap-3 shrink-0 shadow-lg">
      {/* Status Bar */}
      <div className="w-full flex items-center justify-between px-2">
        <div className="flex items-center gap-2">
          {!connected ? (
            <span className="flex items-center gap-1.5 text-xs text-amber-500 font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Connecting...
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 font-medium">
              <span
                className={`w-2 h-2 rounded-full ${
                  status === "listening"
                    ? "bg-rose-500 animate-ping"
                    : status === "speaking"
                    ? "bg-emerald-500 animate-pulse"
                    : "bg-blue-500"
                }`}
              />
              {getStatusLabel()}
            </span>
          )}
        </div>

        {onClose && (
          <button
            type="button"
            onClick={() => {
              handleInterrupt();
              onClose();
            }}
            className="flex items-center gap-1 text-xs font-semibold text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-white transition-colors cursor-pointer border-0 bg-transparent"
            title="Switch back to Text Input"
          >
            <Keyboard size={13} />
            <span>Switch to Text</span>
          </button>
        )}
      </div>

      {/* Error Message Banner */}
      {errorMsg && (
        <div className="w-full bg-rose-500/10 border border-rose-500/20 text-rose-500 px-3 py-1.5 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span className="flex-1">{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-rose-500 hover:text-rose-700">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* Visualizer Pulsing Orb Center */}
      <div className="relative flex flex-col items-center justify-center py-2">
        <div
          ref={orbGlowRef}
          className="absolute w-20 h-20 rounded-full filter blur-[10px] opacity-20 transition-all duration-100 ease-out pointer-events-none"
          style={{
            background: `radial-gradient(circle, ${botColor} 0%, transparent 70%)`,
          }}
        />

        <button
          type="button"
          onClick={handleMicButton}
          title={status === "speaking" ? "Tap to interrupt speech" : isRecordingRef.current ? "Tap to send speech" : "Tap to speak"}
          ref={orbRef}
          className="relative w-16 h-16 rounded-full shadow-lg transition-transform duration-100 ease-out flex items-center justify-center border border-white/20 outline-none cursor-pointer"
          style={{
            background: `radial-gradient(circle at 30% 30%, ${botColor} 0%, #090d16 100%)`,
            boxShadow: `0 0 18px ${botColor}60`,
          }}
        >
          {status === "speaking" ? (
            <Volume2 className="text-white animate-pulse w-6 h-6" />
          ) : status === "processing" ? (
            <Sparkles className="text-white animate-spin w-6 h-6" />
          ) : (
            <Mic className="text-white w-6 h-6" />
          )}
        </button>
      </div>

      {/* Control Actions Form */}
      <form
        onSubmit={handleTextSubmit}
        className="w-full max-w-xl flex items-center gap-2 bg-slate-50 dark:bg-slate-900/60 rounded-full py-1 px-3 border border-slate-200 dark:border-white/10"
      >
        <input
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Speak or type a message here..."
          className="flex-1 bg-transparent border-0 outline-none text-slate-800 dark:text-slate-100 placeholder-slate-400 text-xs px-2"
          disabled={!connected}
        />

        {textInput.trim() && (
          <button
            type="submit"
            className="p-1.5 rounded-full text-white hover:opacity-90 transition-opacity border-0 cursor-pointer"
            style={{ backgroundColor: botColor }}
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Mic Button */}
        <button
          type="button"
          onClick={handleMicButton}
          disabled={!connected}
          title={isMuted ? "Unmute Mic" : isRecordingRef.current ? "Tap to finish speaking" : "Tap to speak"}
          className={`w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer border-0 ${
            isMuted
              ? "bg-slate-300 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
              : status === "listening"
              ? "bg-rose-500 text-white shadow-sm shadow-rose-500/40 animate-pulse"
              : "bg-rose-500 text-white"
          }`}
        >
          {isMuted ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
        </button>
      </form>
    </div>
  );
}
