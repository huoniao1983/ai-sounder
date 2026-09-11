import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Settings, Trash2, X } from "lucide-react";

const API_BASE = "http://127.0.0.1:8765";

type TabId = "live" | "scripts" | "interactions" | "bgm" | "voices" | "leads" | "settings";
type InteractionId = "enter" | "gift" | "follow" | "keyword" | "like";
type PlaybackMode = "sequential" | "shuffle";
type PlatformKey = "douyin" | "kuaishou" | "bilibili";

type ScriptItem = {
  id: string;
  label: string;
  weight: number;
  content: string;
  instruction?: string;
  ssml?: string;
};

type LlmSettings = {
  baseUrl: string;
  model: string;
  apiKey: string;
};

type MusicAsset = {
  id: string;
  title: string;
  category: string;
  duration: string;
  file: string;
  url: string;
  licensed?: boolean;
};

type VoiceAsset = {
  id: string;
  name: string;
  style: string;
  provider: string;
  description?: string;
  status?: string;
  target_model?: string;
  sample_file?: string;
  sample_url: string;
  preset?: boolean;
};

type InteractionConfig = {
  id: InteractionId;
  name: string;
  enabled: boolean;
  template: string;
  mode: "queue" | "interrupt" | "pause";
  keywords: string;
};

type SceneItem = {
  id: string;
  title: string;
  description: string;
  platforms: PlatformKey[];
  scripts: ScriptItem[];
  voiceId: string;
  bgmIndex: number;
  playbackMode: PlaybackMode;
  createdAt: string;
};

type PlatformSetup = {
  wsUrl: string;
  headersJson: string;
  paramsJson: string;
};

const NAV_ITEMS: { id: TabId; label: string }[] = [
  { id: "live", label: "直播台" },
  { id: "scripts", label: "文案" },
  { id: "interactions", label: "互动" },
  { id: "bgm", label: "背景音乐" },
  { id: "voices", label: "音色" },
  { id: "leads", label: "线索" },
  { id: "settings", label: "设置" },
];

const PLATFORM_LABELS: Record<PlatformKey, string> = {
  douyin: "抖音",
  kuaishou: "快手",
  bilibili: "B站",
};

const PLATFORM_ICONS: Record<PlatformKey, string> = {
  douyin: "/platforms/douyin.svg",
  kuaishou: "/platforms/kuaishou.svg",
  bilibili: "/platforms/bilibili.svg",
};

const EMPTY_PLATFORM_SETUP: PlatformSetup = {
  wsUrl: "",
  headersJson: "{}",
  paramsJson: "{}",
};

const DEFAULT_SCRIPTS: ScriptItem[] = [
  { id: "s1", label: "羽绒服福利款", weight: 3, content: "欢迎来到直播间，今天这款羽绒服工厂直发，先给大家一个福利价。" },
  { id: "s2", label: "留人话术 A", weight: 2, content: "不要划走，主播正在检查库存，稍后马上放最后一波福利。" },
  { id: "s3", label: "商品讲解 B", weight: 2, content: "内胆加厚、上身显瘦，链接就在左下角，没点关注的先点关注。" },
  { id: "s4", label: "憋单话术", weight: 1, content: "数量只剩最后几十件，客服正在改价，想要的扣 1。" },
];

const DEFAULT_SCENES: SceneItem[] = [
  {
    id: "scene-jacket",
    title: "羽绒服专场",
    description: "秋冬羽绒服福利款循环讲解",
    platforms: ["douyin", "kuaishou"],
    scripts: DEFAULT_SCRIPTS.map((item) => ({ ...item })),
    voiceId: "",
    bgmIndex: 1,
    playbackMode: "sequential",
    createdAt: "2026-09-10T00:00:00.000Z",
  },
];

const BGM_TRACKS: MusicAsset[] = [
  { id: "sold-out", title: "Sold Out", category: "燃向促销", duration: "03:33", file: "sold-out.mp3", url: "/media/music/sold-out.mp3", licensed: true },
  { id: "wake", title: "Wake", category: "轻快带货", duration: "04:15", file: "wake.mp3", url: "/media/music/wake.mp3", licensed: true },
];

const VOICE_ITEMS: VoiceAsset[] = [];

const DEFAULT_INTERACTIONS: InteractionConfig[] = [
  { id: "enter", name: "进入直播间", enabled: true, template: "欢迎{nickname}来到直播间", mode: "queue", keywords: "" },
  { id: "gift", name: "收到礼物", enabled: true, template: "感谢{nickname}送出{gift}，大气", mode: "interrupt", keywords: "" },
  { id: "follow", name: "关注主播", enabled: true, template: "欢迎{nickname}关注，福利马上安排", mode: "queue", keywords: "" },
  { id: "keyword", name: "意向关键词", enabled: true, template: "{nickname}想了解{keyword}，客服稍后联系您", mode: "interrupt", keywords: "多少钱,怎么买,下单,链接" },
  { id: "like", name: "点赞", enabled: true, template: "感谢大家的点赞，继续刷起来", mode: "queue", keywords: "" },
];

const LEAD_ITEMS = [
  { id: 1, nickname: "张哥", score: 60, level: "高意向", source: "礼物 + 私信", time: "12:03:48" },
  { id: 2, nickname: "小雅", score: 35, level: "待跟进", source: "关注 + 提问", time: "12:04:18" },
  { id: 3, nickname: "Momo", score: 18, level: "低意向", source: "意向词", time: "12:05:02" },
];

const DEFAULT_LLM: LlmSettings = {
  baseUrl: "https://api.openai.com/v1",
  model: "gpt-4o-mini",
  apiKey: "",
};

const LLM_STORAGE_KEY = "aisounder.llm.config";
const SAMPLE_TTS_TEXT = "欢迎来到直播间，今天为家人们带来专属福利。";

function parseScriptResponse(content: string): string[] {
  let text = content.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return text.split("\n").map((line) => line.replace(/^[\d.、\s-]+/, "").trim()).filter(Boolean);
  }
  let items: unknown[] = [];
  if (Array.isArray(parsed)) {
    items = parsed;
  } else if (parsed && typeof parsed === "object" && "scripts" in parsed) {
    const candidate = (parsed as { scripts?: unknown }).scripts;
    if (Array.isArray(candidate)) items = candidate;
  }
  const result: string[] = [];
  for (const item of items) {
    const value = item && typeof item === "object" && "content" in item
      ? (item as { content?: unknown }).content
      : item;
    if (typeof value === "string" && value.trim() && !result.includes(value.trim())) {
      result.push(value.trim());
    }
  }
  return result;
}

function cleanSpokenName(nickname: string): string {
  let text = nickname.normalize("NFKC").replace(/[\u{1F300}-\u{1FAFF}\u2600-\u27BF]/gu, "").trim();
  const asciiPrefix = text.match(/^[A-Za-z0-9_\- ]*(?=[\u4e00-\u9fff])/);
  if (asciiPrefix) text = text.slice(asciiPrefix[0].length);
  return text || "朋友";
}

function speechReadyText(template: string, nickname = "", gift = "", keyword = ""): string {
  let text = template
    .replace(/[｛{]\s*nickname\s*[｝}]/gi, cleanSpokenName(nickname))
    .replace(/[｛{]\s*gift\s*[｝}]/gi, gift || "礼物")
    .replace(/[｛{]\s*keyword\s*[｝}]/gi, keyword || "福利")
    .replace(/[｛{][^｝}]*[｝}]/g, "朋友")
    .replace(/xxx/gi, "朋友");
  text = text.replace(/\s+/g, " ").trim();
  text = text.replace(/([\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])/g, "$1");
  const duplicate = /([\u4e00-\u9fff]{3,})\1/g;
  while (duplicate.test(text)) {
    text = text.replace(duplicate, "$1");
  }
  return text.trim();
}

function startMedia(audio: HTMLAudioElement) {
  audio.muted = true;
  void audio
    .play()
    .then(() => {
      window.setTimeout(() => {
        audio.muted = false;
      }, 100);
    })
    .catch(() => {
      audio.muted = false;
    });
}

function fadeVolume(audio: HTMLAudioElement | null, target: number, duration = 500) {
  return new Promise<void>((resolve) => {
    if (!audio) {
      resolve();
      return;
    }
    const start = audio.volume;
    const steps = Math.max(1, Math.round(duration / 25));
    let step = 0;
    const timer = window.setInterval(() => {
      step += 1;
      const progress = Math.min(1, step / steps);
      audio.volume = start + (target - start) * progress;
      if (progress >= 1) {
        window.clearInterval(timer);
        resolve();
      }
    }, 25);
  });
}

function Dot({ active }: { active: boolean }) {
  return <span className={`dot ${active ? "dot-on" : ""}`} />;
}

