import { createRoot } from "react-dom/client";
import StoriesTestimonials from "@/components/StoriesTestimonials";
import "./index.css";

document.querySelectorAll("[data-stories-root]").forEach((el) => {
  createRoot(el).render(<StoriesTestimonials />);
});
