import { useState } from "react";

import { applyBase, loadBase, saveBase } from "../theme/theme";

export function BaseColorPicker() {
  const [base, setBase] = useState(loadBase);

  function onChange(e: React.ChangeEvent<HTMLInputElement>) {
    const hex = e.target.value;
    setBase(hex);
    saveBase(hex);
    applyBase(hex);
  }

  return (
    <span className="swatch" style={{ background: base }}>
      <input type="color" aria-label="Base color" value={base} onChange={onChange} />
    </span>
  );
}
