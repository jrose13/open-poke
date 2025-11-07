import { useState } from 'react';
import { Send } from 'lucide-react';
import { clsx } from 'clsx';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function MessageInput({ onSendMessage, disabled = false, placeholder = "Type a message..." }: MessageInputProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-3 p-4 bg-white border-t border-gray-300">
      <div className="flex-1 relative">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          className={clsx(
            "w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 transition-all",
            "min-h-[44px] max-h-32 scrollbar-hide text-gray-900",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          rows={1}
          style={{
            height: 'auto',
            minHeight: '44px',
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = 'auto';
            target.style.height = Math.min(target.scrollHeight, 128) + 'px';
          }}
        />
      </div>
      
      <button
        type="submit"
        disabled={!message.trim() || disabled}
        className={clsx(
          "p-3 rounded-xl transition-all flex items-center justify-center shadow-sm",
          message.trim() && !disabled
            ? "bg-blue-600 text-white hover:bg-blue-700 shadow-md" 
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        )}
      >
        <Send className="w-5 h-5" />
      </button>
    </form>
  );
}