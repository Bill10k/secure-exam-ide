import { useEffect, useRef } from "react";
import { onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { invoke } from "@tauri-apps/api/core";

type DeepLinkHandler = (sessionId: number, examId: number) => void;

function parseLaunchUrl(urlStr: string) {
  try {
    const url = new URL(urlStr);
    const sessionId = url.searchParams.get("session_id");
    const examId = url.searchParams.get("exam_id");

    if (!sessionId || !examId) {
      console.warn("[useDeepLink] Ignoring launch URL without session/exam ids", urlStr);
      return null;
    }

    const parsedSessionId = Number(sessionId);
    const parsedExamId = Number(examId);

    if (Number.isNaN(parsedSessionId) || Number.isNaN(parsedExamId)) {
      console.warn("[useDeepLink] Ignoring launch URL with invalid ids", urlStr);
      return null;
    }

    return { sessionId: parsedSessionId, examId: parsedExamId };
  } catch (error) {
    console.error("[useDeepLink] Failed to parse launch URL", error);
    return null;
  }
}

export function useDeepLink(onReceive: DeepLinkHandler) {
  const callbackRef = useRef(onReceive);
  const lastHandledUrlRef = useRef<string | null>(null);

  useEffect(() => {
    callbackRef.current = onReceive;
  }, [onReceive]);

  useEffect(() => {
    let isCancelled = false;

    const handleUrl = (urlStr: string) => {
      if (!urlStr) {
        return;
      }

      if (lastHandledUrlRef.current === urlStr) {
        console.log("[useDeepLink] Skipping duplicate launch URL", urlStr);
        return;
      }

      lastHandledUrlRef.current = urlStr;
      const launch = parseLaunchUrl(urlStr);
      if (!launch) {
        return;
      }

      console.log("[useDeepLink] Dispatching launch", launch);
      callbackRef.current(launch.sessionId, launch.examId);
    };

    invoke<string[]>("get_cli_args")
      .then((args) => {
        if (isCancelled) {
          return;
        }

        console.log("[useDeepLink] CLI args", args);
        const urlStr = args.find((arg) => arg.startsWith("proctoride://"));
        if (urlStr) {
          handleUrl(urlStr);
        }
      })
      .catch((error) => {
        console.error("[useDeepLink] Failed to read CLI args", error);
      });

    const unsubscribe = onOpenUrl((urls) => {
      console.log("[useDeepLink] Received open-url event", urls);
      if (urls.length > 0) {
        handleUrl(urls[0]);
      }
    });

    return () => {
      isCancelled = true;
      unsubscribe
        .then((fn) => fn())
        .catch((error) => {
          console.error("[useDeepLink] Failed to unsubscribe open-url listener", error);
        });
    };
  }, []);
}