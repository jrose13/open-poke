import { useState, useEffect, useRef, useCallback } from 'react';
import { User } from 'lucide-react';
import { ConnectionSetup } from './components/ConnectionSetup';
import { ChatBubble } from './components/ChatBubble';
import { TypingIndicator } from './components/TypingIndicator';
import { MessageInput } from './components/MessageInput';
import { apiClient, API_BASE_URL } from './api';
import type { ApiError } from './api';
import type { Message } from './types';

const SESSION_RESET_MESSAGE = "Our secure session restarted, so let's reconnect before I keep helping.";

const isSessionExpiredError = (error: unknown): error is ApiError => {
  const candidate = error as ApiError | undefined;
  return typeof candidate?.status === 'number' && candidate.status === 404;
};

function App() {
  const [userId, setUserId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const [isWebsocketReady, setIsWebsocketReady] = useState(false);
  const isWebsocketReadyRef = useRef(false);
  const conversationPollingRef = useRef<number | null>(null);
  const conversationPollingAttemptsRef = useRef(0);
  const messagePollingRefs = useRef<Record<string, { attempts: number; timeoutId: number | null }>>({});

  const mapConversationsToMessages = useCallback((conversations: any[]): Message[] => {
    if (!Array.isArray(conversations)) {
      return [];
    }

    return conversations.map((conv: any, index: number) => {
      const timestamp = conv.timestamp ? new Date(conv.timestamp) : new Date();
      return {
        id: conv.id ?? `conv_${index}_${timestamp.getTime()}`,
        content: conv.message ?? '',
        sender: conv.type === 'agent' ? 'agent' : 'user',
        timestamp,
      };
    });
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('poke_messages', JSON.stringify(messages));
    } else {
      localStorage.removeItem('poke_messages');
    }
  }, [messages]);

  useEffect(() => {
    localStorage.setItem('poke_is_typing', JSON.stringify(isTyping));
  }, [isTyping]);

  useEffect(() => {
    localStorage.setItem('poke_is_loading', JSON.stringify(isLoading));
  }, [isLoading]);

  useEffect(() => {
    const savedUserId = localStorage.getItem('poke_user_id');
    const savedMessages = localStorage.getItem('poke_messages');
    const savedIsTyping = localStorage.getItem('poke_is_typing');
    const savedIsLoading = localStorage.getItem('poke_is_loading');

    if (!savedUserId) {
      return;
    }

    setUserId(savedUserId);

    if (savedMessages) {
      try {
        const parsed = JSON.parse(savedMessages).map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(parsed);
      } catch (error) {
        console.error('Failed to parse saved messages:', error);
        localStorage.removeItem('poke_messages');
      }
    }

    if (savedIsTyping) {
      try {
        setIsTyping(JSON.parse(savedIsTyping));
      } catch (error) {
        console.error('Failed to parse saved typing state:', error);
        localStorage.removeItem('poke_is_typing');
      }
    }

    if (savedIsLoading) {
      try {
        setIsLoading(JSON.parse(savedIsLoading));
      } catch (error) {
        console.error('Failed to parse saved loading state:', error);
        localStorage.removeItem('poke_is_loading');
      }
    }

  }, []);

  useEffect(() => {
    isWebsocketReadyRef.current = isWebsocketReady;
  }, [isWebsocketReady]);

  const clearConversationPolling = useCallback(() => {
    if (conversationPollingRef.current !== null) {
      window.clearTimeout(conversationPollingRef.current);
      conversationPollingRef.current = null;
    }
    conversationPollingAttemptsRef.current = 0;
  }, []);

  const clearMessagePolling = useCallback((messageId?: string) => {
    if (messageId) {
      const entry = messagePollingRefs.current[messageId];
      if (entry?.timeoutId !== null) {
        window.clearTimeout(entry.timeoutId);
      }
      delete messagePollingRefs.current[messageId];
      return;
    }

    Object.keys(messagePollingRefs.current).forEach(key => {
      const entry = messagePollingRefs.current[key];
      if (entry?.timeoutId !== null) {
        window.clearTimeout(entry.timeoutId);
      }
    });
    messagePollingRefs.current = {};
  }, []);

  const clearStoredState = useCallback((includeUser = false) => {
    localStorage.removeItem('poke_messages');
    localStorage.removeItem('poke_is_typing');
    localStorage.removeItem('poke_is_loading');
    if (includeUser) {
      localStorage.removeItem('poke_user_id');
    }
  }, []);

  const resetSession = useCallback((notice: string = SESSION_RESET_MESSAGE) => {
    clearStoredState(true);
    clearConversationPolling();
    clearMessagePolling();
    setMessages([]);
    setIsTyping(false);
    setIsLoading(false);
    setIsWebsocketReady(false);
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
    setUserId(null);
    setSessionNotice(notice);
  }, [clearConversationPolling, clearMessagePolling, clearStoredState]);

  const handleDisconnect = () => {
    localStorage.removeItem('poke_user_id');
    clearStoredState();
    clearConversationPolling();
    clearMessagePolling();
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
    setIsWebsocketReady(false);
    setUserId(null);
    setMessages([]);
    setIsTyping(false);
    setIsLoading(false);
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const shouldReset = params.get('reset');

    if (shouldReset) {
      resetSession();
      params.delete('reset');
      const newSearch = params.toString();
      const newUrl = `${window.location.origin}${window.location.pathname}${newSearch ? `?${newSearch}` : ''}${window.location.hash}`;
      window.history.replaceState({}, '', newUrl);
    }
  }, [resetSession]);

  const handleConnectionEstablished = (newUserId: string) => {
    clearStoredState();
    setMessages([]);
    setIsTyping(false);
    setIsLoading(false);
    setSessionNotice(null);
    clearConversationPolling();
    clearMessagePolling();
    setIsWebsocketReady(false);

    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }

    setUserId(newUserId);
    localStorage.setItem('poke_user_id', newUserId);
  };

  const startConversationPolling = useCallback(
    (userIdToPoll: string) => {
      if (!userIdToPoll) {
        return;
      }

      clearConversationPolling();

      const maxAttempts = 24;

      const poll = async () => {
        if (isWebsocketReadyRef.current) {
          clearConversationPolling();
          return;
        }

        try {
          const conversations = await apiClient.getUserConversations(userIdToPoll);
          const conversationList = conversations?.conversations ?? [];
          if (Array.isArray(conversationList) && conversationList.length > 0) {
            const backendMessages = mapConversationsToMessages(conversationList);
            setMessages(backendMessages);
            setIsTyping(false);
            clearConversationPolling();
            return;
          }
        } catch (error) {
          console.error('Conversation polling failed:', error);
          if (isSessionExpiredError(error)) {
            resetSession();
            return;
          }
        }

        conversationPollingAttemptsRef.current += 1;
        if (conversationPollingAttemptsRef.current < maxAttempts) {
          conversationPollingRef.current = window.setTimeout(poll, 5000);
        } else {
          clearConversationPolling();
          setIsTyping(false);
          setMessages([
            {
              id: 'msg_fallback',
              content:
                "I'm still analyzing your data. This might take a moment as I research your Gmail and web presence thoroughly.",
              sender: 'agent',
              timestamp: new Date(),
            },
          ]);
        }
      };

      poll();
    },
    [clearConversationPolling, mapConversationsToMessages, resetSession],
  );

  const startMessagePolling = useCallback(
    (messageId: string) => {
      if (!messageId) {
        return;
      }

      if (messagePollingRefs.current[messageId]?.timeoutId !== null) {
        return;
      }

      messagePollingRefs.current[messageId] = { attempts: 0, timeoutId: null };
      const maxAttempts = 30;

      const poll = async () => {
        if (isWebsocketReadyRef.current) {
          clearMessagePolling(messageId);
          return;
        }

        try {
          const responseData = await apiClient.getMessageResponse(messageId);

          if (responseData.status === 'completed') {
            const agentMessage: Message = {
              id: `msg_${Date.now()}`,
              content: responseData.response,
              sender: 'agent',
              timestamp: new Date(),
            };

            setMessages(prev => [...prev, agentMessage]);
            setIsTyping(false);
            clearMessagePolling(messageId);
            return;
          }

          if (responseData.status === 'error') {
            const errorMessage: Message = {
              id: `msg_${Date.now()}`,
              content: 'Sorry, I encountered an error processing your message.',
              sender: 'agent',
              timestamp: new Date(),
            };

            setMessages(prev => [...prev, errorMessage]);
            setIsTyping(false);
            clearMessagePolling(messageId);
            return;
          }
        } catch (error) {
          console.error('Failed to poll for response:', error);
          if (isSessionExpiredError(error)) {
            clearMessagePolling(messageId);
            resetSession();
            return;
          }
        }

        const entry = messagePollingRefs.current[messageId];
        if (!entry) {
          return;
        }

        entry.attempts += 1;
        if (entry.attempts < maxAttempts) {
          entry.timeoutId = window.setTimeout(poll, 5000);
        } else {
          clearMessagePolling(messageId);
          setIsTyping(false);
          const timeoutMessage: Message = {
            id: 'msg_timeout',
            content: "I'm taking longer than usual to respond. Please try your message again.",
            sender: 'agent',
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, timeoutMessage]);
        }
      };

      poll();
    },
    [clearMessagePolling, resetSession],
  );


  const handleSendMessage = async (content: string) => {
    if (!userId) {
      return;
    }

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      content,
      sender: 'user',
      timestamp: new Date(),
      status: 'sending',
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const result = await apiClient.sendMessage(userId, content);

      setMessages(prev =>
        prev.map(msg =>
          msg.id === userMessage.id ? { ...msg, status: 'sent' as const } : msg,
        ),
      );

      setIsTyping(true);
      if (!isWebsocketReadyRef.current && result?.message_id) {
        startMessagePolling(result.message_id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);

      if (isSessionExpiredError(error)) {
        resetSession();
        return;
      }

      setMessages(prev =>
        prev.map(msg =>
          msg.id === userMessage.id ? { ...msg, status: 'failed' as const } : msg,
        ),
      );
      setIsTyping(false);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    if (!userId) {
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
      setIsWebsocketReady(false);
      clearConversationPolling();
      clearMessagePolling();
      return;
    }

    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }

    let cancelled = false;

    const resolveWebsocketUrl = () => {
      try {
        const baseUrl = new URL(API_BASE_URL);
        const wsProtocol = baseUrl.protocol === 'https:' ? 'wss:' : 'ws:';
        const basePath = baseUrl.pathname.replace(/\/$/, '');
        return `${wsProtocol}//${baseUrl.host}${basePath}/ws/users/${encodeURIComponent(userId)}`;
      } catch {
        const origin = window.location.origin;
        const wsOrigin = origin.startsWith('https://')
          ? origin.replace('https://', 'wss://')
          : origin.replace('http://', 'ws://');
        const basePath = API_BASE_URL.startsWith('/') ? API_BASE_URL : `/${API_BASE_URL}`;
        const trimmed = basePath === '/' ? '' : basePath.replace(/\/$/, '');
        return `${wsOrigin}${trimmed}/ws/users/${encodeURIComponent(userId)}`;
      }
    };

    try {
      const wsUrl = resolveWebsocketUrl();
      const websocket = new WebSocket(wsUrl);
      websocketRef.current = websocket;

      websocket.onopen = () => {
        if (cancelled) {
          return;
        }
        setIsWebsocketReady(true);
        clearConversationPolling();
        clearMessagePolling();
      };

      websocket.onmessage = event => {
        if (cancelled) {
          return;
        }
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'conversation_snapshot' || data.type === 'conversation_update') {
            const conversationList = Array.isArray(data.conversations) ? data.conversations : [];
            if (conversationList.length > 0) {
              const converted = mapConversationsToMessages(conversationList);
              setMessages(converted);
            }
            setIsTyping(false);
          }
        } catch (error) {
          console.error('Failed to parse websocket message:', error);
        }
      };

      websocket.onerror = error => {
        if (cancelled) {
          return;
        }
        console.error('Websocket error:', error);
        setIsWebsocketReady(false);
        if (userId) {
          startConversationPolling(userId);
        }
      };

      websocket.onclose = () => {
        if (websocketRef.current === websocket) {
          websocketRef.current = null;
        }
        if (cancelled) {
          return;
        }
        setIsWebsocketReady(false);
        setIsTyping(false);
        if (userId) {
          startConversationPolling(userId);
        }
      };

      return () => {
        cancelled = true;
        if (websocketRef.current === websocket) {
          websocketRef.current = null;
        }
        websocket.close();
      };
    } catch (error) {
      console.error('Failed to establish websocket connection:', error);
      setIsWebsocketReady(false);
      startConversationPolling(userId);
    }
  }, [
    userId,
    mapConversationsToMessages,
    clearConversationPolling,
    clearMessagePolling,
    startConversationPolling,
  ]);

  if (!userId) {
    return (
      <ConnectionSetup
        onConnectionEstablished={handleConnectionEstablished}
        notice={sessionNotice}
      />
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      <div className="bg-white border-b border-gray-300 px-6 py-4 flex items-center gap-4">
        <img src="/src/assets/voyager_health.svg" alt="Voyager Health" className="h-10" />
        <div className="flex-1">
          <h1 className="text-xl font-bold text-gray-900">Carl</h1>
          <p className="text-xs text-gray-600">Healthcare Assistant</p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-6 scrollbar-hide bg-gray-50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mb-6">
              <User className="w-10 h-10 text-blue-600" />
            </div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-3">Welcome to Carl</h3>
            <p className="text-gray-600 max-w-md">I'm your personal healthcare assistant. Ask me about your benefits, coverage, or any healthcare questions.</p>
          </div>
        ) : (
          <>
            {messages.map(message => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isLoading}
        placeholder="Ask Carl about your healthcare benefits, coverage, or questions..."
      />
    </div>
  );
}

export default App;
