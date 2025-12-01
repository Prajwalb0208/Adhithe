export interface Episode {
  episode_number: number;
  title: string;
  duration_minutes: number;
  script: string;
  difficulty: string;
  quiz: string[];
  audio_file?: string | null;
}

export interface TopicPayload {
  topic: string;
  slug: string;
  requested_days: number;
  content_days: number;
  episode_count: number;
  total_minutes: number;
  audio_enabled: boolean;
  episodes: Episode[];
  course_url?: string;
  tts_file?: string;
}

export interface UserProfile {
  name: string;
  email: string;
  topics: TopicPayload[];
}

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
  audio_url?: string | null;
  topic?: string | null;
  duration_value?: number | null;
  duration_unit?: string | null;
  course_url?: string | null;
}

