import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import { API_BASE_URL, createPlan } from "../lib/api";
const TopicPlanner = ({ user, onPlanSaved, suggestedTopic, suggestedDurationValue, suggestedDurationUnit, }) => {
    const [topic, setTopic] = useState("");
    const [durationValue, setDurationValue] = useState(5);
    const [durationUnit, setDurationUnit] = useState("days");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (suggestedTopic) {
            setTopic(suggestedTopic);
        }
    }, [suggestedTopic]);
    useEffect(() => {
        if (suggestedDurationValue) {
            setDurationValue(Math.max(1, Math.round(suggestedDurationValue)));
        }
        if (suggestedDurationUnit) {
            setDurationUnit(suggestedDurationUnit);
        }
    }, [suggestedDurationValue, suggestedDurationUnit]);
    const latestTopic = useMemo(() => user.topics[0], [user.topics]);
    const handleSubmit = async (event) => {
        event.preventDefault();
        setError(null);
        setLoading(true);
        try {
            const payload = {
                email: user.email,
                topic: topic || latestTopic?.topic || "",
                duration_value: durationValue,
                duration_unit: durationUnit,
            };
            if (!payload.topic) {
                setError("Please enter a topic or capture one via the chatbot.");
                setLoading(false);
                return;
            }
            const created = await createPlan(payload);
            onPlanSaved(created);
            setTopic("");
        }
        catch (err) {
            const message = err instanceof Error ? err.message : "Unable to run the pipeline.";
            setError(message);
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("section", { className: "card", style: { marginBottom: 24 }, children: [_jsx("h3", { style: { marginTop: 0 }, children: "Generate a fresh learning sprint" }), _jsx("p", { style: { color: "#475569", marginTop: 4 }, children: "This will run the Anthropic \u2192 Fetch \u2192 OpenAI \u2192 ElevenLabs pipeline and save the episodes + audio back to Redis." }), _jsxs("form", { onSubmit: handleSubmit, style: { display: "grid", gap: 16, marginTop: 16 }, children: [_jsx("textarea", { rows: 2, placeholder: "Topic name (e.g., Answer Engine Optimization)", value: topic, onChange: (e) => setTopic(e.target.value) }), _jsxs("div", { style: { display: "flex", gap: 12 }, children: [_jsx("input", { type: "number", min: 1, style: { flex: 1 }, value: durationValue, onChange: (e) => setDurationValue(Number(e.target.value)) }), _jsxs("select", { value: durationUnit, onChange: (e) => setDurationUnit(e.target.value), children: [_jsx("option", { value: "days", children: "days" }), _jsx("option", { value: "hours", children: "hours" })] })] }), error && (_jsx("p", { style: { color: "#dc2626", margin: 0, fontSize: "0.9rem" }, children: error })), _jsx("button", { className: "primary", type: "submit", disabled: loading, children: loading ? "Building plan..." : "Generate plan" })] }), user.topics.length > 0 && (_jsxs("div", { style: { marginTop: 24 }, children: [_jsxs("h4", { style: { marginBottom: 12 }, children: ["Stored topics (", user.topics.length, ")"] }), _jsx("div", { style: { display: "grid", gap: 12 }, children: user.topics.map((entry) => (_jsxs("article", { style: {
                                border: "1px solid #e2e8f0",
                                borderRadius: 12,
                                padding: 16,
                            }, children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between" }, children: [_jsx("strong", { children: entry.topic }), _jsxs("span", { className: "pill", children: [entry.episode_count, " episodes \u2022 ", entry.content_days, " days"] })] }), _jsxs("p", { style: { color: "#475569", marginBottom: 8 }, children: ["Total listening: ~", Math.round(entry.total_minutes), " minutes"] }), _jsx("div", { style: { display: "grid", gap: 6 }, children: entry.episodes.slice(0, 3).map((episode) => (_jsxs("div", { style: {
                                            padding: "8px 0",
                                            borderTop: "1px dashed #e2e8f0",
                                        }, children: [_jsxs("div", { style: { fontWeight: 600 }, children: ["Day ", episode.episode_number, ": ", episode.title] }), _jsxs("div", { style: { fontSize: "0.9rem", color: "#475569" }, children: [episode.difficulty, " \u2022 ", episode.duration_minutes.toFixed(1), " min"] }), episode.audio_file && (_jsx("audio", { style: { marginTop: 6, width: "100%" }, controls: true, src: episode.audio_file.startsWith("http")
                                                    ? episode.audio_file
                                                    : `${API_BASE_URL}${episode.audio_file}` }))] }, episode.episode_number))) }), entry.course_url && (_jsx("a", { href: `${API_BASE_URL}${entry.course_url}`, target: "_blank", rel: "noreferrer", style: {
                                        display: "inline-block",
                                        marginTop: 12,
                                        fontWeight: 600,
                                        color: "#0ea5e9",
                                        textDecoration: "none",
                                    }, children: "Open course JSON" }))] }, entry.slug))) })] }))] }));
};
export default TopicPlanner;
