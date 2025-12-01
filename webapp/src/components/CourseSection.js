import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { API_BASE_URL } from "../lib/api";
const CourseSection = ({ course }) => {
    if (!course) {
        return (_jsxs("section", { className: "card", children: [_jsx("h3", { style: { marginTop: 0 }, children: "Course" }), _jsx("p", { style: { color: "#475569" }, children: "Your personalized course will appear here once it is generated through the chatbot or planner." })] }));
    }
    const courseUrl = course.course_url ? `${API_BASE_URL}${course.course_url}` : undefined;
    return (_jsxs("section", { className: "card", children: [_jsxs("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" }, children: [_jsx("h3", { style: { margin: 0 }, children: "Course" }), courseUrl && (_jsx("a", { className: "pill", href: courseUrl, target: "_blank", rel: "noreferrer", title: "Opens the generated JSON outline", children: "View JSON" }))] }), _jsxs("p", { style: { color: "#475569" }, children: [_jsx("strong", { children: course.topic }), " \u00B7 ", course.content_days, " day plan (~", Math.round(course.total_minutes), " minutes of listening)"] }), _jsx("div", { style: { display: "grid", gap: 12 }, children: course.episodes.slice(0, 3).map((episode) => (_jsxs("article", { style: { border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }, children: [_jsxs("div", { style: { fontWeight: 600 }, children: ["Day ", episode.episode_number, ": ", episode.title] }), _jsxs("div", { style: { fontSize: "0.9rem", color: "#475569" }, children: [episode.difficulty, " \u00B7 ", episode.duration_minutes.toFixed(1), " min"] }), episode.audio_file && (_jsx("audio", { style: { marginTop: 8, width: "100%" }, controls: true, src: episode.audio_file.startsWith("http")
                                ? episode.audio_file
                                : `${API_BASE_URL}${episode.audio_file}` }))] }, episode.episode_number))) }), !course.audio_enabled && (_jsx("p", { style: { color: "#f97316", fontSize: "0.9rem", marginTop: 16 }, children: "ElevenLabs audio is disabled. Add ELEVENLABS_API_KEY to enable narration." }))] }));
};
export default CourseSection;
