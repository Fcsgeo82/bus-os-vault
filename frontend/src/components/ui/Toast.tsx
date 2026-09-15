"use client";

import React from "react";
import { CheckCircle, AlertCircle, X } from "lucide-react";

export interface ToastData {
  id: number;
  type: "success" | "error";
  message: string;
}

interface ToastProps {
  toast: ToastData;
  onDismiss: (id: number) => void;
}

export function Toast({ toast, onDismiss }: ToastProps) {
  const isError = toast.type === "error";
  return (
    <div
      role="alert"
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        zIndex: 2000,
        background: "rgba(17, 23, 38, 0.95)",
        backdropFilter: "blur(16px)",
        border: isError ? "1px solid rgba(248, 113, 113, 0.4)" : "1px solid var(--border-glow)",
        borderRadius: "var(--radius-md)",
        boxShadow: "0 15px 40px rgba(0, 0, 0, 0.4)",
        padding: "14px 16px",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        maxWidth: "400px",
        animation: "toastIn 0.25s ease-out forwards",
      }}
    >
      {isError ? (
        <AlertCircle size={18} color="#f87171" style={{ flexShrink: 0 }} />
      ) : (
        <CheckCircle size={18} color="#34d399" style={{ flexShrink: 0 }} />
      )}
      <span style={{ fontSize: "0.85rem", color: "var(--text-primary)", lineHeight: 1.4 }}>
        {toast.message}
      </span>
      <button
        onClick={() => onDismiss(toast.id)}
        style={{
          background: "transparent",
          border: "none",
          color: "var(--text-muted)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          padding: "2px",
          flexShrink: 0,
        }}
        aria-label="Fechar aviso"
      >
        <X size={15} />
      </button>
    </div>
  );
}