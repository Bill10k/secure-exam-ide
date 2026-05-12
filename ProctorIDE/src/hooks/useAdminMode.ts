import { useEffect, useState } from "react";

type AdminModeOptions = {
  password: string;
  timeout?: number;
};

export const useAdminMode = ({
  password,
  timeout = 60000,
}: AdminModeOptions) => {

  const [showAdminModal, setShowAdminModal] =
    useState(false);

  const [adminMode, setAdminMode] =
    useState(false);

  const [inputPassword, setInputPassword] =
    useState("");

  const [error, setError] =
    useState("");

  // TRACK SECRET COMBO PRESSES
  const [comboCount, setComboCount] =
    useState(0);

  // HOTKEY DETECTION
  useEffect(() => {

    let resetTimer: number;

    const handleKeyDown = (e: KeyboardEvent) => {

      const isSecretCombo =
        e.ctrlKey &&
        e.shiftKey &&
        e.key.toLowerCase() === "a";

      if (isSecretCombo) {

        e.preventDefault();

        setComboCount((prev) => {

          const next = prev + 1;

          // OPEN MODAL AFTER 3 PRESSES
          if (next >= 3) {

            setShowAdminModal(true);

            return 0;
          }

          return next;
        });

        // RESET AFTER 4 SECONDS
        window.clearTimeout(resetTimer);

        resetTimer = window.setTimeout(() => {

          setComboCount(0);

        }, 4000);
      }
    };

    window.addEventListener(
      "keydown",
      handleKeyDown
    );

    return () => {

      window.removeEventListener(
        "keydown",
        handleKeyDown
      );

      window.clearTimeout(resetTimer);
    };

  }, []);

  // AUTO DISABLE ADMIN MODE
  useEffect(() => {

    if (!adminMode) return;

    const timer = setTimeout(() => {

      setAdminMode(false);

    }, timeout);

    return () => clearTimeout(timer);

  }, [adminMode, timeout]);

  // VALIDATE PASSWORD
  const validateAdmin = () => {

    if (inputPassword === password) {

      setAdminMode(true);

      setShowAdminModal(false);

      setInputPassword("");

      setError("");

    } else {

      setError("Invalid admin password");
    }
  };

  const closeAdminModal = () => {

    setShowAdminModal(false);

    setInputPassword("");

    setError("");
  };

  return {
    adminMode,

    showAdminModal,

    inputPassword,

    setInputPassword,

    validateAdmin,

    closeAdminModal,

    error,

    setAdminMode,
  };
};