function PanelHeading({ title, meta, right }: { title: string; meta: string; right?: ReactNode }) {
  return (
    <div className="panel-heading">
      <div>
        <strong>{title}</strong>
        <span>{meta}</span>
      </div>
      {right}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<TabId>("live");
  const [scenes, setScenes] = useState<SceneItem[]>(() => {
    try {
      const stored = localStorage.getItem("aisounder.scenes.v1");
      if (stored) return JSON.parse(stored) as SceneItem[];
    } catch {
      // fall through to defaults
    }
    return DEFAULT_SCENES;
  });
  const [activeSceneId, setActiveSceneId] = useState<string | null>(null);
  const [sceneModalOpen, setSceneModalOpen] = useState(false);
  const [sceneStep, setSceneStep] = useState<1 | 2>(1);
  const [draftScene, setDraftScene] = useState<SceneItem | null>(null);
  const [platformSetups, setPlatformSetups] = useState<Record<PlatformKey, PlatformSetup>>(() => {
    const defaults: Record<PlatformKey, PlatformSetup> = {
      douyin: { ...EMPTY_PLATFORM_SETUP },
      kuaishou: { ...EMPTY_PLATFORM_SETUP },
      bilibili: { ...EMPTY_PLATFORM_SETUP },
    };
    try {
      const stored = localStorage.getItem("aisounder.platformSetups.v1");
      return stored ? { ...defaults, ...JSON.parse(stored) } : defaults;
    } catch {
      return defaults;
    }
  });
  const [settingsTab, setSettingsTab] = useState<"models" | "live" | "platforms">("models");
  const [selectedPlatform, setSelectedPlatform] = useState<PlatformKey>("douyin");
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, boolean>>({});
  const [platformEvents, setPlatformEvents] = useState<Array<Record<string, unknown>>>([]);
  const [running, setRunning] = useState(false);
  const [engineReady, setEngineReady] = useState(false);
  const [scripts, setScripts] = useState<ScriptItem[]>(() => {
    try {
      const stored = localStorage.getItem("aisounder.scripts.v1");
      if (stored) return JSON.parse(stored) as ScriptItem[];
    } catch {
      // fall through to defaults
    }
    return DEFAULT_SCRIPTS;
  });
  const [interactions, setInteractions] = useState<InteractionConfig[]>(() => {
    try {
      const stored = localStorage.getItem("aisounder.interactions.v2");
      if (stored) return JSON.parse(stored) as InteractionConfig[];
    } catch {
      // fall through to defaults
    }
    return DEFAULT_INTERACTIONS;
  });
  const [remaining, setRemaining] = useState(4);
  const [bgmIndex, setBgmIndex] = useState(() => {
    const stored = Number(localStorage.getItem("aisounder.bgmIndex"));
    return Number.isFinite(stored) && stored >= 1 ? stored : 3;
  });
  const [bgmVolume, setBgmVolume] = useState(() => {
    const stored = Number(localStorage.getItem("aisounder.bgmVolume"));
    return Number.isFinite(stored) && stored > 0 ? stored : 0.35;
  });
  const [ducking, setDucking] = useState(() => localStorage.getItem("aisounder.ducking") !== "false");
  const [musicItems, setMusicItems] = useState<MusicAsset[]>(BGM_TRACKS);
  const [voiceItems, setVoiceItems] = useState<VoiceAsset[]>(VOICE_ITEMS);
  const [voiceProviderStatus, setVoiceProviderStatus] = useState({ cosyvoice: false, model: "", provider: "" });
  const [audioSrc, setAudioSrc] = useState("");
  const [audioLabel, setAudioLabel] = useState("");
  const [bgmSrc, setBgmSrc] = useState("");
  const [bgmLabel, setBgmLabel] = useState("");
  const audioRef = useRef<HTMLAudioElement>(null);
  const bgmAudioRef = useRef<HTMLAudioElement>(null);
  const voiceFileRef = useRef<HTMLInputElement>(null);
  const [voiceSynthesisText, setVoiceSynthesisText] = useState(SAMPLE_TTS_TEXT);
  const [uploadingVoice, setUploadingVoice] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState("");
  const [voiceName, setVoiceName] = useState("");
  const [voiceDescription, setVoiceDescription] = useState("");
  const [voiceSampleUrl, setVoiceSampleUrl] = useState("");
  const [voiceFileName, setVoiceFileName] = useState("");
  const [ttsConfigOpen, setTtsConfigOpen] = useState(false);
  const [ttsConfig, setTtsConfig] = useState({
    apiKey: "",
    baseUrl: "https://dashscope.aliyuncs.com/api/v1",
    model: "cosyvoice-v3.5-flash",
  });
  const [liveScriptIndex, setLiveScriptIndex] = useState(0);
  const [liveStatus, setLiveStatus] = useState("");
  const [playbackMode, setPlaybackMode] = useState<PlaybackMode>(() => {
    return localStorage.getItem("aisounder.playbackMode") === "shuffle" ? "shuffle" : "sequential";
  });
  const [minGapSeconds, setMinGapSeconds] = useState(() => {
    const stored = Number(localStorage.getItem("aisounder.minGapSeconds"));
    return Number.isFinite(stored) && stored >= 0 ? stored : 2;
  });
  const [maxGapSeconds, setMaxGapSeconds] = useState(() => {
    const stored = Number(localStorage.getItem("aisounder.maxGapSeconds"));
    return Number.isFinite(stored) && stored >= 0 ? stored : 4;
  });
  const [duckedRatio, setDuckedRatio] = useState(() => {
    const stored = Number(localStorage.getItem("aisounder.duckedRatio"));
    return Number.isFinite(stored) && stored > 0 && stored < 1 ? stored : 0.28;
  });
  const [previewVoiceId, setPreviewVoiceId] = useState(() => localStorage.getItem("aisounder.voiceId") ?? "");
  const runningRef = useRef(false);
  const scriptsRef = useRef(scripts);
  const voiceIdRef = useRef("xiaoya");
  const ttsCacheRef = useRef(new Map<string, string>());
  const playbackModeRef = useRef<PlaybackMode>("sequential");
  const liveIndexRef = useRef(-1);
  const shuffleQueueRef = useRef<string[]>([]);
  const lastPlayedIdRef = useRef<string | null>(null);
  const bgmVolumeRef = useRef(bgmVolume);
  const duckingRef = useRef(ducking);
  const [llm, setLlm] = useState<LlmSettings>(() => {
    try {
      const stored = localStorage.getItem(LLM_STORAGE_KEY);
      if (stored) return { ...DEFAULT_LLM, ...JSON.parse(stored) } as LlmSettings;
    } catch {
      // fall through to defaults
    }
    return DEFAULT_LLM;
  });
  const [generating, setGenerating] = useState(false);
  const [generationMessage, setGenerationMessage] = useState("");
  const [pendingScripts, setPendingScripts] = useState<Record<string, ScriptItem[]>>(() => {
    try {
      const stored = localStorage.getItem("aisounder.pendingScripts.v1");
      return stored ? JSON.parse(stored) as Record<string, ScriptItem[]> : {};
    } catch {
      return {};
    }
  });
  const [llmConfigOpen, setLlmConfigOpen] = useState(false);
  const [product, setProduct] = useState("轻薄羽绒服");
  const [sellingPoints, setSellingPoints] = useState("保暖\n显瘦\n工厂直发");
  const [audience, setAudience] = useState("泛流量");

  useEffect(() => {
    const tauri = (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
    setEngineReady(Boolean(tauri));
  }, []);

  useEffect(() => {
    localStorage.setItem(LLM_STORAGE_KEY, JSON.stringify(llm));
  }, [llm]);

  useEffect(() => {
    localStorage.setItem("aisounder.scripts.v1", JSON.stringify(scripts));
  }, [scripts]);

  useEffect(() => {
    localStorage.setItem("aisounder.scenes.v1", JSON.stringify(scenes));
  }, [scenes]);

  useEffect(() => {
    localStorage.setItem("aisounder.pendingScripts.v1", JSON.stringify(pendingScripts));
  }, [pendingScripts]);

  useEffect(() => {
    localStorage.setItem("aisounder.platformSetups.v1", JSON.stringify(platformSetups));
  }, [platformSetups]);

  useEffect(() => {
    const refreshPlatforms = async () => {
      try {
        const [statusResponse, eventsResponse] = await Promise.all([
          fetch(`${API_BASE}/platform/status`),
          fetch(`${API_BASE}/platform/events`),
        ]);
        if (statusResponse.ok) {
          const statusData = (await statusResponse.json()) as { items: { platform: string; connected: boolean }[] };
          setPlatformStatuses(Object.fromEntries(statusData.items.map((item) => [item.platform, item.connected])));
        }
        if (eventsResponse.ok) {
          const eventData = (await eventsResponse.json()) as { items: Array<Record<string, unknown>> };
          setPlatformEvents(eventData.items);
        }
      } catch {
        // platform service is optional until configured
      }
    };
    void refreshPlatforms();
    const timer = window.setInterval(refreshPlatforms, 3000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    localStorage.setItem("aisounder.interactions.v2", JSON.stringify(interactions));
  }, [interactions]);

  useEffect(() => {
    localStorage.setItem("aisounder.bgmIndex", String(bgmIndex));
    if (activeSceneId) {
      setScenes((items) => items.map((scene) => scene.id === activeSceneId ? { ...scene, bgmIndex } : scene));
    }
  }, [activeSceneId, bgmIndex]);

  useEffect(() => {
    localStorage.setItem("aisounder.ducking", String(ducking));
    duckingRef.current = ducking;
    if (!ducking && bgmAudioRef.current) {
      void fadeVolume(bgmAudioRef.current, bgmVolumeRef.current, 300);
    }
  }, [ducking]);

  useEffect(() => {
    const safeMin = Math.max(0, minGapSeconds);
    const safeMax = Math.max(safeMin, maxGapSeconds);
    localStorage.setItem("aisounder.minGapSeconds", String(safeMin));
    localStorage.setItem("aisounder.maxGapSeconds", String(safeMax));
  }, [maxGapSeconds, minGapSeconds]);

  useEffect(() => {
    localStorage.setItem("aisounder.duckedRatio", String(duckedRatio));
  }, [duckedRatio]);

  useEffect(() => {
    bgmVolumeRef.current = bgmVolume;
    localStorage.setItem("aisounder.bgmVolume", String(bgmVolume));
    if (!runningRef.current && bgmAudioRef.current) {
      bgmAudioRef.current.volume = bgmVolume;
    }
  }, [bgmVolume]);

  useEffect(() => {
    runningRef.current = running;
  }, [running]);

  useEffect(() => {
    scriptsRef.current = scripts;
    shuffleQueueRef.current = [];
  }, [scripts]);

  useEffect(() => {
    localStorage.setItem("aisounder.voiceId", previewVoiceId);
    voiceIdRef.current = previewVoiceId;
    if (activeSceneId) {
      setScenes((items) => items.map((scene) => scene.id === activeSceneId ? { ...scene, voiceId: previewVoiceId } : scene));
    }
  }, [activeSceneId, previewVoiceId]);

  useEffect(() => {
    playbackModeRef.current = playbackMode;
    localStorage.setItem("aisounder.playbackMode", playbackMode);
    shuffleQueueRef.current = [];
    if (activeSceneId) {
      setScenes((items) => items.map((scene) => scene.id === activeSceneId ? { ...scene, playbackMode } : scene));
    }
  }, [activeSceneId, playbackMode]);

  useEffect(() => {
    if (bgmSrc && bgmAudioRef.current) startMedia(bgmAudioRef.current);
  }, [bgmSrc]);

  useEffect(() => {
    if (audioSrc && audioRef.current) startMedia(audioRef.current);
  }, [audioSrc]);

  useEffect(() => {
    const loadAssets = async () => {
      try {
        const [musicResponse, voiceResponse, enginesResponse, ttsConfigResponse] = await Promise.all([
          fetch(`${API_BASE}/assets/music`),
          fetch(`${API_BASE}/assets/voices`),
          fetch(`${API_BASE}/engines`),
          fetch(`${API_BASE}/config/tts`),
        ]);
        if (musicResponse.ok) {
          const musicData = (await musicResponse.json()) as { items: MusicAsset[] };
          if (musicData.items.length) setMusicItems(musicData.items);
        }
        if (voiceResponse.ok) {
          const voiceData = (await voiceResponse.json()) as { items: VoiceAsset[] };
          if (voiceData.items.length) setVoiceItems(voiceData.items);
        }
        if (enginesResponse.ok) {
          setEngineReady(true);
          setVoiceProviderStatus((await enginesResponse.json()) as { cosyvoice: boolean; model: string; provider: string });
        }
        if (ttsConfigResponse.ok) {
          const config = (await ttsConfigResponse.json()) as { base_url: string; model: string };
          setTtsConfig((items) => ({ ...items, baseUrl: config.base_url, model: config.model }));
        }
      } catch {
        // local capability service is optional for pure UI development
      }
    };
    void loadAssets();
  }, []);

  useEffect(() => {
    if (musicItems.length && bgmIndex > musicItems.length) {
      setBgmIndex(1);
    }
  }, [bgmIndex, musicItems.length]);

  useEffect(() => {
    if (!voiceItems.length) {
      setPreviewVoiceId("");
      return;
    }
    if (!voiceItems.some((voice) => voice.id === previewVoiceId)) {
      setPreviewVoiceId(voiceItems[0].id);
    }
  }, [previewVoiceId, voiceItems]);

  useEffect(() => {
    if (!voiceItems.some((voice) => voice.status === "DEPLOYING")) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE}/assets/voices`);
        if (!response.ok) return;
        const data = (await response.json()) as { items: VoiceAsset[] };
        setVoiceItems(data.items);
      } catch {
        // keep the previous status until the local service is reachable again
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [voiceItems]);

  const current = scripts[0] ?? { id: "empty", label: "暂无文案", weight: 0, content: "" };
  const activeScene = activeSceneId ? scenes.find((scene) => scene.id === activeSceneId) ?? null : null;
  const liveCurrent = scripts.length ? scripts[liveScriptIndex % scripts.length] : current;
  const recentPlatformEvents = useMemo(() => platformEvents.slice(-4).reverse(), [platformEvents]);
  const pendingGenerated = activeSceneId ? pendingScripts[activeSceneId] ?? [] : [];
  const progress = scripts.length ? Math.round((remaining / scripts.length) * 100) : 0;
  const poolLabel = useMemo(() => `${remaining}/${scripts.length}`, [remaining, scripts.length]);

  const updateSceneScripts = (updater: (items: ScriptItem[]) => ScriptItem[]) => {
    const next = updater(scripts);
    setScripts(next);
    if (activeSceneId) {
      setScenes((sceneItems) =>
        sceneItems.map((scene) => (scene.id === activeSceneId ? { ...scene, scripts: next } : scene)),
      );
    }
    if (draftScene) setDraftScene((scene) => (scene ? { ...scene, scripts: next } : scene));
  };

  const adjustWeight = (id: string, delta: number) => {
    updateSceneScripts((items) => items.map((item) => (item.id === id ? { ...item, weight: Math.max(1, item.weight + delta) } : item)));
  };

  const updateScriptContent = (id: string, content: string) => {
    updateSceneScripts((items) =>
      items.map((item) => (item.id === id ? { ...item, content, ssml: "" } : item)),
    );
  };

  const updateScriptLabel = (id: string, label: string) => {
    updateSceneScripts((items) => items.map((item) => (item.id === id ? { ...item, label } : item)));
  };

  const updateScriptInstruction = (id: string, instruction: string) => {
    updateSceneScripts((items) => items.map((item) => (item.id === id ? { ...item, instruction } : item)));
  };

  const updateScriptSsml = (id: string, ssml: string) => {
    updateSceneScripts((items) => items.map((item) => (item.id === id ? { ...item, ssml } : item)));
  };

  const deleteScript = (id: string) => {
    updateSceneScripts((items) => items.filter((item) => item.id !== id));
  };

  const createSceneDraft = () => {
    const id = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `scene-${Date.now()}`;
    setDraftScene({
      id,
      title: "",
      description: "",
      platforms: ["douyin"],
      scripts: [{ id: `script-${Date.now()}`, label: "开场话术", weight: 1, content: "" }],
      voiceId: previewVoiceId,
      bgmIndex,
      playbackMode,
      createdAt: new Date().toISOString(),
    });
    setSceneStep(1);
    setSceneModalOpen(true);
  };

  const updateDraftScene = (patch: Partial<SceneItem>) => {
    setDraftScene((scene) => (scene ? { ...scene, ...patch } : scene));
  };

  const enterScene = (scene: SceneItem, targetTab: TabId = "live") => {
    runningRef.current = false;
    setRunning(false);
    setActiveSceneId(scene.id);
    setScripts(scene.scripts.map((item) => ({ ...item })));
    setPreviewVoiceId(scene.voiceId || "");
    setBgmIndex(scene.bgmIndex || 1);
    setPlaybackMode(scene.playbackMode || "sequential");
    setTab(targetTab);
  };

  const leaveScene = () => {
    runningRef.current = false;
    setRunning(false);
    setAudioSrc("");
    setBgmSrc("");
    setActiveSceneId(null);
  };

  const saveDraftScene = (openLive: boolean) => {
    if (!draftScene) return;
    const saved: SceneItem = {
      ...draftScene,
      title: draftScene.title.trim() || "未命名直播专场",
      scripts: draftScene.scripts.filter((item) => item.content.trim() || item.label.trim()),
    };
    setScenes((items) => {
      const exists = items.some((scene) => scene.id === saved.id);
      return exists ? items.map((scene) => scene.id === saved.id ? saved : scene) : [...items, saved];
    });
    setSceneModalOpen(false);
    setDraftScene(null);
    if (openLive) enterScene(saved);
  };

  const deleteScene = (sceneId: string) => {
    setScenes((items) => items.filter((scene) => scene.id !== sceneId));
    if (activeSceneId === sceneId) leaveScene();
  };

  const updatePlatformSetup = (platform: PlatformKey, patch: Partial<PlatformSetup>) => {
    setPlatformSetups((items) => ({
      ...items,
      [platform]: { ...items[platform], ...patch },
    }));
  };

  const connectPlatform = async (platform: PlatformKey) => {
    const setup = platformSetups[platform];
    try {
      const headers = JSON.parse(setup.headersJson || "{}") as Record<string, string>;
      const params = JSON.parse(setup.paramsJson || "{}") as Record<string, string>;
      const response = await fetch(`${API_BASE}/platform/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          platform,
          config: { ws_url: setup.wsUrl.trim(), headers, params },
        }),
      });
      const payload = await response.json() as { error?: string };
      if (!response.ok) throw new Error(payload.error || "连接失败");
      setPlatformStatuses((items) => ({ ...items, [platform]: true }));
      setVoiceMessage("");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "平台连接失败");
    }
  };

  const disconnectPlatform = async (platform: PlatformKey) => {
    await fetch(`${API_BASE}/platform/disconnect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform }),
    });
    setPlatformStatuses((items) => ({ ...items, [platform]: false }));
  };

  const updateInteraction = (id: InteractionId, patch: Partial<InteractionConfig>) => {
    setInteractions((items) => items.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  };

  const playAudio = (url: string, label: string) => {
    if (!url) return;
    const source = `${API_BASE}${url}`;
    setBgmSrc(source);
    setBgmLabel(label);
    if (bgmAudioRef.current) {
      bgmAudioRef.current.src = source;
      bgmAudioRef.current.volume = bgmVolumeRef.current;
      bgmAudioRef.current.load();
      startMedia(bgmAudioRef.current);
    }
  };

  const playVoiceSample = (url: string, label: string) => {
    if (!url) return;
    const source = url.startsWith("http") ? url : `${API_BASE}${url}`;
    setAudioSrc(source);
    setAudioLabel(label);
    if (audioRef.current) {
      audioRef.current.src = source;
      audioRef.current.load();
      startMedia(audioRef.current);
    }
  };

  const moveBgm = (delta: number) => {
    if (!musicItems.length) return;
    const next = (((bgmIndex - 1 + delta) % musicItems.length) + musicItems.length) % musicItems.length + 1;
    setBgmIndex(next);
    const track = musicItems[next - 1];
    if (track) playAudio(track.url, track.title);
  };

  const toggleLive = (next?: boolean) => {
    const value = next ?? !running;
    runningRef.current = value;
    setRunning(value);
    if (!value) {
      setAudioSrc("");
      setBgmSrc("");
      setLiveStatus("");
      return;
    }
    if (!scripts.length) {
      setVoiceMessage("文案组为空，请先添加文案");
      return;
    }
    if (!previewVoiceId) {
      setVoiceMessage("请先在音色库创建并选择一个音色");
      runningRef.current = false;
      setRunning(false);
      return;
    }
    const track = musicItems[bgmIndex - 1] ?? musicItems[0];
    if (track) playAudio(track.url, track.title);
    void runLiveNarration();
  };

  const sleep = (milliseconds: number) => new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

  const waitForAudioEnd = (url: string, label: string) =>
    new Promise<void>((resolve) => {
      const audio = audioRef.current;
      if (!audio) {
        resolve();
        return;
      }
      setAudioSrc(url);
      setAudioLabel(label);
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        audio.onended = null;
        audio.onerror = null;
        audio.oncanplay = null;
        resolve();
      };
      const timeout = window.setTimeout(finish, 30000);
      const cleanup = () => {
        window.clearTimeout(timeout);
      };
      audio.onended = finish;
      audio.onerror = finish;
      audio.src = url;
      audio.load();
      startMedia(audio);
    });

  const getCachedTtsUrl = async (
    voiceId: string,
    text: string,
    instruction = "",
    ssml = "",
  ) => {
    const key = `${voiceId}\u0000${text}\u0000${instruction}\u0000${ssml}`;
    const cached = ttsCacheRef.current.get(key);
    if (cached) return cached;
    const params = new URLSearchParams({ voice: voiceId, text });
    if (instruction) params.set("instruction", instruction);
    if (ssml) params.set("ssml", ssml);
    const url = `${API_BASE}/tts?${params.toString()}`;
    const response = await fetch(url);
    if (!response.ok) {
      const errorBody = (await response.json()) as { error?: string };
      throw new Error(errorBody.error || `合成失败 ${response.status}`);
    }
    const objectUrl = URL.createObjectURL(await response.blob());
    ttsCacheRef.current.set(key, objectUrl);
    return objectUrl;
  };

  const chooseNextScript = () => {
    const items = scriptsRef.current;
    if (!items.length) return null;
    if (playbackModeRef.current === "sequential") {
      liveIndexRef.current = liveIndexRef.current < 0 ? 0 : (liveIndexRef.current + 1) % items.length;
      const script = items[liveIndexRef.current];
      lastPlayedIdRef.current = script.id;
      return { script, index: liveIndexRef.current };
    }

    if (!shuffleQueueRef.current.length) {
      const ids = items.map((item) => item.id);
      for (let index = ids.length - 1; index > 0; index -= 1) {
        const swap = Math.floor(Math.random() * (index + 1));
        [ids[index], ids[swap]] = [ids[swap], ids[index]];
      }
      if (ids.length > 1 && ids[0] === lastPlayedIdRef.current) {
        const swap = 1 + Math.floor(Math.random() * (ids.length - 1));
        [ids[0], ids[swap]] = [ids[swap], ids[0]];
      }
      shuffleQueueRef.current = ids;
    }
    const id = shuffleQueueRef.current.shift();
    const index = items.findIndex((item) => item.id === id);
    if (index < 0) return chooseNextScript();
    lastPlayedIdRef.current = id ?? null;
    return { script: items[index], index };
  };

  const runLiveNarration = async () => {
    liveIndexRef.current = -1;
    shuffleQueueRef.current = [];
    lastPlayedIdRef.current = null;
    setLiveStatus("正在启动文案播报…");
    while (runningRef.current) {
      const next = chooseNextScript();
      if (!next) {
        setVoiceMessage("文案组为空，播报已停止");
        break;
      }
      const { script, index } = next;
      setLiveScriptIndex(index);
      setLiveStatus(`正在合成：${script.label}`);
      try {
        const audioUrl = await getCachedTtsUrl(
          voiceIdRef.current,
          script.content,
          script.instruction,
          script.ssml,
        );
        setVoiceMessage("");
        if (duckingRef.current) {
          await fadeVolume(bgmAudioRef.current, bgmVolumeRef.current * duckedRatio, 500);
        }
        await waitForAudioEnd(audioUrl, script.label);
        if (duckingRef.current) {
          await fadeVolume(bgmAudioRef.current, bgmVolumeRef.current, 500);
        }
      } catch (error) {
        setVoiceMessage(error instanceof Error ? error.message : "合成失败");
        await sleep(3000);
      }
      if (!runningRef.current) break;
      const gap = (
        minGapSeconds
        + Math.random() * Math.max(0, maxGapSeconds - minGapSeconds)
      ) * 1000;
      setLiveStatus(`${(gap / 1000).toFixed(1)} 秒后播放下一条`);
      await sleep(gap);
    }
    setRunning(false);
    runningRef.current = false;
    setLiveStatus("");
  };

  const playTtsPreview = async (voiceId: string, text: string) => {
    setVoiceMessage("合成中…");
    try {
      const audioUrl = await getCachedTtsUrl(voiceId, text);
      setAudioSrc(audioUrl);
      setAudioLabel(`合成：${voiceId}`);
      setVoiceMessage("已缓存，可重复试听");
      if (audioRef.current) {
        audioRef.current.load();
        startMedia(audioRef.current);
      }
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "合成失败");
    }
  };

  const handleVoiceFileSelected = (file: File) => {
    setVoiceFileName(file.name);
    const objectUrl = URL.createObjectURL(file);
    playVoiceSample(objectUrl, file.name);
    setVoiceMessage("本地录音已选择，请填写公网样本 URL 后创建音色");
  };

  const createVoiceProfile = async () => {
    if (!voiceSampleUrl.trim()) {
      setVoiceMessage("CosyVoice 声音复刻需要公网可访问的音频 URL");
      return;
    }
    setUploadingVoice(true);
    setVoiceMessage("正在提交声音复刻…");
    try {
      const response = await fetch(`${API_BASE}/voice/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sample_url: voiceSampleUrl.trim(),
          display_name: voiceName.trim() || "我的音色",
          description: voiceDescription.trim(),
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = (await response.json()) as { profile: VoiceAsset };
      setVoiceItems((items) => [...items.filter((item) => item.id !== payload.profile.id), payload.profile]);
      setPreviewVoiceId(payload.profile.id);
      setVoiceMessage("音色创建请求已提交，审核完成后即可合成");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "音色创建失败");
    } finally {
      setUploadingVoice(false);
    }
  };

  const saveTtsConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/config/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          api_key: ttsConfig.apiKey,
          base_url: ttsConfig.baseUrl,
          model: ttsConfig.model,
        }),
      });
      if (!response.ok) throw new Error(await response.text());
      const enginesResponse = await fetch(`${API_BASE}/engines`);
      if (enginesResponse.ok) {
        setVoiceProviderStatus((await enginesResponse.json()) as { cosyvoice: boolean; model: string; provider: string });
      }
      setTtsConfig((items) => ({ ...items, apiKey: "" }));
      setTtsConfigOpen(false);
      setVoiceMessage("千问语音配置已保存");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "保存失败");
    }
  };

  const deleteVoiceProfile = async (voiceId: string) => {
    try {
      await fetch(`${API_BASE}/voice/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: voiceId }),
      });
      setVoiceItems((items) => items.filter((item) => item.id !== voiceId));
      if (previewVoiceId === voiceId) setPreviewVoiceId("");
    } catch (error) {
      setVoiceMessage(error instanceof Error ? error.message : "删除音色失败");
    }
  };

  const exportLeadsCsv = () => {
    const header = ["昵称", "分数", "等级", "来源", "时间"];
    const rows = LEAD_ITEMS.map((lead) => [lead.nickname, lead.score, lead.level, lead.source, lead.time]);
    const csv = [header, ...rows].map((row) => row.join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `aisounder-leads-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const generateScripts = async () => {
    if (!activeSceneId) {
      setGenerationMessage("请先选择或新建直播专场");
      return;
    }
    if (!llm.baseUrl.trim() || !llm.model.trim() || !llm.apiKey.trim()) {
      setLlmConfigOpen(true);
      setGenerationMessage("");
      return;
    }

    setGenerating(true);
    setGenerationMessage("生成中…");
    try {
      const response = await fetch(`${API_BASE}/scripts/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          base_url: llm.baseUrl.trim(),
          model: llm.model.trim(),
          api_key: llm.apiKey.trim(),
          product,
          selling_points: sellingPoints.split("\n").map((item) => item.trim()).filter(Boolean),
          audience,
          count: 5,
        }),
      });
      if (!response.ok) {
        throw new Error(`本地能力服务返回 ${response.status}`);
      }
      const data = (await response.json()) as {
        scripts?: {
          id: string;
          label: string;
          content: string;
          weight: number;
          instruction?: string;
          ssml?: string;
        }[];
      };
      const contents = data.scripts ?? [];
      const startIndex = scripts.length + 1;
      const generated = contents.map((item, index) => ({
        id: item.id || `llm-${Date.now()}-${index}`,
        label: item.label || `AI 文案 ${String(startIndex + index).padStart(2, "0")}`,
        weight: item.weight || 1,
        content: item.content,
        instruction: item.instruction || "",
        ssml: item.ssml || "",
      }));
      if (!generated.length) throw new Error("模型返回的文案为空");
      setPendingScripts((items) => ({ ...items, [activeSceneId]: generated }));
      setGenerationMessage(`已生成 ${generated.length} 条，请确认后保存`);
    } catch (error) {
      setGenerationMessage(error instanceof Error ? error.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const confirmGeneratedScripts = () => {
    if (!activeSceneId || !pendingGenerated.length) return;
    updateSceneScripts((items) => [...items, ...pendingGenerated]);
    setPendingScripts((items) => ({ ...items, [activeSceneId]: [] }));
    setGenerationMessage(`已保存 ${pendingGenerated.length} 条到当前专场`);
  };

  const discardGeneratedScripts = () => {
    if (!activeSceneId) return;
    setPendingScripts((items) => ({ ...items, [activeSceneId]: [] }));
    setGenerationMessage("已丢弃本次生成结果");
  };

  const renderSceneHome = () => (
    <div className="scene-home">
      <div className="view-heading">
        <div>
          <h2>直播专场</h2>
          <span>每个专场独立管理平台、文案、音色、BGM 和播放模式</span>
        </div>
        <button className="accent-button" onClick={createSceneDraft}>新建直播专场</button>
      </div>
      <section className="panel scene-panel">
        <div className="scene-list">
          {scenes.map((scene) => {
            const voice = voiceItems.find((item) => item.id === scene.voiceId);
            const music = musicItems[(scene.bgmIndex || 1) - 1];
            return (
              <div key={scene.id} className="scene-row">
                <button className="scene-main" onClick={() => enterScene(scene)}>
                  <strong>{scene.title}</strong>
                  <span>{scene.description || "暂无描述"}</span>
                </button>
                <div className="scene-platforms">
                  {scene.platforms.map((platform) => (
                    <span key={platform} className={`platform-tag platform-${platform}`}>
                      <img src={PLATFORM_ICONS[platform]} alt="" />
                      {PLATFORM_LABELS[platform]}
                    </span>
                  ))}
                </div>
                <span className="scene-meta">{scene.scripts.length} 条文案 · {voice?.name || "未选音色"} · {music?.title || "未选 BGM"}</span>
                <button className="accent-button" onClick={() => enterScene(scene)}>进入直播</button>
                <button className="delete-button" onClick={() => deleteScene(scene.id)} aria-label="删除专场">
                  <Trash2 size={14} />
                </button>
              </div>
            );
          })}
          {!scenes.length ? <div className="empty-state">还没有直播专场，点击右上角新建</div> : null}
        </div>
      </section>
    </div>
  );

  const renderLive = () => (activeScene ? renderLiveConsole() : renderSceneHome());

  const renderLiveConsole = () => (
    <>
      <section className="transport-bar">
        <div className="transport-now">
          <button className="back-button" onClick={leaveScene}>← 返回专场</button>
          <span className="transport-kicker">当前主文案</span>
          <strong>{liveCurrent.label}</strong>
          <span className="transport-detail">{liveStatus || "间隔 3-8s · 随机不重复"}</span>
        </div>
        <div className="transport-controls">
          <button className="icon-button" aria-label="上一首">‹</button>
          <button className="icon-button play" aria-label={running ? "暂停" : "开始"} onClick={() => toggleLive()}>
            {running ? "Ⅱ" : "▶"}
          </button>
          <button className="icon-button" aria-label="下一首">›</button>
        </div>
        <div className="transport-status">
          <span><Dot active={running} /> {running ? "直播中" : "待开播"}</span>
          <b>{String(bgmIndex).padStart(2, "0")} · 轻快带货</b>
        </div>
        <button className={running ? "run-button stop" : "run-button"} onClick={() => toggleLive()}>
          {running ? "停止" : "一键开播"}
        </button>
      </section>

      <div className="workbench">
        <section className="panel stage-panel">
          <PanelHeading
            title="播出序列"
            meta="已播 12 条 · 周期 03"
            right={
              <div className="signal-bars" aria-hidden="true">
                {[5, 8, 6, 10, 7, 9, 4].map((height, index) => (
                  <i key={index} style={{ height: `${height * 6}px` }} />
                ))}
              </div>
            }
          />
          <div className="sequence-list">
            {scripts.map((item, index) => (
              <div key={item.id} className={`sequence-row ${index === liveScriptIndex ? "current" : ""}`}>
                <span className="sequence-index">{String(index + 1).padStart(2, "0")}</span>
                <strong>{item.label}</strong>
                <span className="sequence-state">{index === liveScriptIndex ? "正在播放" : index === liveScriptIndex + 1 ? "下一句" : "待播放"}</span>
              </div>
            ))}
          </div>
          <div className="panel-foot">
            <span>池剩余 {poolLabel}</span>
            <span>进度 {progress}%</span>
          </div>
        </section>

        <section className="panel script-panel">
          <PanelHeading title="文案权重" meta="同周期不重复" />
          <div className="weight-list">
            {scripts.map((item) => (
              <div key={item.id} className="weight-row">
                <span>{item.label}</span>
                <button onClick={() => adjustWeight(item.id, -1)} aria-label="降低权重">−</button>
                <b>{item.weight}</b>
                <button onClick={() => adjustWeight(item.id, 1)} aria-label="提高权重">+</button>
              </div>
            ))}
          </div>
          <div className="script-input">
            <select value={previewVoiceId} onChange={(event) => setPreviewVoiceId(event.target.value)}>
              {voiceItems.map((voice) => (
                <option key={voice.id} value={voice.id}>{voice.name} · {voice.style}</option>
              ))}
            </select>
            <select value={playbackMode} onChange={(event) => setPlaybackMode(event.target.value as PlaybackMode)}>
              <option value="sequential">顺序循环</option>
              <option value="shuffle">随机 · 首尾不重复</option>
            </select>
            <select
              value={bgmIndex}
              onChange={(event) => {
                const index = Number(event.target.value);
                setBgmIndex(index);
                const track = musicItems[index - 1];
                if (track) playAudio(track.url, track.title);
              }}
            >
              {musicItems.map((track, index) => (
                <option key={track.id} value={index + 1}>{track.title} · {track.category}</option>
              ))}
            </select>
            <button className="accent-button" onClick={() => setRemaining(scripts.length)}>应用到直播</button>
          </div>
        </section>

        <section className="panel event-panel">
          <PanelHeading
            title="弹幕互动"
            meta="抖音 · B站"
            right={
              <div className="heading-actions">
                <span className="count-badge">+4</span>
                <button className="gear-button" onClick={() => setTab("interactions")} aria-label="互动配置">
                  <Settings size={15} />
                </button>
              </div>
            }
          />
          <div className="event-stream">
            {recentPlatformEvents.length ? recentPlatformEvents.map((event, index) => (
              <div key={`${String(event.received_at)}-${index}`} className="event-row">
                <span className="event-user">{String(event.nickname || "系统")}</span>
                <span className={`event-type ${String(event.type || "")}`}>
                  {String(event.content || event.type || "")}
                </span>
                <time>{new Date(Number(event.received_at || Date.now()) * 1000).toLocaleTimeString("zh-CN", { hour12: false })}</time>
              </div>
            )) : (
              <>
                <div className="event-row"><span className="event-user">ok小李</span><span className="event-type enter">进入</span><time>12:04:11</time></div>
                <div className="event-row"><span className="event-user">小雅</span><span className="event-type danmaku">这个多少钱？</span><time>12:04:18</time></div>
                <div className="event-row"><span className="event-user">礼物哥</span><span className="event-type gift">礼物 ×1</span><time>12:04:24</time></div>
                <div className="event-row"><span className="event-user">正午晒太阳</span><span className="event-type follow">关注</span><time>12:04:30</time></div>
              </>
            )}
          </div>
        </section>
      </div>
    </>
  );

  const renderScripts = () => (
    <div className="scripts-page">
      <div className="scripts-toolbar">
        <label>当前直播专场
          <select
            value={activeSceneId ?? ""}
            onChange={(event) => {
              const scene = scenes.find((item) => item.id === event.target.value);
              if (scene) enterScene(scene, "scripts");
            }}
          >
            {scenes.map((scene) => (
              <option key={scene.id} value={scene.id}>{scene.title}</option>
            ))}
          </select>
        </label>
        <span>{scripts.length} 条文案 · {activeScene?.description || "未设置描述"}</span>
        <button className="tool-button" onClick={createSceneDraft}>新建直播专场</button>
      </div>
      {activeScene ? (
      <div className="management-layout">
      <section className="panel list-panel">
        <PanelHeading
          title="当前文案组"
          meta={`${activeScene.title} · ${scripts.length} 条`}
          right={<span className="count-badge">{scripts.length}</span>}
        />
        <div className="script-editor-list">
          {scripts.map((item, index) => (
            <div key={item.id} className="script-editor-row">
              <span className="script-index">{index + 1}</span>
              <div className="script-editor-main">
                <input value={item.label} onChange={(event) => updateScriptLabel(item.id, event.target.value)} />
                <textarea value={item.content} onChange={(event) => updateScriptContent(item.id, event.target.value)} rows={3} />
                <details className="performance-details">
                  <summary>表演指令与 SSML</summary>
                  <textarea
                    value={item.instruction || ""}
                    onChange={(event) => updateScriptInstruction(item.id, event.target.value)}
                    rows={2}
                    placeholder="例如：亲切、有交流感，重点词加重"
                  />
                  <textarea
                    value={item.ssml || ""}
                    onChange={(event) => updateScriptSsml(item.id, event.target.value)}
                    rows={2}
                    placeholder='例如：<speak>别急，<break time="300ms"/>马上上链接。</speak>'
                  />
                </details>
              </div>
              <div className="script-editor-controls">
                <button onClick={() => adjustWeight(item.id, -1)} aria-label="降低权重">−</button>
                <b>{item.weight}</b>
                <button onClick={() => adjustWeight(item.id, 1)} aria-label="提高权重">+</button>
                <button className="delete-button" onClick={() => deleteScript(item.id)} aria-label="删除文案">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="panel side-panel">
        <PanelHeading
          title="AI 文案生成"
          meta="外部大模型"
          right={
            <button className="gear-button" onClick={() => setLlmConfigOpen(true)} aria-label="模型配置">
              <Settings size={15} />
            </button>
          }
        />
        <div className="form-stack">
          <label>商品名称
            <input value={product} onChange={(event) => setProduct(event.target.value)} />
          </label>
          <label>卖点
            <textarea value={sellingPoints} onChange={(event) => setSellingPoints(event.target.value)} rows={4} />
          </label>
          <label>目标人群
            <select value={audience} onChange={(event) => setAudience(event.target.value)}>
              <option>泛流量</option>
              <option>宝妈</option>
              <option>通勤族</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button className="accent-button" disabled={generating} onClick={() => void generateScripts()}>
            {generating ? "生成中…" : "生成 5 条"}
          </button>
          {generationMessage ? <span className="generation-message">{generationMessage}</span> : null}
        </div>
        {pendingGenerated.length ? (
          <div className="pending-scripts">
            <div className="pending-scripts-head">
              <strong>待确认文案</strong>
              <span>{pendingGenerated.length} 条</span>
            </div>
            <div className="pending-scripts-list">
              {pendingGenerated.map((item) => (
                <div key={item.id} className="pending-script-item">
                  <strong>{item.label}</strong>
                  <p>{item.content}</p>
                  {item.instruction ? <span>{item.instruction}</span> : null}
                </div>
              ))}
            </div>
            <div className="pending-scripts-actions">
              <button className="tool-button" onClick={discardGeneratedScripts}>取消</button>
              <button className="accent-button" onClick={confirmGeneratedScripts}>保存到当前文案组</button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
      ) : (
        <div className="empty-state">还没有直播专场，请先新建直播专场。</div>
      )}
    </div>
  );

  const renderInteractions = () => (
    <div className="management-layout">
      <section className="panel list-panel">
        <PanelHeading
          title="互动回应规则"
          meta="进入 · 礼物 · 关注 · 关键词 · 点赞"
          right={<span className="count-badge">{interactions.filter((item) => item.enabled).length} 启用</span>}
        />
        <div className="interaction-list">
          {interactions.map((item) => (
            <div key={item.id} className={`interaction-row ${item.enabled ? "" : "disabled"}`}>
              <div className="interaction-top">
                <label className="check-line">
                  <input
                    type="checkbox"
                    checked={item.enabled}
                    onChange={(event) => updateInteraction(item.id, { enabled: event.target.checked })}
                  />
                  <strong>{item.name}</strong>
                </label>
                <select
                  value={item.mode}
                  onChange={(event) => updateInteraction(item.id, { mode: event.target.value as InteractionConfig["mode"] })}
                >
                  <option value="queue">排队播报</option>
                  <option value="interrupt">立即插播</option>
                  <option value="pause">活跃暂停</option>
                </select>
              </div>
              <div className="interaction-body">
                <input
                  value={item.template}
                  onChange={(event) => updateInteraction(item.id, { template: event.target.value })}
                />
                {item.id === "keyword" ? (
                  <input
                    className="keyword-input"
                    value={item.keywords}
                    placeholder="关键词，逗号分隔"
                    onChange={(event) => updateInteraction(item.id, { keywords: event.target.value })}
                  />
                ) : null}
              </div>
              <div className="interaction-actions">
                <span>占位符：昵称/礼物/关键词</span>
                <button
                  className="tool-button"
                  disabled={!item.enabled}
                  onClick={() => void playTtsPreview(
                    previewVoiceId,
                    speechReadyText(item.template, "小李", "大火箭", "优惠价"),
                  )}
                >
                  试听回应
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      <section className="panel side-panel">
        <PanelHeading title="播报声音" meta="试听与合成" />
        <div className="form-stack">
          <label>回应音色
            <select value={previewVoiceId} onChange={(event) => setPreviewVoiceId(event.target.value)}>
              {voiceItems.map((voice) => (
                <option key={voice.id} value={voice.id}>{voice.name}</option>
              ))}
            </select>
          </label>
          <label>试听文本
            <textarea value={voiceSynthesisText} onChange={(event) => setVoiceSynthesisText(event.target.value)} rows={5} />
          </label>
        </div>
        <div className="form-actions">
          <button className="accent-button" onClick={() => void playTtsPreview(previewVoiceId, voiceSynthesisText)}>
            合成并播放
          </button>
          {voiceMessage ? <span className="generation-message">{voiceMessage}</span> : null}
        </div>
      </section>
    </div>
  );

  const renderBgm = () => (
    <div className="management-layout">
      <section className="panel list-panel">
        <PanelHeading title="播放歌单" meta="本地真实文件 · 顺序循环" right={<span className="count-badge">{musicItems.length}</span>} />
        <div className="table-list">
          {musicItems.map((track, index) => (
            <div key={track.id} className={`table-row ${index === bgmIndex - 1 ? "selected" : ""}`}>
              <button
                className="mini-play"
                aria-label="播放"
                onClick={() => {
                  setBgmIndex(index + 1);
                  playAudio(track.url, track.title);
                }}
              >
                {index === bgmIndex - 1 && bgmLabel === track.title ? "Ⅱ" : "▶"}
              </button>
              <strong>{track.title}</strong>
              <span>{track.category}</span>
              <time>{track.duration}</time>
              <span className="license-tag">CC0</span>
            </div>
          ))}
        </div>
        <div className="panel-foot">
          <span>{String(bgmIndex).padStart(2, "0")} / {musicItems.length}</span>
          <span>{bgmLabel || "未播放"}</span>
        </div>
      </section>
      <section className="panel side-panel">
        <PanelHeading title="播放控制" meta="背景音量" />
        <div className="volume-block">
          <input
            type="range"
            min={0}
            max={100}
            value={Math.round(bgmVolume * 100)}
            onChange={(event) => setBgmVolume(Number(event.target.value) / 100)}
            aria-label="音量"
          />
          <strong>{Math.round(bgmVolume * 100)}%</strong>
        </div>
        <div className="button-stack">
          <button className="tool-button" onClick={() => moveBgm(-1)}>上一首</button>
          <button className="tool-button" onClick={() => moveBgm(1)}>下一首</button>
          <button className="accent-button full-button" onClick={() => playAudio(musicItems[bgmIndex - 1]?.url ?? "", musicItems[bgmIndex - 1]?.title ?? "")}>
            播放当前曲目
          </button>
        </div>
      </section>
    </div>
  );

  const renderVoices = () => (
    <div className="management-layout">
      <section className="panel list-panel">
        <PanelHeading
          title="音色库"
          meta="CosyVoice v3.5 Flash"
          right={
            <div className="heading-actions">
              <span className="count-badge">{voiceItems.length}</span>
              <button className="gear-button" onClick={() => setTtsConfigOpen(true)} aria-label="语音 API 配置">
                <Settings size={15} />
              </button>
            </div>
          }
        />
        <div className="table-list">
          {voiceItems.length ? voiceItems.map((voice) => (
            <div key={voice.id} className={`table-row voice-table-row ${voice.id === previewVoiceId ? "selected" : ""}`}>
              <button
                className="mini-play"
                aria-label="试听"
                onClick={() => {
                  setPreviewVoiceId(voice.id);
                  playVoiceSample(voice.sample_url, voice.name);
                }}
              >
                ▶
              </button>
              <div className="voice-name">
                <strong>{voice.name}</strong>
                <span>{voice.description || voice.style || "自定义音色"}</span>
              </div>
              <span>{voice.target_model || voiceProviderStatus.model || "cosyvoice-v3.5-flash"}</span>
              <span className="license-tag">{voice.status === "OK" ? "可用" : voice.status || "部署中"}</span>
              <button className="delete-button" onClick={() => void deleteVoiceProfile(voice.id)} aria-label="删除音色">
                <Trash2 size={14} />
              </button>
            </div>
          )) : (
            <div className="empty-state">还没有音色，请先通过公网音频样本创建</div>
          )}
        </div>
      </section>
      <section className="panel side-panel">
        <PanelHeading title="创建克隆音色" meta="CosyVoice 声音复刻" />
        <div className="form-stack">
          <label>音色名称
            <input value={voiceName} onChange={(event) => setVoiceName(event.target.value)} placeholder="例如：小李直播音色" />
          </label>
          <label>音色描述
            <input value={voiceDescription} onChange={(event) => setVoiceDescription(event.target.value)} placeholder="例如：女声、亲和、语速稍快" />
          </label>
          <label>公网样本 URL
            <input
              value={voiceSampleUrl}
              onChange={(event) => setVoiceSampleUrl(event.target.value)}
              placeholder="https://.../voice-sample.mp3"
            />
          </label>
          <input
            ref={voiceFileRef}
            type="file"
            accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg"
            style={{ display: "none" }}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) handleVoiceFileSelected(file);
              event.target.value = "";
            }}
          />
          <span className="field-note">CosyVoice 复刻要求 10-20 秒、无背景音乐、单声道、16kHz 以上，且音频 URL 必须公网可访问。</span>
          {voiceFileName ? <span className="field-note">本地已选择：{voiceFileName}</span> : null}
        </div>
        <div className="button-stack">
          <button
            className="tool-button full-button"
            onClick={() => voiceFileRef.current?.click()}
          >
            选择本地录音试听
          </button>
          <button
            className="accent-button full-button"
            disabled={uploadingVoice}
            onClick={() => void createVoiceProfile()}
          >
            {uploadingVoice ? "提交中…" : "创建克隆音色"}
          </button>
          <button
            className="tool-button full-button"
            disabled={!previewVoiceId}
            onClick={() => void playTtsPreview(previewVoiceId, voiceSynthesisText)}
          >
            用当前音色合成试听
          </button>
          {voiceMessage ? <span className="generation-message">{voiceMessage}</span> : null}
        </div>
        <div className="engine-status">
          <span>千问 API {voiceProviderStatus.cosyvoice ? "已配置" : "未配置"}</span>
          <span>{voiceProviderStatus.model || "cosyvoice-v3.5-flash"}</span>
        </div>
      </section>
    </div>
  );

  const renderLeads = () => (
    <div className="management-layout">
      <section className="panel list-panel">
        <PanelHeading title="获客线索" meta="自动打分 · 实时更新" right={<span className="count-badge">+1</span>} />
        <div className="lead-table">
          <div className="lead-head"><span>昵称</span><span>分数</span><span>等级</span><span>来源</span><span>时间</span></div>
          {LEAD_ITEMS.map((lead) => (
            <div key={lead.id} className="lead-row">
              <strong>{lead.nickname}</strong>
              <b>{lead.score}</b>
              <span className={`level level-${lead.level === "高意向" ? "high" : lead.level === "待跟进" ? "mid" : "low"}`}>{lead.level}</span>
              <span>{lead.source}</span>
              <time>{lead.time}</time>
            </div>
          ))}
        </div>
      </section>
      <section className="panel side-panel">
        <PanelHeading title="推送规则" meta="分级跟进" />
        <div className="rule-list">
          <div><b>高意向 ≥ 50</b><span>即时推送企微</span></div>
          <div><b>待跟进 20-49</b><span>进入跟进列表</span></div>
          <div><b>低意向 10-19</b><span>留档观察</span></div>
        </div>
        <div className="button-stack">
          <button className="accent-button full-button" onClick={exportLeadsCsv}>导出 CSV</button>
        </div>
      </section>
    </div>
  );

  const renderSettings = () => (
    <div className="settings-layout">
      <nav className="settings-tabs">
        {[
          { id: "models", label: "模型设置", meta: "大模型与语音" },
          { id: "live", label: "直播设置", meta: "播放与音频" },
          { id: "platforms", label: "平台接入", meta: "抖音 / 快手 / B站" },
        ].map((item) => (
          <button
            key={item.id}
            className={`settings-tab ${settingsTab === item.id ? "active" : ""}`}
            onClick={() => setSettingsTab(item.id as "models" | "live" | "platforms")}
          >
            <strong>{item.label}</strong>
            <span>{item.meta}</span>
          </button>
        ))}
      </nav>

      <section className="panel settings-content">
        {settingsTab === "models" ? (
          <>
            <PanelHeading title="模型设置" meta="文案大模型与语音合成" />
            <div className="settings-section">
              <h3>AI 文案大模型</h3>
              <div className="form-stack">
                <label>Base URL
                  <input value={llm.baseUrl} onChange={(event) => setLlm((items) => ({ ...items, baseUrl: event.target.value }))} />
                </label>
                <label>模型
                  <input value={llm.model} onChange={(event) => setLlm((items) => ({ ...items, model: event.target.value }))} />
                </label>
                <label>API Key
                  <input
                    type="password"
                    value={llm.apiKey}
                    onChange={(event) => setLlm((items) => ({ ...items, apiKey: event.target.value }))}
                    autoComplete="off"
                  />
                </label>
              </div>
            </div>
            <div className="settings-section">
              <h3>CosyVoice 语音合成</h3>
              <div className="form-stack">
                <label>Base URL
                  <input value={ttsConfig.baseUrl} onChange={(event) => setTtsConfig((items) => ({ ...items, baseUrl: event.target.value }))} />
                </label>
                <label>模型
                  <input value={ttsConfig.model} onChange={(event) => setTtsConfig((items) => ({ ...items, model: event.target.value }))} />
                </label>
                <label>API Key
                  <input
                    type="password"
                    value={ttsConfig.apiKey}
                    onChange={(event) => setTtsConfig((items) => ({ ...items, apiKey: event.target.value }))}
                    placeholder={voiceProviderStatus.cosyvoice ? "已配置，留空不修改" : "输入 DashScope API Key"}
                    autoComplete="off"
                  />
                </label>
              </div>
              <div className="form-actions">
                <button className="accent-button" onClick={() => void saveTtsConfig()}>保存语音配置</button>
              </div>
            </div>
          </>
        ) : null}

        {settingsTab === "live" ? (
          <>
            <PanelHeading title="直播设置" meta="默认播放参数与音频混音" />
            <div className="settings-section">
              <h3>播放参数</h3>
              <div className="form-stack">
                <label>默认播放模式
                  <select value={playbackMode} onChange={(event) => setPlaybackMode(event.target.value as PlaybackMode)}>
                    <option value="sequential">顺序循环</option>
                    <option value="shuffle">随机 · 首尾不重复</option>
                  </select>
                </label>
                <div className="settings-inline-fields">
                  <label>最小停顿（秒）
                    <input type="number" min={0} step={0.5} value={minGapSeconds} onChange={(event) => setMinGapSeconds(Number(event.target.value) || 0)} />
                  </label>
                  <label>最大停顿（秒）
                    <input type="number" min={0} step={0.5} value={maxGapSeconds} onChange={(event) => setMaxGapSeconds(Number(event.target.value) || 0)} />
                  </label>
                </div>
              </div>
            </div>
            <div className="settings-section">
              <h3>音频与 Ducking</h3>
              <div className="form-stack">
                <label>BGM 默认音量：{Math.round(bgmVolume * 100)}%
                  <input type="range" min={0} max={100} value={Math.round(bgmVolume * 100)} onChange={(event) => setBgmVolume(Number(event.target.value) / 100)} />
                </label>
                <label>文案时 BGM 保留比例：{Math.round(duckedRatio * 100)}%
                  <input type="range" min={5} max={100} value={Math.round(duckedRatio * 100)} onChange={(event) => setDuckedRatio(Number(event.target.value) / 100)} />
                </label>
                <div className="toggle-row">
                  <div><strong>Ducking 自动闪避</strong><span>文案前 0.5 秒压低，结束后 0.5 秒恢复</span></div>
                  <button className={`switch ${ducking ? "on" : ""}`} onClick={() => setDucking(!ducking)} aria-label="切换 Ducking"><i /></button>
                </div>
              </div>
            </div>
          </>
        ) : null}

        {settingsTab === "platforms" ? (
          <>
            <PanelHeading title="平台接入" meta="互动信息与人工授权参数" />
            <div className="platform-tabs">
              {(["douyin", "kuaishou", "bilibili"] as PlatformKey[]).map((platform) => (
                <button
                  key={platform}
                  className={`platform-tab ${selectedPlatform === platform ? "active" : ""}`}
                  onClick={() => setSelectedPlatform(platform)}
                >
                  <img src={PLATFORM_ICONS[platform]} alt="" />
                  <strong>{PLATFORM_LABELS[platform]}</strong>
                  <span className={platformStatuses[platform] ? "online" : ""}>
                    {platformStatuses[platform] ? "已连接" : "未连接"}
                  </span>
                </button>
              ))}
            </div>
            <div className="platform-config-pane">
              <div className="form-stack">
                <label>{PLATFORM_LABELS[selectedPlatform]} WebSocket URL
                  <input value={platformSetups[selectedPlatform].wsUrl} onChange={(event) => updatePlatformSetup(selectedPlatform, { wsUrl: event.target.value })} />
                </label>
                <label>Headers JSON
                  <textarea value={platformSetups[selectedPlatform].headersJson} onChange={(event) => updatePlatformSetup(selectedPlatform, { headersJson: event.target.value })} rows={4} />
                </label>
                <label>Query Params JSON
                  <textarea value={platformSetups[selectedPlatform].paramsJson} onChange={(event) => updatePlatformSetup(selectedPlatform, { paramsJson: event.target.value })} rows={4} />
                </label>
                <div className="button-stack">
                  <button className="accent-button full-button" onClick={() => void connectPlatform(selectedPlatform)}>保存并连接</button>
                  <button className="tool-button full-button" onClick={() => void disconnectPlatform(selectedPlatform)}>断开连接</button>
                </div>
              </div>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );

  return (
    <div className="desktop-app">
      <header className="app-titlebar">
        <div className="brand-lockup">
          <span className="brand-glyph">Ai</span>
          <strong>AISounder</strong>
        </div>
        <div className="session-name">{activeScene?.title ?? "直播专场"}</div>
        <div className="titlebar-right">
          <span className={engineReady ? "engine-chip online" : "engine-chip"}>
            <Dot active={engineReady} />
            {engineReady ? "引擎在线" : "预览"}
          </span>
        </div>
      </header>

      <main className="desktop-content">
        <nav className="tab-strip" aria-label="功能页签">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`app-tab ${tab === item.id ? "active" : ""}`}
              onClick={() => {
                if (item.id === "live" && activeSceneId) leaveScene();
                if (item.id === "scripts" && !activeSceneId && scenes[0]) {
                  enterScene(scenes[0], "scripts");
                  return;
                }
                setTab(item.id);
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="view-body">
          {tab === "live" && renderLive()}
          {tab === "scripts" && renderScripts()}
          {tab === "interactions" && renderInteractions()}
          {tab === "bgm" && renderBgm()}
          {tab === "voices" && renderVoices()}
          {tab === "leads" && renderLeads()}
          {tab === "settings" && renderSettings()}
        </div>
        <div className={`audio-dock media-dock ${audioSrc || bgmSrc ? "" : "empty"}`}>
          <div className="media-row">
            <span className="media-kind">语音</span>
            <span className="audio-label">{audioLabel || (running ? "文案语音播放中" : "未播放")}</span>
            <audio
              ref={audioRef}
              src={audioSrc}
              controls={Boolean(audioSrc)}
              autoPlay
              preload="none"
              onEnded={() => {
                if (!runningRef.current) setAudioSrc("");
              }}
            />
            <button className="audio-close" onClick={() => setAudioSrc("")} aria-label="停止语音">
              <X size={15} />
            </button>
          </div>
          <div className="media-row">
            <span className="media-kind">BGM</span>
            <span className="audio-label">{bgmLabel || "未播放"}</span>
            <audio
              ref={bgmAudioRef}
              src={bgmSrc}
              controls={Boolean(bgmSrc)}
              loop
              preload="none"
            />
            <button className="audio-close" onClick={() => setBgmSrc("")} aria-label="停止背景乐">
              <X size={15} />
            </button>
          </div>
        </div>
        <footer className="statusbar">
          <span><Dot active /> 48kHz / 16bit</span>
          <span>BGM {Math.round(bgmVolume * 100)}%</span>
          <span>Ducking {ducking ? "开" : "关"}</span>
          <span className="statusbar-spacer" />
          <span>线索 +1 · 张哥</span>
        </footer>
      </main>

      {llmConfigOpen ? (
        <div className="modal-backdrop" onMouseDown={() => setLlmConfigOpen(false)}>
          <section
            className="config-dialog"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="dialog-heading">
              <div>
                <strong>模型连接</strong>
                <span>Base URL · 模型 · API Key</span>
              </div>
              <button className="dialog-close" onClick={() => setLlmConfigOpen(false)} aria-label="关闭">
                <X size={16} />
              </button>
            </div>
            <div className="form-stack llm-config-modal">
              <label>Base URL
                <input
                  value={llm.baseUrl}
                  onChange={(event) => setLlm((prev) => ({ ...prev, baseUrl: event.target.value }))}
                  placeholder="https://api.example.com/v1"
                />
              </label>
              <label>模型
                <input
                  value={llm.model}
                  onChange={(event) => setLlm((prev) => ({ ...prev, model: event.target.value }))}
                  placeholder="gpt-4o-mini"
                />
              </label>
              <label>API Key
                <input
                  type="password"
                  value={llm.apiKey}
                  onChange={(event) => setLlm((prev) => ({ ...prev, apiKey: event.target.value }))}
                  autoComplete="off"
                />
              </label>
            </div>
            <div className="dialog-actions">
              <button className="tool-button" onClick={() => setLlmConfigOpen(false)}>取消</button>
              <button className="accent-button" onClick={() => setLlmConfigOpen(false)}>保存</button>
            </div>
          </section>
        </div>
      ) : null}

      {ttsConfigOpen ? (
        <div className="modal-backdrop" onMouseDown={() => setTtsConfigOpen(false)}>
          <section
            className="config-dialog"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="dialog-heading">
              <div>
                <strong>千问语音配置</strong>
                <span>DashScope CosyVoice</span>
              </div>
              <button className="dialog-close" onClick={() => setTtsConfigOpen(false)} aria-label="关闭">
                <X size={16} />
              </button>
            </div>
            <div className="form-stack llm-config-modal">
              <label>Base URL
                <input
                  value={ttsConfig.baseUrl}
                  onChange={(event) => setTtsConfig((items) => ({ ...items, baseUrl: event.target.value }))}
                />
              </label>
              <label>模型
                <input
                  value={ttsConfig.model}
                  onChange={(event) => setTtsConfig((items) => ({ ...items, model: event.target.value }))}
                />
              </label>
              <label>API Key
                <input
                  type="password"
                  value={ttsConfig.apiKey}
                  onChange={(event) => setTtsConfig((items) => ({ ...items, apiKey: event.target.value }))}
                  placeholder={voiceProviderStatus.cosyvoice ? "已配置，留空则不修改" : "输入 DashScope API Key"}
                  autoComplete="off"
                />
              </label>
            </div>
            <div className="dialog-actions">
              <button className="tool-button" onClick={() => setTtsConfigOpen(false)}>取消</button>
              <button className="accent-button" onClick={() => void saveTtsConfig()}>保存</button>
            </div>
          </section>
        </div>
      ) : null}

      {sceneModalOpen && draftScene ? (
        <div className="modal-backdrop" onMouseDown={() => setSceneModalOpen(false)}>
          <section
            className="config-dialog scene-dialog"
            role="dialog"
            aria-modal="true"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="dialog-heading">
              <div>
                <strong>新建直播专场</strong>
                <span>步骤 {sceneStep} / 2 · {sceneStep === 1 ? "基础信息" : "配置文案"}</span>
              </div>
              <button className="dialog-close" onClick={() => setSceneModalOpen(false)} aria-label="关闭">
                <X size={16} />
              </button>
            </div>

            {sceneStep === 1 ? (
              <div className="form-stack">
                <label>专场标题
                  <input
                    autoFocus
                    value={draftScene.title}
                    onChange={(event) => updateDraftScene({ title: event.target.value })}
                    placeholder="例如：羽绒服秋冬福利专场"
                  />
                </label>
                <label>专场描述
                  <textarea
                    value={draftScene.description}
                    onChange={(event) => updateDraftScene({ description: event.target.value })}
                    rows={3}
                    placeholder="说明本场商品、活动或目标"
                  />
                </label>
                <div>
                  <span className="field-label">直播平台</span>
                  <div className="platform-checkboxes">
                    {(["douyin", "kuaishou", "bilibili"] as PlatformKey[]).map((platform) => (
                      <label key={platform} className="check-line">
                        <input
                          type="checkbox"
                          checked={draftScene.platforms.includes(platform)}
                          onChange={(event) => {
                            const next = event.target.checked
                              ? [...draftScene.platforms, platform]
                              : draftScene.platforms.filter((item) => item !== platform);
                            updateDraftScene({ platforms: next });
                          }}
                        />
                        <span>{PLATFORM_LABELS[platform]}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="scene-script-editor">
                {draftScene.scripts.map((script, index) => (
                  <div key={script.id} className="scene-script-row">
                    <input
                      value={script.label}
                      onChange={(event) => {
                        const scriptsNext = draftScene.scripts.map((item) =>
                          item.id === script.id ? { ...item, label: event.target.value } : item,
                        );
                        updateDraftScene({ scripts: scriptsNext });
                      }}
                      placeholder={`文案 ${index + 1}`}
                    />
                    <textarea
                      value={script.content}
                      onChange={(event) => {
                        const scriptsNext = draftScene.scripts.map((item) =>
                          item.id === script.id ? { ...item, content: event.target.value } : item,
                        );
                        updateDraftScene({ scripts: scriptsNext });
                      }}
                      rows={3}
                      placeholder="输入本场直播话术"
                    />
                    <button
                      className="delete-button"
                      onClick={() => updateDraftScene({ scripts: draftScene.scripts.filter((item) => item.id !== script.id) })}
                      aria-label="删除文案"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
                <button
                  className="tool-button"
                  onClick={() => updateDraftScene({
                    scripts: [
                      ...draftScene.scripts,
                      { id: `script-${Date.now()}`, label: `文案 ${draftScene.scripts.length + 1}`, weight: 1, content: "" },
                    ],
                  })}
                >
                  + 添加文案
                </button>
              </div>
            )}

            <div className="dialog-actions">
              {sceneStep === 2 ? <button className="tool-button" onClick={() => setSceneStep(1)}>上一步</button> : null}
              {sceneStep === 1 ? (
                <button
                  className="accent-button"
                  onClick={() => {
                    if (draftScene.title.trim()) setSceneStep(2);
                  }}
                >
                  下一步
                </button>
              ) : (
                <>
                  <button className="tool-button" onClick={() => saveDraftScene(false)}>保存</button>
                  <button className="accent-button" onClick={() => saveDraftScene(true)}>去开播</button>
                </>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
