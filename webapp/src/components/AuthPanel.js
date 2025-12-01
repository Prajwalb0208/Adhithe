import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { login, signup } from "../lib/api";
const AuthPanel = ({ onAuthSuccess }) => {
    const [mode, setMode] = useState("signup");
    const [formState, setFormState] = useState({
        name: "",
        email: "",
        password: "",
        confirm_password: "",
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const handleChange = (field, value) => {
        setFormState((prev) => ({ ...prev, [field]: value }));
    };
    const handleSubmit = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError(null);
        try {
            const signupPayload = { ...formState };
            const loginPayload = { email: formState.email, password: formState.password };
            const user = mode === "signup" ? await signup(signupPayload) : await login(loginPayload);
            onAuthSuccess(user);
        }
        catch (err) {
            const message = err instanceof Error ? err.message : "Unable to complete request.";
            setError(message);
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsxs("div", { className: "card", style: { maxWidth: 420, width: "100%" }, children: [_jsx("h2", { style: { marginTop: 0 }, children: mode === "signup" ? "Create your study locker" : "Jump back in" }), _jsx("p", { style: { marginTop: 4, color: "#475569" }, children: "Store your topics, quizzes, and audio plans securely via Redis." }), _jsxs("form", { onSubmit: handleSubmit, style: { display: "grid", gap: 16 }, children: [mode === "signup" && (_jsx("input", { type: "text", placeholder: "Full name", value: formState.name, onChange: (e) => handleChange("name", e.target.value), required: true })), _jsx("input", { type: "email", placeholder: "Email address", value: formState.email, onChange: (e) => handleChange("email", e.target.value), required: true }), _jsx("input", { type: "password", placeholder: "Password", value: formState.password, onChange: (e) => handleChange("password", e.target.value), required: true }), mode === "signup" && (_jsx("input", { type: "password", placeholder: "Confirm password", value: formState.confirm_password, onChange: (e) => handleChange("confirm_password", e.target.value), required: true })), error && (_jsx("div", { style: { color: "#dc2626", fontSize: "0.9rem" }, children: error })), _jsx("button", { className: "primary", type: "submit", disabled: loading, children: loading ? "Working..." : mode === "signup" ? "Create account" : "Login" })] }), _jsxs("p", { style: { marginTop: 16, fontSize: "0.9rem" }, children: [mode === "signup" ? "Already registered? " : "Need an account? ", _jsx("button", { type: "button", className: "secondary", onClick: () => setMode(mode === "signup" ? "login" : "signup"), style: { padding: "0.35rem 0.75rem", marginLeft: 8 }, children: mode === "signup" ? "Log in" : "Sign up" })] })] }));
};
export default AuthPanel;
