"use client";

import React, { useEffect, useState } from "react";
import { Plus, X } from "lucide-react";

interface MultiInputFieldProps {
  label: string;
  values: string[];
  placeholder?: string;
  maxItems?: number;
  validate?: (value: string) => string | null;
  onChange: (values: string[]) => void;
  hint?: string;
}

export const MultiInputField: React.FC<MultiInputFieldProps> = ({
  label,
  values,
  placeholder,
  maxItems = 2,
  validate,
  onChange,
  hint,
}) => {
  const [errors, setErrors] = useState<(string | null)[]>(values.map(() => null));

  useEffect(() => {
    setErrors((prev) => {
      const next = [...prev];
      while (next.length < values.length) next.push(null);
      return next.slice(0, values.length);
    });
  }, [values.length]);

  const handleChange = (index: number, value: string) => {
    const next = [...values];
    next[index] = value;
    onChange(next);
    setErrors((prev) => {
      const copy = [...prev];
      copy[index] = null;
      return copy;
    });
  };

  const handleAdd = () => {
    onChange([...values, ""]);
  };

  const handleRemove = (index: number) => {
    onChange(values.filter((_, i) => i !== index));
  };

  const handleBlur = (index: number) => {
    if (!validate) return;
    const error = validate(values[index] ?? "");
    setErrors((prev) => {
      const copy = [...prev];
      copy[index] = error;
      return copy;
    });
  };

  return (
    <div>
      <label
        style={{
          display: "block",
          fontSize: "0.82rem",
          color: "var(--text-secondary)",
          marginBottom: "6px",
          fontWeight: 600,
        }}
      >
        {label}
      </label>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {values.map((value, index) => (
          <div key={index}>
            <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
              <input
                type="text"
                className="input-glass"
                placeholder={placeholder}
                value={value}
                onChange={(e) => handleChange(index, e.target.value)}
                onBlur={() => handleBlur(index)}
                style={{ flex: 1 }}
              />
              {values.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemove(index)}
                  aria-label={`Remover ${index + 1}º item`}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--text-muted)",
                    cursor: "pointer",
                    padding: "4px",
                    flexShrink: 0,
                  }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
            {errors[index] && (
              <span style={{ display: "block", fontSize: "0.72rem", color: "#f87171", marginTop: "4px" }}>
                {errors[index]}
              </span>
            )}
          </div>
        ))}
      </div>
      {values.length < maxItems ? (
        <button
          type="button"
          onClick={handleAdd}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            background: "none",
            border: "none",
            color: "var(--accent-cyan)",
            cursor: "pointer",
            fontSize: "0.78rem",
            marginTop: "8px",
            padding: 0,
          }}
        >
          <Plus size={14} />
          Adicionar
        </button>
      ) : (
        <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "8px" }}>
          Máximo de {maxItems} itens.
        </p>
      )}
      {hint && <p style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "4px" }}>{hint}</p>}
    </div>
  );
};