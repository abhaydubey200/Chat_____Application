"use client";

import React, { useState, useRef, useEffect } from "react";
import { useChatStore } from "../store/chatStore";
import MessageBubble from "./MessageBubble";
import ModelSelector from "./ModelSelector";
import { 
  Send, 
  Square, 
  ArrowDown, 
  Bot, 
  Sparkles,
  Zap,
  Cpu,
  AlertCircle
} from "lucide-react";

export default function ChatWindow() {
  const {
    messages,
    isGenerating,
    sendMessage,
    stopGeneration,
    currentConversationId,
    conversations,
    modelType,
    error
  } = useChatStore();

  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  // Find current conversation title
  const activeConversation = conversations.find(c => c.id === currentConversationId);
  const chatTitle = activeConversation ? activeConversation.title : "New Conversation";

  // Scroll to bottom helper
  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  // Scroll automatically when messages change or streaming is active
  useEffect(() => {
    scrollToBottom(isGenerating ? "auto" : "smooth");
  }, [messages.length, isGenerating]);

  // Monitor scroll height to show/hide "scroll to bottom" button
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Show button if user is scrolled up by more than 400px
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 400);
  };

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isGenerating) return;
    
    const messageToSend = input.trim();
    setInput(""); // Clear input immediately
    await sendMessage(messageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Get active model details for header
  const getModelLabel = () => {
    switch (modelType) {
      case "fast":
        return { label: "Fast Model", icon: Zap, color: "text-amber-400" };
      case "reasoning":
        return { label: "Reasoning Model", icon: Cpu, color: "text-cyan-400" };
      case "default":
      default:
        return { label: "Standard Model", icon: Sparkles, color: "text-violet-400" };
    }
  };

  const modelInfo = getModelLabel();
  const ModelIcon = modelInfo.icon;

  const quickPrompts = [
    { title: "Optimize a SQL query", text: "How do I optimize a PostgreSQL query that has multiple JOINs and slow response times?" },
    { title: "Explain SSE", text: "Explain Server-Sent Events (SSE) and how to handle them on the client side in a React app." },
    { title: "Design a DAG pipeline", text: "How would I structure a directed acyclic graph (DAG) for a Python data integration pipeline?" }
  ];

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-900/10 text-slate-100 overflow-hidden relative">
      {/* Header */}
      <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md flex items-center justify-between px-6 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-col min-w-0">
            <h2 className="text-sm font-semibold text-white truncate">
              {chatTitle}
            </h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <ModelIcon className={`w-3 h-3 ${modelInfo.color}`} />
              <span className="text-[10px] text-slate-400 font-medium font-mono">
                {modelInfo.label}
              </span>
            </div>
          </div>
        </div>

        {/* Right header actions */}
        <div className="flex items-center gap-2">
          {isGenerating && (
            <span className="flex items-center gap-1.5 text-xs text-violet-400 bg-violet-950/20 border border-violet-900/30 px-2.5 py-1 rounded-full font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
              Thinking...
            </span>
          )}
        </div>
      </header>

      {/* Chat Messages */}
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto custom-scrollbar flex flex-col"
      >
        {messages.length === 0 ? (
          /* Empty / Welcome State */
          <div className="flex-1 flex flex-col justify-center items-center px-4 py-12 max-w-3xl mx-auto w-full">
            <div className="p-4 rounded-2xl bg-gradient-to-tr from-violet-600 to-indigo-600 shadow-xl shadow-violet-600/10 mb-6 animate-bounce-subtle">
              <Bot className="w-8 h-8 text-white" />
            </div>
            
            <h1 className="text-2xl md:text-3xl font-extrabold text-white text-center bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
              What can I help you build today?
            </h1>
            <p className="text-slate-400 text-xs md:text-sm text-center mt-2 mb-8 max-w-md">
              Dushman AI orchestrates state-of-the-art LLMs to deliver code, analysis, and reasoning on demand. Select a model below to begin.
            </p>

            {/* Model Selector Panel */}
            <div className="w-full mb-8">
              <ModelSelector />
            </div>

            {/* Quick Prompts */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full mt-4">
              {quickPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => setInput(prompt.text)}
                  className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/20 hover:border-slate-700/60 hover:bg-slate-900/50 transition-all duration-300 text-left group cursor-pointer"
                >
                  <span className="text-xs font-semibold text-slate-300 group-hover:text-white block">
                    {prompt.title}
                  </span>
                  <span className="text-[11px] text-slate-500 line-clamp-2 mt-1 block">
                    {prompt.text}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Messages List */
          <div className="flex-1 pb-24">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            
            {/* Error display */}
            {error && (
              <div className="flex gap-4 p-4 md:px-6 bg-rose-950/10 border-b border-rose-900/20 text-rose-300 items-start">
                <div className="w-8 h-8 rounded-xl bg-rose-950/40 border border-rose-900/30 flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-4 h-4 text-rose-400" />
                </div>
                <div className="flex-1 space-y-1">
                  <p className="text-xs font-bold text-rose-400">System Error</p>
                  <p className="text-xs leading-relaxed">{error}</p>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Floating Scroll to Bottom Button */}
      {showScrollBtn && (
        <button
          onClick={() => scrollToBottom()}
          className="absolute bottom-28 right-6 p-2 rounded-full border border-slate-800 bg-slate-950/80 text-slate-400 hover:text-white hover:bg-slate-900 shadow-xl backdrop-blur transition-all duration-200 cursor-pointer z-10 hover:scale-105"
        >
          <ArrowDown className="w-4 h-4" />
        </button>
      )}

      {/* Input Form Panel */}
      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent pt-12 z-10 pointer-events-none">
        <div className="max-w-3xl mx-auto w-full pointer-events-auto">
          <form onSubmit={handleSend} className="relative rounded-2xl border border-slate-800/80 bg-slate-950/80 backdrop-blur-md shadow-2xl p-1 focus-within:border-slate-700/80 transition-all duration-300">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message Dushman AI..."
              rows={1}
              className="w-full resize-none bg-transparent py-3.5 pl-4 pr-16 text-sm text-slate-200 placeholder-slate-500 focus:outline-none max-h-36 custom-scrollbar"
              style={{ height: "auto", minHeight: "48px" }}
            />

            <div className="absolute right-2.5 bottom-2 flex items-center gap-2">
              {isGenerating ? (
                <button
                  type="button"
                  onClick={stopGeneration}
                  className="p-2 rounded-xl text-rose-400 hover:text-rose-300 bg-rose-950/20 border border-rose-900/30 hover:bg-rose-950/30 transition-all duration-200 cursor-pointer shadow-lg shadow-rose-950/10"
                  title="Stop Generating"
                >
                  <Square className="w-4 h-4 fill-rose-400" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="p-2 rounded-xl text-white bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 shadow-md shadow-violet-600/10 disabled:opacity-30 disabled:hover:from-violet-600 disabled:hover:to-indigo-600 transition-all duration-200 disabled:cursor-not-allowed cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </form>
          
          <div className="text-[10px] text-center text-slate-600 mt-2 font-medium">
            Dushman AI can make mistakes. Verify important code and data.
          </div>
        </div>
      </div>
    </div>
  );
}
