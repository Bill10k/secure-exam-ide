import { useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";

type DeepLinkData = {
  sessionId: string;
  examId: string;
} | null;

export function useDeepLink(onReceive: (data: DeepLinkData) => void) {
  useEffect(() => {
    let unlisten: (() => void) | undefined;

    const handleUrl = (urlStr: string) => {
      try {
        console.log("🔥 Deep link:", urlStr);

        const url = new URL(urlStr);

        const sessionId = url.searchParams.get("session_id");
        const examId = url.searchParams.get("exam_id");

        if (!sessionId || !examId) return;

        onReceive({ sessionId, examId });
      } catch (err) {
        console.error("Deep link parse error:", err);
      }
    };

  const setup = async () => {
  // 1. Listen for live events
  unlisten = await listen<string>("deep-link", (event) => {
    handleUrl(event.payload);
  });

  // 2. Immediate fallback (cold start / missed event)
  try {
    const saved = await invoke<string | null>("get_deep_link");

    if (saved) {
      handleUrl(saved);
    }
  } catch (err) {
    console.error("Failed to fetch saved deep link:", err);
  }

  // 3. 🔥 EXTRA SAFETY NET (ADD HERE)
  setTimeout(async () => {
    try {
      const saved = await invoke<string | null>("get_deep_link");

      if (saved) {
        handleUrl(saved);
      }
    } catch (err) {
      console.error("Retry deep link fetch failed:", err);
    }
  }, 500);
};
    setup();

    return () => {
      if (unlisten) unlisten();
    };
  }, [onReceive]);
}