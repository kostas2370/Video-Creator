import { diagramPlan } from "../utils/diagrams";
import { videoFontFamily } from "../utils/fonts";

export function DiagramLayer({ item, time, duration, frameSize }) {
  const [width, height] = frameSize;
  return <div className="absolute inset-0" data-testid="educational-diagram">
    {diagramPlan(item.diagram, frameSize, duration).map((element, index) => {
      const elapsed = time - element.start;
      if (elapsed < 0) return null;
      const progress = Math.min(1, elapsed / element.reveal);
      const style = { position: "absolute", left: `${element.x / width * 100}%`, top: `${element.y / height * 100}%` };
      return element.kind === "rect" ? <div key={index} style={{ ...style, width: `${element.width / width * 100}%`, height: `${element.height / height * 100}%`, background: element.color, transformOrigin: "left", transform: element.grow ? `scaleX(${progress})` : undefined, opacity: item.opacity }} /> : <div key={index} style={{ ...style, color: element.color, fontSize: `${element.size / width * 100}cqw`, fontFamily: videoFontFamily("Poppins"), fontWeight: 700, lineHeight: 1.3, whiteSpace: "pre", opacity: progress * item.opacity }}>{element.text}</div>;
    })}
  </div>;
}
