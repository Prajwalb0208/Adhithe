import axios from "axios";

import type { ChatMessage, TopicPayload, UserProfile } from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
});

export interface SignupPayload {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface PlanPayload {
  email: string;
  topic: string;
  duration_value: number;
  duration_unit: "hours" | "days";
}

export interface ChatPayload {
  email: string;
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  reply: string;
  audio_url?: string | null;
  topic?: string | null;
  duration_value?: number | null;
  duration_unit?: string | null;
}

export const signup = async (payload: SignupPayload): Promise<UserProfile> => {
  const { data } = await api.post<UserProfile>("/auth/signup", payload);
  return data;
};

export const login = async (payload: LoginPayload): Promise<UserProfile> => {
  const { data } = await api.post<UserProfile>("/auth/login", payload);
  return data;
};

export const createPlan = async (payload: PlanPayload): Promise<TopicPayload> => {
  const { data } = await api.post<TopicPayload>("/planning/episodes", payload);
  return data;
};

export const fetchTopics = async (email: string): Promise<TopicPayload[]> => {
  const { data } = await api.get<TopicPayload[]>(`/users/${email}/topics`);
  return data;
};

export const sendChat = async (payload: ChatPayload): Promise<ChatResponse> => {
  const { data } = await api.post<ChatResponse>("/chat", payload);
  return data;
};

