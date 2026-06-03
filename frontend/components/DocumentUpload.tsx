"use client";

import { useRef, useState } from "react";

interface Props {
  files: File[];
  onChange: (files: File[]) => void;
}

export default function DocumentUpload({ files, onChange }: Props) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const valid = Array.from(incoming).filter((f) =>
      ["image/jpeg", "image/png", "image/webp", "application/pdf"].includes(f.type)
    );
    onChange([...files, ...valid]);
  }

  function remove(index: number) {
    onChange(files.filter((_, i) => i !== index));
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files); }}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          dragging ? "border-plum-500 bg-plum-50" : "border-slate-300 hover:border-plum-400 hover:bg-slate-50"
        }`}
      >
        <p className="text-3xl mb-2">📎</p>
        <p className="text-sm font-medium text-slate-700">Drop files here or click to browse</p>
        <p className="text-xs text-slate-400 mt-1">JPG, PNG, PDF · Max 10MB per file</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((f, i) => (
            <li key={i} className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">{f.type === "application/pdf" ? "📄" : "🖼"}</span>
                <div>
                  <p className="text-sm font-medium text-slate-700">{f.name}</p>
                  <p className="text-xs text-slate-400">{(f.size / 1024).toFixed(0)} KB</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => remove(i)}
                className="text-slate-400 hover:text-red-500 transition-colors text-sm"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
