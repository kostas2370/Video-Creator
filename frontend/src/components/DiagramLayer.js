import { diagramElementState, diagramPlan } from "../utils/diagrams";
import { useIconFiles } from "../hooks/useIconFiles";
import { videoFontFamily } from "../utils/fonts";

export function DiagramLayer({ item, time, duration, frameSize }) {
  const [width, height] = frameSize;
  const icons = useIconFiles(item.diagram.items.map(stage => stage.icon));
  return <div className="absolute inset-0" data-testid="educational-diagram">
    {diagramPlan(item.diagram, frameSize, duration).map((element, index) => {
      const { x, y, visible, progress } = diagramElementState(element, time);
      if (!visible) return null;
      const style = { position: "absolute", left: `${x / width * 100}%`, top: `${y / height * 100}%` };
      if (element.kind === "icon") {
        const icon = icons[element.icon];
        return icon ? <img key={index} src={icon.file} alt="" style={{ ...style, width: `${element.width / width * 100}%`, height: `${element.height / height * 100}%`, opacity: item.opacity }} /> : null;
      }
      const clipPath = element.kind === "polygon" ? `polygon(${element.points.map(([px, py]) => `${px / element.width * 100}% ${py / element.height * 100}%`).join(",")})` : element.kind === "arrow" ? "polygon(0 0, 100% 0, 50% 100%)" : undefined;
      return element.kind !== "text" ? <div key={index} style={{ ...style, width: `${element.width / width * 100}%`, height: `${element.height / height * 100}%`, background: element.color, clipPath, transformOrigin: "left", transform: element.grow ? `scaleX(${progress})` : undefined, opacity: item.opacity }} /> : <div key={index} style={{ ...style, width: element.centered ? `${element.centered / width * 100}%` : undefined, textAlign: element.centered ? "center" : undefined, color: element.color, fontSize: `${element.size / width * 100}cqw`, fontFamily: videoFontFamily("Poppins"), fontWeight: 700, lineHeight: 1.3, whiteSpace: "pre", opacity: progress * item.opacity }}>{element.text}</div>;
    })}
  </div>;
}
