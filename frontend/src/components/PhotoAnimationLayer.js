import { animationProgress } from "../utils/photoAnimation";

export function PhotoAnimationLayer({ plan, time, duration, fps = 24 }) {
  if (!plan?.particles?.length) return null;
  const progress = animationProgress(time, duration, fps);
  return <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden" style={{ containerType: "inline-size" }}>
    {plan.particles.map((particle, index) => <div key={index} style={{
      position: "absolute", left: `${(particle.x + (particle.to_x - particle.x) * progress) * 100}%`,
      top: `${(particle.y + (particle.to_y - particle.y) * progress) * 100}%`,
      width: `${particle.size * 100}cqw`, height: `${particle.size * 100}cqw`,
      background: particle.color, opacity: particle.opacity,
    }} />)}
  </div>;
}
