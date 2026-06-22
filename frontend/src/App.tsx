import { useEffect, useState } from "react";

import { getHome, Home } from "./api/client";
import { BaseColorPicker } from "./components/BaseColorPicker";

export default function App() {
  const [home, setHome] = useState<Home | null>(null);

  useEffect(() => {
    getHome().then(setHome).catch(() => setHome(null));
  }, []);

  return (
    <main style={{ background: "var(--bg)", color: "var(--text)", minHeight: "100vh" }}>
      <header style={{ display: "flex", justifyContent: "space-between", padding: 12 }}>
        <span>PKB</span>
        <BaseColorPicker />
      </header>
      {home && (
        <>
          <section aria-label="ongoing">
            {home.ongoing.map((t) => (
              <div key={t.id}>{t.title}</div>
            ))}
          </section>
          <section aria-label="goals">
            {home.goals.map((t) => (
              <div key={t.id}>{t.title}</div>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
