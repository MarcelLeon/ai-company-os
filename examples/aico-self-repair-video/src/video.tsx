import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const COLORS = {
  bg: "#07111f",
  panel: "#0d1b2d",
  panel2: "#12243a",
  text: "#eef6ff",
  muted: "#95aac4",
  blue: "#4f8cff",
  purple: "#a78bfa",
  orange: "#f59e0b",
  green: "#2dd4a3",
  teal: "#22d3ee",
  red: "#fb7185",
};

type SceneProps = {
  title: string;
  eyebrow: string;
  children: React.ReactNode;
  duration: number;
};

const fade = (frame: number, duration: number) =>
  interpolate(frame, [0, 16, duration - 18, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

const Scene: React.FC<SceneProps> = ({title, eyebrow, children, duration}) => {
  const frame = useCurrentFrame();
  const opacity = fade(frame, duration);
  const y = interpolate(frame, [0, 24], [24, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <AbsoluteFill
      style={{
        background:
          "radial-gradient(circle at 15% 10%, #172b4d 0%, #07111f 43%, #050b14 100%)",
        color: COLORS.text,
        fontFamily:
          '"SF Pro Display", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif',
        padding: "72px 92px",
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <div style={{fontSize: 24, color: COLORS.teal, letterSpacing: 2, fontWeight: 700}}>
        {eyebrow}
      </div>
      <div style={{fontSize: 64, fontWeight: 760, marginTop: 14, maxWidth: 1500}}>
        {title}
      </div>
      <div style={{flex: 1, display: "flex", alignItems: "center"}}>{children}</div>
      <div
        style={{
          position: "absolute",
          right: 92,
          bottom: 48,
          color: COLORS.muted,
          fontSize: 20,
        }}
      >
        AICO · personal human-on-the-loop control plane
      </div>
    </AbsoluteFill>
  );
};

const Card: React.FC<{
  children: React.ReactNode;
  accent?: string;
  width?: number | string;
}> = ({children, accent = COLORS.blue, width = "100%"}) => (
  <div
    style={{
      width,
      background: "linear-gradient(145deg, rgba(18,36,58,.98), rgba(9,24,41,.98))",
      border: `2px solid ${accent}66`,
      borderLeft: `8px solid ${accent}`,
      borderRadius: 24,
      padding: "30px 34px",
      boxShadow: "0 24px 80px rgba(0,0,0,.34)",
    }}
  >
    {children}
  </div>
);

const Pill: React.FC<{children: React.ReactNode; color: string}> = ({children, color}) => (
  <span
    style={{
      display: "inline-block",
      padding: "8px 15px",
      borderRadius: 999,
      background: `${color}24`,
      border: `1px solid ${color}88`,
      color,
      fontWeight: 700,
      fontSize: 22,
    }}
  >
    {children}
  </span>
);

const ChatLine: React.FC<{
  side?: "owner" | "aico";
  children: React.ReactNode;
  color?: string;
}> = ({side = "aico", children, color}) => (
  <div
    style={{
      alignSelf: side === "owner" ? "flex-end" : "flex-start",
      maxWidth: "84%",
      background: side === "owner" ? "#2563eb" : COLORS.panel2,
      border: `1px solid ${color ?? (side === "owner" ? COLORS.blue : "#36506e")}`,
      borderRadius: side === "owner" ? "22px 22px 5px 22px" : "22px 22px 22px 5px",
      padding: "18px 22px",
      fontSize: 27,
      lineHeight: 1.45,
    }}
  >
    {children}
  </div>
);

const Phone: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div
    style={{
      width: 600,
      height: 650,
      border: "11px solid #20344d",
      borderRadius: 48,
      background: "#081525",
      padding: "42px 26px 26px",
      boxShadow: "0 30px 100px rgba(0,0,0,.48)",
      position: "relative",
      display: "flex",
      flexDirection: "column",
      gap: 17,
    }}
  >
    <div
      style={{
        position: "absolute",
        top: 14,
        left: "37%",
        width: "26%",
        height: 10,
        borderRadius: 8,
        background: "#334b67",
      }}
    />
    {children}
  </div>
);

const FlowNode: React.FC<{label: string; color: string; sub: string}> = ({label, color, sub}) => (
  <div
    style={{
      width: 245,
      minHeight: 150,
      borderRadius: 22,
      border: `2px solid ${color}`,
      background: `${color}18`,
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      textAlign: "center",
      padding: 18,
    }}
  >
    <div style={{fontSize: 31, fontWeight: 760}}>{label}</div>
    <div style={{fontSize: 20, color: COLORS.muted, marginTop: 10}}>{sub}</div>
  </div>
);

const Arrow: React.FC = () => (
  <div style={{fontSize: 48, color: COLORS.muted, padding: "0 8px"}}>→</div>
);

const TitleScene: React.FC = () => (
  <Scene eyebrow="真实 DOGFOOD · 2026-07-27" title="AICO 自己修了一个真实小问题" duration={460}>
    <div style={{display: "flex", alignItems: "center", width: "100%", gap: 68}}>
      <div style={{flex: 1}}>
        <div style={{fontSize: 38, lineHeight: 1.55, color: COLORS.muted}}>
          人离开电脑后，从 Telegram 交任务；
          <br />
          Agent 在已知边界内推进，风险和例外再找你。
        </div>
        <div style={{display: "flex", gap: 16, marginTop: 34}}>
          <Pill color={COLORS.purple}>个人开发者</Pill>
          <Pill color={COLORS.green}>本机 Agent</Pill>
          <Pill color={COLORS.orange}>单次审批</Pill>
        </div>
      </div>
      <Phone>
        <ChatLine side="owner">/ask implementer 修复中文 README 的旧快速上手入口</ChatLine>
        <ChatLine color={COLORS.orange}>Approval required · shell_exec</ChatLine>
        <ChatLine side="owner">/approve 62a84f46</ChatLine>
      </Phone>
    </div>
  </Scene>
);

const BoundaryScene: React.FC = () => (
  <Scene eyebrow="01 · 授权包络" title="Prompt 让 Agent 少请示，门禁决定它能不能做" duration={602}>
    <div style={{display: "flex", alignItems: "center", width: "100%", justifyContent: "center"}}>
      <FlowNode label="Owner" color={COLORS.purple} sub="Telegram / Feishu" />
      <Arrow />
      <FlowNode label="项目办公室" color={COLORS.blue} sub="Project / Role / Context" />
      <Arrow />
      <FlowNode label="风险与授权" color={COLORS.orange} sub="read-only / approve / grant" />
      <Arrow />
      <FlowNode label="本机 Agent" color={COLORS.green} sub="Claude Code / Codex" />
      <Arrow />
      <FlowNode label="证据与接手" color={COLORS.teal} sub="Task / Audit / Morning" />
    </div>
  </Scene>
);

const ApprovalScene: React.FC = () => (
  <Scene eyebrow="02 · 真实任务" title="修改文件和运行检查，被 AICO 拦在审批前" duration={788}>
    <div style={{display: "flex", gap: 54, width: "100%", alignItems: "center"}}>
      <Phone>
        <ChatLine side="owner">
          /ask implementer
          <br />
          只修快速上手，不 commit、不 push
        </ChatLine>
        <ChatLine color={COLORS.orange}>
          <b>Approval required: 62a84f46</b>
          <br />
          shell_exec · file/code change
        </ChatLine>
        <ChatLine side="owner">/approve 62a84f46</ChatLine>
      </Phone>
      <div style={{flex: 1, display: "flex", flexDirection: "column", gap: 24}}>
        <Card accent={COLORS.orange}>
          <div style={{fontSize: 31, fontWeight: 760}}>审批的是具体任务</div>
          <div style={{fontSize: 25, color: COLORS.muted, marginTop: 12, lineHeight: 1.5}}>
            明确文件、目标和禁止项；不是“Agent 可以自己审批”，也不是永久授权。
          </div>
        </Card>
        <Card accent={COLORS.green}>
          <div style={{fontSize: 31, fontWeight: 760}}>批准后才派发到本机 CLI</div>
          <div style={{fontSize: 25, color: COLORS.muted, marginTop: 12}}>
            approval_approved → adapter_dispatched
          </div>
        </Card>
      </div>
    </div>
  </Scene>
);

const HonestFailureScene: React.FC = () => (
  <Scene eyebrow="03 · 不粉饰失败" title="第一次执行失败，失败也进入任务状态" duration={876}>
    <div style={{display: "flex", width: "100%", gap: 46, alignItems: "stretch"}}>
      <Card accent={COLORS.red} width="48%">
        <Pill color={COLORS.red}>ca692ce1 · failed</Pill>
        <div style={{fontSize: 38, fontWeight: 760, marginTop: 28}}>Not logged in</div>
        <div style={{fontSize: 25, color: COLORS.muted, marginTop: 18, lineHeight: 1.55}}>
          当前 LaunchAgent 环境里的 Claude Code 无法读取登录状态。AICO 没有把 Provider 失败写成
          “已完成”。
        </div>
      </Card>
      <Card accent={COLORS.teal} width="48%">
        <Pill color={COLORS.teal}>最小诊断</Pill>
        <div style={{fontSize: 38, fontWeight: 760, marginTop: 28}}>同一 CLI，正常用户环境探针成功</div>
        <div style={{fontSize: 25, color: COLORS.muted, marginTop: 18, lineHeight: 1.55}}>
          结论收窄为运行环境差异；切换到已验证的前台 Runtime，再提交同一范围任务。
          首用清单因此新增 Provider 登录探针。
        </div>
      </Card>
    </div>
  </Scene>
);

const DiffScene: React.FC = () => (
  <Scene eyebrow="04 · 真实修改" title="批准后，公开入口从旧命令收口到统一 CLI" duration={666}>
    <div style={{display: "flex", width: "100%", gap: 44, alignItems: "center"}}>
      <div style={{flex: 1}}>
        <Card accent={COLORS.red}>
          <div style={{fontFamily: "ui-monospace, SFMono-Regular", fontSize: 27, lineHeight: 1.7}}>
            <span style={{color: COLORS.red}}>- aico-release-room-demo</span>
            <br />
            <span style={{color: COLORS.red}}>- export AICO_* ...</span>
            <br />
            <span style={{color: COLORS.red}}>- aico-phase1</span>
          </div>
        </Card>
        <div style={{height: 24}} />
        <Card accent={COLORS.green}>
          <div style={{fontFamily: "ui-monospace, SFMono-Regular", fontSize: 27, lineHeight: 1.7}}>
            <span style={{color: COLORS.green}}>+ aico demo</span>
            <br />
            <span style={{color: COLORS.green}}>+ aico init → doctor → run</span>
            <br />
            <span style={{color: COLORS.green}}>+ aico service install</span>
          </div>
        </Card>
      </div>
      <div style={{width: 520, display: "flex", flexDirection: "column", gap: 20}}>
        <Pill color={COLORS.green}>62a84f46 · done</Pill>
        <div style={{fontSize: 34, lineHeight: 1.48}}>
          只改公开文档；
          <br />
          不碰 owner 的本地配置；
          <br />
          不 commit、不 push、不发布。
        </div>
      </div>
    </div>
  </Scene>
);

const ReviewScene: React.FC = () => (
  <Scene eyebrow="05 · 多 Agent 协作" title="Implementer 主动找只读 Reviewer，不需要 Owner 重新调度" duration={845}>
    <div style={{display: "flex", alignItems: "center", justifyContent: "center", width: "100%"}}>
      <FlowNode label="Implementer" color={COLORS.green} sub="Claude Code · shell_exec · done" />
      <Arrow />
      <FlowNode label="Reviewer" color={COLORS.blue} sub="Codex · read_only · done" />
      <Arrow />
      <Card accent={COLORS.orange} width={560}>
        <div style={{fontSize: 30, fontWeight: 760}}>复核发现一个剩余文档漂移</div>
        <div style={{fontSize: 24, color: COLORS.muted, lineHeight: 1.5, marginTop: 12}}>
          Reviewer 没有修改文件，只指出 Quickstart 中仍有面向用户的旧入口，并给出后续修正范围。
        </div>
      </Card>
    </div>
  </Scene>
);

const HandoffScene: React.FC = () => (
  <Scene eyebrow="06 · 老板接手" title="回来先看 Morning，再按短 ID 深挖" duration={743}>
    <div style={{display: "flex", width: "100%", gap: 44, alignItems: "stretch"}}>
      <Card accent={COLORS.teal} width="56%">
        <div style={{fontSize: 31, fontWeight: 760}}>Morning handoff: aico</div>
        <div style={{fontSize: 25, lineHeight: 1.65, marginTop: 20}}>
          <span style={{color: COLORS.green}}>Done</span> · 62a84f46 implementer
          <br />
          <span style={{color: COLORS.green}}>Done</span> · 2a3553ee reviewer
          <br />
          <span style={{color: COLORS.orange}}>Risks</span> · shell_exec approved once
          <br />
          <span style={{color: COLORS.muted}}>Recent</span> · dispatched → reviewed → completed
        </div>
      </Card>
      <Card accent={COLORS.purple} width="40%">
        <div style={{fontSize: 31, fontWeight: 760}}>Audit trace</div>
        <div style={{fontSize: 24, color: COLORS.muted, lineHeight: 1.7, marginTop: 18}}>
          approval_approved
          <br />
          adapter_dispatched
          <br />
          collaboration_requested
          <br />
          task_completed × 2
        </div>
      </Card>
    </div>
  </Scene>
);

const EndScene: React.FC = () => (
  <Scene eyebrow="结果" title="AICO 不是替你审批，而是把你留在正确的环上" duration={420}>
    <div style={{display: "flex", flexDirection: "column", gap: 22}}>
      <div style={{fontSize: 36, color: COLORS.muted}}>
        Mac + Claude Code / Codex + 离开电脑后的真实接手需求
      </div>
      <div style={{display: "flex", gap: 16}}>
        <Pill color={COLORS.green}>边界内继续</Pill>
        <Pill color={COLORS.orange}>风险与意外找人</Pill>
        <Pill color={COLORS.teal}>结果可接手</Pill>
      </div>
    </div>
  </Scene>
);

const scenes = [
  {from: 0, duration: 460, component: <TitleScene />},
  {from: 460, duration: 602, component: <BoundaryScene />},
  {from: 1062, duration: 788, component: <ApprovalScene />},
  {from: 1850, duration: 876, component: <HonestFailureScene />},
  {from: 2726, duration: 666, component: <DiffScene />},
  {from: 3392, duration: 845, component: <ReviewScene />},
  {from: 4237, duration: 743, component: <HandoffScene />},
  {from: 4980, duration: 420, component: <EndScene />},
];

export const AicoSelfRepair: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: COLORS.bg}}>
    <Audio src={staticFile("audio/narration.mp3")} volume={0.95} />
    {scenes.map((scene) => (
      <Sequence key={scene.from} from={scene.from} durationInFrames={scene.duration}>
        {scene.component}
      </Sequence>
    ))}
  </AbsoluteFill>
);

const TeaserMilestone: React.FC<{
  eyebrow: string;
  title: string;
  body: string;
  color: string;
}> = ({eyebrow, title, body, color}) => (
  <Scene eyebrow={eyebrow} title={title} duration={300}>
    <Card accent={color}>
      <div style={{fontSize: 30, lineHeight: 1.55, color: COLORS.muted}}>{body}</div>
    </Card>
  </Scene>
);

export const AicoSelfRepairTeaser: React.FC = () => {
  const {width} = useVideoConfig();
  const scale = width / 1920;
  return (
    <AbsoluteFill style={{backgroundColor: COLORS.bg}}>
      <div style={{width: 1920, height: 1080, transform: `scale(${scale})`, transformOrigin: "top left"}}>
        <Sequence from={0} durationInFrames={300}>
          <TeaserMilestone
            eyebrow="真实任务"
            title="从 Telegram 让 AICO 修一个公开文档问题"
            body="任务范围明确：只修旧 Quickstart 入口，不 commit、不 push、不发布。"
            color={COLORS.blue}
          />
        </Sequence>
        <Sequence from={300} durationInFrames={300}>
          <TeaserMilestone
            eyebrow="人工在环"
            title="shell_exec 先停在 Approval required"
            body="Owner 批准的是任务 62a84f46，不是给 Agent 无限权限。"
            color={COLORS.orange}
          />
        </Sequence>
        <Sequence from={600} durationInFrames={300}>
          <TeaserMilestone
            eyebrow="真实协作"
            title="Claude Code 修改，Codex 只读复核"
            body="主任务与 Reviewer 子任务均为 done，失败和等待没有被剪成成功。"
            color={COLORS.green}
          />
        </Sequence>
        <Sequence from={900} durationInFrames={300}>
          <TeaserMilestone
            eyebrow="重新接手"
            title="Morning + Audit 告诉你发生过什么"
            body="边界内继续；写入、Shell、未知和例外找人；结果保持可追溯。"
            color={COLORS.teal}
          />
        </Sequence>
      </div>
    </AbsoluteFill>
  );
};
