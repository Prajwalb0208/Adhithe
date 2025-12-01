import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, sendChat } from "../lib/api";
const Chatbot = ({ email, onSuggestion, suggestion, onGenerateCourse, generatingCourse, courseAnnouncement, }) => {
    const [messages, setMessages] = useState([
        {
            role: "assistant",
            content: "Hey! I'm your personal learning coach. Tell me the topic you want to master and how many days or hours you can dedicate. I can listen to your voice or text.",
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState(null);
    const recognitionRef = useRef(null);
    const lastAnnouncementId = useRef(null);
    useEffect(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = "en-US";
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;
            recognitionRef.current.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                setInput((prev) => `${prev} ${transcript}`.trim());
                setIsRecording(false);
            };
            recognitionRef.current.onerror = () => setIsRecording(false);
        }
    }, []);
    useEffect(() => {
        const latest = messages[messages.length - 1];
        if (latest?.role === "assistant" && latest.audio_url) {
            const htmlAudio = new Audio(latest.audio_url);
            htmlAudio.play().catch(() => {
                /* autoplay may be blocked */
            });
        }
    }, [messages]);
    useEffect(() => {
        if (!courseAnnouncement ||
            !courseAnnouncement.id ||
            courseAnnouncement.id === lastAnnouncementId.current) {
            return;
        }
        lastAnnouncementId.current = courseAnnouncement.id;
        setMessages((prev) => [
            ...prev,
            {
                role: "assistant",
                content: `Your course on ${courseAnnouncement.topic} is ready. Open it below.`,
                course_url: courseAnnouncement.url ?? null,
            },
        ]);
    }, [courseAnnouncement]);
    const handleSend = async (event) => {
        event?.preventDefault();
        if (!input.trim() || loading)
            return;
        const pendingHistory = [
            ...messages,
            { role: "user", content: input.trim() },
        ];
        setMessages(pendingHistory);
        setInput("");
        setLoading(true);
        setError(null);
        try {
            const response = await sendChat({
                email,
                message: pendingHistory[pendingHistory.length - 1].content,
                history: pendingHistory,
            });
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: response.reply,
                    audio_url: response.audio_url ?? undefined,
                    topic: response.topic ?? undefined,
                    duration_value: response.duration_value ?? undefined,
                    duration_unit: response.duration_unit ?? undefined,
                },
            ]);
            if (response.topic || response.duration_value) {
                onSuggestion(response.topic, response.duration_value ?? null, response.duration_unit ?? null);
            }
        }
        catch (err) {
            const message = err instanceof Error ? err.message : "Chat server appears offline.";
            setError(message);
        }
        finally {
            setLoading(false);
        }
    };
    const handleCourseClick = async () => {
        if (!suggestion.topic || !suggestion.durationValue || !suggestion.durationUnit) {
            setError("Share your topic and time in the chat before requesting a course.");
            return;
        }
        setError(null);
        try {
            await onGenerateCourse();
        }
        catch (err) {
            const message = err instanceof Error ? err.message : "Unable to generate the course right now.";
            setError(message);
        }
    };
    const buildCourseLink = (value) => {
        if (!value)
            return null;
        return value.startsWith("http") ? value : `${API_BASE_URL}${value}`;
    };
    const toggleRecording = () => {
        if (!recognitionRef.current) {
            setError("Speech recognition is not supported in this browser.");
            return;
        }
        if (isRecording) {
            recognitionRef.current.stop();
            setIsRecording(false);
            return;
        }
        setError(null);
        setIsRecording(true);
        recognitionRef.current.start();
    };
    return (_jsxs("section", { className: "card", children: [_jsx("h3", { style: { marginTop: 0 }, children: "Interactive chatbot" }), _jsx("div", { style: {
                    maxHeight: 320,
                    overflowY: "auto",
                    border: "1px solid #e2e8f0",
                    borderRadius: 16,
                    padding: 16,
                    marginTop: 12,
                    display: "grid",
                    gap: 12,
                }, children: messages.map((message, index) => (_jsxs("div", { style: {
                        justifySelf: message.role === "user" ? "end" : "start",
                        background: message.role === "user" ? "#312e81" : "#f1f5f9",
                        color: message.role === "user" ? "#fff" : "#0f172a",
                        padding: "12px 16px",
                        borderRadius: 14,
                        maxWidth: "80%",
                        whiteSpace: "pre-line",
                    }, children: [message.content, message.topic && (_jsxs("div", { className: "pill", style: { marginTop: 8 }, children: ["topic hint: ", message.topic] })), message.duration_value && (_jsxs("div", { className: "pill", style: { marginTop: 8 }, children: ["time hint: ", message.duration_value, " ", message.duration_unit] })), message.course_url && (_jsx("a", { href: buildCourseLink(message.course_url) ?? "#", target: "_blank", rel: "noreferrer", style: {
                                display: "inline-block",
                                marginTop: 10,
                                color: "#0ea5e9",
                                textDecoration: "none",
                                fontWeight: 600,
                            }, children: "Open course" }))] }, `${message.role}-${index}`))) }), _jsxs("form", { onSubmit: handleSend, style: { marginTop: 16, display: "flex", gap: 12, alignItems: "center" }, children: [_jsxs("div", { className: "input-with-voice", children: [_jsx("input", { type: "text", placeholder: "Ask for a plan, e.g., 'I need to learn GenAI in 2 hours'", value: input, onChange: (e) => setInput(e.target.value) }), _jsx("button", { type: "button", className: `voice-btn ${isRecording ? "active" : ""}`, onClick: toggleRecording, "aria-label": isRecording ? "Stop voice input" : "Start voice input", children: "\uD83C\uDF99" })] }), _jsx("button", { className: "primary", type: "submit", disabled: loading, children: loading ? "..." : "Send" }), _jsx("button", { type: "button", className: "secondary", onClick: handleCourseClick, disabled: generatingCourse, children: generatingCourse ? "Building..." : "Course" })] }), error && (_jsx("p", { style: { color: "#dc2626", fontSize: "0.9rem", marginTop: 8 }, children: error }))] }));
};
export default Chatbot;
