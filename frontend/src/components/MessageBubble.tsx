"use client";

import React, { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Message } from "../store/chatStore";
import { Bot, User, Copy, Check, ChevronDown, ChevronRight } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [text]);

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-mono transition-all duration-200 hover:bg-slate-700/50 active:scale-95"
      aria-label={copied ? "Copied" : "Copy code"}
    >
      {copied ? (
        <>
          <Check className="size-3 text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="size-3 text-slate-500" />
          <span className="text-slate-500">Copy</span>
        </>
      )}
    </button>
  );
}

function CodeBlock({ language, children }: { language: string; children: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const code = String(children).replace(/\n$/, "");
  const lineCount = code.split("\n").length;
  const isLongCode = lineCount > 15;

  return (
    <div className="my-4 rounded-xl overflow-hidden border border-slate-800 group/code">
      {/* Code block header */}
      <div className="bg-slate-900/80 px-4 py-2 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2">
          {isLongCode && (
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-0.5 rounded hover:bg-slate-700/50 transition-colors"
              aria-label={collapsed ? "Expand code" : "Collapse code"}
            >
              {collapsed ? (
                <ChevronRight className="size-3 text-slate-500" />
              ) : (
                <ChevronDown className="size-3 text-slate-500" />
              )}
            </button>
          )}
          <span className="text-slate-400 font-mono text-[10px] font-semibold tracking-wider">
            {language.toUpperCase()}
          </span>
          <span className="text-[10px] text-slate-600 font-mono">
            {code.split("\n").length} lines
          </span>
        </div>
        <CopyButton text={code} />
      </div>

      {/* Code block content */}
      <div className={collapsed ? "max-h-20 overflow-hidden relative" : ""}>
        <SyntaxHighlighter
          language={language}
          PreTag="div"
          style={oneDark}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: "#0d1117",
            padding: "16px",
            fontSize: "12px",
            lineHeight: "1.5",
          }}
          showLineNumbers={lineCount > 3}
        >
          {code}
        </SyntaxHighlighter>
        {collapsed && (
          <div className="absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-[#0d1117] to-transparent flex items-end justify-center pb-2">
            <button
              onClick={() => setCollapsed(false)}
              className="text-[10px] text-violet-400 hover:text-violet-300 font-medium transition-colors"
            >
              Show more ({lineCount - 5} lines)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const timestamp = message.created_at ? new Date(message.created_at).toLocaleTimeString() : "";
  const isStreaming = !message.content;

  return (
    <div className={`flex w-full gap-4 p-4 md:px-6 border-b border-slate-900/40 transition-colors duration-300
      ${isUser ? "bg-slate-950/20" : "bg-slate-900/10"}
    `}>
      {/* Avatar Icon */}
      <div className={`size-8 rounded-xl flex items-center justify-center flex-shrink-0 border shadow-md transition-all duration-200
        ${isUser 
          ? "bg-slate-800 border-slate-700 text-slate-300" 
          : "bg-gradient-to-tr from-violet-600 to-indigo-600 border-indigo-500/30 text-white"
        }
      `}>
        {isUser ? <User className="size-4" /> : <Bot className="size-4" />}
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-300">
            {isUser ? "You" : "ChatHub"}
          </span>
          {!isStreaming && (
            <span className="text-[10px] text-slate-600 font-medium" suppressHydrationWarning>
              {timestamp}
            </span>
          )}
        </div>

        {/* Text Container */}
        <div className={`text-slate-300 text-sm leading-relaxed break-words font-normal ${isStreaming ? "streaming-cursor" : ""}`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                h1: ({ children }) => <h1 className="text-lg font-semibold text-white mt-4 mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-base font-semibold text-white mt-3 mb-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-sm font-semibold text-white mt-2 mb-1">{children}</h3>,
                ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="text-slate-300">{children}</li>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-violet-500/40 bg-gradient-to-r from-violet-500/10 via-slate-900/70 to-slate-900/70 px-4 py-3 my-3 text-slate-300 rounded-r-lg">
                    {children}
                  </blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-3 rounded-lg border border-slate-800">
                    <table className="min-w-full divide-y divide-slate-800 text-left text-xs text-slate-300">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-slate-900/80 font-semibold text-slate-200">{children}</thead>,
                th: ({ children }) => <th className="px-4 py-2 border-b border-slate-800">{children}</th>,
                td: ({ children }) => <td className="px-4 py-2 border-b border-slate-900">{children}</td>,
                code: ({ className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match;
                  const { ref: _ref, style: _style, ...codeProps } = props as Record<string, unknown>;
                  return !isInline ? (
                    <CodeBlock language={match[1]}>{String(children)}</CodeBlock>
                  ) : (
                    <code className="bg-slate-900/80 text-violet-400 px-1.5 py-0.5 rounded font-mono text-xs border border-slate-800/40" {...codeProps}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {message.content || "_Generating response…_"}
            </ReactMarkdown>
          )}
        </div>

        {/* Copy message button for assistant responses */}
        {!isUser && message.content && (
          <div className="flex items-center gap-2 pt-1">
            <CopyButton text={message.content} />
          </div>
        )}

        {/* Model Badge */}
        {!isUser && (message.provider_used || message.model_used) && (
          <div className="flex items-center gap-1.5 pt-1">
            {message.provider_used && (
              <span className="text-[9px] uppercase tracking-wider bg-slate-900/80 border border-slate-800/60 text-slate-500 px-2 py-0.5 rounded-full font-semibold">
                {message.provider_used}
              </span>
            )}
            {message.model_used && (
              <span className="text-[9px] bg-slate-900/80 border border-slate-800/60 text-violet-400/80 px-2 py-0.5 rounded-full font-mono">
                {message.model_used.split("/").pop()}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
