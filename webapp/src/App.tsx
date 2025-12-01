import { useMemo, useState } from "react";

import AuthPanel from "./components/AuthPanel";
import Chatbot from "./components/Chatbot";
import CourseSection from "./components/CourseSection";
import TopicPlanner from "./components/TopicPlanner";
import { API_BASE_URL, createPlan } from "./lib/api";
import type { TopicPayload, UserProfile } from "./types";

const App = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [suggestedTopic, setSuggestedTopic] = useState<string | null>(null);
  const [suggestedDurationValue, setSuggestedDurationValue] = useState<number | null>(null);
  const [suggestedDurationUnit, setSuggestedDurationUnit] = useState<"hours" | "days" | null>(null);
  const [latestCourse, setLatestCourse] = useState<TopicPayload | null>(null);
  const [courseAnnouncement, setCourseAnnouncement] = useState<
    { id: string; topic: string; url?: string } | null
  >(null);
  const [courseLoading, setCourseLoading] = useState(false);

  const courseUrlFromTopic = (topic: TopicPayload) =>
    topic.course_url ? `${API_BASE_URL}${topic.course_url}` : undefined;

  const handleAuthSuccess = (profile: UserProfile) => {
    const normalizedTopics = profile.topics ?? [];
    setUser({ ...profile, topics: normalizedTopics });
    setLatestCourse(normalizedTopics[0] ?? null);
  };

  const handlePlanSaved = (topic: TopicPayload) => {
    setUser((prev) => {
      if (!prev) return prev;
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

  const handleSuggestion = (topic?: string | null, value?: number | null, unit?: string | null) => {
    if (topic) setSuggestedTopic(topic);
    if (value) setSuggestedDurationValue(value);
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
    } finally {
      setCourseLoading(false);
    }
  };

  const heroCopy = useMemo(
    () => ({
      title: "AI-powered answer engine coach",
      subtitle:
        "Research the web, write conversational lessons with quizzes, and speak them aloud with ElevenLabs—all from a single dashboard.",
    }),
    [],
  );

  if (!user) {
    return (
      <main
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <AuthPanel onAuthSuccess={handleAuthSuccess} />
      </main>
    );
  }

  return (
    <main style={{ padding: 32, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ marginBottom: 32 }}>
        <div className="pill">Signed in as {user.email}</div>
        <h1 style={{ marginBottom: 8 }}>{heroCopy.title}</h1>
        <p style={{ color: "#475569", maxWidth: 720 }}>{heroCopy.subtitle}</p>
      </header>
      <div style={{ display: "grid", gap: 24 }}>
        <CourseSection course={latestCourse} />
        <TopicPlanner
          user={user}
          onPlanSaved={handlePlanSaved}
          suggestedTopic={suggestedTopic}
          suggestedDurationValue={suggestedDurationValue}
          suggestedDurationUnit={suggestedDurationUnit}
        />
        <Chatbot
          email={user.email}
          onSuggestion={handleSuggestion}
          suggestion={{
            topic: suggestedTopic,
            durationValue: suggestedDurationValue,
            durationUnit: suggestedDurationUnit,
          }}
          onGenerateCourse={handleGenerateCourse}
          generatingCourse={courseLoading}
          courseAnnouncement={courseAnnouncement}
        />
      </div>
    </main>
  );
};

export default App;

