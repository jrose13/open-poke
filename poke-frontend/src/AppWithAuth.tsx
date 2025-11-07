import { useState, useEffect, useRef } from 'react';
import { User } from 'lucide-react';
import { AuthForm } from './components/AuthForm';
import voyagerHealthLogo from './assets/voyager_health.svg';
import { ChatBubble } from './components/ChatBubble';
import { TypingIndicator } from './components/TypingIndicator';
import { MessageInput } from './components/MessageInput';
import { supabase } from './supabase';
import { useRealtimeMessages } from './hooks/useRealtimeMessages';
import type { Message } from './types';
import type { User as SupabaseUser } from '@supabase/supabase-js';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AppWithAuth() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      container.scrollTop = container.scrollHeight;
    }
  };

  // Scroll when messages change or typing indicator appears
  useEffect(() => {
    const timer = setTimeout(() => {
      scrollToBottom();
    }, 100);
    return () => clearTimeout(timer);
  }, [messages, isTyping]);

  // Initial scroll on mount
  useEffect(() => {
    scrollToBottom();
  }, []);

  // Check for existing session on mount
  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Load conversation history when user logs in
  useEffect(() => {
    if (!user) return;

    const loadConversations = async () => {
      try {
        const session = await supabase.auth.getSession();
        if (!session.data.session) return;

        const response = await fetch(`${API_BASE_URL}/conversations`, {
          headers: {
            Authorization: `Bearer ${session.data.session.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          const conversations = data.conversations || [];
          
          // Get the most recent conversation with messages
          if (conversations.length > 0) {
            const convId = conversations[0].id;
            setConversationId(convId);

            const msgResponse = await fetch(`${API_BASE_URL}/conversations/${convId}`, {
              headers: {
                Authorization: `Bearer ${session.data.session.access_token}`,
              },
            });

            if (msgResponse.ok) {
              const convData = await msgResponse.json();
              const formattedMessages: Message[] = (convData.messages || []).map((msg: any) => ({
                id: msg.id,
                content: msg.content,
                sender: msg.role === 'user' ? 'user' : 'agent',
                timestamp: new Date(msg.created_at),
              }));
              setMessages(formattedMessages);
              // Scroll after messages are loaded
              setTimeout(scrollToBottom, 200);
            }
          }
        }
      } catch (error) {
        console.error('Failed to load conversations:', error);
      }
    };

    loadConversations();
  }, [user]);

  // Subscribe to realtime messages
  useRealtimeMessages({
    conversationId,
    enabled: !!user && !!conversationId,
    onNewMessage: (newMessage) => {
      console.log('📨 Adding new message from Realtime:', newMessage);
      setMessages(prev => {
        // Avoid duplicates
        if (prev.some(m => m.id === newMessage.id)) {
          return prev;
        }
        return [...prev, newMessage];
      });
      setIsTyping(false);
    },
  });

  const handleAuthSuccess = () => {
    // User state will be updated by the auth state listener
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setMessages([]);
    setConversationId(null);
  };

  const handleSendMessage = async (content: string) => {
    if (!user) return;

    setIsSending(true);
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      content,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);

    try {
      const session = await supabase.auth.getSession();
      if (!session.data.session) {
        throw new Error('No active session');
      }

      const response = await fetch(`${API_BASE_URL}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.data.session.access_token}`,
        },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const result = await response.json();
      
      // Set conversation ID if we just created it
      if (result.conversation_id && !conversationId) {
        setConversationId(result.conversation_id);
      }

      // Show typing indicator
      setIsTyping(true);

      // Realtime subscription will handle the response automatically!
      // No more polling needed!

    } catch (error) {
      console.error('Failed to send message:', error);
      setIsTyping(false);
    } finally {
      setIsSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="text-center">
          <div className="flex items-center justify-center mx-auto mb-4">
            <img src={voyagerHealthLogo} alt="Voyager Health" className="h-12" />
          </div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthForm onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="bg-white border-b border-gray-200 px-4 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={voyagerHealthLogo} alt="Voyager Health" className="h-8" />
        </div>
        <button
          onClick={handleSignOut}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          Sign Out
        </button>
      </div>

      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-4 scrollbar-hide">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <User className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Welcome to Voyager Health!
            </h3>
            <p className="text-gray-500 max-w-sm">
              Your healthcare conversations are securely saved and will persist across sessions.
            </p>
          </div>
        ) : (
          <>
            {messages.map(message => (
              <ChatBubble key={message.id} message={message} />
            ))}
            {isTyping && <TypingIndicator />}
          </>
        )}
      </div>

      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={isSending}
        placeholder="Ask about your health, symptoms, or medical questions..."
      />
    </div>
  );
}

export default AppWithAuth;
