"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { Message } from "../store/chatStore";
import { Bot, User } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex w-full gap-4 p-4 md:px-6 border-b border-slate-900/40
      ${isUser ? "bg-slate-950/20" : "bg-slate-900/10"}
    `}>
      {/* Avatar Icon */}
      <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 border shadow-md
        ${isUser 
          ? "bg-slate-800 border-slate-700 text-slate-300" 
          : "bg-gradient-to-tr from-violet-600 to-indigo-600 border-indigo-500/30 text-white"
        }
      `}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message Content */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-300">
            {isUser ? "You" : "Dushman AI"}
          </span>
          <span className="text-[10px] text-slate-600 font-medium">
            {message.created_at ? new Date(message.created_at).toLocaleTimeString() : ""}
          </span>
        </div>

        {/* Text Container */}
        <div className="text-slate-300 text-sm leading-relaxed break-words font-normal">
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                h1: ({ children }) => <h1 className="text-lg font-bold text-white mt-4 mb-2">{children}</h1>,
                h2: ({ children }) => <h2 className="text-base font-bold text-white mt-3 mb-2">{children}</h2>,
                h3: ({ children }) => <h3 className="text-sm font-bold text-white mt-2 mb-1">{children}</h3>,
                ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                li: ({ children }) => <li className="text-slate-300">{children}</li>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-violet-500 bg-slate-900/60 pl-3 py-1 my-3 text-slate-400 rounded-r-md">
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
                  const { ref: _ref, style: _style, ...rest } = props;
                  void _ref;
                  void _style;
                  return !isInline ? (
                    <div className="my-4 rounded-xl overflow-hidden border border-slate-800">
                      <div className="bg-slate-900 px-4 py-2 flex items-center justify-between text-slate-400 font-mono text-[10px] border-b border-slate-800">
                        <span>{match[1].toUpperCase()}</span>
                      </div>
                      <SyntaxHighlighter
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ margin: 0, borderRadius: 0, background: "#090d16", padding: "16px" }}
                        {...rest}
                      >
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    </div>
                  ) : (
                    <code className="bg-slate-900/80 text-violet-400 px-1.5 py-0.5 rounded font-mono text-xs border border-slate-800/40" {...props}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {message.content || "_Generating response..._"}
            </ReactMarkdown>
          )}
        </div>

        {/* Model Badge */}
        {!isUser && (message.provider_used || message.model_used) && (
          <div className="flex items-center gap-1.5 pt-1.5">
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
