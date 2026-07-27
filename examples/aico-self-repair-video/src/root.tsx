import React from "react";
import {Composition} from "remotion";
import {AicoSelfRepair, AicoSelfRepairTeaser} from "./video";

export const VideoRoot: React.FC = () => (
  <>
    <Composition
      id="AicoSelfRepair"
      component={AicoSelfRepair}
      durationInFrames={5400}
      fps={30}
      width={1920}
      height={1080}
    />
    <Composition
      id="AicoSelfRepairTeaser"
      component={AicoSelfRepairTeaser}
      durationInFrames={1200}
      fps={30}
      width={1280}
      height={720}
    />
  </>
);
