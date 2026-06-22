import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { applyBase, loadBase } from "./theme/theme";

applyBase(loadBase());

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
