"use client";

import { useRef, useState } from "react";
import { UploadCloud, FileText, Image as ImageIcon, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

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
        className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200 ${
          dragging
            ? "border-verdict-violet bg-verdict-violet/5"
            : "border-ivory-line hover:border-verdict-violet/50 hover:bg-ivory-hover"
        }`}
      >
        <UploadCloud size={30} strokeWidth={1.6} className="mx-auto mb-2 text-ink-faint" />
        <p className="text-sm font-medium text-ink">Drop files here or click to browse</p>
        <p className="mt-1 text-xs text-ink-faint">JPG, PNG, PDF · Max 10MB per file</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          className="hidden"
          onChange={(e) => addFiles(e.target.files)}
        />
      </div>

      <AnimatePresence initial={false}>
        {files.length > 0 && (
          <ul className="space-y-2">
            {files.map((f, i) => (
              <motion.li
                key={`${f.name}-${f.size}-${i}`}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-center justify-between rounded-lg border border-ivory-line bg-ivory-head px-4 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  {f.type === "application/pdf"
                    ? <FileText size={18} className="text-verdict-violet" strokeWidth={1.8} />
                    : <ImageIcon size={18} className="text-verdict-violet" strokeWidth={1.8} />}
                  <div>
                    <p className="text-sm font-medium text-ink">{f.name}</p>
                    <p className="text-xs text-ink-faint tnum">{(f.size / 1024).toFixed(0)} KB</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); remove(i); }}
                  className="rounded-md p-1 text-ink-faint transition-colors hover:bg-verdict-red/10 hover:text-verdict-red"
                  aria-label={`Remove ${f.name}`}
                >
                  <X size={16} strokeWidth={2} />
                </button>
              </motion.li>
            ))}
          </ul>
        )}
      </AnimatePresence>
    </div>
  );
}
