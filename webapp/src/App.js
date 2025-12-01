import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useState } from "react";
import AuthPanel from "./components/AuthPanel";
import Chatbot from "./components/Chatbot";
import CourseSection from "./components/CourseSection";
import TopicPlanner from "./components/TopicPlanner";
import { API_BASE_URL, createPlan } from "./lib/api";
const App = () => {
    const [user, setUser] = useState(null);
    const [suggestedTopic, setSuggestedTopic] = useState(null);
    const [suggestedDurationValue, setSuggestedDurationValue] = useState(null);
    const [suggestedDurationUnit, setSuggestedDurationUnit] = useState(null);
    const [latestCourse, setLatestCourse] = useState(null);
    const [courseAnnouncement, setCourseAnnouncement] = useState(null);
    const [courseLoading, setCourseLoading] = useState(false);
    const courseUrlFromTopic = (topic) => topic.course_url ? `${API_BASE_URL}${topic.course_url}` : undefined;
    const handleAuthSuccess = (profile) => {
        const normalizedTopics = profile.topics ?? [];
        setUser({ ...profile, topics: normalizedTopics });
        setLatestCourse(normalizedTopics[0] ?? null);
    };
    const handlePlanSaved = (topic) => {
        setUser((prev) => {
            if (!prev)
                return prev;
            const others = prev.topics.filter((entry) => entry.slug !== topic.slug);
            return { ...prev, topics: [topic, ...others] };
        });
        setLatestCourse(topic);
        setCourseAnnouncement({
            id: crypto.randomUUID?.() ?? `${Date.now()}`,
            topic: topic.topic,
            url: courseUrlFromTopic(topic),
        });
    };
    const handleSuggestion = (topic, value, unit) => {
        if (topic)
            setSuggestedTopic(topic);
        if (value)
            setSuggestedDurationValue(value);
        if (unit === "hours" || unit === "days") {
            setSuggestedDurationUnit(unit);
        }
    };
    const handleGenerateCourse = async () => {
        if (!user) {
            throw new Error("Please sign in to generate a course.");
        }
        if (!suggestedTopic || !suggestedDurationValue || !suggestedDurationUnit) {
            throw new Error("Share your topic and time estimate in the chat before requesting a course.");
        }
        setCourseLoading(true);
        try {
            const plan = await createPlan({
                email: user.email,
                topic: suggestedTopic,
                duration_value: suggestedDurationValue,
                duration_unit: suggestedDurationUnit,
            });
            handlePlanSaved(plan);
        }
        finally {
            setCourseLoading(false);
        }
    };
    const heroCopy = useMemo(() => ({
        title: "AI-powered answer engine coach",
        subtitle: "Research the web, write conversational lessons with quizzes, and speak them aloud with ElevenLabs—all from a single dashboard.",
    }), []);
    if (!user) {
        return (_jsx("main", { style: {
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 24,
            }, children: _jsx(AuthPanel, { onAuthSuccess: handleAuthSuccess }) }));
    }
    return (_jsxs("main", { style: { padding: 32, maxWidth: 1200, margin: "0 auto" }, children: [_jsxs("header", { style: { marginBottom: 32 }, children: [_jsxs("div", { className: "pill", children: ["Signed in as ", user.email] }), _jsx("h1", { style: { marginBottom: 8 }, children: heroCopy.title }), _jsx("p", { style: { color: "#475569", maxWidth: 720 }, children: heroCopy.subtitle })] }), _jsxs("div", { style: { display: "grid", gap: 24 }, children: [_jsx(CourseSection, { course: latestCourse }), _jsx(TopicPlanner, { user: user, onPlanSaved: handlePlanSaved, suggestedTopic: suggestedTopic, suggestedDurationValue: suggestedDurationValue, suggestedDurationUnit: suggestedDurationUnit }), _jsx(Chatbot, { email: user.email, onSuggestion: handleSuggestion, suggestion: {
                            topic: suggestedTopic,
                            durationValue: suggestedDurationValue,
                            durationUnit: suggestedDurationUnit,
                        }, onGenerateCourse: handleGenerateCourse, generatingCourse: courseLoading, courseAnnouncement: courseAnnouncement })] })] }));
};
export default App;
