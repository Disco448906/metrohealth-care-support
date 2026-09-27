import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Send, Bot, User, HelpCircle, ShieldCheck, Ticket, RefreshCw } from 'lucide-react';
import api from '../services/api';

const createConversationId = (userId) => {
  const id = `conv_${globalThis.crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`}`;
  sessionStorage.setItem(`chat_conversation_id_${userId || 'guest'}`, id);
  return id;
};

const getConversationId = (userId) => sessionStorage.getItem(`chat_conversation_id_${userId || 'guest'}`) || createConversationId(userId);

// Lightweight markdown → React renderer (no external dependency)
const renderMarkdown = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Headings: ### ## #
    const headingMatch = line.match(/^(#{1,3})\s+(.*)/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = headingMatch[2];
      const Tag = `h${level + 2}`; // h3→h5, h2→h4, h1→h3 (keeps visual hierarchy reasonable)
      const sizes = { 1: 'text-base font-bold', 2: 'text-sm font-bold', 3: 'text-sm font-semibold' };
      elements.push(
        <Tag key={i} className={`${sizes[level]} mt-2 mb-1`}>
          {inlineMarkdown(content)}
        </Tag>
      );
      i++;
      continue;
    }

    // Bullet list items: * or -
    if (/^[*-]\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^[*-]\s+/.test(lines[i])) {
        listItems.push(
          <li key={i} className="ml-4 list-disc">{inlineMarkdown(lines[i].replace(/^[*-]\s+/, ''))}</li>
        );
        i++;
      }
      elements.push(<ul key={`ul-${i}`} className="my-1 space-y-0.5">{listItems}</ul>);
      continue;
    }

    // Numbered list items: 1. 2. etc.
    if (/^\d+\.\s+/.test(line)) {
      const listItems = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        listItems.push(
          <li key={i} className="ml-4 list-decimal">{inlineMarkdown(lines[i].replace(/^\d+\.\s+/, ''))}</li>
        );
        i++;
      }
      elements.push(<ol key={`ol-${i}`} className="my-1 space-y-0.5">{listItems}</ol>);
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(line.trim())) {
      elements.push(<hr key={i} className="my-2 border-slate-200" />);
      i++;
      continue;
    }

    // Empty line → spacing
    if (line.trim() === '') {
      elements.push(<div key={i} className="h-2" />);
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={i} className="leading-relaxed">{inlineMarkdown(line)}</p>
    );
    i++;
  }

  return elements;
};

// Handle inline formatting: **bold**, *italic*, `code`
const inlineMarkdown = (text) => {
  if (!text) return null;
  const parts = [];
  const regex = /\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1]) {
      parts.push(<strong key={match.index} className="font-semibold">{match[1]}</strong>);
    } else if (match[2]) {
      parts.push(<em key={match.index}>{match[2]}</em>);
    } else if (match[3]) {
      parts.push(<code key={match.index} className="bg-slate-100 px-1 rounded text-xs font-mono">{match[3]}</code>);
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length === 1 && typeof parts[0] === 'string' ? parts[0] : parts;
};

export const ChatPage = () => {
  const { user } = useAuth();
  const [conversationId, setConversationId] = useState(() => getConversationId(user?.id));
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'ai',
      text: `Hello ${user?.name || 'there'} — I’m your MetroHealth care assistant. I can help with appointments, your reports and prescriptions, bills, and questions for our team. What can I help you with today?`,
      intent: 'greeting',
      severity: 'LOW',
      action: 'AUTO_RESOLVE',
      suggested: [
        "I want to book an appointment.",
        "Show me available doctors.",
        "What are the hospital timings?",
        "I want to reschedule my appointment.",
        "Show my next appointment",
        "Show my health reports",
        "What medicines were prescribed to me?",
        "Show my bills",
        "I have a billing question",
        "I need help with a medical concern"
      ]
    }
  ]);

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  useEffect(() => {
    let active = true;
    api.get('/api/chat/history', { params: { conversation_id: conversationId } })
      .then(({ data }) => {
        if (!active || !data?.length) return;
        const restored = data.flatMap((turn, index) => [
          { id: `user-${index}-${turn.created_at}`, sender: 'user', text: turn.user_message },
          { id: `assistant-${index}-${turn.created_at}`, sender: 'ai', text: turn.ai_response, intent: turn.intent, category: turn.category, severity: turn.severity, action: turn.action, ticket_id: turn.ticket_id, department: turn.department, suggested: [] },
        ]);
        setMessages((current) => current.length === 1 ? [current[0], ...restored] : current);
      })
      .catch(() => {});
    return () => { active = false; };
  }, [conversationId]);

  const handleSend = async (textToSend) => {
    const query = textToSend || input;
    if (!query || !query.trim() || loading) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const res = await api.post('/api/chat', {
        message: query,
        conversation_id: conversationId
      });
      const aiResponse = res.data;

      const aiMsg = {
        id: Date.now() + 1,
        sender: 'ai',
        text: aiResponse.message,
        intent: aiResponse.intent,
        category: aiResponse.category,
        severity: aiResponse.severity,
        priority: aiResponse.priority,
        action: aiResponse.action,
        ticket_id: aiResponse.ticket_id,
        department: aiResponse.department,
        rag_used: aiResponse.rag_used,
        suggested: aiResponse.suggested_actions || []
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          sender: 'ai',
          text: 'Sorry, I encountered a communication error with our server. Please try again.',
          severity: 'LOW',
          action: 'AUTO_RESOLVE'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 h-[calc(100vh-5rem)] flex flex-col">
      
      {/* Header */}
      <div className="bg-white rounded-t-2xl p-4 border border-slate-200 border-b-0 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-medical-600 to-medical-500 text-white flex items-center justify-center shadow-md">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-bold text-slate-900 text-base flex items-center space-x-1.5">
              <span>MetroHealth Care Assistant</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-semibold rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Ready to help
              </span>
            </h2>
            <p className="text-xs text-slate-500">Appointments, records and support in one conversation</p>
          </div>
        </div>

        <button
          onClick={() => {
            setMessages([messages[0]]);
            setConversationId(createConversationId(user?.id));
          }}
          className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors text-xs flex items-center space-x-1"
          title="Reset Conversation"
        >
          <RefreshCw className="w-4 h-4" />
          <span className="hidden sm:inline">Reset</span>
        </button>
      </div>

      <div className="bg-white border-x border-slate-200 px-4 py-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-600">
        <ShieldCheck className="w-4 h-4 text-emerald-600" />
        <span>Your chat is connected to your patient account. Reports and prescriptions are visible to you and your doctor.</span>
      </div>

      {/* Messages Scroll Container */}
      <div className="flex-1 bg-slate-50 border border-slate-200 p-4 sm:p-6 overflow-y-auto space-y-6">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${
              msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0 shadow-sm ${
                msg.sender === 'user' ? 'bg-slate-700' : 'bg-medical-600'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={`max-w-2xl space-y-2 ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
              
              {/* Message Box */}
              <div
                className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-medical-600 text-white rounded-tr-none whitespace-pre-wrap'
                    : msg.action === 'CRITICAL_ESCALATION'
                    ? 'bg-rose-50 text-rose-900 border-2 border-rose-300 rounded-tl-none font-medium'
                    : 'bg-white text-slate-800 border border-slate-200 rounded-tl-none'
                }`}
              >
                {msg.sender === 'user' ? msg.text : renderMarkdown(msg.text)}
              </div>

              {/* Ticket Created Notification Banner */}
              {msg.ticket_id && (
                  <div className={`rounded-xl p-3 flex items-center justify-between gap-3 text-xs font-semibold shadow-sm ${msg.department === 'Clinical Review' ? 'bg-rose-50 border border-rose-200 text-rose-900' : 'bg-sky-50 border border-sky-200 text-sky-900'}`}>
                  <div className="flex items-center space-x-2">
                    <Ticket className="w-4 h-4" />
                    <span>{msg.department === 'Clinical Review' ? 'Sent to a doctor' : 'Sent to the support team'} · <strong className="font-mono">{msg.ticket_id}</strong></span>
                  </div>
                  <span className="text-[10px]">Ask me for updates</span>
                </div>
              )}

              {/* Suggested Questions */}
              {msg.suggested && msg.suggested.length > 0 && (
                <div className="pt-2">
                  <span className="text-[11px] font-semibold text-slate-400 block mb-1.5 flex items-center space-x-1">
                    <HelpCircle className="w-3 h-3 text-slate-400" />
                    <span>You can also ask me</span>
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.suggested.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(q)}
                        disabled={loading}
                        className="px-3 py-1 bg-white hover:bg-medical-50 text-slate-700 hover:text-medical-700 border border-slate-200 hover:border-medical-300 rounded-full text-xs transition-colors font-medium text-left"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

            </div>
          </div>
        ))}

        {/* Typing Indicator */}
        {loading && (
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-full bg-medical-600 text-white flex items-center justify-center text-xs">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-white border border-slate-200 px-4 py-3 rounded-2xl rounded-tl-none text-slate-500 text-xs flex items-center space-x-2">
              <div className="w-2 h-2 bg-medical-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-medical-500 rounded-full animate-bounce [animation-delay:0.2s]"></div>
              <div className="w-2 h-2 bg-medical-500 rounded-full animate-bounce [animation-delay:0.4s]"></div>
              <span className="ml-2 font-medium">Preparing a response…</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="bg-white rounded-b-2xl p-4 border border-slate-200 border-t-0 shadow-sm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about an appointment, report, bill or concern…"
            className="flex-1 bg-slate-50 border border-slate-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-medical-500 focus:bg-white"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-medical-600 hover:bg-medical-700 text-white rounded-xl shadow-md transition-colors font-semibold flex items-center space-x-1.5 disabled:opacity-50 text-sm"
          >
            <span>Send</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
};
