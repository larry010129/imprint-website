import { createRoot } from "react-dom/client";
import React from "react";
import StoriesTestimonials from "@/components/StoriesTestimonials";
import TestimonialsWall from "@/components/TestimonialsWall";
import "./index.css";

class StoriesErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="mx-auto max-w-lg px-4 py-16 text-center text-[#2a2438]">
          <p className="text-sm text-[#8a817b]">見證內容暫時無法載入，請重新整理頁面。</p>
        </div>
      );
    }
    return this.props.children;
  }
}

function mount() {
  document.querySelectorAll("[data-stories-root]").forEach((el) => {
    createRoot(el).render(
      <StoriesErrorBoundary>
        <StoriesTestimonials />
      </StoriesErrorBoundary>,
    );
  });

  document.querySelectorAll("[data-home-wall]").forEach((el) => {
    createRoot(el).render(<TestimonialsWall />);
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mount);
} else {
  mount();
}
