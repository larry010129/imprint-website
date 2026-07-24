import { createRoot } from "react-dom/client";
import ProfilePage from "@/components/ProfilePage";
import "./index.css";

document.querySelectorAll("[data-profile-root]").forEach((el) => {
  createRoot(el).render(<ProfilePage />);
});
