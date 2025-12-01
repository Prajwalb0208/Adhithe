import type { TopicPayload } from "../types";
import { API_BASE_URL } from "../lib/api";

interface Props {
  course: TopicPayload | null;
}

const CourseSection = ({ course }: Props) => {
  if (!course) {
    return (
      <section className="card">
        <h3 style={{ marginTop: 0 }}>Course</h3>
        <p style={{ color: "#475569" }}>
          Your personalized course will appear here once it is generated through the chatbot or
          planner.
        </p>
      </section>
    );
  }

  const courseUrl = course.course_url ? `${API_BASE_URL}${course.course_url}` : undefined;

  return (
    <section className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0 }}>Course</h3>
        {courseUrl && (
          <a
            className="pill"
            href={courseUrl}
            target="_blank"
            rel="noreferrer"
            title="Opens the generated JSON outline"
          >
            View JSON
          </a>
        )}
      </div>
      <p style={{ color: "#475569" }}>
        <strong>{course.topic}</strong> · {course.content_days} day plan (~
        {Math.round(course.total_minutes)} minutes of listening)
      </p>
      <div style={{ display: "grid", gap: 12 }}>
        {course.episodes.slice(0, 3).map((episode) => (
          <article
            key={episode.episode_number}
            style={{ border: "1px solid #e2e8f0", borderRadius: 12, padding: 12 }}
          >
            <div style={{ fontWeight: 600 }}>
              Day {episode.episode_number}: {episode.title}
            </div>
            <div style={{ fontSize: "0.9rem", color: "#475569" }}>
              {episode.difficulty} · {episode.duration_minutes.toFixed(1)} min
            </div>
            {episode.audio_file && (
              <audio
                style={{ marginTop: 8, width: "100%" }}
                controls
                src={
                  episode.audio_file.startsWith("http")
                    ? episode.audio_file
                    : `${API_BASE_URL}${episode.audio_file}`
                }
              />
            )}
          </article>
        ))}
      </div>
      {!course.audio_enabled && (
        <p style={{ color: "#f97316", fontSize: "0.9rem", marginTop: 16 }}>
          ElevenLabs audio is disabled. Add ELEVENLABS_API_KEY to enable narration.
        </p>
      )}
    </section>
  );
};

export default CourseSection;

