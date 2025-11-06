import { useEffect } from 'react';
import { supabase } from '../supabase';
import type { Message } from '../types';

interface UseRealtimeMessagesProps {
  conversationId: string | null;
  onNewMessage: (message: Message) => void;
  enabled: boolean;
}

export function useRealtimeMessages({ 
  conversationId, 
  onNewMessage, 
  enabled 
}: UseRealtimeMessagesProps) {
  useEffect(() => {
    if (!enabled || !conversationId) {
      return;
    }

    // Subscribe to new messages in this conversation
    const channel = supabase
      .channel(`messages-${conversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${conversationId}`,
        },
        (payload) => {
          console.log('📨 Realtime message received:', payload);
          
          // Transform database message to our Message type
          const newMessage: Message = {
            id: payload.new.id,
            content: payload.new.content,
            sender: payload.new.role === 'user' ? 'user' : 'agent',
            timestamp: new Date(payload.new.created_at),
          };

          // Only add if it's an assistant message (user messages already in state)
          if (newMessage.sender === 'agent') {
            onNewMessage(newMessage);
          }
        }
      )
      .subscribe((status) => {
        console.log('📡 Subscription status:', status);
      });

    // Cleanup on unmount
    return () => {
      console.log('🔌 Unsubscribing from messages channel');
      supabase.removeChannel(channel);
    };
  }, [conversationId, onNewMessage, enabled]);
}

