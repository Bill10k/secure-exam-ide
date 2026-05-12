import { useEffect } from "react";

type RestrictionOptions = {
  enabled: boolean;
  onViolation?: (event: string) => void;
};

export const useExamRestrictions = ({
  enabled,
  onViolation,
}: RestrictionOptions) => {

  useEffect(() => {

    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {

      const key = e.key.toLowerCase();

      // Block copy/paste/cut/select-all
      if (
        (e.ctrlKey || e.metaKey) &&
        ["c", "v", "x", "a"].includes(key)
      ) {
        e.preventDefault();

        onViolation?.(`Blocked shortcut: Ctrl+${key.toUpperCase()}`);
      }

      // Block F12
      if (e.key === "F12") {
        e.preventDefault();

        onViolation?.("Blocked F12");
      }

      // Block Ctrl+Shift+I
      if (
        e.ctrlKey &&
        e.shiftKey &&
        key === "i"
      ) {
        e.preventDefault();

        onViolation?.("Blocked DevTools Shortcut");
      }

      // Block Ctrl+U
      if (
        e.ctrlKey &&
        key === "u"
      ) {
        e.preventDefault();

        onViolation?.("Blocked View Source");
      }
    };

    const handleContextMenu = (e: MouseEvent) => {
      e.preventDefault();

      onViolation?.("Right click blocked");
    };

    const handleVisibilityChange = () => {

      if (document.hidden) {

        onViolation?.("Tab/window switch detected");
      }
    };

    const handleBlur = () => {

      onViolation?.("Window lost focus");
    };

    // REGISTER EVENTS

    window.addEventListener("keydown", handleKeyDown);

    window.addEventListener("contextmenu", handleContextMenu);

    document.addEventListener(
      "visibilitychange",
      handleVisibilityChange
    );

    window.addEventListener("blur", handleBlur);

    

    return () => {

      window.removeEventListener(
        "keydown",
        handleKeyDown
      );

      window.removeEventListener(
        "contextmenu",
        handleContextMenu
      );

      document.removeEventListener(
        "visibilitychange",
        handleVisibilityChange
      );

      window.removeEventListener(
        "blur",
        handleBlur
      );
    };

  }, [enabled, onViolation]);
};