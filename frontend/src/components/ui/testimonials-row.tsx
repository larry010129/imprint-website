import React from "react";
import { motion } from "motion/react";
import { InitialAvatar, type Testimonial } from "@/components/ui/testimonials-columns-1";

export const TestimonialsRow = (props: {
  className?: string;
  testimonials: Testimonial[];
  duration?: number;
  reverse?: boolean;
}) => {
  return (
    <div className={props.className}>
      <motion.div
        animate={{
          translateX: props.reverse ? "0%" : "-50%",
        }}
        initial={{
          translateX: props.reverse ? "-50%" : "0%",
        }}
        transition={{
          duration: props.duration || 30,
          repeat: Infinity,
          ease: "linear",
          repeatType: "loop",
        }}
        className="flex w-max gap-6 pr-6"
      >
        {[
          ...new Array(2).fill(0).map((_, index) => (
            <React.Fragment key={index}>
              {props.testimonials.map(({ text, image, name, role }, i) => (
                <div
                  className="w-80 shrink-0 rounded-3xl border border-border bg-card p-8 text-card-foreground shadow-lg shadow-primary/10"
                  key={i}
                >
                  <div>{text}</div>
                  <div className="mt-5 flex items-center gap-2">
                    {image ? (
                      <img
                        width={40}
                        height={40}
                        src={image}
                        alt={name}
                        className="h-10 w-10 rounded-full object-cover"
                      />
                    ) : (
                      <InitialAvatar name={name} />
                    )}
                    <div className="flex flex-col">
                      <div className="font-medium tracking-tight leading-5">
                        {name}
                      </div>
                      <div className="leading-5 opacity-60 tracking-tight">
                        {role}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </React.Fragment>
          )),
        ]}
      </motion.div>
    </div>
  );
};
