import { useState, useEffect, useRef, useCallback } from 'react';
import { Mail, User, Loader2, ExternalLink, AlertTriangle } from 'lucide-react';
import { apiClient } from '../api';

interface ConnectionSetupProps {
  onConnectionEstablished: (userId: string) => void;
  notice?: string | null;
}

const POLL_INTERVAL_MS = 4000;

export function ConnectionSetup({ onConnectionEstablished, notice }: ConnectionSetupProps) {
  const [step, setStep] = useState<'user-info' | 'connecting' | 'auth'>('user-info');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authChecking, setAuthChecking] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [userInfo, setUserInfo] = useState({
    name: '',
  });
  const [connectionData, setConnectionData] = useState<{
    userId: string;
    redirectUrl?: string;
    connectionId?: string;
  } | null>(null);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const popupRef = useRef<Window | null>(null);
  const CONNECTION_STORAGE_KEY = 'poke_connection_data';

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const completeConnection = useCallback(
    (userId: string) => {
      stopPolling();
      setPendingStatus(null);
      setError(null);
      if (popupRef.current && !popupRef.current.closed) {
        try {
          popupRef.current.close();
        } catch (err) {
          console.warn('Failed to close Composio popup:', err);
        }
      }
      popupRef.current = null;
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(CONNECTION_STORAGE_KEY);
        try {
          window.focus();
        } catch (err) {
          /* noop */
        }
      }
      setConnectionData(null);
      onConnectionEstablished(userId);
    },
    [onConnectionEstablished, stopPolling],
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedConnection = window.localStorage.getItem(CONNECTION_STORAGE_KEY);
    if (!storedConnection) return;

    try {
      const parsed = JSON.parse(storedConnection);
      if (parsed?.userId && parsed?.connectionId) {
        setConnectionData(parsed);
        setStep('auth');
      } else {
        window.localStorage.removeItem(CONNECTION_STORAGE_KEY);
      }
    } catch (storageError) {
      window.localStorage.removeItem(CONNECTION_STORAGE_KEY);
      console.error('Failed to parse stored connection data', storageError);
    }
  }, []);

  const handleUserInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInfo.name) return;

    setLoading(true);
    setError(null);
    setPendingStatus(null);

    try {
      const userId = `user_${Date.now()}`;
      await apiClient.createUser(userId, userInfo.name);

      const connectionResult = await apiClient.initiateConnection(userId);

      const connectionDetails = {
        userId,
        redirectUrl: connectionResult.redirect_url,
        connectionId: connectionResult.connection_id,
      };

      setConnectionData(connectionDetails);
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(CONNECTION_STORAGE_KEY, JSON.stringify(connectionDetails));
      }

      if (connectionResult.redirect_url) {
        setStep('auth');
      } else {
        completeConnection(userId);
      }
    } catch (err) {
      console.error('Failed to set up connection:', err);
      setError(err instanceof Error ? err.message : 'Failed to set up connection');
    } finally {
      setLoading(false);
    }
  };

  const checkConnectionStatus = async () => {
    if (!connectionData?.connectionId || !connectionData?.userId) return;

    try {
      setAuthChecking(true);
      const status = await apiClient.checkConnectionStatus(connectionData.connectionId);
      const normalizedStatus = (status.status ?? '').toString().toUpperCase();

      if (normalizedStatus === 'ACTIVE' || normalizedStatus === 'CONNECTED') {
        completeConnection(connectionData.userId);
      } else {
        const readable = normalizedStatus || 'PENDING';
        setPendingStatus(`Waiting for Composio confirmation… Current status: ${readable}`);
        setError(null);
      }
    } catch (err) {
      console.error('Failed to check connection status:', err);
      setError('Failed to check connection status');
      setPendingStatus(null);
    } finally {
      setAuthChecking(false);
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
      if (popupRef.current && !popupRef.current.closed) {
        try {
          popupRef.current.close();
        } catch (err) {
          console.warn('Failed to close Composio popup during cleanup:', err);
        }
      }
      popupRef.current = null;
    };
  }, [stopPolling]);

  useEffect(() => {
    if (step !== 'auth' || !connectionData?.connectionId || !connectionData?.userId) {
      setPendingStatus(null);
      stopPolling();
      return;
    }

    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      try {
        setAuthChecking(true);
        setPendingStatus(prev => prev ?? 'Waiting for Composio confirmation…');
        const status = await apiClient.checkConnectionStatus(connectionData.connectionId!);
        if (cancelled) return;

        const normalizedStatus = (status.status ?? '').toString().toUpperCase();

        if (normalizedStatus === 'ACTIVE' || normalizedStatus === 'CONNECTED') {
          completeConnection(connectionData.userId);
        } else {
          const readable = normalizedStatus || 'PENDING';
          setPendingStatus(`Waiting for Composio confirmation… Current status: ${readable}`);
          setError(null);
        }
      } catch (err) {
        if (cancelled) return;
        console.error('Automatic connection status check failed:', err);
        setError('Failed to check connection status');
        setPendingStatus(null);
      } finally {
        if (!cancelled) {
          setAuthChecking(false);
        }
      }
    };

    poll();
    pollingRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [step, connectionData?.connectionId, connectionData?.userId, completeConnection, stopPolling]);

  if (step === 'user-info') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-white p-4">
        <div className="w-full max-w-md bg-white rounded-xl shadow-md border border-gray-200 p-8">
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Mail className="w-10 h-10 text-blue-600" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Welcome to Carl</h1>
            <p className="text-sm text-gray-600">Your Healthcare Assistant</p>
          </div>

          {notice && (
            <div className="mb-5 flex items-start gap-2 rounded-xl border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
              <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{notice}</span>
            </div>
          )}

          <form onSubmit={handleUserInfoSubmit} className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  id="name"
                  value={userInfo.name}
                  onChange={e => setUserInfo({ ...userInfo, name: e.target.value })}
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter your full name"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !userInfo.name}
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-sm"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Connecting...
                </>
              ) : (
                'Connect Gmail'
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (step === 'auth') {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-white p-4">
        <div className="w-full max-w-md bg-white rounded-xl shadow-md border border-gray-200 p-8 text-center">
          <div className="w-20 h-20 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <ExternalLink className="w-10 h-10 text-green-600" />
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-4">Authorize Gmail Access</h2>
          <p className="text-gray-600 mb-6">Authorize Carl in the new tab, then we'll drop you into chat once Composio confirms.</p>

          <div className="space-y-4">
            {connectionData?.redirectUrl && (
              <button
                onClick={() => {
                  if (!connectionData.redirectUrl) return;
                  try {
                    const popup = window.open(
                      connectionData.redirectUrl,
                      'composio-auth',
                      'width=520,height=720,menubar=0,toolbar=0'
                    );
                    if (popup) {
                      popupRef.current = popup;
                      popup.focus();
                    } else {
                      window.location.href = connectionData.redirectUrl;
                    }
                  } catch (err) {
                    console.error('Failed to open Composio auth window:', err);
                    window.location.href = connectionData.redirectUrl;
                  }
                }}
                className="w-full bg-blue-600 text-white py-3 px-4 rounded-xl font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-center gap-2"
              >
                <ExternalLink className="w-5 h-5" />
                Authorize Gmail Access
              </button>
            )}

            <button
              onClick={checkConnectionStatus}
              disabled={authChecking}
              className="w-full bg-gray-100 text-gray-700 py-3 px-4 rounded-xl font-medium hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              {authChecking ? 'Checking authorization…' : 'Refresh status now'}
            </button>
          </div>

          {pendingStatus && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{pendingStatus}</span>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>
      </div>
    );
  }

  return null;
}
