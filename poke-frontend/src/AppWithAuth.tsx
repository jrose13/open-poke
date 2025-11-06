import { useState, useEffect } from 'react';
import { User } from 'lucide-react';
import { AuthForm } from './components/AuthForm';
import { ChatBubble } from './components/ChatBubble';
import { TypingIndicator } from './components/TypingIndicator';
import { MessageInput } from './components/MessageInput';
import { supabase } from './supabase';
import type { Message } from './types';
import type { User as SupabaseUser } from '@supabase/supabase-js';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function AppWithAuth() {
  const [user, setUser] = useState<SupabaseUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isSending, setIsSending] = useState(false);

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
            }
          }
        }
      } catch (error) {
        console.error('Failed to load conversations:', error);
      }
    };

    loadConversations();
  }, [user]);

  const handleAuthSuccess = () => {
    // User state will be updated by the auth state listener
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setMessages([]);
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
      setIsTyping(true);

      // Poll for response
      const pollForResponse = async () => {
        try {
          const session = await supabase.auth.getSession();
          if (!session.data.session) return;

          const responseData = await fetch(
            `${API_BASE_URL}/messages/${result.message_id}/response`,
            {
              headers: {
                Authorization: `Bearer ${session.data.session.access_token}`,
              },
            }
          );

          if (responseData.ok) {
            const data = await responseData.json();

            if (data.status === 'completed') {
              const agentMessage: Message = {
                id: `msg_${Date.now()}`,
                content: data.response,
                sender: 'agent',
                timestamp: new Date(),
              };
              setMessages(prev => [...prev, agentMessage]);
              setIsTyping(false);
            } else if (data.status === 'error') {
              setIsTyping(false);
            } else {
              // Still processing, poll again
              setTimeout(pollForResponse, 2000);
            }
          }
        } catch (error) {
          console.error('Polling error:', error);
          setIsTyping(false);
        }
      };

      setTimeout(pollForResponse, 1000);
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
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🌴</span>
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
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <span className="text-lg">🌴</span>
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">Poke AI</h1>
            <p className="text-sm text-gray-500">AI Email Analyst</p>
          </div>
        </div>
        <button
          onClick={handleSignOut}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          Sign Out
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 scrollbar-hide">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <User className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Welcome to Open Poke!
            </h3>
            <p className="text-gray-500 max-w-sm">
              Your conversations are now saved and will persist across sessions.
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
        placeholder="Ask Poke about your email patterns, contacts, or insights..."
      />
    </div>
  );
}

export default AppWithAuth;

