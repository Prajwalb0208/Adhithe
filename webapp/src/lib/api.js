import axios from "axios";
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const api = axios.create({
    baseURL: API_BASE_URL,
});
export const signup = async (payload) => {
    const { data } = await api.post("/auth/signup", payload);
    return data;
};
export const login = async (payload) => {
    const { data } = await api.post("/auth/login", payload);
    return data;
};
export const createPlan = async (payload) => {
    const { data } = await api.post("/planning/episodes", payload);
    return data;
};
export const fetchTopics = async (email) => {
    const { data } = await api.get(`/users/${email}/topics`);
    return data;
};
export const sendChat = async (payload) => {
    const { data } = await api.post("/chat", payload);
    return data;
};
