import { useCallback, useEffect, useState } from "react";

import { getHome, Home, subscribeEvents } from "../api/client";

export function useHome() {
  const [home, setHome] = useState<Home | null>(null);

  const refresh = useCallback(() => {
    getHome()
      .then(setHome)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const unsubscribe = subscribeEvents((e) => {
      if (e.type === "home_changed") refresh();
    });
    return unsubscribe;
  }, [refresh]);

  return { home, refresh };
}
