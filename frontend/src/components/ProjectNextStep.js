import { HiOutlineArrowRight, HiOutlineCheckCircle, HiOutlineArrowPath } from "react-icons/hi2";
import { projectNextStep } from "../utils/projectNextStep";

export function ProjectNextStep({ video, disabled, canExport, onAction }) {
  const next = projectNextStep(video);
  if (!next) return null;
  const working = ["GENERATION", "RENDERING"].includes(video.status);
  const Icon = working ? HiOutlineArrowPath : HiOutlineCheckCircle;
  return <section aria-live="polite" aria-labelledby="next-step-heading" className="mb-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-blue-200 bg-blue-50/70 p-4 sm:p-5 dark:border-blue-500/25 dark:bg-blue-500/10">
    <div className="flex min-w-0 flex-1 items-start gap-3"><Icon aria-hidden="true" className={`mt-0.5 h-5 w-5 shrink-0 text-blue-600 dark:text-blue-300 ${working ? "motion-safe:animate-spin" : ""}`} /><div><p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-blue-600 dark:text-blue-300">{working ? "In progress" : "Next step"}</p><h2 id="next-step-heading" className="text-sm font-semibold">{next.title}</h2><p className="mt-1 max-w-2xl text-xs leading-relaxed text-gray-600 dark:text-gray-300">{next.description}</p></div></div>
    {next.action && <button type="button" disabled={disabled || (next.action === "export" && !canExport)} onClick={() => onAction(next)} className="studio-primary-button shrink-0 text-xs">{next.label}<HiOutlineArrowRight aria-hidden="true" className="h-4 w-4" /></button>}
  </section>;
}
