import { useEffect, useState } from "react";
import { getCurrent, onOpenUrl, register } from "@tauri-apps/plugin-deep-link";
import { UnlistenFn } from "@tauri-apps/api/event";

function DetectUrl() {
  const [startUrl, setStartUrl] = useState<string | null>(null);
  const [liveUrl, setLiveUrl] = useState<string | null>(null);

  useEffect(() => {
    let unlisten: UnlistenFn | undefined;

    async function setupDeepLinks() {
      await register("proctoride");

      // ✅ Initial deep link
      const startUrls = await getCurrent();

      if (startUrls?.length) {
        setStartUrl(startUrls[0]);
      }

      // ✅ Live deep links
      unlisten = await onOpenUrl((urls) => {
        setLiveUrl(urls[0]);
      });
    }

    setupDeepLinks();

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  return (
    <div>
      <h2>Deep Link Detector</h2>

      <div>
        <strong>Start URL:</strong>{" "}
        {startUrl ? startUrl : "No startup deep link"}
      </div>

      <div>
        <strong>Live URL:</strong>{" "}
        {liveUrl ? liveUrl : "No live deep link yet"}
      </div>
    </div>
  );
}

export default DetectUrl;