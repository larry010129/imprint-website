import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AnimatedSignIn from "@/components/ui/animated-sign-in";
import "./login.css";

document.querySelectorAll<HTMLElement>("[data-login-root]").forEach((el) => {
  createRoot(el).render(
    <StrictMode>
      <AnimatedSignIn />
    </StrictMode>,
  );
});
