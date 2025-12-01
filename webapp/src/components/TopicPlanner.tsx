import { FormEvent, useEffect, useMemo, useState } from "react";

import { API_BASE_URL, createPlan } from "../lib/api";
import type { TopicPayload, UserProfile } from "../types";

interface Props {
  user: UserProfile;
  onPlanSaved: (topic: TopicPayload) => void;
  suggestedTopic?: string | null;
  suggestedDurationValue?: number | null;
  suggestedDurationUnit?: "hours" | "days" | null;
}

const TopicPlanner = ({
  user,
  onPlanSaved,
  suggestedTopic,
  suggestedDurationValue,
  suggestedDurationUnit,
}: Props) => {
  const [topic, setTopic] = useState("");
  const [durationValue, setDurationValue] = useState(5);
  const [durationUnit, setDurationUnit] = useState<"days" | "hours">("days");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const handleSubmit = async (event: FormEvent) => {
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
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to run the pipeline.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card" style={{ marginBottom: 24 }}>
      <h3 style={{ marginTop: 0 }}>Generate a fresh learning sprint</h3>
      <p style={{ color: "#475569", marginTop: 4 }}>
        This will run the Anthropic → Fetch → OpenAI → ElevenLabs pipeline and save
        the episodes + audio back to Redis.
      </p>
      <form
        onSubmit={handleSubmit}
        style={{ display: "grid", gap: 16, marginTop: 16 }}
      >
        <textarea
          rows={2}
          placeholder="Topic name (e.g., Answer Engine Optimization)"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
        />
        <div style={{ display: "flex", gap: 12 }}>
          <input
            type="number"
            min={1}
            style={{ flex: 1 }}
            value={durationValue}
            onChange={(e) => setDurationValue(Number(e.target.value))}
          />
          <select
            value={durationUnit}
            onChange={(e) => setDurationUnit(e.target.value as "hours" | "days")}
          >
            <option value="days">days</option>
            <option value="hours">hours</option>
          </select>
        </div>
        {error && (
          <p style={{ color: "#dc2626", margin: 0, fontSize: "0.9rem" }}>{error}</p>
        )}
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Building plan..." : "Generate plan"}
        </button>
      </form>
      {user.topics.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h4 style={{ marginBottom: 12 }}>Stored topics ({user.topics.length})</h4>
          <div style={{ display: "grid", gap: 12 }}>
            {user.topics.map((entry) => (
              <article
                key={entry.slug}
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 12,
                  padding: 16,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{entry.topic}</strong>
                  <span className="pill">
                    {entry.episode_count} episodes • {entry.content_days} days
                  </span>
                </div>
                <p style={{ color: "#475569", marginBottom: 8 }}>
                  Total listening: ~{Math.round(entry.total_minutes)} minutes
                </p>
                <div style={{ display: "grid", gap: 6 }}>
                  {entry.episodes.slice(0, 3).map((episode) => (
                    <div
                      key={episode.episode_number}
                      style={{
                        padding: "8px 0",
                        borderTop: "1px dashed #e2e8f0",
                      }}
                    >
                      <div style={{ fontWeight: 600 }}>
                        Day {episode.episode_number}: {episode.title}
                      </div>
                      <div style={{ fontSize: "0.9rem", color: "#475569" }}>
                        {episode.difficulty} • {episode.duration_minutes.toFixed(1)} min
                      </div>
                      {episode.audio_file && (
                        <audio
                          style={{ marginTop: 6, width: "100%" }}
                          controls
                          src={
                            episode.audio_file.startsWith("http")
                              ? episode.audio_file
                              : `${API_BASE_URL}${episode.audio_file}`
                          }
                        />
                      )}
                    </div>
                  ))}
                </div>
                {entry.course_url && (
                  <a
                    href={`${API_BASE_URL}${entry.course_url}`}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "inline-block",
                      marginTop: 12,
                      fontWeight: 600,
                      color: "#0ea5e9",
                      textDecoration: "none",
                    }}
                  >
                    Open course JSON
                  </a>
                )}
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};

export default TopicPlanner;

