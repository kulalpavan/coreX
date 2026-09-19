import React from "react";
import { ArrowUpRight, Check, LockKeyhole } from "lucide-react";

export function Sidebar({ screen, setScreen, hasResults }) {
  const steps = [
    { key: "upload", number: "01", label: "Upload report" },
    { key: "review", number: "02", label: "Review values", disabled: !hasResults },
    { key: "explanation", number: "03", label: "Read summary", disabled: screen !== "explanation" && screen !== "trends" },
    { key: "trends", number: "04", label: "Historical trends", disabled: screen !== "explanation" && screen !== "trends" },
  ];

  function isStepDone(stepKey) {
    if (stepKey === "upload") return screen !== "upload";
    if (stepKey === "review") return screen === "explanation" || screen === "trends";
    return false;
  }

  return (
    <aside className="sidebar">
      <p className="eyebrow">Your report, made legible</p>
      <h1>
        Read the numbers.
        <br />
        <em>Keep the context.</em>
      </h1>
      <p className="sidebar-copy">
        A calm, review-first way to understand the information in a lab report. Nothing is finalized until you check it.
      </p>

      <nav className="step-list" aria-label="Workflow Steps">
        {steps.map((s) => {
          const isActive = screen === s.key;
          const done = isStepDone(s.key);
          return (
            <div
              key={s.key}
              className={`step ${isActive ? "active" : ""} ${s.disabled ? "disabled" : ""}`}
              onClick={() => !s.disabled && setScreen(s.key)}
              role="button"
              tabIndex={s.disabled ? -1 : 0}
            >
              <span className={`step-number ${done ? "done" : ""}`}>
                {done ? <Check size={14} /> : s.number}
              </span>
              <span>{s.label}</span>
              {isActive && <ArrowUpRight size={15} />}
            </div>
          );
        })}
      </nav>

      <div className="privacy-note">
        <LockKeyhole size={15} />
        <span>Your report stays in this local prototype. No data is stored externally.</span>
      </div>
    </aside>
  );
}
